# Privacidad

[← Índice](README.md) · [Configuración](configuracion.md) · [Desarrollo](desarrollo.md)

---

- Los datos de compra y precios se guardan **en tu disco**.
- Al buscar, la app contacta con los servicios de las tiendas (y, si los usas, Open Food Facts o Google).
- No compartas ni subas a Internet tu historial personal ni tu clave de IA.

## Git y GitHub

La clave de Gemini **no se sube** a GitHub gracias a [`.gitignore`](../.gitignore):

| Ubicación | Contenido |
|-----------|----------|
| `.env` | `CESTIA_GEMINI_CLAVE=…` (opcional) |
| `datos/cestia.db` | Clave si la guardaste desde Configuración en la app |

Git ignora `.env`, `datos/`, `*.db` y `.cache/`. La plantilla [`.env.example`](../.env.example) sí se puede versionar (sin clave real).

Si alguna vez subiste una clave por error, revócala en [Google AI Studio](https://aistudio.google.com/apikey) y genera otra.

---

[Índice](README.md) · [Aviso legal](aviso-legal.md) · [Licencia y contacto](licencia-y-contacto.md)
