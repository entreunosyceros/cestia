"""Cliente de búsqueda Lidl ES (API pública de búsqueda en lidl.es)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from cestia.cliente.limite_y_cache import CacheDisco, LimitadorPeticiones
from cestia.configuracion import obtener_configuracion
from cestia.normalizacion import coincide_consulta, inferir_marca

registrador = logging.getLogger(__name__)

URL_BUSQUEDA = "https://www.lidl.es/q/api/search"
PREFIJO_ID = "ld:"


class ErrorAPILidl(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteLidl:
    """Búsqueda de productos en Lidl España."""

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

        clave = f"lidl:v3:busqueda:{consulta.lower()}:{limite}"
        acierto = self.cache.obtener(clave)
        if acierto is not None:
            return acierto

        self.limitador.adquirir()
        # Pedimos de más: luego filtramos ruido (bricolaje, juguetes, etc.).
        fetch = max(1, min(max(limite * 2, 24), 48))
        parametros = {
            "assortment": "ES",
            "locale": "es_ES",
            "version": "v2.0.0",
            "q": consulta,
            "sort": "relevancy",
            "fetchsize": fetch,
        }
        url = f"{URL_BUSQUEDA}?{urlencode(parametros)}"
        try:
            with httpx.Client(timeout=self.timeout) as cliente:
                respuesta = cliente.get(
                    url,
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "es-ES,es;q=0.9",
                        "User-Agent": self.agente,
                        "Referer": f"https://www.lidl.es/q/search?q={consulta}",
                        "Origin": "https://www.lidl.es",
                    },
                )
        except httpx.HTTPError as exc:
            raise ErrorAPILidl(f"Error de red Lidl: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPILidl(
                f"HTTP {respuesta.status_code} en búsqueda Lidl",
                codigo_estado=respuesta.status_code,
            )
        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise ErrorAPILidl("Respuesta Lidl no JSON") from exc

        if datos.get("status") and datos.get("status") >= 400:
            raise ErrorAPILidl(
                datos.get("error") or f"Error Lidl HTTP {datos.get('status')}",
                codigo_estado=datos.get("status"),
            )

        brutos: list[tuple[dict[str, Any], bool]] = []
        for item in datos.get("items") or []:
            if item.get("resultClass") != "product" and item.get("type") != "product":
                continue
            grid = (item.get("gridbox") or {}).get("data") or {}
            hit = normalizar_hit_lidl(item)
            if hit.get("precio_unidad") is None:
                continue
            if not coincide_consulta(consulta, hit.get("nombre")):
                continue
            brutos.append((hit, _es_alimentacion_lidl(grid)))

        alimentos = [h for h, food in brutos if food]
        elegidos = alimentos if alimentos else [h for h, _ in brutos]
        productos = elegidos[:limite]
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos


def _es_alimentacion_lidl(datos: dict[str, Any]) -> bool:
    cat = str(datos.get("category") or "").strip()
    if cat == "Food":
        return True
    bajo = cat.casefold()
    return any(
        trozo in bajo
        for trozo in ("food", "aliment", "frescos", "bebida", "nevera")
    )


def normalizar_hit_lidl(item: dict[str, Any]) -> dict[str, Any]:
    datos = (item.get("gridbox") or {}).get("data") or {}
    pid = str(item.get("code") or datos.get("productId") or datos.get("erpNumber") or "")
    nombre = datos.get("title") or datos.get("fullName") or item.get("label") or "Producto Lidl"

    precio_unidad = None
    bloque_precio = datos.get("price")
    if isinstance(bloque_precio, dict):
        try:
            precio_unidad = float(bloque_precio.get("price"))
        except (TypeError, ValueError):
            precio_unidad = None

    miniatura = None
    for clave_img in ("imageList", "cutoutimageV2", "images"):
        imgs = datos.get(clave_img)
        if isinstance(imgs, list) and imgs:
            miniatura = imgs[0] if isinstance(imgs[0], str) else imgs[0].get("url")
            break
        if isinstance(imgs, str):
            miniatura = imgs
            break

    ruta = datos.get("canonicalUrl") or datos.get("canonicalPath") or ""
    url = f"https://www.lidl.es{ruta}" if ruta.startswith("/") else ruta or None

    brand_raw = datos.get("brand")
    brand_name = None
    if isinstance(brand_raw, dict):
        brand_name = brand_raw.get("name")
    elif isinstance(brand_raw, str):
        brand_name = brand_raw
    marca = inferir_marca(nombre, brand_name, fallback="Lidl")

    return {
        "id": f"{PREFIJO_ID}{pid}",
        "id_externo": pid,
        "ean": datos.get("ean") or datos.get("gtin"),
        "nombre": nombre,
        "marca": marca,
        "envase": "",
        "miniatura": miniatura,
        "url_compartir": url,
        "precio_unidad": precio_unidad,
        "precio_bulto": None,
        "tamano_unidad": None,
        "formato_tamano": "",
        "tienda": "lidl",
        "origen": "lidl",
        "name": nombre,
        "brand": marca,
        "thumbnail": miniatura,
        "unit_price": precio_unidad,
        "bulk_price": None,
        "size_format": "",
        "unit_size": None,
        "share_url": url,
    }


def es_id_lidl(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_ld: ClienteLidl | None = None


def obtener_cliente_lidl() -> ClienteLidl:
    global _cliente_ld
    if _cliente_ld is None:
        _cliente_ld = ClienteLidl()
    return _cliente_ld
