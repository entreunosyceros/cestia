"""Asistente IA de CestIA basado en Google Gemini."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

INSTRUCCION_SISTEMA = """Eres CestIA, un asistente de compra para Mercadona en España.
Respondes en español, de forma práctica y concreta.
Cuando propongas productos, usa preferentemente los de la cesta o el catálogo local.
Si das una lista de compra, incluye cantidades aproximadas y coste estimado si hay precios.
No inventes Nutri-Score ni calorías si no te las dan; dilo claramente.
"""

URL_GEMINI = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{modelo}:generateContent"
)

CLAVE_AJUSTE_GEMINI = "gemini_clave"
CLAVE_AJUSTE_MODELO = "gemini_modelo"
MODELO_POR_DEFECTO = "gemini-2.0-flash"


class AsistenteIA:
    def __init__(self, repositorio: Any | None = None) -> None:
        self.repositorio = repositorio

    def obtener_clave(self) -> str:
        if self.repositorio:
            guardada = self.repositorio.obtener_ajuste(CLAVE_AJUSTE_GEMINI, "").strip()
            if guardada:
                return guardada
        return (
            os.getenv("CESTIA_GEMINI_CLAVE")
            or os.getenv("MERCADONIA_GEMINI_CLAVE")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()

    def obtener_modelo(self) -> str:
        if self.repositorio:
            guardado = self.repositorio.obtener_ajuste(CLAVE_AJUSTE_MODELO, "").strip()
            if guardado:
                return guardado
        return (
            os.getenv("CESTIA_GEMINI_MODELO")
            or os.getenv("MERCADONIA_GEMINI_MODELO")
            or os.getenv("GEMINI_MODEL")
            or MODELO_POR_DEFECTO
        ).strip()

    def guardar_clave(self, clave: str) -> None:
        if not self.repositorio:
            raise RuntimeError("No hay repositorio para guardar la clave.")
        self.repositorio.guardar_ajuste(CLAVE_AJUSTE_GEMINI, clave.strip())

    def guardar_modelo(self, modelo: str) -> None:
        if not self.repositorio:
            raise RuntimeError("No hay repositorio para guardar el modelo.")
        self.repositorio.guardar_ajuste(
            CLAVE_AJUSTE_MODELO, (modelo or MODELO_POR_DEFECTO).strip()
        )

    @property
    def clave_api(self) -> str:
        return self.obtener_clave()

    @property
    def modelo(self) -> str:
        return self.obtener_modelo()

    def disponible(self) -> bool:
        clave = self.obtener_clave()
        if not clave:
            return False
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={clave}"
            )
            with httpx.Client(timeout=5.0) as cliente:
                respuesta = cliente.get(url)
            return respuesta.status_code < 500
        except httpx.HTTPError:
            return False

    def comprobar_conexion(self) -> tuple[bool, str]:
        clave = self.obtener_clave()
        if not clave:
            return False, "No hay clave configurada."
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={clave}"
            )
            with httpx.Client(timeout=10.0) as cliente:
                respuesta = cliente.get(url)
            if respuesta.status_code == 200:
                return True, f"Conexión OK con el modelo «{self.obtener_modelo()}»."
            if respuesta.status_code in {400, 403}:
                return False, "Clave inválida o sin permiso. Revísala en Google AI Studio."
            return False, f"Gemini respondió HTTP {respuesta.status_code}."
        except httpx.HTTPError as exc:
            return False, f"Error de red: {exc}"

    def preguntar(self, pregunta: str, contexto: dict[str, Any] | None = None) -> str:
        clave = self.obtener_clave()
        modelo = self.obtener_modelo()
        if not clave:
            return (
                "Falta la clave de Gemini.\n"
                "Ábrela en Configuración → pega tu API key → Guardar.\n"
                "Puedes crearla en https://aistudio.google.com/apikey"
            )

        ctx = contexto or {}
        texto_usuario = (
            f"Contexto local (JSON):\n{json.dumps(ctx, ensure_ascii=False)[:8000]}\n\n"
            f"Pregunta del usuario:\n{pregunta}"
        )
        url = URL_GEMINI.format(modelo=modelo)
        cuerpo = {
            "systemInstruction": {
                "parts": [{"text": INSTRUCCION_SISTEMA}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": texto_usuario}],
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
            },
        }
        try:
            with httpx.Client(timeout=120.0) as cliente:
                respuesta = cliente.post(
                    url,
                    params={"key": clave},
                    headers={"Content-Type": "application/json"},
                    json=cuerpo,
                )
            if respuesta.status_code >= 400:
                detalle = respuesta.text[:500]
                return (
                    f"Gemini respondió con error HTTP {respuesta.status_code}. "
                    f"Revisa la clave en Configuración y el modelo ({modelo}).\n{detalle}"
                )
            datos = respuesta.json()
            return self._extraer_texto(datos)
        except httpx.HTTPError as exc:
            return f"No se pudo contactar con Gemini.\nDetalle: {exc}"

    @staticmethod
    def _extraer_texto(datos: dict[str, Any]) -> str:
        candidatos = datos.get("candidates") or []
        if not candidatos:
            bloqueo = datos.get("promptFeedback") or datos.get("error")
            return f"Gemini no devolvió respuesta.\n{bloqueo or datos}"
        partes = ((candidatos[0].get("content") or {}).get("parts")) or []
        textos = [p.get("text", "") for p in partes if isinstance(p, dict)]
        texto = "\n".join(t for t in textos if t).strip()
        return texto or "Gemini devolvió una respuesta vacía."

    def construir_contexto(self) -> dict[str, Any]:
        if not self.repositorio:
            return {}
        cesta = self.repositorio.items_cesta()
        totales = self.repositorio.totales_cesta()
        insight = self.repositorio.insight_gastos()
        return {
            "cesta": [
                {
                    "id": i["id"],
                    "nombre": i["nombre"],
                    "precio": i.get("precio_unidad"),
                    "cantidad": i.get("cantidad"),
                    "kcal": i.get("energia_kcal"),
                    "proteinas": i.get("proteinas"),
                    "categoria": i.get("categoria"),
                }
                for i in cesta
            ],
            "totales_cesta": totales,
            "resumen_gastos": insight,
        }
