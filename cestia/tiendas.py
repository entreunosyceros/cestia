"""Preferencias de tiendas activas para la búsqueda."""

from __future__ import annotations

from typing import Any

CLAVE_MERCADONA = "buscar_mercadona"
CLAVE_CARREFOUR = "buscar_carrefour"
CLAVE_ALCAMPO = "buscar_alcampo"


def tienda_activa(repositorio: Any, clave: str, por_defecto: bool = True) -> bool:
    valor = repositorio.obtener_ajuste(clave, "1" if por_defecto else "0")
    return valor.strip() not in {"0", "false", "False", "no", "off"}


def mercadona_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_MERCADONA, True)


def carrefour_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_CARREFOUR, True)


def alcampo_activo(repositorio: Any) -> bool:
    return tienda_activa(repositorio, CLAVE_ALCAMPO, True)


def guardar_tiendas(
    repositorio: Any,
    *,
    mercadona: bool,
    carrefour: bool,
    alcampo: bool,
) -> None:
    repositorio.guardar_ajuste(CLAVE_MERCADONA, "1" if mercadona else "0")
    repositorio.guardar_ajuste(CLAVE_CARREFOUR, "1" if carrefour else "0")
    repositorio.guardar_ajuste(CLAVE_ALCAMPO, "1" if alcampo else "0")
