# Configuración

[← Índice](README.md) · [Inicio rápido](inicio-rapido.md) · [Privacidad](privacidad.md)

---

## Tiendas

**Configuración** → marca las tiendas que quieras (Mercadona, Carrefour, Alcampo, Froiz, Eroski, Lidl, Dia, Gadis) → **Guardar**.  
Debe quedar **al menos una** tienda activa.

Lista y notas por cadena: [Cómo funciona → Tiendas](como-funciona.md#tiendas-que-puedes-usar).

## Presupuesto de compra

En **Configuración → Presupuesto de compra** puedes fijar un límite **semanal** y/o **mensual** (0 = sin límite).

En la **Cesta**, la app muestra cuánto llevas gastado según el registro de gastos y cuánto queda del presupuesto. Si la cesta actual haría superar el límite, aparece un **aviso destacado**.

## Alertas de precio automáticas

En **Configuración → Alertas de precio**:

- **Comprobar alertas automáticamente**: revisa en segundo plano los productos con alerta activa.
- **Cada X h**: intervalo entre comprobaciones (1–168 horas; por defecto 6 h).

Cuando un precio baja del objetivo, recibes una **notificación en la bandeja del sistema** (icono de CestIA junto al reloj). También puedes comprobar manualmente en la pestaña **Alertas → Comprobar ahora**.

Las alertas se crean desde la ficha del producto («Crear alerta» con el precio objetivo).

## IA — Google Gemini

<img width="1920" height="1046" alt="conf-gemini-cestia" src="https://github.com/user-attachments/assets/7c701424-28b5-42d8-b80e-9e04ec2bf15a" />

1. En **Configuración**, pulsa **Obtén tu clave Gemini aquí** (abre Google AI Studio) y crea una API key.
2. Pégala en el campo **Clave Gemini** → **Guardar** (puedes usar «Probar conexión» y «Mostrar clave»).

**Modelos recomendados (plan gratuito, claves nuevas):** `gemini-3.1-flash-lite` o `gemini-3.5-flash`.  
Las series 2.0 y 2.5 ya no están disponibles para proyectos nuevos.

La clave se guarda solo en tu equipo. El asistente compara y planifica la compra en **varios supermercados**, no solo en Mercadona.

Prioridad de la clave: ajuste guardado en la interfaz → variables de entorno (`.env`).

## Tema claro / oscuro

**Configuración → Apariencia** → elige tema → **Guardar**.

## Zona de precios (Mercadona)

Si los precios de Mercadona no coinciden con tu zona, indica el almacén en `.env` (plantilla en `.env.example`). Valores habituales: `mad1`, `bcn1`, `vlc1`, `svq1`…

Variables detalladas: [Desarrollo → Variables de entorno](desarrollo.md#variables-de-entorno).

---

[Índice](README.md) · [Privacidad](privacidad.md) · [Desarrollo](desarrollo.md)
