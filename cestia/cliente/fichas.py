"""Datos ampliados de ficha (EAN, Nutri-Score, nutrición) desde cada tienda."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from cestia.cliente.froiz import URL_PRODUCTO as URL_FROIZ
from cestia.cliente.limite_y_cache import CacheDisco
from cestia.configuracion import obtener_configuracion
from cestia.enriquecimiento import quitar_html

registrador = logging.getLogger(__name__)

_AGENTE = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def normalizar_grado_nutriscore(valor: Any) -> str | None:
    grado = (str(valor or "")).strip().upper()
    if grado in {"A", "B", "C", "D", "E"}:
        return grado
    return None


def _ean_valido(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = re.sub(r"\D", "", str(valor))
    if len(texto) in {8, 12, 13, 14} and texto != "0" * len(texto):
        return texto
    return None


def _extraer_ean_html(html: str) -> str | None:
    for patron in (
        r'"gtin13"\s*:\s*\[\s*"(\d{8,14})"',
        r'"gtin13"\s*:\s*"(\d{8,14})"',
        r'"ean13"\s*:\s*"(\d{8,14})"',
        r'"ean"\s*:\s*"(\d{8,14})"',
        r'"gtin"\s*:\s*"(\d{8,14})"',
        r"EAN[^0-9]{0,12}(\d{8,14})",
    ):
        coincidencia = re.search(patron, html, re.I)
        if coincidencia:
            ean = _ean_valido(coincidencia.group(1))
            if ean:
                return ean
    return None


def _extraer_nutriscore_html(html: str) -> str | None:
    for patron in (
        r'"nutriscore(?:_grade)?"\s*:\s*"([A-Ea-e])"',
        r'"nutritionGrade"\s*:\s*"([A-Ea-e])"',
        r'"nutri_score"\s*:\s*"([A-Ea-e])"',
        r"Nutri-Score[^A-E]{0,24}([A-E])\b",
    ):
        coincidencia = re.search(patron, html, re.I)
        if coincidencia:
            grado = normalizar_grado_nutriscore(coincidencia.group(1))
            if grado:
                return grado
    return None


def _nutricion_desde_dia(prod: dict[str, Any]) -> dict[str, Any]:
    info = prod.get("nutritional_info") or {}
    valores = info.get("nutritional_values") or {}
    resultado: dict[str, Any] = {
        "energia_kcal": valores.get("energy_value"),
        "nutricion_por": "100g",
    }
    for bloque in valores.get("values") or []:
        if not isinstance(bloque, dict):
            continue
        titulo = (bloque.get("title") or "").casefold()
        cantidad = bloque.get("value_per_100_g")
        if cantidad is None:
            cantidad = bloque.get("value")
        if "grasa" in titulo:
            resultado["grasas"] = cantidad
        elif "hidrat" in titulo or "carboh" in titulo:
            resultado["hidratos"] = cantidad
        elif "fibra" in titulo:
            resultado["fibra"] = cantidad
        elif "prote" in titulo:
            resultado["proteinas"] = cantidad
        elif titulo == "sal" or titulo.startswith("sal "):
            resultado["sal"] = cantidad
        for sub in bloque.get("items") or []:
            if not isinstance(sub, dict):
                continue
            subtitulo = (sub.get("title") or "").casefold()
            subvalor = sub.get("value_per_100_g")
            if subvalor is None:
                subvalor = sub.get("value")
            if "azúcar" in subtitulo or "azucar" in subtitulo:
                resultado["azucares"] = subvalor
    return resultado


def _ficha_dia(registro: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    sku = registro.get("id_externo") or str(registro.get("id", "")).split(":", 1)[-1]
    if not sku:
        return {}
    referer = registro.get("url_compartir") or "https://www.dia.es/"
    url = f"https://www.dia.es/api/v1/pdp-back/{sku}"
    with httpx.Client(timeout=timeout) as cliente:
        respuesta = cliente.get(
            url,
            headers={
                "User-Agent": _AGENTE,
                "Accept": "application/json",
                "Referer": referer,
            },
        )
    if respuesta.status_code >= 400:
        return {}
    prod = (respuesta.json() or {}).get("product") or {}
    if not prod:
        return {}

    ficha: dict[str, Any] = {}
    grado = normalizar_grado_nutriscore(prod.get("nutri_score"))
    if grado:
        ficha["nutriscore"] = grado

    ingredientes = prod.get("ingredients") or {}
    if isinstance(ingredientes, dict) and ingredientes.get("text"):
        ficha["ingredientes"] = quitar_html(ingredientes.get("text"))

    alergenos = prod.get("allergens")
    if isinstance(alergenos, list):
        nombres = [
            str(item.get("name") or "").strip()
            for item in alergenos
            if isinstance(item, dict) and item.get("name")
        ]
        if nombres:
            ficha["alergenos"] = ", ".join(nombres)

    ficha.update(_nutricion_desde_dia(prod))
    return ficha


def _ficha_froiz(registro: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    slug = registro.get("slug")
    if not slug:
        url = registro.get("url_compartir") or ""
        if "/product/" in url:
            slug = url.rstrip("/").split("/product/")[-1]
    if not slug:
        return {}

    url = URL_FROIZ.format(slug=slug)
    with httpx.Client(timeout=timeout, follow_redirects=True) as cliente:
        respuesta = cliente.get(
            url,
            headers={
                "User-Agent": _AGENTE,
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://supermercado.froiz.com/",
            },
        )
    if respuesta.status_code >= 400:
        return {}

    html = respuesta.text
    ficha: dict[str, Any] = {}

    ean = _extraer_ean_html(html)
    if ean:
        ficha["ean"] = ean

    grado = _extraer_nutriscore_html(html)
    if grado:
        ficha["nutriscore"] = grado

    coincidencia = re.search(
        r'ingredients_and_allergens:"((?:\\.|[^"\\])*)"',
        html,
    )
    if coincidencia:
        ficha["ingredientes"] = coincidencia.group(1).strip()

    coincidencia = re.search(r'allergens:"((?:\\.|[^"\\])*)"', html)
    if coincidencia:
        texto = coincidencia.group(1).strip()
        if texto and texto != ficha.get("ingredientes"):
            ficha["alergenos"] = texto

    return ficha


def _ficha_lidl(registro: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    url = registro.get("url_compartir")
    if not url:
        return {}
    with httpx.Client(timeout=timeout, follow_redirects=True) as cliente:
        respuesta = cliente.get(
            url,
            headers={
                "User-Agent": _AGENTE,
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://www.lidl.es/",
            },
        )
    if respuesta.status_code >= 400:
        return {}

    html = respuesta.text
    ficha: dict[str, Any] = {}
    ean = _extraer_ean_html(html)
    if ean:
        ficha["ean"] = ean
    grado = _extraer_nutriscore_html(html)
    if grado:
        ficha["nutriscore"] = grado
    return ficha


def _ficha_alcampo(registro: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    url = registro.get("url_compartir")
    if not url:
        return {}
    with httpx.Client(timeout=timeout, follow_redirects=True) as cliente:
        respuesta = cliente.get(
            url,
            headers={
                "User-Agent": _AGENTE,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "es-ES,es;q=0.9",
            },
        )
    if respuesta.status_code >= 400:
        return {}

    html = respuesta.text
    ficha: dict[str, Any] = {}
    if "window.__INITIAL_STATE__" in html:
        try:
            from cestia.cliente.alcampo import _extraer_estado_inicial

            estado = _extraer_estado_inicial(html)
            texto = json.dumps(estado, ensure_ascii=False)
            ean = _extraer_ean_html(texto)
            if ean:
                ficha["ean"] = ean
            grado = _extraer_nutriscore_html(texto)
            if grado:
                ficha["nutriscore"] = grado
        except Exception as exc:  # noqa: BLE001
            registrador.debug("Estado Alcampo no legible: %s", exc)

    if not ficha.get("ean"):
        ean = _extraer_ean_html(html)
        if ean:
            ficha["ean"] = ean
    if not ficha.get("nutriscore"):
        grado = _extraer_nutriscore_html(html)
        if grado:
            ficha["nutriscore"] = grado
    return ficha


def _ficha_carrefour(registro: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    if _ean_valido(registro.get("ean")):
        return {}
    url = registro.get("url_compartir")
    if not url:
        return {}
    with httpx.Client(timeout=timeout, follow_redirects=True) as cliente:
        respuesta = cliente.get(
            url,
            headers={
                "User-Agent": _AGENTE,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": "https://www.carrefour.es/",
            },
        )
    if respuesta.status_code >= 400:
        return {}

    html = respuesta.text
    ficha: dict[str, Any] = {}
    ean = _extraer_ean_html(html)
    if ean:
        ficha["ean"] = ean
    grado = _extraer_nutriscore_html(html)
    if grado:
        ficha["nutriscore"] = grado
    return ficha


_DISPATCH: dict[str, Any] = {
    "dia": _ficha_dia,
    "froiz": _ficha_froiz,
    "lidl": _ficha_lidl,
    "alcampo": _ficha_alcampo,
    "carrefour": _ficha_carrefour,
}


def obtener_ficha_tienda(registro: dict[str, Any]) -> dict[str, Any]:
    """Consulta la ficha de la tienda y devuelve campos nutricionales conocidos."""
    tienda = (registro.get("tienda") or registro.get("origen") or "").strip().lower()
    funcion = _DISPATCH.get(tienda)
    if funcion is None:
        return {}

    cfg = obtener_configuracion()
    cache = CacheDisco(cfg.directorio_cache)
    clave = f"ficha:{tienda}:{registro.get('id')}"
    acierto = cache.obtener(clave)
    if isinstance(acierto, dict):
        return acierto

    try:
        ficha = funcion(registro, timeout=cfg.timeout_http) or {}
    except httpx.HTTPError as exc:
        registrador.info("Ficha %s falló (red): %s", tienda, exc)
        ficha = {}
    except Exception as exc:  # noqa: BLE001
        registrador.info("Ficha %s falló: %s", tienda, exc)
        ficha = {}

    if isinstance(ficha.get("ean"), str):
        ficha["ean"] = _ean_valido(ficha["ean"])
    if ficha.get("nutriscore"):
        ficha["nutriscore"] = normalizar_grado_nutriscore(ficha["nutriscore"])

    cache.guardar(clave, ficha, cfg.ttl_cache_productos)
    return ficha


def fusionar_ficha(
    registro: dict[str, Any], ficha: dict[str, Any]
) -> dict[str, Any]:
    """Combina datos de ficha en el registro sin pisar valores ya presentes."""
    if not ficha:
        return registro

    if ficha.get("ean") and not registro.get("ean"):
        registro["ean"] = ficha["ean"]
    if ficha.get("nutriscore") and not registro.get("nutriscore"):
        registro["nutriscore"] = ficha["nutriscore"]
    if ficha.get("ingredientes") and not registro.get("ingredientes"):
        registro["ingredientes"] = ficha["ingredientes"]
    if ficha.get("alergenos") and not registro.get("alergenos"):
        registro["alergenos"] = ficha["alergenos"]

    for clave in (
        "energia_kcal",
        "proteinas",
        "hidratos",
        "grasas",
        "fibra",
        "azucares",
        "sal",
        "nutricion_por",
    ):
        if ficha.get(clave) is not None and registro.get(clave) is None:
            registro[clave] = ficha[clave]
    return registro
