"""Normalización de productos y categorías."""

from __future__ import annotations

import re
from typing import Any

_GENERICOS_NOMBRE = {
    "aceite", "agua", "arroz", "azucar", "azúcar", "bebida", "café", "cafe",
    "carne", "cerveza", "chocolate", "cola", "crema", "detergente", "dulce",
    "filete", "fruta", "galletas", "harina", "huevos", "huevo", "jugo",
    "leche", "mantequilla", "mermelada", "pan", "pasta", "pescado", "pizza",
    "pollo", "queso", "refresco", "sal", "salsa", "snack", "sopa", "té", "te",
    "tomate", "vino", "yogur", "yogurt", "zumo", "pack", "packs", "lonchas",
    "semidesnatada", "desnatada", "entera", "fresca", "fresco", "natural",
    "integral", "extra", "virgen", "eco", "bio", "sin", "con", "del", "de",
    "la", "el", "los", "las", "para", "y", "en", "galicia", "asturiana",
    "pais", "país", "vasco", "navarra",
}

_UNIDADES_ENVASE = {
    "brik", "botella", "lata", "pack", "ud", "uds", "g", "kg", "ml", "l",
    "litro", "litros", "gramos", "kilos", "unidad", "unidades", "caja",
}


def inferir_marca(
    nombre: str | None,
    marca: str | None = None,
    *,
    fallback: str | None = None,
) -> str | None:
    """Devuelve marca explícita o una estimación razonable a partir del nombre."""
    if marca is not None and str(marca).strip():
        limpia = str(marca).strip()
        if limpia.lower() not in {"none", "null", "unknown", "-"}:
            return limpia

    texto = (nombre or "").strip()
    if not texto:
        return fallback

    principal = re.split(r"[,|·•]", texto, maxsplit=1)[0].strip()
    tokens = [t for t in re.split(r"\s+", principal) if t]
    if len(tokens) < 2:
        return fallback

    candidatos: list[str] = []
    i = len(tokens) - 1
    while i >= 0:
        tok = tokens[i]
        bajo = re.sub(r"[^0-9a-záéíóúüñ]", "", tok.lower())
        if not bajo or bajo in _UNIDADES_ENVASE or bajo.isdigit():
            i -= 1
            continue
        if bajo in _GENERICOS_NOMBRE:
            break
        if tok[:1].isupper() or tok.isupper() or (len(tok) > 2 and tok.isalnum()):
            candidatos.append(tok)
            i -= 1
            # marcas de 2 palabras tipo "Dia Láctea" / "LA CANTARA"
            if i >= 0:
                prev = tokens[i]
                prev_bajo = re.sub(r"[^0-9a-záéíóúüñ]", "", prev.lower())
                if (
                    prev[:1].isupper()
                    and prev_bajo not in _GENERICOS_NOMBRE
                    and prev_bajo not in _UNIDADES_ENVASE
                    and not prev_bajo.isdigit()
                ):
                    candidatos.append(prev)
                    i -= 1
            break
        i -= 1

    if candidatos:
        marca_est = " ".join(reversed(candidatos)).strip(" ,.-")
        if marca_est and marca_est.lower() not in _GENERICOS_NOMBRE:
            return marca_est
    return fallback


_STOPWORDS_BUSQUEDA = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "y", "o", "en", "con", "para", "por", "a", "al", "the",
    "producto", "productos", "articulo", "artículos", "articulo", "articulos",
}

# Cualificadores que el usuario añade pero a menudo no figuran en el nombre del súper.
_CUALIFICADORES_OPCIONALES = {
    "fresco", "fresca", "frescos", "frescas",
    "congelado", "congelada", "congelados", "congeladas",
    "natural", "naturales", "casero", "casera", "caseros", "caseras",
    "aprox", "aproximado", "aproximada", "granel",
}


def tokens_consulta(consulta: str) -> list[str]:
    """Palabras significativas de una búsqueda (sin stopwords cortas)."""
    palabras = re.findall(r"[0-9a-záéíóúüñ]+", (consulta or "").casefold())
    return [p for p in palabras if len(p) > 2 and p not in _STOPWORDS_BUSQUEDA]


def coincide_consulta(consulta: str, nombre: str | None) -> bool:
    """True si el nombre cubre los términos clave de la consulta.

    Consultas cortas (≤3 tokens) exigen todos los términos obligatorios; las
    largas, al menos 2/3. Los cualificadores («fresco», «congelado»…) son
    opcionales: si no están en el nombre, no descartan el producto.
    Evita falsos positivos tipo «manzana» → «manguera» / «lomo» → «lona».
    """
    tokens = tokens_consulta(consulta)
    if not tokens:
        return True
    obligatorios = [t for t in tokens if t not in _CUALIFICADORES_OPCIONALES]
    if not obligatorios:
        # Solo cualificadores (p. ej. «frescos»): no filtrar por nombre.
        return True

    palabras = set(re.findall(r"[0-9a-záéíóúüñ]+", (nombre or "").casefold()))
    if not palabras:
        return False

    def _cubre(token: str) -> bool:
        for w in palabras:
            if w == token:
                return True
            # Prefijos solo entre palabras «largas» (evita manzana≈m por «20 m»).
            if len(token) >= 4 and len(w) >= 4:
                if w.startswith(token) or token.startswith(w):
                    return True
        return False

    aciertos = sum(1 for t in obligatorios if _cubre(t))
    if len(obligatorios) <= 3:
        return aciertos == len(obligatorios)
    minimo = max(2, (len(obligatorios) * 2 + 2) // 3)
    return aciertos >= minimo


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
    marca = inferir_marca(
        nombre,
        bruto.get("brand") or (bruto.get("details") or {}).get("brand"),
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
        "marca": marca,
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
        "brand": marca,
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
