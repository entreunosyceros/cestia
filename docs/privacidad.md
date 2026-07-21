# Privacidad

[← Índice](README.md) · [Configuración](configuracion.md) · [Desarrollo](desarrollo.md)

---

- Los datos de compra y precios se guardan **en tu disco**.
- Al buscar, la app contacta con los servicios de las tiendas (y, si los usas, Open Food Facts o Google).
- No compartas ni subas a Internet tu historial personal ni tu clave de IA.

## Git y GitHub (`git push`)

Tu clave de Gemini y otros datos locales **no deben subirse** al remoto. Pueden estar en:

| Ubicación | Contenido |
|-----------|----------|
| `.env` | `CESTIA_GEMINI_CLAVE=…` (opcional) |
| `datos/cestia.db` | Clave guardada desde Configuración en la app |

### Protección automática

1. **`.gitignore`** — Git ignora `.env`, `datos/`, `data/`, `*.db` y `.cache/` (no entran en commits normales).
2. **Hook `pre-push`** — Si algún commit incluye esos archivos, `git push` **falla** antes de subir nada.

Activa el hook una vez en tu clon del repo:

```bash
git config core.hooksPath .githooks
```

Antes de hacer `git push`, comprueba con `git status` que no aparezcan `.env` ni `datos/`. Si alguna vez subiste una clave por error, revócala en [Google AI Studio](https://aistudio.google.com/apikey) y genera otra.

---

[Índice](README.md) · [Aviso legal](aviso-legal.md) · [Licencia y contacto](licencia-y-contacto.md)
