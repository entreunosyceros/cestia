"""Cliente de búsqueda Dia (API search-back no oficial)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from cestia.cliente.limite_y_cache import CacheDisco, LimitadorPeticiones
from cestia.configuracion import obtener_configuracion

registrador = logging.getLogger(__name__)

URL_BUSQUEDA = "https://www.dia.es/api/v1/search-back/search"
PREFIJO_ID = "di:"
URL_IMAGEN = "https://www.dia.es"


class ErrorAPIDia(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteDia:
    """Búsqueda de productos en Dia.es vía search-back."""

    def __init__(self) -> None:
        cfg = obtener_configuracion()
        self.cache = CacheDisco(cfg.directorio_cache)
        self.limitador = LimitadorPeticiones(cfg.limite_peticiones_por_minuto)
        self.timeout = cfg.timeout_http
        self.agente = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def buscar(self, consulta: str, *, limite: int = 24) -> list[dict[str, Any]]:
        consulta = consulta.strip()
        if not consulta:
            return []

        clave = f"dia:v3:busqueda:{consulta.lower()}:{limite}"
        acierto = self.cache.obtener(clave)
        if acierto is not None:
            return acierto

        self.limitador.adquirir()
        parametros = {
            "q": consulta,
            "page": 0,
            "page_size": max(1, min(limite, 30)),
        }
        url = f"{URL_BUSQUEDA}?{urlencode(parametros)}"
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "es-ES,es;q=0.9",
                    "User-Agent": self.agente,
                    "Referer": f"https://www.dia.es/search?q={consulta}",
                    "Origin": "https://www.dia.es",
                },
            ) as cliente:
                respuesta = cliente.get(url)
        except httpx.HTTPError as exc:
            raise ErrorAPIDia(f"Error de red Dia: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPIDia(
                f"HTTP {respuesta.status_code} en búsqueda Dia",
                codigo_estado=respuesta.status_code,
            )
        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise ErrorAPIDia("Respuesta Dia no JSON") from exc

        if isinstance(datos, dict) and datos.get("code") == 404:
            raise ErrorAPIDia(datos.get("message") or "API Dia no encontrada")

        productos = [
            normalizar_hit_dia(item)
            for item in (datos.get("search_items") or [])
        ]
        productos = [p for p in productos if p.get("nombre")][:limite]
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos


def _url_absoluta(ruta: str | None) -> str | None:
    if not ruta:
        return None
    if ruta.startswith("http"):
        return ruta
    if not ruta.startswith("/"):
        ruta = "/" + ruta
    return f"{URL_IMAGEN}{ruta}"


def _url_miniatura(ruta: str | None) -> str | None:
    """Miniatura reducida: las fichas Dia a tamaño completo (~2400px) fallan en la UI."""
    url = _url_absoluta(ruta)
    if not url:
        return None
    if "product_images" in url and "imwidth=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}imwidth=200"
    return url


def normalizar_hit_dia(item: dict[str, Any]) -> dict[str, Any]:
    from cestia.normalizacion import inferir_marca

    pid = str(item.get("sku_id") or item.get("object_id") or "")
    nombre = item.get("display_name") or item.get("name") or "Producto Dia"
    precios = item.get("prices") or {}
    try:
        precio_unidad = float(precios.get("price")) if precios.get("price") is not None else None
    except (TypeError, ValueError):
        precio_unidad = None
    try:
        precio_bulto = (
            float(precios.get("price_per_unit"))
            if precios.get("price_per_unit") is not None
            else None
        )
    except (TypeError, ValueError):
        precio_bulto = None

    anterior = None
    try:
        strike = precios.get("strikethrough_price")
        if strike is not None and precio_unidad is not None and float(strike) > precio_unidad:
            anterior = float(strike)
    except (TypeError, ValueError):
        pass

    ruta = item.get("url") or ""
    url = _url_absoluta(ruta) if ruta else None
    miniatura = _url_miniatura(item.get("image"))
    marca = inferir_marca(nombre, item.get("brand"), fallback="Dia")
    formato = (precios.get("measure_unit") or "").strip().lower()
    if formato in {"litro", "litros"}:
        formato = "l"
    elif formato in {"kilo", "kilogramo", "kg"}:
        formato = "kg"
    elif formato in {"gramo", "gramos", "g"}:
        formato = "g"

    return {
        "id": f"{PREFIJO_ID}{pid}",
        "id_externo": pid,
        "ean": item.get("ean") or item.get("ean13"),
        "nombre": nombre,
        "marca": marca,
        "envase": "",
        "categoria": item.get("l2_category_description")
        or item.get("l1_category_description"),
        "miniatura": miniatura,
        "url_compartir": url,
        "precio_unidad": precio_unidad,
        "precio_bulto": precio_bulto,
        "precio_unidad_anterior": anterior,
        "tamano_unidad": None,
        "formato_tamano": formato,
        "tienda": "dia",
        "origen": "dia",
        "name": nombre,
        "brand": marca,
        "thumbnail": miniatura,
        "unit_price": precio_unidad,
        "bulk_price": precio_bulto,
        "previous_unit_price": anterior,
        "size_format": formato,
        "unit_size": None,
        "share_url": url,
    }


def es_id_dia(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_di: ClienteDia | None = None


def obtener_cliente_dia() -> ClienteDia:
    global _cliente_di
    if _cliente_di is None:
        _cliente_di = ClienteDia()
    return _cliente_di
