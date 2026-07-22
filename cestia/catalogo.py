"""Sincroniza productos de varias tiendas → SQLite."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from typing import Any

from cestia.base_datos.repositorio import Repositorio
from cestia.cliente import ClienteMercadona, obtener_cliente
from cestia.cliente.alcampo import (
    ClienteAlcampo,
    es_id_alcampo,
    obtener_cliente_alcampo,
)
from cestia.cliente.carrefour import (
    ClienteCarrefour,
    es_id_carrefour,
    obtener_cliente_carrefour,
)
from cestia.cliente.froiz import (
    ClienteFroiz,
    es_id_froiz,
    obtener_cliente_froiz,
)
from cestia.cliente.eroski import (
    ClienteEroski,
    es_id_eroski,
    obtener_cliente_eroski,
)
from cestia.cliente.lidl import (
    ClienteLidl,
    es_id_lidl,
    obtener_cliente_lidl,
)
from cestia.cliente.dia import (
    ClienteDia,
    es_id_dia,
    obtener_cliente_dia,
)
from cestia.cliente.gadis import (
    ClienteGadis,
    es_id_gadis,
    obtener_cliente_gadis,
)
from cestia.cliente.fichas import fusionar_ficha, obtener_ficha_tienda
from cestia.enriquecimiento import (
    ClienteOpenFoodFacts,
    deduplicar_alergenos,
    parsear_nutricion_mercadona,
)
from cestia.normalizacion import coincide_consulta, normalizar_producto
from cestia.configuracion import obtener_configuracion
from cestia.tiendas import (
    alcampo_activo,
    carrefour_activo,
    dia_activo,
    eroski_activo,
    froiz_activo,
    gadis_activo,
    lidl_activo,
    mercadona_activo,
)

_ORDEN_TIENDA = {
    "mercadona": 0,
    "carrefour": 1,
    "alcampo": 2,
    "froiz": 3,
    "eroski": 4,
    "lidl": 5,
    "dia": 6,
    "gadis": 7,
}

# Baja prioridad: ruido / no relevantes frente a lo que pide la consulta.
_RE_RUIDO = re.compile(
    r"manguera|grifo|juguete|bricolaje|taladro|tornillo|"
    r"comida perro|comida gato|mascot|\bpienso\b|arenas?\s+para|"
    r"compy|supreme compy",
    re.IGNORECASE,
)
_RE_PROCESADO = re.compile(
    r"fiambre|lonchas?|brasead\w*|al horno|en conserva|enlatad\w*|"
    r"empanad\w*|precocin\w*|nachos",
    re.IGNORECASE,
)
# Consultas / productos de parafarmacia e higiene (no deben quedar fuera).
_RE_PARAFARMACIA = re.compile(
    r"algod[oó]n|oxigenad|betadine|antisept|venda|gasas?|tiritas?|"
    r"parafarmac|farmac|suero\b|alcohol\b|term[oó]metro|mascarilla|"
    r"gel\s+hidro|compresa|protegeslips?|preservativo|pomada|crema\s+solar|"
    r"desinfect|agua\s+oxigen|ibuprofeno|paracetamol|aposito|apósito|"
    r"bastoncill|higiene\s+intima|higiene\s+íntima|pañales?|toallitas",
    re.IGNORECASE,
)


def _penalizacion_busqueda(producto: dict[str, Any], consulta: str) -> int:
    """Ordena resultados: menos puntos = más arriba."""
    nombre = producto.get("nombre") or producto.get("name") or ""
    if _RE_RUIDO.search(nombre):
        return 5
    consulta_farma = bool(_RE_PARAFARMACIA.search(consulta or ""))
    producto_farma = bool(_RE_PARAFARMACIA.search(nombre))
    if consulta_farma:
        # Buscando parafarmacia: priorizar esos productos, no relegarlos.
        return 0 if producto_farma else 2
    if producto_farma:
        return 0
    if not _RE_PROCESADO.search(nombre):
        return 0
    if re.search(r"fiambre|lonchas?|brasead|al horno", nombre, re.I):
        return 2
    return 1


class ServicioCatalogo:
    def __init__(
        self,
        repositorio: Repositorio,
        cliente: ClienteMercadona | None = None,
        cliente_carrefour: ClienteCarrefour | None = None,
        cliente_alcampo: ClienteAlcampo | None = None,
        cliente_froiz: ClienteFroiz | None = None,
        cliente_eroski: ClienteEroski | None = None,
        cliente_lidl: ClienteLidl | None = None,
        cliente_dia: ClienteDia | None = None,
        cliente_gadis: ClienteGadis | None = None,
        off: ClienteOpenFoodFacts | None = None,
    ) -> None:
        self.repositorio = repositorio
        self.cliente = cliente or obtener_cliente()
        self.cliente_carrefour = cliente_carrefour or obtener_cliente_carrefour()
        self.cliente_alcampo = cliente_alcampo or obtener_cliente_alcampo()
        self.cliente_froiz = cliente_froiz or obtener_cliente_froiz()
        self.cliente_eroski = cliente_eroski or obtener_cliente_eroski()
        self.cliente_lidl = cliente_lidl or obtener_cliente_lidl()
        self.cliente_dia = cliente_dia or obtener_cliente_dia()
        self.cliente_gadis = cliente_gadis or obtener_cliente_gadis()
        self.off = off or ClienteOpenFoodFacts()

    def buscar(self, consulta: str, limite: int = 24) -> list[dict[str, Any]]:
        """API síncrona (UI / hilos). Las tiendas se consultan en paralelo."""
        return asyncio.run(self.buscar_async(consulta, limite=limite))

    async def buscar_async(
        self, consulta: str, limite: int = 24
    ) -> list[dict[str, Any]]:
        """Consulta todas las tiendas activas en paralelo y unifica resultados.

        Los clientes HTTP siguen siendo síncronos: cada ``.buscar`` se ejecuta
        en un hilo con ``asyncio.to_thread``. La persistencia en SQLite se hace
        después, en serie, para no mezclar escrituras concurrentes.
        """
        trabajos: list[tuple[str, Callable[[], Any]]] = []

        if mercadona_activo(self.repositorio):
            trabajos.append(
                (
                    "Mercadona",
                    lambda: self.cliente.buscar(consulta, limite=limite),
                )
            )
        if carrefour_activo(self.repositorio):
            trabajos.append(
                (
                    "Carrefour",
                    lambda: self.cliente_carrefour.buscar(consulta, limite=limite),
                )
            )
        if alcampo_activo(self.repositorio):
            trabajos.append(
                (
                    "Alcampo",
                    lambda: self.cliente_alcampo.buscar(consulta, limite=limite),
                )
            )
        if froiz_activo(self.repositorio):
            trabajos.append(
                (
                    "Froiz",
                    lambda: self.cliente_froiz.buscar(consulta, limite=limite),
                )
            )
        if eroski_activo(self.repositorio):
            trabajos.append(
                (
                    "Eroski",
                    lambda: self.cliente_eroski.buscar(consulta, limite=limite),
                )
            )
        if lidl_activo(self.repositorio):
            trabajos.append(
                (
                    "Lidl",
                    lambda: self.cliente_lidl.buscar(consulta, limite=limite),
                )
            )
        if dia_activo(self.repositorio):
            trabajos.append(
                (
                    "Dia",
                    lambda: self.cliente_dia.buscar(consulta, limite=limite),
                )
            )
        if gadis_activo(self.repositorio):
            trabajos.append(
                (
                    "Gadis",
                    lambda: self.cliente_gadis.buscar(consulta, limite=limite),
                )
            )

        if not trabajos:
            return []

        # Los clientes usan timeout_http; Froiz puede hacer 2 fases (búsqueda + fichas).
        # wait_for va por tienda (nunca alrededor del gather): si una caduca, las demás siguen.
        tope_tienda = obtener_configuracion().timeout_http * 2 + 2.0

        async def _consultar_tienda(
            etiqueta: str, fn: Callable[[], Any]
        ) -> tuple[str, Any]:
            try:
                datos = await asyncio.wait_for(
                    asyncio.to_thread(fn),
                    timeout=tope_tienda,
                )
                return etiqueta, datos
            except TimeoutError:
                return (
                    etiqueta,
                    TimeoutError(f"sin respuesta en {tope_tienda:.0f}s"),
                )
            except Exception as exc:  # noqa: BLE001
                return etiqueta, exc

        # Una corrutina por tienda, cada una con su wait_for aislado.
        tareas = [
            _consultar_tienda(etiqueta, fn) for etiqueta, fn in trabajos
        ]
        brutos = await asyncio.gather(*tareas)

        resultados: list[dict[str, Any]] = []
        errores: list[str] = []

        for etiqueta, bruto in brutos:
            if isinstance(bruto, BaseException):
                errores.append(f"{etiqueta}: {bruto}")
                continue
            try:
                resultados.extend(self._persistir_bruto_tienda(etiqueta, bruto))
            except Exception as exc:  # noqa: BLE001
                errores.append(f"{etiqueta}: {exc}")

        if not resultados and errores:
            raise RuntimeError(" · ".join(errores))

        # Relevancia por nombre en todas las tiendas (evita mangueras con «manzana»,
        # y no exige la palabra «fresco» en el título del producto).
        resultados = [
            p
            for p in resultados
            if coincide_consulta(consulta, p.get("nombre") or p.get("name"))
        ]

        resultados.sort(
            key=lambda p: (
                _penalizacion_busqueda(p, consulta),
                _ORDEN_TIENDA.get((p.get("tienda") or "mercadona"), 9),
                p.get("precio_unidad") is None,
                p.get("precio_unidad") or 1e9,
            )
        )
        return resultados

    def _persistir_bruto_tienda(
        self, etiqueta: str, bruto: Any
    ) -> list[dict[str, Any]]:
        """Convierte la respuesta cruda de una tienda en registros persistidos."""
        productos: list[dict[str, Any]] = []
        if etiqueta == "Mercadona":
            for acierto in (bruto or {}).get("hits") or []:
                producto = self._persistir_mercadona(acierto, enriquecer=False)
                if acierto.get("_precios_actualizados_en"):
                    producto["_precios_actualizados_en"] = acierto[
                        "_precios_actualizados_en"
                    ]
                elif isinstance(bruto, dict) and bruto.get("_precios_actualizados_en"):
                    producto["_precios_actualizados_en"] = bruto[
                        "_precios_actualizados_en"
                    ]
                productos.append(producto)
            return productos

        persistidores = {
            "Carrefour": self._persistir_carrefour,
            "Alcampo": self._persistir_alcampo,
            "Froiz": self._persistir_froiz,
            "Eroski": self._persistir_eroski,
            "Lidl": self._persistir_lidl,
            "Dia": self._persistir_dia,
            "Gadis": self._persistir_gadis,
        }
        persistir = persistidores.get(etiqueta)
        if persistir is None:
            return productos
        for hit in bruto or []:
            producto = persistir(hit, enriquecer=False)
            if isinstance(hit, dict) and hit.get("_precios_actualizados_en"):
                producto["_precios_actualizados_en"] = hit["_precios_actualizados_en"]
            productos.append(producto)
        return productos

    def obtener_producto(
        self, id_producto: str, *, enriquecer: bool = True
    ) -> dict[str, Any]:
        if (
            es_id_carrefour(id_producto)
            or es_id_alcampo(id_producto)
            or es_id_froiz(id_producto)
            or es_id_eroski(id_producto)
            or es_id_lidl(id_producto)
            or es_id_dia(id_producto)
            or es_id_gadis(id_producto)
        ):
            local = self.repositorio.obtener_producto(id_producto)
            if local:
                if enriquecer:
                    local = fusionar_ficha(local, obtener_ficha_tienda(local))
                    return self._enriquecer_registro(local)
                return local
            if es_id_carrefour(id_producto):
                marca = "Carrefour"
            elif es_id_alcampo(id_producto):
                marca = "Alcampo"
            elif es_id_froiz(id_producto):
                marca = "Froiz"
            elif es_id_eroski(id_producto):
                marca = "Eroski"
            elif es_id_lidl(id_producto):
                marca = "Lidl"
            elif es_id_dia(id_producto):
                marca = "Dia"
            else:
                marca = "Gadis"
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
                    es_id_carrefour(acierto["id"])
                    or es_id_alcampo(acierto["id"])
                    or es_id_froiz(acierto["id"])
                    or es_id_eroski(acierto["id"])
                    or es_id_lidl(acierto["id"])
                    or es_id_dia(acierto["id"])
                    or es_id_gadis(acierto["id"])
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

    def _persistir_froiz(
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
            "tienda": "froiz",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _persistir_eroski(
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
            "tienda": "eroski",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _persistir_lidl(
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
            "tienda": "lidl",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _persistir_dia(
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
            "precio_unidad_anterior": hit.get("precio_unidad_anterior"),
            "tienda": "dia",
        }
        return self._guardar_y_opcionalmente_enriquecer(registro, enriquecer=enriquecer)

    def _persistir_gadis(
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
            "precio_unidad_anterior": hit.get("precio_unidad_anterior"),
            "tienda": "gadis",
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
            if not registro.get("marca"):
                registro["marca"] = existente.get("marca")
            if not registro.get("miniatura"):
                registro["miniatura"] = existente.get("miniatura")

        if not registro.get("marca"):
            from cestia.normalizacion import inferir_marca

            registro["marca"] = inferir_marca(registro.get("nombre"))
        if registro.get("marca"):
            registro["brand"] = registro["marca"]

        if enriquecer:
            registro = self._enriquecer_registro(registro, persistir=False)

        if registro.get("alergenos") and "x99" in (registro.get("alergenos") or ""):
            registro["alergenos"] = ""
        if registro.get("alergenos"):
            registro["alergenos"] = deduplicar_alergenos(registro["alergenos"])

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
                registro["alergenos"] = deduplicar_alergenos(off["alergenos_off"])
        if persistir:
            if registro.get("alergenos"):
                registro["alergenos"] = deduplicar_alergenos(registro["alergenos"])
            self.repositorio.guardar_producto(registro)
            return self.repositorio.obtener_producto(registro["id"]) or registro
        return registro
