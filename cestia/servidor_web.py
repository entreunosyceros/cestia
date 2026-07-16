"""Servidor web opcional de CestIA."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cestia import __version__
from cestia.cliente import ErrorAPIMercadona, obtener_cliente
from cestia.configuracion import obtener_configuracion
from cestia.normalizacion import (
    aplanar_arbol_categorias,
    agrupar_estanterias_categoria,
    formatear_euros,
    normalizar_producto,
)

logging.basicConfig(level=logging.INFO)
registrador = logging.getLogger("cestia")

DIRECTORIO_BASE = Path(__file__).resolve().parent
plantillas = Jinja2Templates(directory=str(DIRECTORIO_BASE / "plantillas"))
plantillas.env.globals["format_eur"] = formatear_euros
plantillas.env.globals["formatear_euros"] = formatear_euros
plantillas.env.globals["app_version"] = __version__

aplicacion = FastAPI(
    title="CestIA",
    description="Consulta personal de precios Mercadona (API no oficial)",
    version=__version__,
)
aplicacion.mount(
    "/static",
    StaticFiles(directory=str(DIRECTORIO_BASE / "estaticos")),
    name="static",
)


def _error_api(exc: ErrorAPIMercadona) -> HTTPException:
    estado = (
        exc.codigo_estado
        if exc.codigo_estado and exc.codigo_estado < 500
        else 502
    )
    return HTTPException(status_code=estado or 502, detail=str(exc))


@aplicacion.get("/", response_class=HTMLResponse)
async def inicio(request: Request, q: str = "") -> HTMLResponse:
    cliente = obtener_cliente()
    configuracion = obtener_configuracion()
    salud = cliente.comprobar_salud()
    resultados: list[dict[str, Any]] = []
    total_aciertos = 0
    error: str | None = None

    if q.strip():
        try:
            bruto = cliente.buscar(q.strip())
            resultados = [
                normalizar_producto(h, origen="busqueda")
                for h in bruto.get("hits") or []
            ]
            total_aciertos = int(bruto.get("nbHits") or len(resultados))
        except ErrorAPIMercadona as exc:
            error = str(exc)

    try:
        categorias = aplanar_arbol_categorias(cliente.listar_categorias())
    except ErrorAPIMercadona:
        categorias = []

    return plantillas.TemplateResponse(
        request,
        "index.html",
        {
            "query": q,
            "results": resultados,
            "nb_hits": total_aciertos,
            "categories": categorias,
            "health": {
                "ok": salud.get("ok"),
                "error": salud.get("error"),
            },
            "warehouse": configuracion.almacen_mercadona,
            "error": error,
        },
    )


@aplicacion.get("/categoria/{id_categoria}", response_class=HTMLResponse)
async def pagina_categoria(request: Request, id_categoria: int) -> HTMLResponse:
    cliente = obtener_cliente()
    try:
        categoria = cliente.obtener_categoria(id_categoria)
    except ErrorAPIMercadona as exc:
        raise _error_api(exc) from exc

    estanterias = agrupar_estanterias_categoria(categoria)
    return plantillas.TemplateResponse(
        request,
        "category.html",
        {
            "category": categoria,
            "shelves": estanterias,
            "health": cliente.comprobar_salud(),
            "warehouse": obtener_configuracion().almacen_mercadona,
        },
    )


@aplicacion.get("/producto/{id_producto}", response_class=HTMLResponse)
async def pagina_producto(request: Request, id_producto: str) -> HTMLResponse:
    cliente = obtener_cliente()
    try:
        bruto = cliente.obtener_producto(id_producto)
    except ErrorAPIMercadona as exc:
        raise _error_api(exc) from exc

    producto = normalizar_producto(bruto)
    detalles = bruto.get("details") or {}
    fotos = bruto.get("photos") or []
    return plantillas.TemplateResponse(
        request,
        "product.html",
        {
            "product": producto,
            "raw": bruto,
            "details": detalles,
            "photos": fotos,
            "health": cliente.comprobar_salud(),
            "warehouse": obtener_configuracion().almacen_mercadona,
        },
    )


@aplicacion.get("/api/salud")
@aplicacion.get("/api/health")
async def api_salud(forzar: bool = False, force: bool = False) -> JSONResponse:
    salud = obtener_cliente().comprobar_salud(forzar=forzar or force)
    estado = 200 if salud.get("ok") else 503
    return JSONResponse(salud, status_code=estado)


@aplicacion.get("/api/categorias")
@aplicacion.get("/api/categories")
async def api_categorias() -> list[dict[str, Any]]:
    try:
        return aplanar_arbol_categorias(obtener_cliente().listar_categorias())
    except ErrorAPIMercadona as exc:
        raise _error_api(exc) from exc


@aplicacion.get("/api/categorias/{id_categoria}")
@aplicacion.get("/api/categories/{id_categoria}")
async def api_categoria(id_categoria: int) -> dict[str, Any]:
    try:
        categoria = obtener_cliente().obtener_categoria(id_categoria)
    except ErrorAPIMercadona as exc:
        raise _error_api(exc) from exc
    return {
        "id": categoria.get("id"),
        "nombre": categoria.get("name"),
        "estanterias": agrupar_estanterias_categoria(categoria),
    }


@aplicacion.get("/api/productos/{id_producto}")
@aplicacion.get("/api/products/{id_producto}")
async def api_producto(id_producto: str) -> dict[str, Any]:
    try:
        bruto = obtener_cliente().obtener_producto(id_producto)
    except ErrorAPIMercadona as exc:
        raise _error_api(exc) from exc
    return {"producto": normalizar_producto(bruto), "bruto": bruto}


@aplicacion.get("/api/buscar")
@aplicacion.get("/api/search")
async def api_buscar(
    q: str = Query(..., min_length=1),
    limite: int = Query(24, ge=1, le=50),
    limit: int | None = None,
) -> dict[str, Any]:
    tope = limit if limit is not None else limite
    try:
        bruto = obtener_cliente().buscar(q, limite=tope)
    except ErrorAPIMercadona as exc:
        raise _error_api(exc) from exc
    return {
        "consulta": q,
        "total": bruto.get("nbHits", 0),
        "resultados": [
            normalizar_producto(h, origen="busqueda") for h in bruto.get("hits") or []
        ],
    }


@aplicacion.post("/api/cache/vaciar")
@aplicacion.post("/api/cache/clear")
async def api_vaciar_cache() -> dict[str, Any]:
    eliminados = obtener_cliente().vaciar_cache()
    return {"eliminados": eliminados}
