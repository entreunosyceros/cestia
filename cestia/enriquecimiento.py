"""Enriquecimiento nutricional vía Open Food Facts."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

registrador = logging.getLogger(__name__)
AGENTE_USUARIO = "CestIA/0.2 (personal; app local)"


def quitar_html(html: str | None) -> str:
    if not html:
        return ""
    texto = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    texto = re.sub(r"</p\s*>", "\n", texto, flags=re.I)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"&nbsp;", " ", texto)
    texto = re.sub(r"&amp;", "&", texto)
    texto = re.sub(r"\s+\n", "\n", texto)
    return re.sub(r"[ \t]+", " ", texto).strip()


def parsear_nutricion_mercadona(bruto: dict[str, Any]) -> dict[str, Any]:
    info = bruto.get("nutrition_information") or {}
    return {
        "ingredientes": quitar_html(info.get("ingredients")),
        "alergenos": quitar_html(info.get("allergens")),
    }


class ClienteOpenFoodFacts:
    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def por_ean(self, ean: str) -> dict[str, Any] | None:
        if not ean:
            return None
        url = f"https://world.openfoodfacts.org/api/v2/product/{ean}.json"
        try:
            with httpx.Client(
                timeout=self.timeout, headers={"User-Agent": AGENTE_USUARIO}
            ) as cliente:
                respuesta = cliente.get(url)
            if respuesta.status_code != 200:
                return None
            datos = respuesta.json()
            if datos.get("status") != 1:
                return None
            return self._extraer(datos.get("product") or {})
        except httpx.HTTPError as exc:
            registrador.info("OFF EAN falló %s: %s", ean, exc)
            return None

    def buscar(self, consulta: str) -> dict[str, Any] | None:
        if not consulta.strip():
            return None
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        parametros = {
            "search_terms": consulta,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
            "fields": (
                "code,product_name,brands,nutriscore_grade,nutriments,"
                "allergens_tags,ingredients_text"
            ),
        }
        try:
            with httpx.Client(
                timeout=self.timeout, headers={"User-Agent": AGENTE_USUARIO}
            ) as cliente:
                respuesta = cliente.get(url, params=parametros)
            respuesta.raise_for_status()
            productos = respuesta.json().get("products") or []
            if not productos:
                return None
            return self._extraer(productos[0])
        except httpx.HTTPError as exc:
            registrador.info("OFF búsqueda falló: %s", exc)
            return None

    def enriquecer(
        self, *, ean: str | None, nombre: str | None, marca: str | None
    ) -> dict[str, Any]:
        if ean:
            datos = self.por_ean(ean)
            if datos:
                return datos
        if nombre:
            consulta = " ".join(x for x in [marca, nombre] if x)
            suave = self.buscar(consulta)
            if suave:
                return {
                    "nutriscore": suave.get("nutriscore"),
                    "ingredientes_off": suave.get("ingredientes_off"),
                    "alergenos_off": suave.get("alergenos_off"),
                }
        return {}

    @staticmethod
    def _extraer(producto: dict[str, Any]) -> dict[str, Any]:
        n = producto.get("nutriments") or {}
        grado = producto.get("nutriscore_grade") or producto.get("nutrition_grades")
        grado = (grado or "").upper()
        if grado not in {"A", "B", "C", "D", "E"}:
            grado = None
        alergenos = producto.get("allergens") or ""
        if not alergenos and producto.get("allergens_tags"):
            alergenos = ", ".join(
                t.replace("en:", "").replace("es:", "")
                for t in producto["allergens_tags"]
            )
        return {
            "ean": producto.get("code") or producto.get("ean"),
            "nutriscore": grado,
            "energia_kcal": _numero(n.get("energy-kcal_100g") or n.get("energy-kcal")),
            "proteinas": _numero(n.get("proteins_100g")),
            "hidratos": _numero(n.get("carbohydrates_100g")),
            "grasas": _numero(n.get("fat_100g")),
            "fibra": _numero(n.get("fiber_100g")),
            "azucares": _numero(n.get("sugars_100g")),
            "sal": _numero(n.get("salt_100g")),
            "nutricion_por": "100g",
            "ingredientes_off": producto.get("ingredients_text") or "",
            "alergenos_off": alergenos,
        }


def _numero(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None
