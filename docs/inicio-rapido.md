# Inicio rápido

[← Índice](README.md) · [Configuración](configuracion.md) · [Cómo funciona](como-funciona.md)

---

## Requisitos

- Ordenador con pantalla (app de escritorio) y conexión a Internet para buscar productos.
- Python 3 (el script `run_app.py` puede crear el entorno virtual por ti).

## Arrancar la aplicación

```bash
python3 run_app.py
```

Eso prepara el entorno si hace falta e inicia CestIA. Verás un **icono en la bandeja del sistema**; desde ahí puedes mostrar u ocultar la ventana o salir por completo.

## Primeros pasos

1. Abre **Configuración** y marca las tiendas que quieras usar → **Guardar** (al menos una).
2. Busca un producto en **Productos** y abre su ficha (doble clic) o añádelo con **clic derecho** a favoritos o a una lista.
3. Opcional: configura **presupuesto**, **alertas automáticas** y la IA con **Obtén tu clave Gemini aquí** (ver [Configuración](configuracion.md)).

## Consejos útiles

- **Búsquedas recientes**: bajo el campo de búsqueda; pulsa una para repetirla. **Limpiar historial** borra la lista.
- **Listas**: marca productos con ✓ mientras compras; **Actualizar precios** refresca los importes guardados.
- **Cesta → Calcular óptima → Aplicar óptima**: sustituye productos por alternativas más baratas ya conocidas.
- **Registro de gasto → Repetir compra**: vuelve a cargar esa compra en la cesta.

## Escáner de códigos (opcional)

En Debian/Ubuntu, si usas la cámara para códigos de barras:

```bash
sudo apt install libzbar0
```

---

[Índice](README.md) · [Funcionalidades](funcionalidades.md) · [Configuración](configuracion.md)
