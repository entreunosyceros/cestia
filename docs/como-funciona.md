# Cómo funciona

[← Índice](README.md) · [Funcionalidades](funcionalidades.md) · [Inicio rápido](inicio-rapido.md)

---

CestIA trabaja **en tu ordenador**:

1. Cuando buscas un producto, consulta las tiendas que tengas activadas (en paralelo).
2. Guarda en tu equipo los productos, precios, cesta, registro de gastos y alertas.
3. Te muestra fichas, comparaciones y estadísticas a partir de ese historial.
4. Si configuras la IA, puedes hacer preguntas sobre menús, presupuestos o listas de compra.

## Flujo típico

```text
Tú buscas «leche»
        │
        ▼
┌───────────────────┐     ┌──────────────────────────┐
│ Tiendas activas   │────▶│ Resultados unificados    │
│ Mercadona / …     │     │ + columna supermercado   │
└───────────────────┘     └────────────┬─────────────┘
                                       │
                         clic derecho / doble clic
                                       │
                                       ▼
                            Ficha del producto
                   (datos locales al instante;
                    Nutri-Score e ingredientes en 2.º plano)
                                       │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
                    Cesta           Alerta         Comparador /
              (óptima, precios)   de precio       estadísticas
```

## Ficha de producto: carga en dos fases

Al abrir una ficha, CestIA muestra **de inmediato** lo que ya guardó en la búsqueda (nombre, precio, foto…). Después, en segundo plano, puede completar:

- Ingredientes y alérgenos (API de Mercadona u otras tiendas).
- Nutri-Score y nutrición (ficha de tienda u Open Food Facts).
- Precio actualizado si faltaba algún dato.

Así la ficha no espera a terminar todas las consultas de red antes de mostrarse.

## Bandeja del sistema

Al cerrar la ventana con la X, CestIA **no se cierra del todo**: queda en la bandeja. Desde el icono (clic derecho) puedes mostrar u ocultar la ventana o **Salir**.

Las **alertas de precio** disparadas también pueden avisarte ahí si tienes activada la comprobación automática en Configuración.

## Dónde se guardan tus datos

Todo queda **en tu máquina** (base de datos local y ajustes).  
**No hay cuenta en la nube de CestIA.** Si no configuras la IA, la app no envía tu lista de compra a ningún servicio de inteligencia artificial.

Incluye búsquedas recientes, favoritos, listas, registro de gastos y preferencias de alertas.

## Tiendas que puedes usar

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

Activa o desactiva cada una en **Configuración → Tiendas**. Detalle en [Configuración](configuracion.md).

---

[Índice](README.md) · [Funcionalidades](funcionalidades.md) · [Configuración](configuracion.md)
