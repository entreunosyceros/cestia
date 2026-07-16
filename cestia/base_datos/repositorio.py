"""Repositorio SQLite de CestIA."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any


def _ahora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Repositorio:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def guardar_producto(self, producto: dict[str, Any]) -> None:
        columnas = [
            "id", "ean", "nombre", "marca", "envase", "categoria", "miniatura",
            "url_compartir", "ingredientes", "alergenos", "nutriscore",
            "energia_kcal", "proteinas", "hidratos", "grasas", "fibra",
            "azucares", "sal", "nutricion_por", "tamano_unidad", "formato_tamano",
            "precio_unidad", "precio_bulto", "precio_unidad_anterior", "tienda",
            "actualizado_en",
        ]
        datos = {c: producto.get(c) for c in columnas}
        if not datos.get("tienda"):
            datos["tienda"] = "mercadona"
        # mapear alias ingleses si llegan
        alias = {
            "nombre": "name",
            "marca": "brand",
            "envase": "packaging",
            "miniatura": "thumbnail",
            "url_compartir": "share_url",
            "ingredientes": "ingredients",
            "alergenos": "allergens",
            "energia_kcal": "energy_kcal",
            "proteinas": "proteins",
            "hidratos": "carbs",
            "grasas": "fat",
            "fibra": "fiber",
            "azucares": "sugars",
            "sal": "salt",
            "tamano_unidad": "unit_size",
            "formato_tamano": "size_format",
            "precio_unidad": "unit_price",
            "precio_bulto": "bulk_price",
            "precio_unidad_anterior": "previous_unit_price",
        }
        for es, en in alias.items():
            if datos.get(es) is None and producto.get(en) is not None:
                datos[es] = producto.get(en)
        datos["actualizado_en"] = datos.get("actualizado_en") or _ahora()
        marcadores = ", ".join("?" for _ in columnas)
        asignaciones = ", ".join(f"{c}=excluded.{c}" for c in columnas if c != "id")
        self.conexion.execute(
            f"""
            INSERT INTO productos ({', '.join(columnas)})
            VALUES ({marcadores})
            ON CONFLICT(id) DO UPDATE SET {asignaciones}
            """,
            [datos[c] for c in columnas],
        )
        self.conexion.commit()

    def registrar_precio(
        self,
        id_producto: str,
        precio_unidad: float | None,
        precio_bulto: float | None = None,
        *,
        registrado_en: str | None = None,
    ) -> bool:
        if precio_unidad is None:
            return False
        ultimo = self.conexion.execute(
            """
            SELECT precio_unidad, precio_bulto FROM historial_precios
            WHERE id_producto = ? ORDER BY registrado_en DESC LIMIT 1
            """,
            (id_producto,),
        ).fetchone()
        if ultimo and ultimo["precio_unidad"] == precio_unidad and (
            ultimo["precio_bulto"] == precio_bulto
            or (ultimo["precio_bulto"] is None and precio_bulto is None)
        ):
            return False
        cuando = registrado_en or _ahora()
        self.conexion.execute(
            """
            INSERT INTO historial_precios
                (id_producto, precio_unidad, precio_bulto, registrado_en)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id_producto, registrado_en) DO UPDATE SET
                precio_unidad = excluded.precio_unidad,
                precio_bulto = excluded.precio_bulto
            """,
            (id_producto, precio_unidad, precio_bulto, cuando),
        )
        self.conexion.commit()
        return True

    def obtener_producto(self, id_producto: str) -> dict[str, Any] | None:
        fila = self.conexion.execute(
            "SELECT * FROM productos WHERE id = ?", (id_producto,)
        ).fetchone()
        return self._con_alias(dict(fila)) if fila else None

    def buscar_local(self, consulta: str, limite: int = 40) -> list[dict[str, Any]]:
        q = f"%{consulta.strip()}%"
        filas = self.conexion.execute(
            """
            SELECT * FROM productos
            WHERE nombre LIKE ? OR marca LIKE ? OR ean LIKE ?
            ORDER BY nombre LIMIT ?
            """,
            (q, q, q, limite),
        ).fetchall()
        return [self._con_alias(dict(f)) for f in filas]

    def historial_precios(self, id_producto: str) -> list[dict[str, Any]]:
        filas = self.conexion.execute(
            """
            SELECT * FROM historial_precios
            WHERE id_producto = ?
            ORDER BY registrado_en ASC
            """,
            (id_producto,),
        ).fetchall()
        return [dict(f) for f in filas]

    def comparar_precio(
        self, id_producto: str, dias_atras: int = 180
    ) -> dict[str, Any] | None:
        producto = self.obtener_producto(id_producto)
        if not producto:
            return None
        historial = self.historial_precios(id_producto)
        if not historial:
            return {
                "producto": producto,
                "precio_antiguo": None,
                "precio_nuevo": producto.get("precio_unidad"),
                "cambio_pct": None,
                "fecha_antigua": None,
                "fecha_nueva": producto.get("actualizado_en"),
            }
        reciente = historial[-1]
        antiguo = historial[0]
        try:
            dt_reciente = datetime.fromisoformat(reciente["registrado_en"])
            corte = dt_reciente - timedelta(days=dias_atras)
            for fila in historial:
                dt = datetime.fromisoformat(fila["registrado_en"])
                if dt <= corte:
                    antiguo = fila
                else:
                    break
        except ValueError:
            pass

        precio_viejo = antiguo["precio_unidad"]
        precio_nuevo = reciente["precio_unidad"]
        cambio = None
        if precio_viejo and precio_nuevo and precio_viejo > 0:
            cambio = ((precio_nuevo - precio_viejo) / precio_viejo) * 100
        return {
            "producto": producto,
            "precio_antiguo": precio_viejo,
            "precio_nuevo": precio_nuevo,
            "cambio_pct": cambio,
            "fecha_antigua": antiguo["registrado_en"],
            "fecha_nueva": reciente["registrado_en"],
            "old_price": precio_viejo,
            "new_price": precio_nuevo,
            "change_pct": cambio,
            "product": producto,
        }

    def productos_con_historial(self, limite: int = 100) -> list[dict[str, Any]]:
        filas = self.conexion.execute(
            """
            SELECT p.*
            FROM productos p
            WHERE EXISTS (
                SELECT 1 FROM historial_precios h WHERE h.id_producto = p.id
            )
            ORDER BY p.actualizado_en DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        return [self._con_alias(dict(f)) for f in filas]

    def items_cesta(self) -> list[dict[str, Any]]:
        filas = self.conexion.execute(
            """
            SELECT c.cantidad, c.anadido_en, p.*
            FROM cesta c
            JOIN productos p ON p.id = c.id_producto
            ORDER BY c.anadido_en DESC
            """
        ).fetchall()
        return [self._con_alias(dict(f)) for f in filas]

    def cesta_anadir(self, id_producto: str, cantidad: float = 1.0) -> None:
        existente = self.conexion.execute(
            "SELECT cantidad FROM cesta WHERE id_producto = ?", (id_producto,)
        ).fetchone()
        if existente:
            self.conexion.execute(
                "UPDATE cesta SET cantidad = ? WHERE id_producto = ?",
                (float(existente["cantidad"]) + cantidad, id_producto),
            )
        else:
            self.conexion.execute(
                "INSERT INTO cesta (id_producto, cantidad, anadido_en) VALUES (?, ?, ?)",
                (id_producto, cantidad, _ahora()),
            )
        self.conexion.commit()

    def cesta_fijar_cantidad(self, id_producto: str, cantidad: float) -> None:
        if cantidad <= 0:
            self.cesta_quitar(id_producto)
            return
        self.conexion.execute(
            "UPDATE cesta SET cantidad = ? WHERE id_producto = ?",
            (cantidad, id_producto),
        )
        self.conexion.commit()

    def cesta_quitar(self, id_producto: str) -> None:
        self.conexion.execute("DELETE FROM cesta WHERE id_producto = ?", (id_producto,))
        self.conexion.commit()

    def cesta_vaciar(self) -> None:
        self.conexion.execute("DELETE FROM cesta")
        self.conexion.commit()

    def totales_cesta(self) -> dict[str, float]:
        items = self.items_cesta()
        totales = {
            "coste": 0.0,
            "energia_kcal": 0.0,
            "proteinas": 0.0,
            "hidratos": 0.0,
            "grasas": 0.0,
            "fibra": 0.0,
            "azucares": 0.0,
            "sal": 0.0,
        }
        for item in items:
            cantidad = float(item["cantidad"] or 0)
            precio = float(item["precio_unidad"] or 0)
            totales["coste"] += cantidad * precio
            factor = self._factor_nutricion(item) * cantidad
            for clave in (
                "energia_kcal", "proteinas", "hidratos", "grasas",
                "fibra", "azucares", "sal",
            ):
                valor = item.get(clave)
                if valor is not None:
                    totales[clave] += float(valor) * factor
        # alias
        totales["cost"] = totales["coste"]
        totales["energy_kcal"] = totales["energia_kcal"]
        totales["proteins"] = totales["proteinas"]
        totales["carbs"] = totales["hidratos"]
        totales["fat"] = totales["grasas"]
        totales["fiber"] = totales["fibra"]
        totales["sugars"] = totales["azucares"]
        totales["salt"] = totales["sal"]
        return totales

    @staticmethod
    def _factor_nutricion(item: dict[str, Any]) -> float:
        tamano = item.get("tamano_unidad") or item.get("unit_size")
        formato = (item.get("formato_tamano") or item.get("size_format") or "").lower()
        if tamano and formato in {"g", "ml"}:
            return float(tamano) / 100.0
        if tamano and formato in {"kg", "l"}:
            return float(tamano) * 10.0
        return 1.0

    def guardar_compra(self, notas: str = "") -> int | None:
        items = self.items_cesta()
        if not items:
            return None
        totales = self.totales_cesta()
        cursor = self.conexion.execute(
            "INSERT INTO compras (comprado_en, total, notas) VALUES (?, ?, ?)",
            (_ahora(), totales["coste"], notas),
        )
        id_compra = int(cursor.lastrowid)
        for item in items:
            cantidad = float(item["cantidad"])
            precio = float(item["precio_unidad"] or 0)
            factor = self._factor_nutricion(item) * cantidad
            self.conexion.execute(
                """
                INSERT INTO lineas_compra (
                    id_compra, id_producto, nombre, categoria, cantidad,
                    precio_unidad, total_linea,
                    energia_kcal, proteinas, hidratos, grasas, fibra, azucares, sal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_compra,
                    item["id"],
                    item["nombre"],
                    item.get("categoria"),
                    cantidad,
                    precio,
                    cantidad * precio,
                    (item.get("energia_kcal") or 0) * factor
                    if item.get("energia_kcal") is not None else None,
                    (item.get("proteinas") or 0) * factor
                    if item.get("proteinas") is not None else None,
                    (item.get("hidratos") or 0) * factor
                    if item.get("hidratos") is not None else None,
                    (item.get("grasas") or 0) * factor
                    if item.get("grasas") is not None else None,
                    (item.get("fibra") or 0) * factor
                    if item.get("fibra") is not None else None,
                    (item.get("azucares") or 0) * factor
                    if item.get("azucares") is not None else None,
                    (item.get("sal") or 0) * factor
                    if item.get("sal") is not None else None,
                ),
            )
        self.cesta_vaciar()
        self.conexion.commit()
        return id_compra

    def listar_compras(self, limite: int = 100) -> list[dict[str, Any]]:
        filas = self.conexion.execute(
            "SELECT * FROM compras ORDER BY comprado_en DESC LIMIT ?",
            (limite,),
        ).fetchall()
        return [dict(f) for f in filas]

    def lineas_de_compra(self, id_compra: int) -> list[dict[str, Any]]:
        filas = self.conexion.execute(
            "SELECT * FROM lineas_compra WHERE id_compra = ? ORDER BY id",
            (id_compra,),
        ).fetchall()
        return [dict(f) for f in filas]

    def resumen_gastos(self) -> dict[str, Any]:
        filas = self.conexion.execute(
            """
            SELECT substr(comprado_en, 1, 7) AS mes, SUM(total) AS total
            FROM compras
            GROUP BY mes
            ORDER BY mes
            """
        ).fetchall()
        mensual = [{"mes": f["mes"], "month": f["mes"], "total": f["total"]} for f in filas]
        anual: dict[str, float] = {}
        for m in mensual:
            anio = m["mes"][:4]
            anual[anio] = anual.get(anio, 0.0) + float(m["total"])
        por_cat = self.conexion.execute(
            """
            SELECT COALESCE(categoria, 'Sin categoría') AS categoria, SUM(total_linea) AS total
            FROM lineas_compra
            GROUP BY categoria
            ORDER BY total DESC
            """
        ).fetchall()
        return {
            "mensual": mensual,
            "monthly": mensual,
            "anual": [{"anio": a, "year": a, "total": t} for a, t in sorted(anual.items())],
            "yearly": [{"anio": a, "year": a, "total": t} for a, t in sorted(anual.items())],
            "por_categoria": [
                {"categoria": f["categoria"], "category": f["categoria"], "total": f["total"]}
                for f in por_cat
            ],
            "by_category": [
                {"categoria": f["categoria"], "category": f["categoria"], "total": f["total"]}
                for f in por_cat
            ],
        }

    def insight_gastos(self) -> str:
        resumen = self.resumen_gastos()
        mensual = resumen["mensual"]
        anual = resumen["anual"]
        lineas: list[str] = []
        if mensual:
            ultimo = mensual[-1]
            lineas.append(f"En {ultimo['mes']} gastaste {ultimo['total']:.2f} €.")
        if len(anual) >= 2:
            anterior, actual = anual[-2], anual[-1]
            diff = actual["total"] - anterior["total"]
            if diff >= 0:
                lineas.append(
                    f"En {actual['anio']} llevas {diff:.2f} € más que en {anterior['anio']}."
                )
            else:
                lineas.append(
                    f"En {actual['anio']} llevas {abs(diff):.2f} € menos que en {anterior['anio']}."
                )
        elif anual:
            lineas.append(
                f"Este año ({anual[-1]['anio']}) llevas {anual[-1]['total']:.2f} €."
            )
        if not lineas:
            return "Aún no hay compras guardadas. Guarda tu primera cesta para ver el historial."
        return "\n".join(lineas)

    def anadir_alerta(
        self, id_producto: str, nombre_producto: str, precio_objetivo: float
    ) -> int:
        cursor = self.conexion.execute(
            """
            INSERT INTO alertas
                (id_producto, nombre_producto, precio_objetivo, activa, creada_en)
            VALUES (?, ?, ?, 1, ?)
            """,
            (id_producto, nombre_producto, precio_objetivo, _ahora()),
        )
        self.conexion.commit()
        return int(cursor.lastrowid)

    def listar_alertas(self, solo_activas: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM alertas"
        if solo_activas:
            sql += " WHERE activa = 1"
        sql += " ORDER BY creada_en DESC"
        return [dict(f) for f in self.conexion.execute(sql).fetchall()]

    def desactivar_alerta(self, id_alerta: int) -> None:
        self.conexion.execute(
            "UPDATE alertas SET activa = 0, disparada_en = ? WHERE id = ?",
            (_ahora(), id_alerta),
        )
        self.conexion.commit()

    def eliminar_alerta(self, id_alerta: int) -> None:
        self.conexion.execute("DELETE FROM alertas WHERE id = ?", (id_alerta,))
        self.conexion.commit()

    def comprobar_alertas(self) -> list[dict[str, Any]]:
        disparadas: list[dict[str, Any]] = []
        for alerta in self.listar_alertas(solo_activas=True):
            producto = self.obtener_producto(alerta["id_producto"])
            if not producto or producto.get("precio_unidad") is None:
                continue
            if float(producto["precio_unidad"]) <= float(alerta["precio_objetivo"]):
                self.desactivar_alerta(alerta["id"])
                disparadas.append(
                    {
                        **alerta,
                        "precio_actual": producto["precio_unidad"],
                        "current_price": producto["precio_unidad"],
                        "product_name": alerta["nombre_producto"],
                        "target_price": alerta["precio_objetivo"],
                    }
                )
        return disparadas

    def obtener_ajuste(self, clave: str, por_defecto: str = "") -> str:
        fila = self.conexion.execute(
            "SELECT valor FROM ajustes WHERE clave = ?", (clave,)
        ).fetchone()
        return fila["valor"] if fila else por_defecto

    def guardar_ajuste(self, clave: str, valor: str) -> None:
        self.conexion.execute(
            """
            INSERT INTO ajustes (clave, valor) VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
            """,
            (clave, valor),
        )
        self.conexion.commit()

    @staticmethod
    def _con_alias(fila: dict[str, Any]) -> dict[str, Any]:
        """Añade claves EN para la UI y APIs internas."""
        mapa = {
            "name": "nombre",
            "brand": "marca",
            "packaging": "envase",
            "thumbnail": "miniatura",
            "share_url": "url_compartir",
            "ingredients": "ingredientes",
            "allergens": "alergenos",
            "energy_kcal": "energia_kcal",
            "proteins": "proteinas",
            "carbs": "hidratos",
            "fat": "grasas",
            "fiber": "fibra",
            "sugars": "azucares",
            "salt": "sal",
            "unit_size": "tamano_unidad",
            "size_format": "formato_tamano",
            "unit_price": "precio_unidad",
            "bulk_price": "precio_bulto",
            "previous_unit_price": "precio_unidad_anterior",
            "category": "categoria",
            "quantity": "cantidad",
        }
        for en, es in mapa.items():
            if es in fila and en not in fila:
                fila[en] = fila[es]
        if "cantidad" not in fila and "quantity" in fila:
            fila["cantidad"] = fila["quantity"]
        return fila
