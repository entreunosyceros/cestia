# Desarrollo

[← Índice](README.md) · [Configuración](configuracion.md) · [Privacidad](privacidad.md)

---

Esta sección es opcional. El uso normal de CestIA no requiere leerla.

## Stack

- Escritorio: Python + PySide6
- Datos locales: SQLite (`datos/cestia.db`)
- Red: cliente HTTP (`httpx`), caché en disco y límite de peticiones
- Nutrición extra: Open Food Facts
- IA opcional: Google Gemini
- Web auxiliar (experimental): FastAPI + Uvicorn

## Arranque alternativo

Con el entorno virtual ya activo:

```bash
source .venv/bin/activate
python cestia.py
```

Servidor web opcional:

```bash
uvicorn cestia.servidor_web:aplicacion --reload --host 0.0.0.0 --port 8000
```

## Variables de entorno

Plantilla: [`.env.example`](../.env.example).

```env
# Zona Mercadona
MERCADONA_WAREHOUSE=mad1
MERCADONA_LANG=es

# Caché y ritmo
CACHE_TTL_CATEGORIES=3600
CACHE_TTL_PRODUCTS=1800
CACHE_TTL_SEARCH=900
RATE_LIMIT_PER_MINUTE=30
TIMEOUT_HTTP=8

# IA
CESTIA_GEMINI_CLAVE=
CESTIA_GEMINI_MODELO=gemini-3.1-flash-lite
```

Prioridad de la clave Gemini: ajuste guardado en la interfaz → variables de entorno.

## Cómo consulta cada tienda

| Tienda | Integración (resumen) |
|--------|------------------------|
| Mercadona | Catálogo / búsqueda del ecommerce |
| Carrefour | Empathy (`carrefour`) |
| Alcampo | Estado inicial de compraonline.alcampo.es |
| Froiz | Empathy (`froiz`) + precio desde la ficha del producto |
| Eroski | HTML de búsqueda supermercado.eroski.es |
| Lidl | API de búsqueda lidl.es |
| Dia | API search-back dia.es |
| Gadis | API de catálogo catalog.gadisline.com |

## Estructura del proyecto

```
cestia.py                 # entrada escritorio
run_app.py                # venv + dependencias + arranque
LICENSE                   # GNU GPL v3
README.md
docs/                     # documentación
.env.example
requirements.txt
cestia/
  configuracion.py
  catalogo.py             # orquesta búsqueda multi-tienda (paralela)
  tiendas.py              # preferencias de tiendas activas
  enriquecimiento.py      # Open Food Facts
  asistente_ia.py         # Gemini (modelos 3.x)
  servidor_web.py         # API/web opcional
  cliente/                # clientes tienda, fichas, caché
  base_datos/             # SQLite local
  interfaz/               # PySide6
img/
datos/                    # cestia.db (se crea al usar la app)
```

## Dependencias

Ver [`requirements.txt`](../requirements.txt) (PySide6, httpx, matplotlib, FastAPI/Uvicorn, OpenCV/pyzbar para el escáner, etc.).

---

[Índice](README.md) · [Inicio rápido](inicio-rapido.md)
