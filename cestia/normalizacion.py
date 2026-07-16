"""Normalización de productos y categorías."""

from __future__ import annotations

from typing import Any


def _a_dinero(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def normalizar_producto(bruto: dict[str, Any], *, origen: str = "api") -> dict[str, Any]:
    """Unifica forma REST y resultados de Algolia."""
    precio = bruto.get("price_instructions") or {}
    precio_unidad = _a_dinero(
        precio.get("unit_price") or bruto.get("unit_price") or bruto.get("price")
    )
    precio_bulto = _a_dinero(precio.get("bulk_price") or bruto.get("bulk_price"))
    anterior = _a_dinero(
        precio.get("previous_unit_price")
        or bruto.get("previous_unit_price")
        or bruto.get("previous_price")
    )
    formato_tamano = precio.get("size_format") or bruto.get("size_format") or ""
    tamano_unidad = precio.get("unit_size") or bruto.get("unit_size")
    envase = bruto.get("packaging") or ""
    if not envase and precio.get("is_pack") and precio.get("total_units"):
        nombre_unidad = precio.get("unit_name") or "ud"
        envase = f"Pack {int(precio['total_units'])} {nombre_unidad}"
    nombre = (
        bruto.get("display_name")
        or bruto.get("display_name_es")
        or bruto.get("name")
        or bruto.get("label")
        or "Producto"
    )
    miniatura = bruto.get("thumbnail") or bruto.get("image_url")
    fotos = bruto.get("photos")
    if not miniatura and isinstance(fotos, list) and fotos:
        primera = fotos[0] if isinstance(fotos[0], dict) else {}
        miniatura = primera.get("thumbnail") or primera.get("regular")
    imagenes = bruto.get("images")
    if not miniatura and isinstance(imagenes, list) and imagenes:
        miniatura = imagenes[0] if isinstance(imagenes[0], str) else None

    rebajado = bool(
        precio.get("price_decreased")
        or (anterior is not None and precio_unidad is not None and anterior > precio_unidad)
    )

    return {
        "id": str(bruto.get("id") or bruto.get("objectID") or ""),
        "nombre": nombre,
        "marca": bruto.get("brand") or (bruto.get("details") or {}).get("brand"),
        "envase": envase,
        "miniatura": miniatura,
        "precio_unidad": precio_unidad,
        "precio_unidad_anterior": anterior,
        "precio_bulto": precio_bulto,
        "formato_tamano": formato_tamano,
        "tamano_unidad": tamano_unidad,
        "precio_rebajado": rebajado,
        "url_compartir": bruto.get("share_url"),
        "slug": bruto.get("slug"),
        "es_nuevo": bool(
            precio.get("is_new") or bruto.get("is_new") or bruto.get("is_new_arrival")
        ),
        "origen": origen,
        "categorias_brutas": bruto.get("categories") or [],
        # alias compatibles con código que aún use claves EN de la API
        "name": nombre,
        "brand": bruto.get("brand") or (bruto.get("details") or {}).get("brand"),
        "packaging": envase,
        "thumbnail": miniatura,
        "unit_price": precio_unidad,
        "previous_unit_price": anterior,
        "bulk_price": precio_bulto,
        "size_format": formato_tamano,
        "unit_size": tamano_unidad,
        "price_decreased": rebajado,
        "share_url": bruto.get("share_url"),
        "is_new": bool(
            precio.get("is_new") or bruto.get("is_new") or bruto.get("is_new_arrival")
        ),
        "raw_categories": bruto.get("categories") or [],
    }


def formatear_euros(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def aplanar_arbol_categorias(
    categorias: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plano: list[dict[str, Any]] = []
    for superior in categorias:
        hijos = []
        for media in superior.get("categories") or []:
            hijos.append(
                {
                    "id": media.get("id"),
                    "nombre": media.get("name"),
                    "name": media.get("name"),
                    "publicado": media.get("published", True),
                }
            )
        plano.append(
            {
                "id": superior.get("id"),
                "nombre": superior.get("name"),
                "name": superior.get("name"),
                "hijos": hijos,
                "children": hijos,
            }
        )
    return plano


def agrupar_estanterias_categoria(categoria: dict[str, Any]) -> list[dict[str, Any]]:
    estanterias: list[dict[str, Any]] = []
    for hija in categoria.get("categories") or []:
        productos = [normalizar_producto(p) for p in (hija.get("products") or [])]
        estanterias.append(
            {
                "id": hija.get("id"),
                "nombre": hija.get("name"),
                "name": hija.get("name"),
                "subtitulo": hija.get("subtitle"),
                "subtitle": hija.get("subtitle"),
                "productos": productos,
                "products": productos,
            }
        )
    if not estanterias and categoria.get("products"):
        productos = [normalizar_producto(p) for p in categoria["products"]]
        estanterias.append(
            {
                "id": categoria.get("id"),
                "nombre": categoria.get("name"),
                "name": categoria.get("name"),
                "subtitulo": None,
                "subtitle": None,
                "productos": productos,
                "products": productos,
            }
        )
    return estanterias
