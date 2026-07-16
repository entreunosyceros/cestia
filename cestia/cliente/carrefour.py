"""Cliente de búsqueda Carrefour ES vía Empathy (API no oficial)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from cestia.cliente.limite_y_cache import CacheDisco, LimitadorPeticiones
from cestia.configuracion import obtener_configuracion

registrador = logging.getLogger(__name__)

URL_BUSQUEDA = "https://api.empathy.co/search/v1/query/carrefour/search"
PREFIJO_ID = "cf:"


class ErrorAPICarrefour(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteCarrefour:
    """Búsqueda de productos en Carrefour España (Empathy Platform)."""

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

        clave = f"carrefour:busqueda:{consulta.lower()}:{limite}"
        acierto = self.cache.obtener(clave)
        if acierto is not None:
            return acierto

        self.limitador.adquirir()
        parametros = {
            "query": consulta,
            "lang": "es",
            "rows": max(1, min(limite, 50)),
            "start": 0,
        }
        url = f"{URL_BUSQUEDA}?{urlencode(parametros)}"
        try:
            with httpx.Client(timeout=self.timeout) as cliente:
                respuesta = cliente.get(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": self.agente,
                        "Referer": "https://www.carrefour.es/",
                    },
                )
        except httpx.HTTPError as exc:
            raise ErrorAPICarrefour(f"Error de red Carrefour: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPICarrefour(
                f"HTTP {respuesta.status_code} en búsqueda Carrefour",
                codigo_estado=respuesta.status_code,
            )
        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise ErrorAPICarrefour("Respuesta Carrefour no JSON") from exc

        catalogo = datos.get("catalog") or {}
        productos = [
            normalizar_hit_carrefour(item)
            for item in (catalogo.get("content") or [])
        ]
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos


def normalizar_hit_carrefour(item: dict[str, Any]) -> dict[str, Any]:
    """Convierte un hit Empathy a la forma interna de CestIA."""
    pid = str(item.get("product_id") or item.get("sms") or "")
    imagenes = item.get("image_path") or {}
    miniatura = (
        item.get("image_for_play_service")
        or (imagenes.get("food") if isinstance(imagenes, dict) else None)
        or item.get("image")
    )
    ruta = ""
    urls = item.get("urls") or {}
    if isinstance(urls, dict):
        ruta = urls.get("food") or ""
    if not ruta:
        ruta = item.get("url_for_play_service") or ""
    url_compartir = (
        f"https://www.carrefour.es{ruta}" if ruta.startswith("/") else ruta
    )

    precio = item.get("active_price")
    try:
        precio_unidad = float(precio) if precio is not None else None
    except (TypeError, ValueError):
        precio_unidad = None

    formato = (item.get("unit_short_name") or item.get("measure_unit") or "").strip()
    peso = item.get("average_weight")
    precio_bulto = None
    tamano_unidad = None
    try:
        if peso is not None:
            tamano_unidad = float(peso)
            # average_weight suele ir en gramos/ml; si formato es l/kg, convertir
            if formato.lower() in {"l", "kg"} and tamano_unidad >= 10:
                tamano_unidad = tamano_unidad / 1000.0
            if precio_unidad is not None and tamano_unidad:
                precio_bulto = round(precio_unidad / tamano_unidad, 2)
    except (TypeError, ValueError):
        pass

    return {
        "id": f"{PREFIJO_ID}{pid}",
        "id_externo": pid,
        "ean": item.get("ean13") or item.get("ean"),
        "nombre": item.get("display_name") or item.get("name") or "Producto Carrefour",
        "marca": item.get("brand"),
        "envase": item.get("recipient") or "",
        "miniatura": miniatura,
        "url_compartir": url_compartir or None,
        "precio_unidad": precio_unidad,
        "precio_bulto": precio_bulto,
        "tamano_unidad": tamano_unidad,
        "formato_tamano": formato,
        "tienda": "carrefour",
        "origen": "carrefour",
        # aliases
        "name": item.get("display_name") or item.get("name"),
        "brand": item.get("brand"),
        "thumbnail": miniatura,
        "unit_price": precio_unidad,
        "bulk_price": precio_bulto,
        "size_format": formato,
        "unit_size": tamano_unidad,
        "share_url": url_compartir or None,
    }


def es_id_carrefour(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_cf: ClienteCarrefour | None = None


def obtener_cliente_carrefour() -> ClienteCarrefour:
    global _cliente_cf
    if _cliente_cf is None:
        _cliente_cf = ClienteCarrefour()
    return _cliente_cf
