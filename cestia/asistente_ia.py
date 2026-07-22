"""Asistente IA de CestIA basado en Google Gemini."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

INSTRUCCION_SISTEMA = """Eres CestIA, un asistente de compras de supermercado en España.
Ayudas a comparar precios y planificar la compra en varias cadenas (Mercadona, Carrefour,
Alcampo, Froiz, Eroski, Lidl, Dia, Gadis) según el catálogo y la cesta local del usuario.
No te presentes como asistente exclusivo de Mercadona: habla de «tu compra» o «los supermercados
disponibles», no de una sola tienda salvo que el usuario pregunte por ella.
Respondes en español, de forma práctica y concreta.
Formatea las respuestas con Markdown (listas, encabezados, negritas) para facilitar la lectura.
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
MODELO_POR_DEFECTO = "gemini-3.1-flash-lite"

# Sustitutos oficiales cuando un modelo ya no admite claves/proyectos nuevos.
MIGRACION_MODELOS: dict[str, str] = {
    "gemini-2.0-flash": "gemini-3.1-flash-lite",
    "gemini-2.0-flash-lite": "gemini-3.1-flash-lite",
    "gemini-1.5-flash": "gemini-3.1-flash-lite",
    "gemini-1.5-flash-8b": "gemini-3.1-flash-lite",
    "gemini-1.5-pro": "gemini-3.5-flash",
    "gemini-2.5-flash": "gemini-3.5-flash",
    "gemini-2.5-flash-lite": "gemini-3.1-flash-lite",
}
MODELOS_OBSOLETOS = frozenset(MIGRACION_MODELOS.keys())
MODELOS_GRATUITOS_SUGERIDOS = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
)


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
                return self.normalizar_modelo(guardado)
        return self.normalizar_modelo(
            os.getenv("CESTIA_GEMINI_MODELO")
            or os.getenv("MERCADONIA_GEMINI_MODELO")
            or os.getenv("GEMINI_MODEL")
            or MODELO_POR_DEFECTO
        )

    def guardar_clave(self, clave: str) -> None:
        if not self.repositorio:
            raise RuntimeError("No hay repositorio para guardar la clave.")
        self.repositorio.guardar_ajuste(CLAVE_AJUSTE_GEMINI, clave.strip())

    def guardar_modelo(self, modelo: str) -> None:
        if not self.repositorio:
            raise RuntimeError("No hay repositorio para guardar el modelo.")
        self.repositorio.guardar_ajuste(
            CLAVE_AJUSTE_MODELO, self.normalizar_modelo(modelo)
        )

    @staticmethod
    def normalizar_modelo(modelo: str | None) -> str:
        elegido = (modelo or MODELO_POR_DEFECTO).strip()
        return MIGRACION_MODELOS.get(elegido, elegido or MODELO_POR_DEFECTO)

    def comprobar_conexion(self) -> tuple[bool, str]:
        clave = self.obtener_clave()
        if not clave:
            return False, "No hay clave configurada."
        modelo = self.obtener_modelo()
        url = URL_GEMINI.format(modelo=modelo)
        cuerpo = {
            "contents": [
                {"role": "user", "parts": [{"text": "Responde solo: OK"}]}
            ],
            "generationConfig": {"maxOutputTokens": 16, "temperature": 0},
        }
        try:
            with httpx.Client(timeout=20.0) as cliente:
                respuesta = cliente.post(
                    url,
                    params={"key": clave},
                    headers={"Content-Type": "application/json"},
                    json=cuerpo,
                )
            if respuesta.status_code == 200:
                return True, f"Conexión OK con el modelo «{modelo}»."
            if respuesta.status_code in {400, 403}:
                return False, "Clave inválida o sin permiso. Revísala en Google AI Studio."
            return False, self._mensaje_error_http(
                respuesta.status_code, respuesta.text, modelo
            )
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
                return self._mensaje_error_http(
                    respuesta.status_code, respuesta.text, modelo
                )
            datos = respuesta.json()
            return self._extraer_texto(datos)
        except httpx.HTTPError as exc:
            return f"No se pudo contactar con Gemini.\nDetalle: {exc}"

    @staticmethod
    def _mensaje_error_http(codigo: int, cuerpo: str, modelo: str) -> str:
        detalle = cuerpo[:700]
        sugeridos = ", ".join(f"«{m}»" for m in MODELOS_GRATUITOS_SUGERIDOS)
        if codigo == 429 and (
            "limit: 0" in detalle
            or modelo in MODELOS_OBSOLETOS
            or "free_tier" in detalle
        ):
            return (
                f"Gemini respondió HTTP 429: el modelo «{modelo}» no tiene cuota "
                f"en el plan gratuito (Google retiró la serie 2.0 en junio de 2026).\n\n"
                f"Cambia en Configuración el modelo a uno de estos (gratuitos): "
                f"{sugeridos}.\n\n"
                f"Detalle:\n{detalle}"
            )
        if codigo == 429:
            return (
                f"Gemini respondió HTTP 429: has superado el límite de peticiones "
                f"del plan gratuito con «{modelo}». Espera un minuto e inténtalo "
                f"de nuevo, o prueba «{MODELO_POR_DEFECTO}».\n\nDetalle:\n{detalle}"
            )
        if codigo == 404 and (
            "no longer available" in detalle.lower()
            or modelo in MODELOS_OBSOLETOS
        ):
            reemplazo = MIGRACION_MODELOS.get(modelo, MODELO_POR_DEFECTO)
            return (
                f"Gemini respondió HTTP 404: el modelo «{modelo}» ya no está "
                f"disponible para claves o proyectos nuevos.\n\n"
                f"Cambia en Configuración el modelo a «{reemplazo}» o "
                f"«{MODELOS_GRATUITOS_SUGERIDOS[1]}» y pulsa Guardar.\n\n"
                f"Detalle:\n{detalle}"
            )
        return (
            f"Gemini respondió con error HTTP {codigo}. "
            f"Revisa la clave en Configuración y el modelo ({modelo}).\n{detalle}"
        )

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
                    "tienda": i.get("tienda"),
                    "kcal": i.get("energia_kcal"),
                    "proteinas": i.get("proteinas"),
                    "categoria": i.get("categoria"),
                }
                for i in cesta
            ],
            "totales_cesta": totales,
            "resumen_gastos": insight,
        }
