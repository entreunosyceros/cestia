# CestIA

<img width="1919" height="1044" alt="about-cestia" src="https://github.com/user-attachments/assets/ed6c86ac-4822-4547-87e6-7ebf2d059030" />

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?style=flat-square&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Datos-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![httpx](https://img.shields.io/badge/HTTP-httpx-007ACC?style=flat-square)
![Matplotlib](https://img.shields.io/badge/Gráficos-Matplotlib-11557C?style=flat-square&logo=plotly&logoColor=white)
![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-4285F4?style=flat-square&logo=google&logoColor=white)
![Open Food Facts](https://img.shields.io/badge/Nutrición-Open%20Food%20Facts-FF6F00?style=flat-square)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Licencia](https://img.shields.io/badge/Licencia-GPL--3.0-blue?style=flat-square)

**CestIA** es una aplicación de escritorio **local** para analizar el precio de tu compra: buscar productos en varios supermercados, comparar precios, llevar una cesta, guardar historial, crear alertas y, si quieres, preguntar a una IA.

Repositorio: [github.com/entreunosyceros/cestia](https://github.com/entreunosyceros/cestia)

> **Aviso:** no está afiliada a ninguna cadena de supermercados. Detalle en [docs/aviso-legal.md](docs/aviso-legal.md).

---

## Inicio rápido

```bash
python3 run_app.py
```

1. **Configuración** → activa las tiendas que quieras → **Guardar**.
2. Busca productos y abre fichas con precio, Nutri-Score y alternativas.
3. Opcional: **Obtén tu clave Gemini aquí** en Configuración para usar la IA.

Guía completa: **[docs/inicio-rapido.md](docs/inicio-rapido.md)**

---

## Documentación

Toda la documentación está en la carpeta **[`docs/`](docs/README.md)**:

| | |
|---|---|
| [Índice](docs/README.md) | Mapa de toda la documentación |
| [Cómo funciona](docs/como-funciona.md) | Flujo, datos locales y tiendas |
| [Funcionalidades](docs/funcionalidades.md) | Módulos de la app |
| [Configuración](docs/configuracion.md) | Tiendas, Gemini, zona Mercadona |
| [Privacidad](docs/privacidad.md) | Datos locales y `git push` |
| [Limitaciones](docs/limitaciones.md) | Qué no garantiza la app |
| [Desarrollo](docs/desarrollo.md) | Stack, `.env` y estructura del código |
| [Licencia y contacto](docs/licencia-y-contacto.md) | GPL-3.0 e issues |

---

## Tiendas soportadas

Mercadona · Carrefour · Alcampo · Froiz · Eroski · Lidl · Dia · Gadis  
(Eroski, Lidl, Dia y Gadis desactivadas por defecto.)

---

## Licencia

[GNU GPL v3.0](LICENSE) — ver [docs/licencia-y-contacto.md](docs/licencia-y-contacto.md).
