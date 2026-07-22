"""Cliente HTTP hacia la API interna de Mercadona y Algolia."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from cestia.cliente.limite_y_cache import CacheDisco, LimitadorPeticiones
from cestia.configuracion import Configuracion, obtener_configuracion

registrador = logging.getLogger(__name__)


class ErrorAPIMercadona(Exception):
    def __init__(self, mensaje: str, *, codigo_estado: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo_estado = codigo_estado


class ClienteMercadona:
    """Cliente no oficial para tienda.mercadona.es con caché y límite de ritmo."""

    def __init__(self, configuracion: Configuracion | None = None) -> None:
        self.configuracion = configuracion or obtener_configuracion()
        self.cache = CacheDisco(self.configuracion.directorio_cache)
        self.limitador = LimitadorPeticiones(
            self.configuracion.limite_peticiones_por_minuto
        )
        self._salud: dict[str, Any] = {
            "ok": None,
            "comprobado_en": None,
            "latencia_ms": None,
            "error": None,
            "endpoints": {},
        }

    def _cabeceras(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Accept-Language": self.configuracion.idioma_mercadona,
            "User-Agent": self.configuracion.agente_usuario,
            "Origin": "https://tienda.mercadona.es",
            "Referer": "https://tienda.mercadona.es/",
        }

    def _parametros(self) -> dict[str, str]:
        return {
            "lang": self.configuracion.idioma_mercadona,
            "wh": self.configuracion.almacen_mercadona,
        }

    def _peticion(
        self,
        metodo: str,
        url: str,
        *,
        cabeceras: dict[str, str] | None = None,
        parametros: dict[str, Any] | None = None,
        cuerpo_json: dict[str, Any] | None = None,
    ) -> Any:
        self.limitador.adquirir()
        unidas = {**self._cabeceras(), **(cabeceras or {})}
        try:
            with httpx.Client(timeout=self.configuracion.timeout_http) as cliente:
                respuesta = cliente.request(
                    metodo,
                    url,
                    headers=unidas,
                    params=parametros,
                    json=cuerpo_json,
                )
        except httpx.HTTPError as exc:
            raise ErrorAPIMercadona(f"Error de red: {exc}") from exc

        if respuesta.status_code >= 400:
            raise ErrorAPIMercadona(
                f"HTTP {respuesta.status_code} en {url}",
                codigo_estado=respuesta.status_code,
            )
        try:
            return respuesta.json()
        except ValueError as exc:
            raise ErrorAPIMercadona("Respuesta no JSON (¿cambió la API?)") from exc

    def _obtener_con_cache(
        self,
        clave_cache: str,
        ttl: int,
        url: str,
        *,
        parametros: dict[str, Any] | None = None,
    ) -> Any:
        acierto = self.cache.obtener(clave_cache)
        if acierto is not None:
            return acierto
        datos = self._peticion("GET", url, parametros=parametros)
        self.cache.guardar(clave_cache, datos, ttl)
        return datos

    def listar_categorias(self) -> list[dict[str, Any]]:
        url = f"{self.configuracion.url_base_mercadona}/categories/"
        clave = (
            f"categorias:{self.configuracion.almacen_mercadona}:"
            f"{self.configuracion.idioma_mercadona}"
        )
        datos = self._obtener_con_cache(
            clave,
            self.configuracion.ttl_cache_categorias,
            url,
            parametros=self._parametros(),
        )
        return datos.get("results") or []

    def obtener_categoria(self, id_categoria: int | str) -> dict[str, Any]:
        url = f"{self.configuracion.url_base_mercadona}/categories/{id_categoria}/"
        clave = (
            f"categoria:{id_categoria}:"
            f"{self.configuracion.almacen_mercadona}:"
            f"{self.configuracion.idioma_mercadona}"
        )
        return self._obtener_con_cache(
            clave,
            self.configuracion.ttl_cache_categorias,
            url,
            parametros=self._parametros(),
        )

    def obtener_producto(self, id_producto: str) -> dict[str, Any]:
        url = f"{self.configuracion.url_base_mercadona}/products/{id_producto}/"
        clave = (
            f"producto:{id_producto}:"
            f"{self.configuracion.almacen_mercadona}:"
            f"{self.configuracion.idioma_mercadona}"
        )
        return self._obtener_con_cache(
            clave,
            self.configuracion.ttl_cache_productos,
            url,
            parametros=self._parametros(),
        )

    def buscar(self, consulta: str, *, limite: int = 24) -> dict[str, Any]:
        consulta = consulta.strip()
        if not consulta:
            return {"hits": [], "nbHits": 0, "query": consulta}

        clave_cache = (
            f"busqueda:{consulta.lower()}:{limite}:"
            f"{self.configuracion.almacen_mercadona}:"
            f"{self.configuracion.idioma_mercadona}"
        )
        from cestia.cliente.limite_y_cache import anotar_frescor

        entrada = self.cache.obtener_entrada(clave_cache)
        if entrada is not None:
            return anotar_frescor(entrada["datos"], entrada["guardado_en"])

        parametros = urlencode(
            {"query": consulta, "hitsPerPage": max(1, min(limite, 50))}
        )
        datos = self._peticion(
            "POST",
            self.configuracion.url_algolia,
            cabeceras={
                "Content-Type": "application/json",
                "X-Algolia-Application-Id": self.configuracion.algolia_id_aplicacion,
                "X-Algolia-API-Key": self.configuracion.algolia_clave_api,
            },
            cuerpo_json={"params": parametros},
        )
        resultado = {
            "hits": datos.get("hits") or [],
            "nbHits": datos.get("nbHits", 0),
            "query": consulta,
        }
        anotar_frescor(resultado)
        self.cache.guardar(
            clave_cache, resultado, self.configuracion.ttl_cache_busqueda
        )
        return resultado

    def productos_de_categoria(self, id_categoria: int | str) -> list[dict[str, Any]]:
        categoria = self.obtener_categoria(id_categoria)
        productos: list[dict[str, Any]] = []

        def recorrer(nodo: dict[str, Any]) -> None:
            for producto in nodo.get("products") or []:
                productos.append(producto)
            for hijo in nodo.get("categories") or []:
                recorrer(hijo)

        recorrer(categoria)
        return productos

    def comprobar_salud(self, *, forzar: bool = False) -> dict[str, Any]:
        comprobado_en = self._salud.get("comprobado_en")
        if (
            not forzar
            and comprobado_en
            and time.time() - comprobado_en < 300
            and self._salud.get("ok") is not None
        ):
            return self._salud

        inicio = time.perf_counter()
        endpoints: dict[str, Any] = {}
        ok = True
        error: str | None = None

        pruebas = [
            ("categorias", lambda: self.listar_categorias()),
            ("producto", lambda: self.obtener_producto("4241")),
            ("busqueda", lambda: self.buscar("leche", limite=1)),
        ]
        for nombre, funcion in pruebas:
            try:
                t0 = time.perf_counter()
                carga = funcion()
                latencia = round((time.perf_counter() - t0) * 1000)
                valido = bool(carga)
                if nombre == "categorias":
                    valido = isinstance(carga, list) and len(carga) > 0
                elif nombre == "producto":
                    valido = isinstance(carga, dict) and "id" in carga
                elif nombre == "busqueda":
                    valido = isinstance(carga, dict) and "hits" in carga
                endpoints[nombre] = {"ok": valido, "latencia_ms": latencia}
                if not valido:
                    ok = False
                    error = f"Respuesta inesperada en {nombre}"
            except ErrorAPIMercadona as exc:
                ok = False
                endpoints[nombre] = {
                    "ok": False,
                    "codigo_estado": exc.codigo_estado,
                    "error": str(exc),
                }
                error = str(exc)
            except Exception as exc:  # noqa: BLE001
                ok = False
                endpoints[nombre] = {"ok": False, "error": str(exc)}
                error = str(exc)

        self._salud = {
            "ok": ok,
            "comprobado_en": time.time(),
            "latencia_ms": round((time.perf_counter() - inicio) * 1000),
            "error": error,
            "endpoints": endpoints,
            "almacen": self.configuracion.almacen_mercadona,
            "limite_peticiones": self.limitador.estadisticas(),
            "cache": self.cache.estadisticas(),
        }
        if not ok:
            registrador.warning("Comprobación de salud fallida: %s", error)
        return self._salud

    def vaciar_cache(self) -> int:
        return self.cache.vaciar()


_cliente: ClienteMercadona | None = None


def obtener_cliente() -> ClienteMercadona:
    global _cliente
    if _cliente is None:
        _cliente = ClienteMercadona()
    return _cliente
