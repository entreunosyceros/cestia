"""Preferencias de tiendas activas para la búsqueda."""

from __future__ import annotations

from typing import Any

CLAVE_MERCADONA = "buscar_mercadona"
CLAVE_CARREFOUR = "buscar_carrefour"
CLAVE_ALCAMPO = "buscar_alcampo"
CLAVE_FROIZ = "buscar_froiz"
CLAVE_EROSKI = "buscar_eroski"
CLAVE_LIDL = "buscar_lidl"
CLAVE_DIA = "buscar_dia"
CLAVE_GADIS = "buscar_gadis"
CLAVE_TEMA = "tema_ui"


def tienda_activa(repositorio: Any, clave: str, por_defecto: bool = True) -> bool:
    valor = repositorio.obtener_ajuste(clave, "1" if por_defecto else "0")
    return valor.strip() not in {"0", "false", "False", "no", "off"}


def mercadona_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_MERCADONA, True)


def carrefour_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_CARREFOUR, True)


def alcampo_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_ALCAMPO, True)


def froiz_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_FROIZ, True)


def eroski_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_EROSKI, False)


def lidl_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_LIDL, False)


def dia_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_DIA, False)


def gadis_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_GADIS, False)


def guardar_tiendas(
    repositorio: Any,
    *,
    mercadona: bool,
    carrefour: bool,
    alcampo: bool,
    froiz: bool,
    eroski: bool = False,
    lidl: bool = False,
    dia: bool = False,
    gadis: bool = False,
) -> None:
    repositorio.guardar_ajuste(CLAVE_MERCADONA, "1" if mercadona else "0")
    repositorio.guardar_ajuste(CLAVE_CARREFOUR, "1" if carrefour else "0")
    repositorio.guardar_ajuste(CLAVE_ALCAMPO, "1" if alcampo else "0")
    repositorio.guardar_ajuste(CLAVE_FROIZ, "1" if froiz else "0")
    repositorio.guardar_ajuste(CLAVE_EROSKI, "1" if eroski else "0")
    repositorio.guardar_ajuste(CLAVE_LIDL, "1" if lidl else "0")
    repositorio.guardar_ajuste(CLAVE_DIA, "1" if dia else "0")
    repositorio.guardar_ajuste(CLAVE_GADIS, "1" if gadis else "0")


NOMBRES_TIENDA = {
    "mercadona": "Mercadona",
    "carrefour": "Carrefour",
    "alcampo": "Alcampo",
    "froiz": "Froiz",
    "eroski": "Eroski",
    "lidl": "Lidl",
    "dia": "Dia",
    "gadis": "Gadis",
}


def nombre_tienda(tienda: str | None, id_producto: str | None = None) -> str:
    t = (tienda or "").strip().lower()
    pid = str(id_producto or "")
    prefijos = {
        "cf:": "carrefour",
        "ac:": "alcampo",
        "fz:": "froiz",
        "er:": "eroski",
        "ld:": "lidl",
        "di:": "dia",
        "gd:": "gadis",
        "cs:": "consum",  # legacy
    }
    for pref, clave in prefijos.items():
        if pid.startswith(pref):
            t = clave
            break
    if not t and pid.isdigit():
        t = "mercadona"
    if t == "consum":
        return "Consum"
    return NOMBRES_TIENDA.get(t, t.capitalize() if t else "Mercadona")
