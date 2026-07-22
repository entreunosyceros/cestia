# Política de seguridad

## Versiones con soporte

| Versión | Soportada |
| ------- | --------- |
| 0.3.x   | ✅        |
| < 0.3   | ❌        |

## Alcance

CestIA es una **aplicación de escritorio** (PySide6 + SQLite) pensada para ejecutarse en el equipo del usuario. Los datos (productos, cesta, registro de gastos, alertas, clave Gemini si se guarda en la app) residen en `datos/cestia.db` y, opcionalmente, en `.env`. En el ámbito de seguridad nos interesa especialmente:

- Exposición involuntaria de la clave de Google Gemini (UI, `.env`, logs o commits).
- Inyección SQL o corrupción de datos en la base SQLite local.
- Lectura o escritura no autorizada de archivos fuera de las rutas previstas (`datos/`, `.cache/`, `.env`).
- Fugas de información sensible (historial de compra, listas) en issues, PRs o capturas.
- Dependencias de Python con vulnerabilidades conocidas que afecten al entorno de ejecución.
- Uso inseguro del servidor web opcional (`cestia/servidor_web.py`) si se expone en red.

**Fuera de alcance habitual:** Disponibilidad o cambios de las webs/APIs no oficiales de las tiendas, cuotas o políticas de Google Gemini, o Open Food Facts.

## Cómo reportar una vulnerabilidad

1. **No** abras un issue público con detalles del fallo de seguridad.
2. Usa [GitHub Security Advisories](https://github.com/entreunosyceros/cestia/security/advisories/new) (**Report a vulnerability**) si la opción está habilitada en este repositorio.
3. Si no puedes usar Advisories, abre un issue con el título `SECURITY (sin detalles)` y solicita un canal de comunicación privado; no incluyas pasos de explotación en el tablón público.

Incluye, en la medida de lo posible:

- Descripción del problema y componente afectado (p. ej. `asistente_ia`, `base_datos`, cliente de una tienda).
- Pasos detallados para reproducir el fallo.
- Impacto estimado (solo local, otros usuarios del equipo, red).
- Versión o commit afectado.
- Sugerencia de mitigación, si dispones de ella.

## Qué esperar

- **Acuse de recibo:** Evaluación inicial en un plazo razonable de pocos días.
- **Resolución:** Parche o mitigación en una versión posterior si procede.
- **Créditos:** Reconocimiento público al informante en las notas de la release, salvo que se solicite expresamente el anonimato.

## Buenas prácticas para usuarios

- **Clave Gemini:** Guárdala en Configuración o en `.env` (ignorado por Git). No la compartas ni la subas a GitHub. Si se filtra, revócala en [Google AI Studio](https://aistudio.google.com/apikey).
- **Datos locales:** `datos/cestia.db` contiene tu historial de precios y compras anotadas. Protege el equipo y no adjuntes esa base en issues.
- **Actualizaciones:** Mantén Python y las dependencias actualizadas (`pip install -r requirements.txt --upgrade`).
- **Origen seguro:** Descarga el código únicamente desde el [repositorio oficial de CestIA](https://github.com/entreunosyceros/cestia).
- **Servidor web:** Si usas Uvicorn/FastAPI, no lo expongas a Internet sin control de acceso.
