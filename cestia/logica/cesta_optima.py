"""Calcula la cesta más barata por tienda o mezclando tiendas."""

from __future__ import annotations

from typing import Any


def _precio(item: dict[str, Any]) -> float:
    p = item.get("precio_unidad") or item.get("unit_price")
    try:
        return float(p or 0)
    except (TypeError, ValueError):
        return 0.0


def _cantidad(item: dict[str, Any]) -> float:
    try:
        return float(item.get("cantidad") or item.get("quantity") or 1)
    except (TypeError, ValueError):
        return 1.0


def calcular_cesta_por_tienda(
    items: list[dict[str, Any]],
    alternativas: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """
    Para cada tienda, suma el precio de los productos de la cesta
    (o alternativas más baratas en esa tienda si existen).
    """
    if not items:
        return {"por_tienda": [], "mejor_tienda": None, "ahorro_vs_peor": 0.0}

    tiendas = sorted({(i.get("tienda") or "mercadona").lower() for i in items})
    alternativas = alternativas or {}
    filas: list[dict[str, Any]] = []

    for tienda in tiendas:
        total = 0.0
        cubiertos = 0
        for item in items:
            pid = item["id"]
            cant = _cantidad(item)
            candidatos = [item] + [
                a
                for a in alternativas.get(pid, [])
                if (a.get("tienda") or "").lower() == tienda
            ]
            precios = [_precio(c) for c in candidatos if _precio(c) > 0]
            if precios:
                total += min(precios) * cant
                cubiertos += 1
            else:
                if (item.get("tienda") or "").lower() == tienda:
                    total += _precio(item) * cant
                    cubiertos += 1
        filas.append(
            {
                "tienda": tienda,
                "total": round(total, 2),
                "productos_cubiertos": cubiertos,
                "productos_total": len(items),
            }
        )

    filas.sort(key=lambda f: f["total"])
    mejor = filas[0] if filas else None
    peor = filas[-1] if filas else None
    ahorro = 0.0
    if mejor and peor and peor["total"] > mejor["total"]:
        ahorro = round(peor["total"] - mejor["total"], 2)

    return {
        "por_tienda": filas,
        "mejor_tienda": mejor,
        "ahorro_vs_peor": ahorro,
    }


def calcular_cesta_optima_mezclada(
    items: list[dict[str, Any]],
    alternativas: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Elige la tienda más barata por cada línea de la cesta."""
    if not items:
        return {"total": 0.0, "lineas": [], "tiendas_usadas": {}}

    alternativas = alternativas or {}
    lineas: list[dict[str, Any]] = []
    total = 0.0
    tiendas_usadas: dict[str, float] = {}

    for item in items:
        pid = item["id"]
        cant = _cantidad(item)
        candidatos = [item] + list(alternativas.get(pid, []))
        validos = [c for c in candidatos if _precio(c) > 0]
        if not validos:
            continue
        mejor = min(validos, key=_precio)
        sub = round(_precio(mejor) * cant, 2)
        total += sub
        tienda = (mejor.get("tienda") or "mercadona").lower()
        tiendas_usadas[tienda] = tiendas_usadas.get(tienda, 0.0) + sub
        lineas.append(
            {
                "id_producto": pid,
                "nombre": mejor.get("nombre") or mejor.get("name"),
                "tienda": tienda,
                "precio_unidad": _precio(mejor),
                "cantidad": cant,
                "subtotal": sub,
            }
        )

    return {
        "total": round(total, 2),
        "lineas": lineas,
        "tiendas_usadas": tiendas_usadas,
    }
