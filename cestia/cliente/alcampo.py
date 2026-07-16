"""Cliente de búsqueda Alcampo (compraonline.alcampo.es, API no oficial)."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote

import httpx

from cestia.cliente.limite_y_cache import CacheDisco, LimitadorPeticiones
from cestia.configuracion import obtener_configuracion

registrador = logging.getLogger(__name__)

URL_BUSQUEDA = "https://www.compraonline.alcampo.es/search?q={consulta}"
PREFIJO_ID = "ac:"


class ErrorAPIAlcampo(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteAlcampo:
    """Búsqueda de productos en Alcampo vía estado inicial de la web."""

    def __init__(self) -> None:
        cfg = obtener_configuracion()
        self.cache = CacheDisco(cfg.directorio_cache)
        self.limitador = LimitadorPeticiones(cfg.limite_peticiones_por_minuto)
        self.timeout = cfg.timeout_http
        self.agente = cfg.agente_usuario

    def buscar(self, consulta: str, *, limite: int = 24) -> list[dict[str, Any]]:
        consulta = consulta.strip()
        if not consulta:
            return []

        clave = f"alcampo:v2:busqueda:{consulta.lower()}:{limite}"
        acierto = self.cache.obtener(clave)
        if acierto is not None:
            return acierto

        self.limitador.adquirir()
        url = URL_BUSQUEDA.format(consulta=quote(consulta))
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": self.agente,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "es-ES,es;q=0.9",
                },
            ) as cliente:
                respuesta = cliente.get(url)
        except httpx.HTTPError as exc:
            raise ErrorAPIAlcampo(f"Error de red Alcampo: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPIAlcampo(
                f"HTTP {respuesta.status_code} en búsqueda Alcampo",
                codigo_estado=respuesta.status_code,
            )

        try:
            estado = _extraer_estado_inicial(respuesta.text)
        except ErrorAPIAlcampo:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ErrorAPIAlcampo(f"No se pudo leer el catálogo Alcampo: {exc}") from exc

        productos = _productos_desde_estado(estado, limite=limite)
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos


def _extraer_estado_inicial(html: str) -> dict[str, Any]:
    marca = "window.__INITIAL_STATE__"
    pos = html.find(marca)
    if pos < 0:
        raise ErrorAPIAlcampo("Respuesta Alcampo sin estado de productos")
    igual = html.find("=", pos)
    if igual < 0:
        raise ErrorAPIAlcampo("Estado inicial Alcampo mal formado")
    inicio = igual + 1
    while inicio < len(html) and html[inicio].isspace():
        inicio += 1
    try:
        obj, _ = json.JSONDecoder().raw_decode(html[inicio:])
    except json.JSONDecodeError as exc:
        raise ErrorAPIAlcampo("JSON de estado Alcampo inválido") from exc
    if not isinstance(obj, dict):
        raise ErrorAPIAlcampo("Estado Alcampo inesperado")
    return obj


def _productos_desde_estado(
    estado: dict[str, Any], *, limite: int
) -> list[dict[str, Any]]:
    data = estado.get("data") or {}
    entidades = (
        ((data.get("products") or {}).get("productEntities")) or {}
    )
    grupos = (
        ((((data.get("search") or {}).get("catalogue") or {}).get("data") or {}).get(
            "productGroups"
        ))
        or []
    )
    ids_ordenados: list[str] = []
    vistos: set[str] = set()
    for grupo in grupos:
        for pid in grupo.get("products") or []:
            if not isinstance(pid, str) or pid in vistos:
                continue
            vistos.add(pid)
            ids_ordenados.append(pid)

    if not ids_ordenados:
        ids_ordenados = list(entidades.keys())

    resultados: list[dict[str, Any]] = []
    for pid in ids_ordenados:
        if len(resultados) >= limite:
            break
        bruto = entidades.get(pid)
        if not isinstance(bruto, dict):
            continue
        resultados.append(normalizar_producto_alcampo(bruto))
    return resultados


def normalizar_producto_alcampo(item: dict[str, Any]) -> dict[str, Any]:
    rid = str(item.get("retailerProductId") or item.get("productId") or "")
    precio_info = item.get("price") or {}
    actual = (precio_info.get("current") or {}).get("amount")
    unidad = ((precio_info.get("unit") or {}).get("current") or {}).get("amount")
    try:
        precio_unidad = float(actual) if actual not in (None, "") else None
    except (TypeError, ValueError):
        precio_unidad = None
    try:
        precio_bulto = float(unidad) if unidad not in (None, "") else None
    except (TypeError, ValueError):
        precio_bulto = None

    imagen = item.get("image") or {}
    miniatura = imagen.get("src") if isinstance(imagen, dict) else None
    cats = item.get("categoryPath") or []
    tamano = item.get("size")
    if isinstance(tamano, dict):
        envase = str(tamano.get("value") or "").strip()
    else:
        envase = str(tamano or "").strip()
    etiqueta_unidad = ((precio_info.get("unit") or {}).get("label") or "")
    formato = ""
    if "litre" in etiqueta_unidad or "litro" in etiqueta_unidad:
        formato = "l"
    elif "kilo" in etiqueta_unidad or "kg" in etiqueta_unidad:
        formato = "kg"

    url = f"https://www.compraonline.alcampo.es/products/{rid}" if rid else None
    nombre = item.get("name") or "Producto Alcampo"
    marca = item.get("brand")
    if isinstance(marca, dict):
        marca = marca.get("name") or marca.get("value")
    return {
        "id": f"{PREFIJO_ID}{rid}",
        "id_externo": rid,
        "ean": None,
        "nombre": nombre,
        "marca": marca,
        "envase": envase,
        "categoria": cats[0] if cats else None,
        "miniatura": miniatura,
        "url_compartir": url,
        "precio_unidad": precio_unidad,
        "precio_bulto": precio_bulto,
        "tamano_unidad": None,
        "formato_tamano": formato or None,
        "tienda": "alcampo",
        "origen": "alcampo",
        "name": nombre,
        "brand": marca,
        "thumbnail": miniatura,
        "unit_price": precio_unidad,
        "bulk_price": precio_bulto,
        "size_format": formato or None,
        "share_url": url,
    }


def es_id_alcampo(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_ac: ClienteAlcampo | None = None


def obtener_cliente_alcampo() -> ClienteAlcampo:
    global _cliente_ac
    if _cliente_ac is None:
        _cliente_ac = ClienteAlcampo()
    return _cliente_ac
