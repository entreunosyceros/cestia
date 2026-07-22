"""Cliente de búsqueda Gadis (API catalog.gadisline.com, no oficial)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from cestia.cliente.limite_y_cache import (
    CacheDisco,
    LimitadorPeticiones,
    anotar_frescor,
)
from cestia.configuracion import obtener_configuracion

registrador = logging.getLogger(__name__)

URL_BUSQUEDA = "https://catalog.gadisline.com/api/v3/catalog/products/search"
URL_WEB = "https://www.gadisline.com"
PREFIJO_ID = "gd:"

# Valores públicos del front de Gadisline (site + almacén por defecto).
SITE_ID = "56df88f9-479f-4361-891e-e1864dba1ca3"
STORE_ID = "891d5c1e-a7a0-4287-9ea3-30c5703a4f63"
IDIOMA = "ES"


class ErrorAPIGadis(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteGadis:
    """Búsqueda de productos en Gadisline vía API de catálogo."""

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

        clave = f"gadis:v1:busqueda:{consulta.lower()}:{limite}"
        entrada = self.cache.obtener_entrada(clave)
        if entrada is not None:
            return anotar_frescor(entrada["datos"], entrada["guardado_en"])

        self.limitador.adquirir()
        parametros = {
            "page_number": 1,
            "rows_per_page": max(1, min(limite, 48)),
            "keep_request": "true",
        }
        url = f"{URL_BUSQUEDA}?{urlencode(parametros)}"
        cuerpo = {"search_term": consulta, "minimum_should_match": 1}
        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": self.agente,
                    "Origin": URL_WEB,
                    "Referer": f"{URL_WEB}/",
                    "site-id": SITE_ID,
                    "store-id": STORE_ID,
                    "accept-language": IDIOMA,
                },
            ) as cliente:
                respuesta = cliente.post(url, json=cuerpo)
        except httpx.HTTPError as exc:
            raise ErrorAPIGadis(f"Error de red Gadis: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPIGadis(
                f"HTTP {respuesta.status_code} en búsqueda Gadis",
                codigo_estado=respuesta.status_code,
            )
        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise ErrorAPIGadis("Respuesta Gadis no JSON") from exc

        productos = [
            normalizar_hit_gadis(item)
            for item in (datos.get("elements") or [])
        ]
        productos = [p for p in productos if p.get("nombre")][:limite]
        anotar_frescor(productos)
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos


def _texto_idioma(campo: Any, idioma: str = IDIOMA) -> str:
    if isinstance(campo, str):
        return campo.strip()
    if not isinstance(campo, list):
        return ""
    for item in campo:
        if isinstance(item, dict) and item.get("language") == idioma:
            return str(item.get("value") or "").strip()
    for item in campo:
        if isinstance(item, dict) and item.get("value"):
            return str(item["value"]).strip()
    return ""


def _formato_desde_suffix(suffix: Any) -> str:
    texto = _texto_idioma(suffix).lower()
    if "litro" in texto:
        return "l"
    if "kilo" in texto:
        return "kg"
    if "gramo" in texto:
        return "g"
    return ""


def _precio_anterior(item: dict[str, Any], precio: float | None) -> float | None:
    ofertas = item.get("offers") or []
    if not isinstance(ofertas, list) or precio is None:
        return None
    for oferta in ofertas:
        if not isinstance(oferta, dict):
            continue
        for clave in ("old_price", "previous_price", "price_before", "strike_price"):
            bruto = oferta.get(clave)
            try:
                anterior = float(bruto) if bruto is not None else None
            except (TypeError, ValueError):
                anterior = None
            if anterior is not None and anterior > precio:
                return anterior
    return None


def normalizar_hit_gadis(item: dict[str, Any]) -> dict[str, Any]:
    from cestia.normalizacion import inferir_marca

    pid = str(item.get("id") or item.get("product_code") or "")
    nombre = _texto_idioma(item.get("commercial_description")) or "Producto Gadis"
    try:
        precio_unidad = float(item["price"]) if item.get("price") is not None else None
    except (TypeError, ValueError):
        precio_unidad = None
    try:
        precio_bulto = (
            float(item["price_kilo_litre"])
            if item.get("price_kilo_litre") is not None
            else None
        )
    except (TypeError, ValueError):
        precio_bulto = None

    imagen = item.get("image") or {}
    miniatura = None
    if isinstance(imagen, dict):
        miniatura = imagen.get("image_thumbnails") or imagen.get("image")
    elif isinstance(imagen, str):
        miniatura = imagen

    slug = (item.get("slug") or "").strip()
    if slug and not slug.startswith("/"):
        slug = "/" + slug
    url = f"{URL_WEB}/catalog/{pid}" if pid else (f"{URL_WEB}{slug}" if slug else None)

    categoria = ""
    cat = item.get("category") or {}
    if isinstance(cat, dict):
        categoria = _texto_idioma(cat.get("descriptions_translate"))
    if not categoria:
        cats = item.get("categories") or []
        if cats and isinstance(cats[-1], dict):
            categoria = _texto_idioma(cats[-1].get("descriptions_translate"))

    marca = inferir_marca(nombre, item.get("brand_description"), fallback="Gadis")
    formato = _formato_desde_suffix(item.get("price_kilo_litre_suffix"))
    anterior = _precio_anterior(item, precio_unidad)

    return {
        "id": f"{PREFIJO_ID}{pid}",
        "id_externo": pid,
        "ean": item.get("ean") or item.get("ean13"),
        "nombre": nombre,
        "marca": marca,
        "envase": "",
        "categoria": categoria or None,
        "miniatura": miniatura,
        "url_compartir": url,
        "precio_unidad": precio_unidad,
        "precio_bulto": precio_bulto,
        "precio_unidad_anterior": anterior,
        "tamano_unidad": None,
        "formato_tamano": formato,
        "tienda": "gadis",
        "origen": "gadis",
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


def es_id_gadis(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_gd: ClienteGadis | None = None


def obtener_cliente_gadis() -> ClienteGadis:
    global _cliente_gd
    if _cliente_gd is None:
        _cliente_gd = ClienteGadis()
    return _cliente_gd
