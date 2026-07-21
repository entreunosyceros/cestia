"""Cliente de búsqueda Eroski (supermercado.eroski.es, API no oficial)."""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any
from urllib.parse import quote

import httpx

from cestia.cliente.limite_y_cache import CacheDisco, LimitadorPeticiones
from cestia.configuracion import obtener_configuracion

registrador = logging.getLogger(__name__)

URL_BUSQUEDA = "https://supermercado.eroski.es/es/search/results/?q={consulta}"
PREFIJO_ID = "er:"


class ErrorAPIEroski(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteEroski:
    """Búsqueda de productos en Eroski vía HTML de resultados."""

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

        clave = f"eroski:v3:busqueda:{consulta.lower()}:{limite}"
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
                    "Accept-Language": "es-ES,es;q=0.9",
                },
            ) as cliente:
                respuesta = cliente.get(url)
        except httpx.HTTPError as exc:
            raise ErrorAPIEroski(f"Error de red Eroski: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPIEroski(
                f"HTTP {respuesta.status_code} en búsqueda Eroski",
                codigo_estado=respuesta.status_code,
            )

        productos = _productos_desde_html(respuesta.text, limite=limite)
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos


def _normalizar_url_imagen(url: str | None, pid: str) -> str:
    if url:
        url = url.replace("://supermercado.eroski.es//", "://supermercado.eroski.es/")
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = "https://supermercado.eroski.es" + url
        return url
    return f"https://supermercado.eroski.es/images/{pid}.jpg"


def _extraer_imagen(bloque: str, pid: str) -> str:
    img_m = re.search(
        r'<img[^>]+class="product-img"[^>]+src="([^"]+)"',
        bloque,
        re.I,
    )
    if not img_m:
        img_m = re.search(
            r'src="(https?://supermercado\.eroski\.es/+images/[^"]+\.(?:jpg|jpeg|png|webp))"',
            bloque,
            re.I,
        )
    if not img_m:
        img_m = re.search(
            r'(https?://supermercado\.eroski\.es/+images/\d+[^"\']*\.(?:jpg|jpeg|png|webp))',
            bloque,
            re.I,
        )
    return _normalizar_url_imagen(img_m.group(1) if img_m else None, pid)


def _productos_desde_html(html: str, *, limite: int) -> list[dict[str, Any]]:
    bloques = re.split(r"productlistitem_\d+", html)[1:]
    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()

    for bloque in bloques:
        enlace = re.search(r"productdetail/(\d+)-([^/?\"]+)", bloque)
        if not enlace:
            continue
        pid, slug = enlace.group(1), enlace.group(2)
        if pid in vistos:
            continue
        precio_m = re.search(
            r'class="price[^"]*"[^>]*>\s*([0-9]+[,.][0-9]+)', bloque
        )
        if not precio_m:
            continue
        vistos.add(pid)
        try:
            precio_unidad = float(precio_m.group(1).replace(",", "."))
        except ValueError:
            continue
        alt_m = re.search(r'class="product-img"[^>]+alt="([^"]+)"', bloque, re.I)
        if not alt_m:
            alt_m = re.search(r'alt="([^"]+)"[^>]+class="product-img"', bloque, re.I)
        nombre = (
            unescape(alt_m.group(1))
            if alt_m
            else unescape(slug.replace("-", " ").title())
        )
        url = (
            f"https://supermercado.eroski.es/es/productdetail/"
            f"{pid}-{slug}/"
        )
        productos.append(
            normalizar_hit_eroski(
                pid,
                nombre,
                precio_unidad,
                _extraer_imagen(bloque, pid),
                url,
            )
        )
        if len(productos) >= limite:
            break

    return productos


def normalizar_hit_eroski(
    pid: str,
    nombre: str,
    precio_unidad: float,
    miniatura: str | None,
    url: str,
) -> dict[str, Any]:
    from cestia.normalizacion import inferir_marca

    marca = inferir_marca(nombre, fallback="Eroski" if "eroski" in nombre.lower() else None)
    return {
        "id": f"{PREFIJO_ID}{pid}",
        "id_externo": pid,
        "ean": None,
        "nombre": nombre,
        "marca": marca,
        "envase": "",
        "miniatura": miniatura,
        "url_compartir": url,
        "precio_unidad": precio_unidad,
        "precio_bulto": None,
        "tamano_unidad": None,
        "formato_tamano": "",
        "tienda": "eroski",
        "origen": "eroski",
        "name": nombre,
        "brand": marca,
        "thumbnail": miniatura,
        "unit_price": precio_unidad,
        "bulk_price": None,
        "size_format": "",
        "unit_size": None,
        "share_url": url,
    }


def es_id_eroski(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_er: ClienteEroski | None = None


def obtener_cliente_eroski() -> ClienteEroski:
    global _cliente_er
    if _cliente_er is None:
        _cliente_er = ClienteEroski()
    return _cliente_er
