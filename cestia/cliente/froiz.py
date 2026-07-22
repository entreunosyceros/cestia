"""Cliente de búsqueda Froiz vía Empathy + precio de ficha (API no oficial)."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
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

URL_BUSQUEDA = "https://api.empathy.co/search/v1/query/froiz/search"
URL_PRODUCTO = "https://supermercado.froiz.com/product/{slug}"
PREFIJO_ID = "fz:"


class ErrorAPIFroiz(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteFroiz:
    """Búsqueda de productos en Froiz (Empathy + ficha para precio)."""

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

        clave = f"froiz:v2:busqueda:{consulta.lower()}:{limite}"
        entrada = self.cache.obtener_entrada(clave)
        if entrada is not None:
            return anotar_frescor(entrada["datos"], entrada["guardado_en"])

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
                        "Referer": "https://supermercado.froiz.com/",
                    },
                )
        except httpx.HTTPError as exc:
            raise ErrorAPIFroiz(f"Error de red Froiz: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPIFroiz(
                f"HTTP {respuesta.status_code} en búsqueda Froiz",
                codigo_estado=respuesta.status_code,
            )
        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise ErrorAPIFroiz("Respuesta Froiz no JSON") from exc

        catalogo = datos.get("catalog") or {}
        brutos = (catalogo.get("content") or [])[:limite]
        productos = [normalizar_hit_froiz(item) for item in brutos]
        self._enriquecer_precios(productos)
        anotar_frescor(productos)
        self.cache.guardar(clave, productos, obtener_configuracion().ttl_cache_busqueda)
        return productos

    def _enriquecer_precios(self, productos: list[dict[str, Any]]) -> None:
        pendientes = [
            p for p in productos if p.get("precio_unidad") is None and p.get("slug")
        ]
        if not pendientes:
            return

        def obtener(p: dict[str, Any]) -> tuple[str, float | None]:
            slug = p["slug"]
            clave = f"froiz:v1:precio:{slug}"
            cacheado = self.cache.obtener(clave)
            if isinstance(cacheado, (int, float)):
                return p["id"], float(cacheado)
            if isinstance(cacheado, dict) and cacheado.get("precio_unidad") is not None:
                return p["id"], float(cacheado["precio_unidad"])

            self.limitador.adquirir()
            precio = _precio_desde_ficha(slug, self.agente, self.timeout)
            if precio is not None:
                self.cache.guardar(
                    clave, {"precio_unidad": precio}, obtener_configuracion().ttl_cache_busqueda
                )
            return p["id"], precio

        with ThreadPoolExecutor(max_workers=6) as pool:
            futuros = [pool.submit(obtener, p) for p in pendientes]
            precios: dict[str, float] = {}
            for fut in as_completed(futuros):
                try:
                    pid, precio = fut.result()
                except Exception as exc:  # noqa: BLE001
                    registrador.debug("Precio Froiz falló: %s", exc)
                    continue
                if precio is not None:
                    precios[pid] = precio

        for p in productos:
            if p["id"] in precios:
                p["precio_unidad"] = precios[p["id"]]
                p["unit_price"] = precios[p["id"]]
                self._completar_precio_bulto(p)

    @staticmethod
    def _completar_precio_bulto(producto: dict[str, Any]) -> None:
        precio = producto.get("precio_unidad")
        tamano = producto.get("tamano_unidad")
        if precio is None or not tamano:
            return
        try:
            producto["precio_bulto"] = round(float(precio) / float(tamano), 2)
            producto["bulk_price"] = producto["precio_bulto"]
        except (TypeError, ValueError, ZeroDivisionError):
            pass


def _precio_desde_ficha(slug: str, agente: str, timeout: float) -> float | None:
    url = URL_PRODUCTO.format(slug=slug)
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": agente,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://supermercado.froiz.com/",
            },
        ) as cliente:
            respuesta = cliente.get(url)
    except httpx.HTTPError:
        return None
    if respuesta.status_code >= 400:
        return None
    m = re.search(r'base_price:"([0-9.]+)"', respuesta.text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def normalizar_hit_froiz(item: dict[str, Any]) -> dict[str, Any]:
    from cestia.normalizacion import inferir_marca

    pid = str(item.get("id") or "")
    slug = item.get("slug") or f"{pid}"
    nombre = item.get("name") or "Producto Froiz"
    miniatura = item.get("imageUrl")
    unidad = (item.get("measurementUnit") or "").strip()
    formato = _formato_unidad(unidad)
    tamano = None
    try:
        peso = item.get("perUnitWeight")
        ratio = item.get("measurementUnitRatio")
        if peso is not None:
            tamano = float(peso)
        elif ratio is not None:
            tamano = float(ratio)
    except (TypeError, ValueError):
        tamano = None

    url = f"https://supermercado.froiz.com/product/{slug}" if slug else None
    marca = inferir_marca(
        nombre,
        item.get("brand") or item.get("manufacturer"),
        fallback="Froiz",
    )
    return {
        "id": f"{PREFIJO_ID}{pid}",
        "id_externo": pid,
        "slug": slug,
        "ean": None,
        "nombre": nombre,
        "marca": marca,
        "envase": "",
        "miniatura": miniatura,
        "url_compartir": url,
        "precio_unidad": None,
        "precio_bulto": None,
        "tamano_unidad": tamano,
        "formato_tamano": formato,
        "tienda": "froiz",
        "origen": "froiz",
        "name": nombre,
        "brand": marca,
        "thumbnail": miniatura,
        "unit_price": None,
        "bulk_price": None,
        "size_format": formato,
        "unit_size": tamano,
        "share_url": url,
    }


def _formato_unidad(unidad: str) -> str | None:
    u = unidad.lower()
    if "litro" in u or u == "l":
        return "l"
    if "kilo" in u or u in {"kg", "kilo"}:
        return "kg"
    if "gramo" in u or u == "g":
        return "g"
    if unidad:
        return unidad[:12]
    return None


def es_id_froiz(id_producto: str) -> bool:
    return str(id_producto).startswith(PREFIJO_ID)


_cliente_fz: ClienteFroiz | None = None


def obtener_cliente_froiz() -> ClienteFroiz:
    global _cliente_fz
    if _cliente_fz is None:
        _cliente_fz = ClienteFroiz()
    return _cliente_fz
