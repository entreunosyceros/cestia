"""Agrupación multi-tienda, filtros y detección de ofertas."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _precio(producto: dict[str, Any]) -> float | None:
    p = producto.get("precio_unidad")
    if p is None:
        p = producto.get("unit_price")
    try:
        return float(p) if p is not None else None
    except (TypeError, ValueError):
        return None


def _normalizar_nombre(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", (nombre or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def clave_agrupacion(producto: dict[str, Any]) -> str:
    """Agrupa el mismo producto entre tiendas por EAN o nombre parecido."""
    ean = (producto.get("ean") or "").strip()
    if ean and len(ean) >= 8:
        return f"ean:{ean}"
    nombre = _normalizar_nombre(producto.get("nombre") or producto.get("name") or "")
    if not nombre:
        return f"id:{producto.get('id')}"
    tokens = sorted(t for t in nombre.split() if len(t) > 2)[:4]
    return "nom:" + "|".join(tokens)


def es_rebajado(
    producto: dict[str, Any],
    historial: list[dict[str, Any]] | None = None,
) -> bool:
    """True si hay precio anterior mayor o bajada respecto al historial."""
    actual = _precio(producto)
    if actual is None:
        return False
    anterior = producto.get("precio_unidad_anterior") or producto.get(
        "previous_unit_price"
    )
    try:
        if anterior is not None and float(anterior) > actual + 0.001:
            return True
    except (TypeError, ValueError):
        pass
    if historial and len(historial) >= 2:
        try:
            ultimos = [
                float(h["precio_unidad"])
                for h in historial[-6:]
                if h.get("precio_unidad") is not None
            ]
            if len(ultimos) >= 2:
                max_reciente = max(ultimos[:-1])
                if max_reciente > actual + 0.001:
                    return True
        except (TypeError, ValueError):
            pass
    return False


def agrupar_multi_tienda(
    resultados: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agrupa resultados y añade mejor precio / ahorro entre tiendas."""
    grupos: dict[str, list[dict[str, Any]]] = {}
    for p in resultados:
        grupos.setdefault(clave_agrupacion(p), []).append(p)

    filas: list[dict[str, Any]] = []
    for miembros in grupos.values():
        con_precio = [m for m in miembros if _precio(m) is not None]
        if not con_precio:
            filas.extend(miembros)
            continue
        mejor = min(con_precio, key=lambda m: _precio(m) or 1e9)
        peor = max(con_precio, key=lambda m: _precio(m) or 0)
        ahorro = None
        pm, pp = _precio(mejor), _precio(peor)
        if pm is not None and pp is not None and pp > pm:
            ahorro = round(pp - pm, 2)
        for m in miembros:
            m = dict(m)
            m["_grupo_tamano"] = len(miembros)
            m["_mejor_tienda"] = mejor.get("tienda")
            m["_mejor_precio"] = pm
            m["_ahorro_max"] = ahorro
            m["_es_mejor"] = m.get("id") == mejor.get("id")
            filas.append(m)
    filas.sort(
        key=lambda p: (
            p.get("_mejor_precio") is None,
            p.get("_mejor_precio") or 1e9,
            p.get("nombre") or p.get("name") or "",
        )
    )
    return filas


def filtrar_resultados(
    resultados: list[dict[str, Any]],
    *,
    tiendas: set[str] | None = None,
    precio_min: float | None = None,
    precio_max: float | None = None,
    nutriscore: set[str] | None = None,
    solo_rebajados: bool = False,
    sin_gluten: bool = False,
    solo_favoritos: set[str] | None = None,
    historial_fn=None,
) -> list[dict[str, Any]]:
    """Filtra resultados de búsqueda según criterios de UI."""
    filtrados: list[dict[str, Any]] = []
    for p in resultados:
        tienda = (p.get("tienda") or "mercadona").lower()
        if tiendas and tienda not in tiendas:
            continue
        precio = _precio(p)
        if precio_min is not None and (precio is None or precio < precio_min):
            continue
        if precio_max is not None and (precio is None or precio > precio_max):
            continue
        if nutriscore:
            ns = (p.get("nutriscore") or "").upper()
            if ns not in {n.upper() for n in nutriscore}:
                continue
        if sin_gluten:
            al = (
                (p.get("alergenos") or p.get("allergens") or "")
                + " "
                + (p.get("ingredientes") or p.get("ingredients") or "")
            ).lower()
            if "gluten" in al and "sin gluten" not in al:
                continue
        if solo_favoritos is not None and p.get("id") not in solo_favoritos:
            continue
        if solo_rebajados:
            hist = historial_fn(p["id"]) if historial_fn else None
            if not es_rebajado(p, hist):
                continue
        filtrados.append(p)
    return filtrados
