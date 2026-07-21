# CestIA

<img width="1919" height="1044" alt="about-cestia" src="https://github.com/user-attachments/assets/ed6c86ac-4822-4547-87e6-7ebf2d059030" />

**CestIA** es una aplicación de escritorio **local** para analizar el precio de tu compra: buscar productos en varios supermercados, comparar precios, llevar una cesta, guardar historial, crear alertas y, si quieres, preguntar a una IA.

Repositorio: [github.com/entreunosyceros/cestia](https://github.com/entreunosyceros/cestia)

---

## Aviso importante (léelo antes de usarla)

**CestIA no está afiliada, asociada, patrocinada ni respaldada por Mercadona, Carrefour, Alcampo, Froiz, Eroski, Lidl, Dia, Gadis, Auchan ni por ninguna otra cadena de supermercados.**

- No es una aplicación oficial de ninguna tienda.
- No sustituye las webs ni las apps oficiales de compra online.
- No vende productos, no gestiona pedidos ni pagos, y no actúa en nombre de ningún comercio.
- Las marcas, logotipos y nombres de las tiendas pertenecen a sus respectivos titulares.
- Los precios y datos de catálogo se obtienen consultando **servicios públicos** utilizados por las tiendas online o **fuentes de acceso público**. Estas interfaces pueden cambiar o dejar de estar disponibles **sin previo aviso**.
- El uso previsto es **personal y local**. Tú eres responsable de cómo uses la aplicación y de cumplir las condiciones de uso de cada servicio de terceros.

Los datos nutricionales adicionales pueden proceder de [Open Food Facts](https://world.openfoodfacts.org/), un proyecto colaborativo independiente. La IA opcional usa [Google Gemini](https://aistudio.google.com/); tampoco implica relación comercial con Google más allá del uso de su servicio con tu propia clave.

**La aplicación se ofrece «tal cual», sin garantía** de exactitud de precios, disponibilidad de productos ni continuidad del servicio de consulta.

---

## ¿Cómo funciona?

CestIA trabaja **en tu ordenador**:

1. Cuando buscas un producto, consulta las tiendas que tengas activadas.
2. Guarda en tu equipo los productos, precios, cesta, compras y alertas.
3. Te muestra fichas, comparaciones y estadísticas a partir de ese historial.
4. Si configuras la IA, puedes hacer preguntas sobre menús, presupuestos o listas de compra.

### Flujo típico

```text
Tú buscas «leche»
        │
        ▼
┌───────────────────┐     ┌──────────────────────────┐
│ Tiendas activas   │────▶│ Resultados unificados    │
│ Mercadona / …     │     │ + columna supermercado   │
└───────────────────┘     └────────────┬─────────────┘
                                       │
                                       ▼
                            Ficha del producto
                            (precio, foto, Nutri-Score…)
                                       │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
                    Cesta           Alerta         Comparador /
                   (totales)       de precio       estadísticas
```

### Dónde se guardan tus datos

Todo queda **en tu máquina** (base de datos local y ajustes).  
**No hay cuenta en la nube de CestIA.** Si no configuras la IA, la app no envía tu lista de compra a ningún servicio de inteligencia artificial.

### Tiendas que puedes usar

| Tienda | Notas |
|--------|--------|
| **Mercadona** | Precios según zona (configurable) |
| **Carrefour** | Catálogo online de España |
| **Alcampo** | Compra online Alcampo |
| **Froiz** | Supermercado online Froiz |
| **Eroski** | Supermercado online Eroski (desactivada por defecto) |
| **Lidl** | Catálogo online Lidl (desactivada por defecto) |
| **Dia** | Catálogo online Dia (desactivada por defecto) |
| **Gadis** | Gadisline / catálogo online (desactivada por defecto) |

Activa o desactiva cada una en **Configuración → Tiendas**.

---

## Funcionalidades

<img width="1920" height="1043" alt="busqueda-productos" src="https://github.com/user-attachments/assets/deaac785-d1b7-4889-9cd2-70b8aa548f9d" />

| Módulo | Qué hace |
|--------|----------|
| **Productos** | Búsqueda multi-tienda con columna de supermercado |
| **Ficha** | Precio, foto, ingredientes, alérgenos, Nutri-Score, nutrición, historial y alternativas más baratas |
| **Cesta** | Cantidades, coste total y resumen nutricional estimado |
| **Historial** | Compras guardadas e insights de gasto |
| **Comparador** | Evolución de precios (~6 meses) según tu historial |
| **Alertas** | Aviso cuando un producto baja de un precio objetivo |
| **Estadísticas** | Gasto semanal, mensual, anual, por categoría e inflación de cesta |
| **IA** | Preguntas con Google Gemini (clave en Configuración) |
| **Escáner** | Webcam o código de barras a mano |
| **Configuración** | Tiendas activas y clave de IA |
| **About** | Resumen de funciones y enlace al repositorio |

<img width="1918" height="1048" alt="ficha-producto" src="https://github.com/user-attachments/assets/e1221251-6ad0-4f5c-a9bb-cb4696359749" />

---

## Cómo empezar

1. Necesitas un ordenador con pantalla (es una app de escritorio) y conexión a Internet para buscar productos.
2. Entra en la carpeta del proyecto y ejecuta:

```bash
python3 run_app.py
```

Eso prepara el entorno si hace falta e inicia CestIA.

3. En **Configuración**, elige las tiendas que quieras usar y, si quieres IA, pega tu clave de Gemini.

### Escáner de códigos (opcional)

En Debian/Ubuntu, si usas la cámara para códigos de barras:

```bash
sudo apt install libzbar0
```

---

## Configuración

### Tiendas

**Configuración** → marca las tiendas que quieras (Mercadona, Carrefour, Alcampo, Froiz, Eroski, Lidl, Dia, Gadis) → **Guardar**.  
Debe quedar **al menos una** tienda activa.

### IA — Google Gemini

<img width="1920" height="1046" alt="conf-gemini-cestia" src="https://github.com/user-attachments/assets/7c701424-28b5-42d8-b80e-9e04ec2bf15a" />

1. Crea una clave en [Google AI Studio](https://aistudio.google.com/apikey).
2. En la app: **Configuración** → pega la clave → **Guardar** (puedes usar «Probar conexión»).

La clave se guarda solo en tu equipo.

### Zona de precios (Mercadona)

Si los precios de Mercadona no coinciden con tu zona, puedes indicar el almacén en el archivo `.env` del proyecto (hay un ejemplo en `.env.example`). Valores habituales: `mad1`, `bcn1`, `vlc1`, `svq1`…

---

## Privacidad

- Los datos de compra y precios se guardan **en tu disco**.
- Al buscar, la app contacta con los servicios de las tiendas (y, si los usas, Open Food Facts o Google).
- No compartas ni subas a Internet tu historial personal ni tu clave de IA.

### Git y GitHub (git push)

Tu clave de Gemini y otros datos locales **no deben subirse** al remoto. Pueden estar en:

| Ubicación | Contenido |
|-----------|----------|
| `.env` | `CESTIA_GEMINI_CLAVE=…` (opcional) |
| `datos/cestia.db` | Clave guardada desde Configuración en la app |

**Protección automática:**

1. **`.gitignore`** — Git ignora `.env`, `datos/`, `data/`, `*.db` y `.cache/` (no entran en commits normales).
2. **Hook `pre-push`** — Si algún commit incluye esos archivos, `git push` **falla** antes de subir nada.

Activa el hook una vez en tu clon del repo:

```bash
git config core.hooksPath .githooks
```

Antes de hacer `git push`, puedes comprobar con `git status` que no aparezcan `.env` ni `datos/`. Si alguna vez subiste una clave por error, revócala en [Google AI Studio](https://aistudio.google.com/apikey) y genera otra.

---

## Limitaciones

- Si una tienda cambia su web o su catálogo online, la búsqueda puede dejar de funcionar hasta actualizar CestIA.
- No todos los productos tienen Nutri-Score, alérgenos o tabla nutricional completa.
- El comparador y las estadísticas dependen de lo que hayas buscado y guardado antes.
- En algunas tiendas, conviene volver a buscar un producto si su ficha aún no está guardada en local.
- La IA puede equivocarse; no sustituye el etiquetado del envase ni un ticket oficial.

---

## Licencia

CestIA se publica bajo la **[GNU General Public License v3.0](LICENSE)** (GPL-3.0).

En la práctica:

- Puedes **usar**, **estudiar**, **modificar** y **redistribuir** el programa.
- Si redistribuyes el programa (o una versión modificada), debes hacerlo **también bajo GPL-3.0** y facilitar el **código fuente**.
- El programa se ofrece **sin garantía**; los detalles están en [`LICENSE`](LICENSE).

Las marcas y datos de las tiendas **no** van incluidos en esta licencia: pertenecen a sus titulares.

---

## Autor y contacto

Desarrollado por **entreunosyceros**.  
Issues y mejoras: [github.com/entreunosyceros/cestia](https://github.com/entreunosyceros/cestia).

Si reportas un fallo con una tienda, indica sistema operativo y un ejemplo de búsqueda que falle.

---

## Para desarrolladores

Esta sección es opcional. El uso normal de CestIA no requiere leerla.

### Stack

- Escritorio: Python + PySide6
- Datos locales: SQLite (`datos/cestia.db`)
- Red: cliente HTTP (`httpx`), caché en disco y límite de peticiones
- Nutrición extra: Open Food Facts
- IA opcional: Google Gemini
- Web auxiliar (experimental): FastAPI + Uvicorn

### Arranque alternativo

Con el entorno virtual ya activo:

```bash
source .venv/bin/activate
python cestia.py
```

Servidor web opcional:

```bash
uvicorn cestia.servidor_web:aplicacion --reload --host 0.0.0.0 --port 8000
```

### Variables de entorno

Plantilla: `.env.example`.

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

### Cómo consulta cada tienda

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

### Estructura del proyecto

```
cestia.py                 # entrada escritorio
run_app.py                # venv + dependencias + arranque
LICENSE                   # GNU GPL v3
README.md
.env.example
requirements.txt
cestia/
  configuracion.py
  catalogo.py             # orquesta búsqueda multi-tienda
  tiendas.py              # preferencias de tiendas activas
  enriquecimiento.py      # Open Food Facts
  asistente_ia.py         # Gemini
  servidor_web.py         # API/web opcional
  cliente/                # Mercadona, Carrefour, Alcampo, Froiz, Eroski, Lidl, Dia, Gadis, caché/límite
  base_datos/             # SQLite local
  interfaz/               # PySide6
img/
datos/                    # cestia.db (se crea al usar la app)
```

### Dependencias

Ver `requirements.txt` (PySide6, httpx, matplotlib, FastAPI/Uvicorn, OpenCV/pyzbar para el escáner, etc.).
