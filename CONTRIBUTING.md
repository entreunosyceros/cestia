# Guía de contribución

¡Gracias por interesarte en **CestIA**! Este proyecto es software libre ([GPL-3.0](LICENSE)): una aplicación de escritorio local (Python + PySide6) para consultar precios en varios supermercados, armar la cesta, alertas, estadísticas e IA opcional. Cualquier mejora bien planteada es bienvenida.

> **Aviso:** CestIA **no** está afiliada a ninguna cadena de supermercados. Consulta [docs/aviso-legal.md](docs/aviso-legal.md).

## Antes de empezar

- Lee el [README](README.md) y la [documentación en `docs/`](docs/README.md).
- Revisa las [issues abiertas](https://github.com/entreunosyceros/cestia/issues) por si alguien ya trabaja en lo mismo.
- Consulta el [Código de conducta](CODE_OF_CONDUCT.md).
- Para vulnerabilidades, sigue [SECURITY.md](SECURITY.md) (no abras issues públicas con detalles de explotación).

## Cómo puedes ayudar

- **Reportar errores** en búsqueda multi-tienda, fichas, cesta, listas, alertas, comparador, IA o escáner.
- **Proponer mejoras** explicando el caso de uso (compra diaria, presupuesto, ofertas, etc.).
- **Enviar pull requests** acotados y probados manualmente.
- **Mejorar documentación** (README, guías en `docs/`, textos de la app).
- **Probar en Linux** (y otros sistemas si puedes) si tu cambio afecta a la UI o al arranque.

## Entorno de desarrollo

Requisitos: **Python 3.10+** y entorno de escritorio (PySide6).

```bash
git clone https://github.com/entreunosyceros/cestia.git
cd cestia
python3 run_app.py
```

`run_app.py` crea el entorno virtual si no existe, instala dependencias y arranca la aplicación.

### Arranque manual (opcional)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python cestia.py
```

### Datos locales y secretos

- La app guarda datos en `datos/cestia.db` (dentro del clon) y puede usar `.env` para la clave Gemini y zona Mercadona.
- **No subas** `.env`, `datos/`, `*.db` ni claves de API a issues, PRs o commits (están en `.gitignore`).
- Plantilla segura: [`.env.example`](.env.example).

## Áreas del código

| Área | Ubicación habitual |
|------|-------------------|
| Ventana principal / navegación | `cestia/interfaz/ventana_principal.py` |
| Páginas UI (búsqueda, cesta, IA…) | `cestia/interfaz/paginas.py`, `paginas_extras.py` |
| Catálogo multi-tienda | `cestia/catalogo.py` |
| Clientes de tiendas | `cestia/cliente/` |
| SQLite / repositorio | `cestia/base_datos/` |
| Lógica (filtros, cesta óptima) | `cestia/logica/` |
| Asistente Gemini | `cestia/asistente_ia.py` |
| API web opcional | `cestia/servidor_web.py` |

## Estilo de código

- Sigue el estilo del código existente (nombres en español cuando ya esté así, imports, nivel de comentarios).
- Cambios **mínimos y enfocados**: no mezcles varias funcionalidades en un mismo PR.
- Los textos visibles para el usuario van en **español**, con tono claro y directo.
- No incluyas secretos (claves Gemini, `.env`) ni bases de datos locales en commits o issues.
- La UI es **PySide6** (sin archivos `.ui`).

## Pull requests

1. Crea una rama descriptiva desde `main` (por ejemplo `fix/busqueda-parafarmacia` o `feat/aviso-frescor`).
2. Describe **qué** cambias y **por qué**.
3. Indica cómo lo has probado (pasos manuales, capturas o comandos).
4. Si tocas un cliente de tienda, indica sistema operativo y un ejemplo de búsqueda.
5. Actualiza el README o las guías en `docs/` solo si el cambio lo requiere.

Usa la [plantilla de pull request](.github/pull_request_template.md) al abrir el PR.

## Reportar problemas

- **Bugs y mejoras:** plantillas de [GitHub Issues](https://github.com/entreunosyceros/cestia/issues/new/choose).
- **Seguridad:** [SECURITY.md](SECURITY.md).

## Licencia

Al contribuir, aceptas que tu aportación se publique bajo la misma licencia del proyecto: [GNU General Public License v3.0](LICENSE).
