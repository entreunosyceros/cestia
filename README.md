# CestIA

<img width="1919" height="1044" alt="about-cestia" src="https://github.com/user-attachments/assets/ed6c86ac-4822-4547-87e6-7ebf2d059030" />

**CestIA** es una aplicación de escritorio **local** (Python + PySide6) para analizar el precio de tu compra: buscar productos en varios supermercados, comparar precios, llevar una cesta, guardar historial, crear alertas y, si quieres, preguntar a una IA (Google Gemini).

Repositorio: [github.com/entreunosyceros/cestia](https://github.com/entreunosyceros/cestia)

---

## Aviso importante (léelo antes de usarla)

**CestIA no está afiliada, asociada, patrocinada ni respaldada por Mercadona, Carrefour, Alcampo, Auchan ni por ninguna otra cadena de supermercados.**

- No es una aplicación oficial de ninguna tienda.
- No sustituye las webs ni las apps oficiales de compra online.
- No vende productos, no gestiona pedidos ni pagos, y no actúa en nombre de ningún comercio.
- Las marcas, logotipos y nombres de las tiendas pertenecen a sus respectivos titulares.
- Los precios y datos de catálogo se obtienen de **fuentes no oficiales** (APIs / páginas públicas usadas por las tiendas online). Esas fuentes pueden cambiar, limitar el acceso o dejar de funcionar **sin aviso**.
- El uso previsto es **personal y local**. Tú eres responsable de cómo uses la aplicación y de cumplir las condiciones de uso de cada servicio de terceros.

Los datos nutricionales adicionales pueden proceder de [Open Food Facts](https://world.openfoodfacts.org/), un proyecto colaborativo independiente. La IA opcional usa [Google Gemini](https://aistudio.google.com/); tampoco implica relación comercial con Google más allá del uso de su API con tu propia clave.

**La aplicación se ofrece «tal cual», sin garantía** de exactitud de precios, disponibilidad de productos ni continuidad del servicio de consulta.

---

## ¿Cómo funciona?

En resumen, CestIA es un **cliente local** que:

1. **Consulta** (cuando tú buscas o abres un producto) información pública de catálogo/precio en las tiendas que tengas activadas.
2. **Guarda en tu equipo** (SQLite) productos, historial de precios, cesta, compras, alertas y ajustes.
3. **Te muestra** comparaciones, estadísticas y fichas enriquecidas (Nutri-Score, alérgenos, macros cuando hay datos).
4. **Opcionalmente** envía a Gemini solo el contexto que la propia app prepara para responder preguntas sobre compra/presupuesto (necesitas tu API key).

### Flujo típico

```text
Tú buscas «leche»
        │
        ▼
┌───────────────────┐     ┌──────────────────┐
│ Tiendas activas   │────▶│ Resultados unificados │
│ Mercadona / …     │     │ + columna supermercado │
└───────────────────┘     └──────────┬───────────┘
                                     │
                                     ▼
                          Ficha del producto
                          (precio, foto, Nutri-Score…)
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
                  Cesta          Alerta          Comparador /
                 (totales)      de precio        estadísticas
```

### Dónde viven tus datos

| Qué | Dónde |
|-----|--------|
| Productos, precios, cesta, compras, alertas, clave Gemini | `datos/cestia.db` (en tu máquina) |
| Caché de búsquedas/respuestas HTTP | carpeta de caché local de la app |
| Configuración opcional | `.env` (ver `.env.example`) |

**No hay cuenta en la nube de CestIA.** Si no configuras Gemini, la app no necesita enviar tu lista de compra a ningún servicio de IA.

### Tiendas soportadas

| Tienda | Cómo se consulta (resumen técnico) |
|--------|-------------------------------------|
| **Mercadona** | API / búsqueda no oficial del catálogo online |
| **Carrefour** | API de búsqueda Empathy usada por carrefour.es |
| **Alcampo** | Catálogo de compraonline.alcampo.es (estado de la página de búsqueda) |

Puedes activar o desactivar cada una en **Configuración → Tiendas**.

---

## Funcionalidades

<img width="1920" height="1043" alt="busqueda-productos" src="https://github.com/user-attachments/assets/deaac785-d1b7-4889-9cd2-70b8aa548f9d" />

| Módulo | Qué hace |
|--------|----------|
| **Productos** | Búsqueda multi-tienda con columna de supermercado y barra de progreso |
| **Ficha** | Precio, foto, ingredientes, alérgenos destacados, Nutri-Score explicado, nutrición, historial y alternativas más baratas clicables |
| **Cesta** | Cantidades, coste total y resumen nutricional estimado |
| **Historial** | Compras guardadas e insights de gasto |
| **Comparador** | Evolución de precios (~6 meses) según tu historial local |
| **Alertas** | Aviso cuando un producto baja de un precio objetivo |
| **Estadísticas** | Gasto semanal, mensual, anual, por categoría e inflación media de cesta |
| **IA** | Preguntas con Google Gemini (menús, presupuestos, listas); clave en Configuración |
| **Escáner** | Webcam o EAN manual (opcional: `libzbar0`) |
| **Configuración** | Tiendas activas, clave/modelo Gemini |
| **About** | Resumen de funciones y enlace al repositorio |

<img width="1918" height="1048" alt="ficha-producto" src="https://github.com/user-attachments/assets/e1221251-6ad0-4f5c-a9bb-cb4696359749" />

---

## Requisitos

- Python 3.10+ recomendado  
- Sistema con interfaz gráfica (la app principal es de escritorio)  
- Conexión a Internet para buscar productos (y para Gemini / Open Food Facts, si los usas)  
- Dependencias en `requirements.txt` (PySide6, httpx, matplotlib, etc.)

Opcional para el escáner de códigos de barras (Debian/Ubuntu):

```bash
sudo apt install libzbar0
```

---

## Arranque (escritorio)

Desde la carpeta del proyecto:

```bash
python3 run_app.py
```

`run_app.py` crea el entorno virtual `.venv` si hace falta, instala las dependencias y lanza la interfaz.

Si el venv ya está activo:

```bash
source .venv/bin/activate
python cestia.py
```

### Arranque web (opcional / experimental)

Existe un servidor FastAPI auxiliar; la experiencia principal está pensada para el escritorio:

```bash
uvicorn cestia.servidor_web:aplicacion --reload --host 0.0.0.0 --port 8000
```

---

## Configuración

### Tiendas

En la app: **Configuración** → marca Mercadona, Carrefour y/o Alcampo → **Guardar**.  
Debe quedar **al menos una** tienda activa.

### IA — Google Gemini

<img width="1920" height="1046" alt="conf-gemini-cestia" src="https://github.com/user-attachments/assets/7c701424-28b5-42d8-b80e-9e04ec2bf15a" />

1. Obtén una API key en [Google AI Studio](https://aistudio.google.com/apikey).  
2. En la app: **Configuración** → pega la clave → **Guardar** (puedes usar «Probar conexión»).  
3. O define variables en `.env` (plantilla: `.env.example`):

```env
CESTIA_GEMINI_CLAVE=tu_api_key
CESTIA_GEMINI_MODELO=gemini-2.0-flash
```

Prioridad: ajuste guardado en la interfaz → variables de entorno.

### Almacén / zona de precios (Mercadona)

En `.env`:

```env
MERCADONA_WAREHOUSE=mad1
```

Otros ejemplos frecuentes: `bcn1`, `vlc1`, `svq1`, etc. Afecta a los precios de Mercadona según la zona.

### Caché y ritmo de peticiones

También en `.env` (valores por defecto razonables para uso personal):

```env
CACHE_TTL_SEARCH=900
RATE_LIMIT_PER_MINUTE=30
```

---

## Estructura del proyecto

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
  cliente/                # Mercadona, Carrefour, Alcampo, caché/límite
  base_datos/             # SQLite local
  interfaz/               # PySide6 (páginas, estilos, progreso…)
img/                      # logo.png, logomini.png
datos/                    # cestia.db (se crea al usar la app)
```

---

## Privacidad (resumen)

- Los datos de compra y precios se guardan **en tu disco**.
- Las búsquedas contactan con servidores de las tiendas (y, si aplica, Open Food Facts / Google).
- No subas tu `.env` ni tu `datos/cestia.db` a repositorios públicos si contienen claves o historial personal.

---

## Licencia

CestIA se publica bajo la **[GNU General Public License v3.0](LICENSE)** (GPL-3.0).

En la práctica, eso significa entre otras cosas:

- Puedes **usar**, **estudiar**, **modificar** y **redistribuir** el programa.
- Si redistribuyes el programa (o una versión modificada), debes hacerlo **también bajo GPL-3.0** y facilitar el **código fuente** correspondiente.
- El programa se ofrece **sin garantía**; los detalles legales están en el archivo [`LICENSE`](LICENSE).

Los datos, marcas y APIs de terceros **no** están cubiertos por esta licencia: siguen siendo de sus titulares y sujetos a sus propias condiciones.

---

## Limitaciones conocidas

- Las integraciones con tiendas son **frágiles**: un cambio en su web/API puede romper la búsqueda.
- **No todos los productos tienen Nutri-Score, alérgenos o tabla nutricional completa**.
- El comparador y las estadísticas dependen de **lo que hayas buscado y guardado** antes (historial local).
- Alcampo/Carrefour: la ficha detallada se basa sobre todo en lo guardado al buscar; conviene volver a buscar el producto si falta en local.
- La IA puede equivocarse; no inventa un ticket oficial ni sustituye el etiquetado del envase.

---

## Contribuir / contacto

Issues y mejoras: [github.com/entreunosyceros/cestia](https://github.com/entreunosyceros/cestia).

Si abres un issue sobre una tienda, indica sistema operativo, versión de Python y un ejemplo de búsqueda que falle.

## Autor

Desarrollado por entreunosyceros.