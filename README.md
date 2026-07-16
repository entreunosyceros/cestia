# CestIA

<img width="1919" height="1044" alt="about-cestia" src="https://github.com/user-attachments/assets/ed6c86ac-4822-4547-87e6-7ebf2d059030" />

Aplicación **local** (Python + PySide6) para analizar el precio de tu compra en **Mercadona**, **Carrefour** y **Alcampo**: búsqueda, cesta, historial, alertas, estadísticas e IA opcional (Gemini).

> APIs no oficiales de las tiendas. Uso personal. Pueden cambiar o dejar de funcionar sin aviso.

Repositorio: [github.com/entreunosyceros/cestia](https://github.com/entreunosyceros/cestia)

## Arranque (escritorio)

```bash
cd /var/www/html/Python/MercadonIA
python3 run_app.py
```

`run_app.py` crea el `.venv` si hace falta, instala `requirements.txt` y lanza la interfaz.

Alternativa con el venv ya activo:

```bash
source .venv/bin/activate
python cestia.py
```

Escáner de códigos (Debian/Ubuntu): `sudo apt install libzbar0`

## Arranque (web opcional)

```bash
uvicorn cestia.servidor_web:aplicacion --reload --host 0.0.0.0 --port 8000
```

## Funcionalidades

<img width="1920" height="1043" alt="busqueda-productos" src="https://github.com/user-attachments/assets/deaac785-d1b7-4889-9cd2-70b8aa548f9d" />

| Módulo | Qué hace |
|--------|----------|
| **Productos** | Búsqueda multi-tienda (Mercadona / Carrefour / Alcampo), con columna de tienda |
| **Configuración → Tiendas** | Activar o desactivar Mercadona, Carrefour y Alcampo |
| **Ficha** | Precio, foto, ingredientes, alérgenos, Nutri-Score, macros, historial y alternativas más baratas |
| **Cesta** | Coste total + kcal / proteínas / hidratos / grasas / fibra / azúcar / sal |
| **Historial** | Compras guardadas e insights de gasto |
| **Comparador** | Precio hace ~6 meses vs hoy |
| **Alertas** | Aviso cuando un producto baja de un precio |
| **Estadísticas** | Gasto mensual / anual / por categoría e inflación de cesta |
| **IA** | Google Gemini (menús, presupuestos, listas); clave desde Configuración |
| **Escáner** | Webcam o EAN manual |
| **About** | Logo, funciones y enlace al repositorio |

## Estructura

<img width="1918" height="1048" alt="ficha-producto" src="https://github.com/user-attachments/assets/e1221251-6ad0-4f5c-a9bb-cb4696359749" />

```
cestia.py                 # entrada escritorio
run_app.py                # venv + dependencias + arranque
cestia/
  configuracion.py
  catalogo.py             # búsqueda Mercadona + Carrefour + Alcampo
  tiendas.py              # preferencias de tiendas activas
  enriquecimiento.py      # Open Food Facts
  asistente_ia.py         # Gemini
  servidor_web.py
  cliente/                # Mercadona, Algolia, Carrefour (Empathy), Alcampo
  base_datos/             # SQLite local
  interfaz/               # PySide6
img/                      # logo.png, logomini.png
datos/cestia.db
```

## Configuración

### Tiendas

En la app: **Configuración** → marca Mercadona, Carrefour y/o Alcampo → **Guardar**.

### IA — Google Gemini

<img width="1920" height="1046" alt="conf-gemini-cestia" src="https://github.com/user-attachments/assets/7c701424-28b5-42d8-b80e-9e04ec2bf15a" />

1. En la app: **Configuración** → pega la API key → Guardar  
   (también «Probar conexión»)
2. O en `.env`:

```
CESTIA_GEMINI_CLAVE=tu_api_key
CESTIA_GEMINI_MODELO=gemini-2.0-flash
```

Clave en [Google AI Studio](https://aistudio.google.com/apikey).  
Prioridad: ajuste de la interfaz → variables de entorno.

### Almacén Mercadona

En `.env`: `MERCADONA_WAREHOUSE=mad1` (`bcn1`, `vlc1`, `svq1`…).
