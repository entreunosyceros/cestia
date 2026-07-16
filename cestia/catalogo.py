"""Sincroniza productos de Mercadona, Carrefour y Alcampo → SQLite."""

from __future__ import annotations

from typing import Any

from cestia.base_datos.repositorio import Repositorio
from cestia.cliente import ClienteMercadona, ErrorAPIMercadona, obtener_cliente
from cestia.cliente.alcampo import (
    ClienteAlcampo,
    ErrorAPIAlcampo,
    es_id_alcampo,
    obtener_cliente_alcampo,
)
from cestia.cliente.carrefour import (
    ClienteCarrefour,
    ErrorAPICarrefour,
    es_id_carrefour,
    obtener_cliente_carrefour,
)
from cestia.enriquecimiento import ClienteOpenFoodFacts, parsear_nutricion_mercadona
from cestia.normalizacion import normalizar_producto
from cestia.tiendas import alcampo_activo, carrefour_activo, mercadona_activo

_ORDEN_TIENDA = {"mercadona": 0, "carrefour": 1, "alcampo": 2}


class ServicioCatalogo:
    def __init__(
        self,
        repositorio: Repositorio,
        cliente: ClienteMercadona | None = None,
        cliente_carrefour: ClienteCarrefour | None = None,
        cliente_alcampo: ClienteAlcampo | None = None,
        off: ClienteOpenFoodFacts | None = None,
    ) -> None:
        self.repositorio = repositorio
        self.cliente = cliente or obtener_cliente()
        self.cliente_carrefour = cliente_carrefour or obtener_cliente_carrefour()
        self.cliente_alcampo = cliente_alcampo or obtener_cliente_alcampo()
        self.off = off or ClienteOpenFoodFacts()

    def buscar(self, consulta: str, limite: int = 24) -> list[dict[str, Any]]:
        resultados: list[dict[str, Any]] = []
        errores: list[str] = []

        if mercadona_activo(self.repositorio):
            try:
                bruto = self.cliente.buscar(consulta, limite=limite)
                for acierto in bruto.get("hits") or []:
                    producto = self._persistir_mercadona(acierto, enriquecer=False)
                    resultados.append(producto)
            except ErrorAPIMercadona as exc:
                errores.append(f"Mercadona: {exc}")

        if carrefour_activo(self.repositorio):
            try:
                hits = self.cliente_carrefour.buscar(consulta, limite=limite)
                for hit in hits:
                    producto = self._persistir_carrefour(hit, enriquecer=False)
                    resultados.append(producto)
            except ErrorAPICarrefour as exc:
                errores.append(f"Carrefour: {exc}")

        if alcampo_activo(self.repositorio):
            try:
                hits = self.cliente_alcampo.buscar(consulta, limite=limite)
                for hit in hits:
                    producto = self._persistir_alcampo(hit, enriquecer=False)
                    resultados.append(producto)
            except ErrorAPIAlcampo as exc:
                errores.append(f"Alcampo: {exc}")

        if not resultados and errores:
            raise RuntimeError(" · ".join(errores))

        resultados.sort(
            key=lambda p: (
                _ORDEN_TIENDA.get((p.get("tienda") or "mercadona"), 9),
                p.get("precio_unidad") is None,
                p.get("precio_unidad") or 1e9,
            )
        )
        return resultados

    def obtener_producto(
        self, id_producto: str, *, enriquecer: bool = True
    ) -> dict[str, Any]:
        if es_id_carrefour(id_producto) or es_id_alcampo(id_producto):
            local = self.repositorio.obtener_producto(id_producto)
            if local:
                if enriquecer:
                    return self._enriquecer_registro(local)
                return local
            marca = "Carrefour" if es_id_carrefour(id_producto) else "Alcampo"
            raise RuntimeError(
                f"Producto {marca} no encontrado en local. Vuelve a buscarlo."
            )

        bruto = self.cliente.obtener_producto(id_producto)
        return self._persistir_mercadona(bruto, enriquecer=enriquecer)

    def obtener_por_ean(
        self, ean: str, *, enriquecer: bool = True
    ) -> dict[str, Any] | None:
        aciertos = self.buscar(ean, limite=10)
        for acierto in aciertos:
            if acierto.get("ean") == ean:
                if enriquecer and not (
                    es_id_carrefour(acierto["id"]) or es_id_alcampo(acierto["id"])
                ):
                    return self.obtener_producto(acierto["id"], enriquecer=True)
                if enriquecer:
                    return self._enriquecer_registro(acierto)
                return acierto
        local = self.repositorio.buscar_local(ean, limite=5)
        for fila in local:
            if fila.get("ean") == ean:
                return fila
        return None

    def alternativas_mas_baratas(
        self, producto: dict[str, Any], limite: int = 6
    ) -> list[dict[str, Any]]:
        nombre = producto.get("nombre") or producto.get("name") or ""
        tokens = [t for t in nombre.split() if len(t) > 3][:2]
        consulta = " ".join(tokens) if tokens else nombre
        if not consulta:
            return []
        candidatos = self.buscar(consulta, limite=20)
        precio = producto.get("precio_unidad") or producto.get("unit_price")
        alternativas = []
        for c in candidatos:
            if c["id"] == producto.get("id"):
                continue
            p = c.get("precio_unidad")
            if precio is not None and p is not None and p < precio:
                alternativas.append(c)
        alternativas.sort(key=lambda x: x.get("precio_unidad") or 1e9)
        return alternativas[:limite]

    def _persistir_mercadona(
        self, bruto: dict[str, Any], *, enriquecer: bool
    ) -> dict[str, Any]:
        norm = normalizar_producto(bruto)
        nutri = parsear_nutricion_mercadona(bruto)
        categoria = None
        cats = bruto.get("categories") or norm.get("categorias_brutas") or []
        if cats:
            categoria = cats[0].get("name")

        precio_info = bruto.get("price_instructions") or {}
        registro: dict[str, Any] = {
            "id": norm["id"],
            "ean": bruto.get("ean"),
            "nombre": norm["nombre"],
            "marca": norm.get("marca"),
            "envase": norm.get("envase"),
            "categoria": categoria,
            "miniatura": norm.get("miniatura"),
            "url_compartir": norm.get("url_compartir"),
            "ingredientes": nutri.get("ingredientes"),
            "alergenos": nutri.get("alergenos"),
            "tamano_unidad": norm.get("tamano_unidad") or precio_info.get("unit_size"),
            "formato_tamano": norm.get("formato_tamano") or precio_info.get("size_format"),
            "precio_unidad": norm.get("precio_unidad"),
            "precio_bulto": norm.get("precio_bulto"),
            "precio_unidad_anterior": norm.get("precio_unidad_anterior"),
            "tienda": "mercadona",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _persistir_carrefour(
        self, hit: dict[str, Any], *, enriquecer: bool
    ) -> dict[str, Any]:
        registro = {
            "id": hit["id"],
            "ean": hit.get("ean"),
            "nombre": hit.get("nombre"),
            "marca": hit.get("marca"),
            "envase": hit.get("envase"),
            "categoria": None,
            "miniatura": hit.get("miniatura"),
            "url_compartir": hit.get("url_compartir"),
            "ingredientes": None,
            "alergenos": None,
            "tamano_unidad": hit.get("tamano_unidad"),
            "formato_tamano": hit.get("formato_tamano"),
            "precio_unidad": hit.get("precio_unidad"),
            "precio_bulto": hit.get("precio_bulto"),
            "precio_unidad_anterior": None,
            "tienda": "carrefour",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _persistir_alcampo(
        self, hit: dict[str, Any], *, enriquecer: bool
    ) -> dict[str, Any]:
        registro = {
            "id": hit["id"],
            "ean": hit.get("ean"),
            "nombre": hit.get("nombre"),
            "marca": hit.get("marca"),
            "envase": hit.get("envase"),
            "categoria": hit.get("categoria"),
            "miniatura": hit.get("miniatura"),
            "url_compartir": hit.get("url_compartir"),
            "ingredientes": None,
            "alergenos": None,
            "tamano_unidad": hit.get("tamano_unidad"),
            "formato_tamano": hit.get("formato_tamano"),
            "precio_unidad": hit.get("precio_unidad"),
            "precio_bulto": hit.get("precio_bulto"),
            "precio_unidad_anterior": None,
            "tienda": "alcampo",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _guardar_y_opcionalmente_enriquecer(
        self, registro: dict[str, Any], *, enriquecer: bool
    ) -> dict[str, Any]:
        existente = self.repositorio.obtener_producto(registro["id"])
        if existente:
            for clave in (
                "nutriscore", "energia_kcal", "proteinas", "hidratos", "grasas",
                "fibra", "azucares", "sal", "nutricion_por",
            ):
                if existente.get(clave) is not None and registro.get(clave) is None:
                    registro[clave] = existente[clave]
            if not registro.get("ean"):
                registro["ean"] = existente.get("ean")
            if not registro.get("ingredientes"):
                registro["ingredientes"] = existente.get("ingredientes")
            if not registro.get("alergenos"):
                registro["alergenos"] = existente.get("alergenos")

        if enriquecer:
            registro = self._enriquecer_registro(registro, persistir=False)

        if registro.get("alergenos") and "x99" in (registro.get("alergenos") or ""):
            registro["alergenos"] = ""

        self.repositorio.guardar_producto(registro)
        self.repositorio.registrar_precio(
            registro["id"], registro.get("precio_unidad"), registro.get("precio_bulto")
        )
        return self.repositorio.obtener_producto(registro["id"]) or registro

    def _enriquecer_registro(
        self, registro: dict[str, Any], *, persistir: bool = True
    ) -> dict[str, Any]:
        off = self.off.enriquecer(
            ean=registro.get("ean"),
            nombre=registro.get("nombre"),
            marca=registro.get("marca"),
        )
        if off:
            if off.get("ean") and not registro.get("ean"):
                registro["ean"] = off["ean"]
            for clave in (
                "nutriscore", "energia_kcal", "proteinas", "hidratos", "grasas",
                "fibra", "azucares", "sal", "nutricion_por",
            ):
                if off.get(clave) is not None:
                    registro[clave] = off[clave]
            if off.get("ingredientes_off") and not registro.get("ingredientes"):
                registro["ingredientes"] = off["ingredientes_off"]
            if off.get("alergenos_off") and (
                not registro.get("alergenos")
                or "x99" in (registro.get("alergenos") or "")
            ):
                registro["alergenos"] = off["alergenos_off"]
        if persistir:
            self.repositorio.guardar_producto(registro)
            return self.repositorio.obtener_producto(registro["id"]) or registro
        return registro
