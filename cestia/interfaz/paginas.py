"""Páginas principales de CestIA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cestia.interfaz.utilidades import formatear_euros, cargar_miniatura, color_nutri
from cestia.interfaz.trabajadores import ejecutar_en_hilo


class PaginaBusqueda(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, catalogo, repositorio=None, parent=None) -> None:
        super().__init__(parent)
        self.catalogo = catalogo
        self.repositorio = repositorio
        self._results: list[dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Productos", objectName="TituloPagina"))
        self.subtitulo = QLabel("Busca productos en las tiendas activas")
        self.subtitulo.setObjectName("Atenuado")
        layout.addWidget(self.subtitulo)

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("leche, aceite, café…")
        self.query.returnPressed.connect(self.buscar)
        btn = QPushButton("Buscar")
        btn.clicked.connect(self.buscar)
        row.addWidget(self.query, 1)
        row.addWidget(btn)
        layout.addLayout(row)

        self.status = QLabel("")
        self.status.setObjectName("Atenuado")
        layout.addWidget(self.status)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["", "Producto", "Tienda", "Precio", "€/ud ref.", "Marca"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._open_row)
        layout.addWidget(self.table, 1)

    def actualizar(self) -> None:
        if not self.repositorio:
            return
        from cestia.tiendas import carrefour_activo, mercadona_activo

        activas = []
        if mercadona_activo(self.repositorio):
            activas.append("Mercadona")
        if carrefour_activo(self.repositorio):
            activas.append("Carrefour")
        if activas:
            self.subtitulo.setText("Busca en: " + " · ".join(activas))
        else:
            self.subtitulo.setText(
                "Ninguna tienda activa. Actívalas en Configuración."
            )

    def buscar(self) -> None:
        q = self.query.text().strip()
        if not q:
            return
        self.status.setText("Buscando…")
        self.table.setRowCount(0)

        def work():
            return self.catalogo.buscar(q)

        ejecutar_en_hilo(work, self._on_results, lambda e: self.status.setText(f"Error: {e}"))

    def _on_results(self, results: list[dict[str, Any]]) -> None:
        self._results = results
        self.status.setText(
            f"{len(results)} resultados (precios guardados en historial local)"
        )
        self.table.setRowCount(len(results))
        for i, p in enumerate(results):
            thumb = QLabel()
            cargar_miniatura(thumb, p.get("miniatura") or p.get("thumbnail"), 48)
            self.table.setCellWidget(i, 0, thumb)
            self.table.setItem(
                i, 1, QTableWidgetItem(p.get("nombre") or p.get("name") or "")
            )
            tienda = (p.get("tienda") or "mercadona").capitalize()
            self.table.setItem(i, 2, QTableWidgetItem(tienda))
            self.table.setItem(
                i,
                3,
                QTableWidgetItem(
                    formatear_euros(
                        p.get("precio_unidad")
                        if p.get("precio_unidad") is not None
                        else p.get("unit_price")
                    )
                ),
            )
            bulk = (
                p.get("precio_bulto")
                if p.get("precio_bulto") is not None
                else p.get("bulk_price")
            )
            fmt = p.get("formato_tamano") or p.get("size_format") or ""
            self.table.setItem(
                i,
                4,
                QTableWidgetItem(f"{formatear_euros(bulk)}/{fmt}" if bulk else "—"),
            )
            self.table.setItem(
                i, 5, QTableWidgetItem(p.get("marca") or p.get("brand") or "")
            )
            self.table.setRowHeight(i, 56)

    def _open_row(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._results):
            self.abrir_producto.emit(self._results[row]["id"])


class PaginaProducto(QWidget):
    anadir_a_cesta = Signal(str)
    crear_alerta = Signal(str, float)

    def __init__(self, catalogo, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.catalogo = catalogo
        self.repositorio = repositorio
        self.product: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.back = QPushButton("← Volver")
        self.back.setProperty("secundario", True)
        top.addWidget(self.back)
        top.addStretch()
        layout.addLayout(top)

        body = QHBoxLayout()
        self.image = QLabel()
        cargar_miniatura(self.image, None, 220)
        body.addWidget(self.image)

        info = QVBoxLayout()
        self.title = QLabel("Producto")
        self.title.setObjectName("TituloPagina")
        self.title.setWordWrap(True)
        self.meta = QLabel("")
        self.meta.setObjectName("Atenuado")
        self.price = QLabel("")
        self.price.setObjectName("Precio")
        self.bulk = QLabel("")
        self.bulk.setObjectName("Atenuado")
        self.nutri = QLabel("")
        self.nutri.setObjectName("Nutri")
        self.compare = QLabel("")
        self.compare.setWordWrap(True)
        info.addWidget(self.title)
        info.addWidget(self.meta)
        info.addWidget(self.price)
        info.addWidget(self.bulk)
        info.addWidget(self.nutri)
        info.addWidget(self.compare)

        actions = QHBoxLayout()
        self.btn_cart = QPushButton("Añadir a la cesta")
        self.btn_cart.clicked.connect(self._cart)
        self.alert_price = QDoubleSpinBox()
        self.alert_price.setPrefix("Alertar < ")
        self.alert_price.setSuffix(" €")
        self.alert_price.setMaximum(9999)
        self.alert_price.setDecimals(2)
        self.btn_alert = QPushButton("Crear alerta")
        self.btn_alert.setProperty("secundario", True)
        self.btn_alert.clicked.connect(self._alert)
        actions.addWidget(self.btn_cart)
        actions.addWidget(self.alert_price)
        actions.addWidget(self.btn_alert)
        info.addLayout(actions)

        self.ingredientes = QPlainTextEdit()
        self.ingredientes.setReadOnly(True)
        self.alergenos = QLabel("")
        self.alergenos.setWordWrap(True)
        self.nutrition = QLabel("")
        self.nutrition.setWordWrap(True)
        self.alts = QListWidget()
        info.addWidget(QLabel("Ingredientes"))
        info.addWidget(self.ingredientes)
        info.addWidget(QLabel("Alérgenos"))
        info.addWidget(self.alergenos)
        info.addWidget(QLabel("Nutrición (por 100 g, Open Food Facts si disponible)"))
        info.addWidget(self.nutrition)
        info.addWidget(QLabel("Alternativas más baratas"))
        info.addWidget(self.alts, 1)
        body.addLayout(info, 1)
        layout.addLayout(body, 1)

    def cargar(self, id_producto: str) -> None:
        self.title.setText("Cargando…")

        def work():
            product = self.catalogo.obtener_producto(id_producto, enriquecer=True)
            compare = self.repositorio.comparar_precio(id_producto, dias_atras=180)
            alts = self.catalogo.alternativas_mas_baratas(product)
            history = self.repositorio.historial_precios(id_producto)
            return product, compare, alts, history

        ejecutar_en_hilo(work, self._show, lambda e: self.title.setText(f"Error: {e}"))

    def _show(self, payload) -> None:
        product, compare, alts, history = payload
        self.product = product
        self.title.setText(product.get("nombre") or product.get("name") or "")
        meta_bits = [
            x
            for x in [
                (product.get("tienda") or "mercadona").capitalize(),
                product.get("marca") or product.get("brand"),
                product.get("envase") or product.get("packaging"),
                product.get("ean"),
            ]
            if x
        ]
        self.meta.setText(" · ".join(meta_bits))
        cargar_miniatura(self.image, product.get("miniatura") or product.get("thumbnail"), 220)
        self.price.setText(formatear_euros(product.get("precio_unidad") if product.get("precio_unidad") is not None else product.get("unit_price")))
        if product.get("precio_bulto") if product.get("precio_bulto") is not None else product.get("bulk_price"):
            self.bulk.setText(
                f"{formatear_euros(product.get('precio_bulto') or product.get('bulk_price'))}/{product.get('formato_tamano') or product.get('size_format') or 'ud'}"
            )
        else:
            self.bulk.setText("")
        grade = product.get("nutriscore")
        if grade:
            self.nutri.setText(f"Nutri-Score {grade}")
            self.nutri.setStyleSheet(
                f"QLabel#Nutri {{ background:{color_nutri(grade)}; color:white; }}"
            )
            self.nutri.show()
        else:
            self.nutri.hide()

        if product.get("precio_unidad") if product.get("precio_unidad") is not None else product.get("unit_price") is not None:
            self.alert_price.setValue(max(0.01, float(product.get("precio_unidad") or product.get("unit_price")) * 0.9))

        precio_ant = compare.get("precio_antiguo") if compare else None
        precio_nue = compare.get("precio_nuevo") if compare else None
        if compare and precio_ant is not None and precio_nue is not None:
            pct = compare.get("cambio_pct")
            arrow = "▲" if (pct or 0) > 0 else "▼"
            color = "BadgeSube" if (pct or 0) > 0 else "BadgeBaja"
            self.compare.setObjectName(color)
            self.compare.setText(
                f"Hace ~6 meses: {formatear_euros(precio_ant)}  →  "
                f"Hoy: {formatear_euros(precio_nue)}   "
                f"{arrow} {pct:+.1f}%" if pct is not None else
                f"Histórico: {formatear_euros(precio_ant)} → {formatear_euros(precio_nue)}"
            )
            self.compare.style().unpolish(self.compare)
            self.compare.style().polish(self.compare)
        elif len(history) <= 1:
            self.compare.setText("Aún poco historial: vuelve otro día para ver la evolución del precio.")
        else:
            self.compare.setText("")

        self.ingredientes.setPlainText(product.get("ingredientes") or product.get("ingredients") or "Sin datos")
        self.alergenos.setText(product.get("alergenos") or product.get("allergens") or "Sin datos de alérgenos")
        nut_parts = []
        mapping = [
            ("energia_kcal", "kcal"),
            ("proteinas", "g prot."),
            ("hidratos", "g hidr."),
            ("grasas", "g grasas"),
            ("fibra", "g fibra"),
            ("azucares", "g azúcares"),
            ("sal", "g sal"),
        ]
        for key, label in mapping:
            if product.get(key) is not None:
                nut_parts.append(f"{product[key]:.1f} {label}")
        self.nutrition.setText(" · ".join(nut_parts) if nut_parts else "Sin tabla nutricional (aún)")

        self.alts.clear()
        for a in alts:
            self.alts.addItem(
                f"{formatear_euros(a.get('precio_unidad') if a.get('precio_unidad') is not None else a.get('unit_price'))} — {a.get('nombre') or a.get('name')}"
            )

    def _cart(self) -> None:
        if self.product:
            self.anadir_a_cesta.emit(self.product["id"])

    def _alert(self) -> None:
        if self.product:
            self.crear_alerta.emit(self.product["id"], float(self.alert_price.value()))


class PaginaCesta(QWidget):
    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cesta de la compra", objectName="TituloPagina"))

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Producto", "Cant.", "Precio", "Subtotal", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        self.totals = QLabel()
        self.totals.setWordWrap(True)
        layout.addWidget(self.totals)

        row = QHBoxLayout()
        save = QPushButton("Guardar compra")
        save.clicked.connect(self.guardar_compra)
        clear = QPushButton("Vaciar")
        clear.setProperty("secundario", True)
        clear.clicked.connect(self.vaciar)
        refresh = QPushButton("Actualizar")
        refresh.setProperty("secundario", True)
        refresh.clicked.connect(self.actualizar)
        row.addWidget(save)
        row.addWidget(clear)
        row.addWidget(refresh)
        row.addStretch()
        layout.addLayout(row)

    def actualizar(self) -> None:
        items = self.repositorio.items_cesta()
        self.table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(item["name"]))
            qty = QDoubleSpinBox()
            qty.setRange(0.1, 99)
            qty.setValue(float(item.get('cantidad') or item.get('quantity')))
            qty.valueChanged.connect(
                lambda v, pid=item["id"]: (self.repositorio.cesta_fijar_cantidad(pid, v), self.actualizar())
            )
            self.table.setCellWidget(i, 1, qty)
            price = float(item.get('precio_unidad') or item.get('unit_price') or 0)
            self.table.setItem(i, 2, QTableWidgetItem(formatear_euros(price)))
            self.table.setItem(
                i, 3, QTableWidgetItem(formatear_euros(price * float(item.get('cantidad') or item.get('quantity'))))
            )
            rm = QPushButton("Quitar")
            rm.setProperty("secundario", True)
            rm.clicked.connect(
                lambda _=False, pid=item["id"]: (self.repositorio.cesta_quitar(pid), self.actualizar())
            )
            self.table.setCellWidget(i, 4, rm)

        t = self.repositorio.totales_cesta()
        self.totals.setText(
            f"<b>Total: {formatear_euros(t['coste'])}</b><br>"
            f"Calorías: {t['energia_kcal']:.0f} kcal · "
            f"Prot. {t['proteinas']:.1f} g · Hidr. {t['hidratos']:.1f} g · "
            f"Grasas {t['grasas']:.1f} g · Fibra {t['fibra']:.1f} g · "
            f"Azúcar {t['azucares']:.1f} g · Sal {t['sal']:.2f} g"
        )

    def guardar_compra(self) -> None:
        pid = self.repositorio.guardar_compra()
        if pid is None:
            QMessageBox.information(self, "Cesta", "La cesta está vacía.")
            return
        QMessageBox.information(self, "Compra guardada", f"Compra #{pid} guardada en el historial.")
        self.actualizar()

    def vaciar(self) -> None:
        self.repositorio.cesta_vaciar()
        self.actualizar()


class PaginaHistorial(QWidget):
    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Historial de compras", objectName="TituloPagina"))
        self.insight = QLabel()
        self.insight.setWordWrap(True)
        layout.addWidget(self.insight)
        split = QSplitter()
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._show)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        split.addWidget(self.list)
        split.addWidget(self.detail)
        split.setStretchFactor(1, 2)
        layout.addWidget(split, 1)
        btn = QPushButton("Actualizar")
        btn.setProperty("secundario", True)
        btn.clicked.connect(self.actualizar)
        layout.addWidget(btn, alignment=Qt.AlignLeft)

    def actualizar(self) -> None:
        self.insight.setText(self.repositorio.insight_gastos())
        self._purchases = self.repositorio.listar_compras()
        self.list.clear()
        for p in self._purchases:
            self.list.addItem(
                f"#{p['id']}  {(p.get('comprado_en') or '')[:16]}  —  {formatear_euros(p['total'])}"
            )

    def _show(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "_purchases", [])):
            return
        p = self._purchases[row]
        items = self.repositorio.lineas_de_compra(p["id"])
        lines = [f"Compra #{p['id']} · {p.get('comprado_en')}", f"Total: {formatear_euros(p['total'])}", ""]
        for it in items:
            lines.append(
                f"- {it['cantidad']:g} × {it['nombre']} @ {formatear_euros(it['precio_unidad'])} "
                f"= {formatear_euros(it['total_linea'])}"
            )
        self.detail.setPlainText("\n".join(lines))


class PaginaComparador(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Comparador de precios", objectName="TituloPagina"))
        layout.addWidget(
            QLabel("Evolución respecto a hace ~6 meses (según tu historial local)", objectName="Atenuado")
        )
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Producto", "Antes", "Hoy", "Cambio", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(
            lambda r, _c: self.abrir_producto.emit(self.table.item(r, 4).text())
        )
        layout.addWidget(self.table, 1)
        btn = QPushButton("Actualizar")
        btn.setProperty("secundario", True)
        btn.clicked.connect(self.actualizar)
        layout.addWidget(btn, alignment=Qt.AlignLeft)

    def actualizar(self) -> None:
        products = self.repositorio.productos_con_historial(80)
        rows = []
        for p in products:
            cmp_ = self.repositorio.comparar_precio(p["id"], dias_atras=180)
            if not cmp_ or cmp_.get("precio_antiguo") is None:
                continue
            rows.append(cmp_)
        self.table.setRowCount(len(rows))
        for i, c in enumerate(rows):
            prod = c["product"]
            pct = c.get("cambio_pct")
            self.table.setItem(i, 0, QTableWidgetItem(prod.get("nombre") or prod.get("name")))
            self.table.setItem(i, 1, QTableWidgetItem(formatear_euros(c["precio_antiguo"])))
            self.table.setItem(i, 2, QTableWidgetItem(formatear_euros(c["precio_nuevo"])))
            txt = f"{pct:+.1f} %" if pct is not None else "—"
            item = QTableWidgetItem(txt)
            if pct is not None:
                item.setForeground(Qt.red if pct > 0 else Qt.darkGreen)
            self.table.setItem(i, 3, item)
            self.table.setItem(i, 4, QTableWidgetItem(prod["id"]))


class PaginaAlertas(QWidget):
    def __init__(self, repositorio, catalogo, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        self.catalogo = catalogo
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Alertas de precio", objectName="TituloPagina"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Producto", "Objetivo", "Estado", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        row = QHBoxLayout()
        check = QPushButton("Comprobar ahora")
        check.clicked.connect(self.comprobar)
        refresh = QPushButton("Actualizar lista")
        refresh.setProperty("secundario", True)
        refresh.clicked.connect(self.actualizar)
        row.addWidget(check)
        row.addWidget(refresh)
        row.addStretch()
        layout.addLayout(row)
        self.msg = QLabel("")
        layout.addWidget(self.msg)

    def actualizar(self) -> None:
        alerts = self.repositorio.listar_alertas()
        self.table.setRowCount(len(alerts))
        for i, a in enumerate(alerts):
            self.table.setItem(i, 0, QTableWidgetItem(a["product_name"]))
            self.table.setItem(i, 1, QTableWidgetItem(formatear_euros(a["target_price"])))
            self.table.setItem(
                i, 2, QTableWidgetItem("Activa" if a["active"] else f"Disparada {a.get('disparada_en') or a.get('triggered_at') or ''}")
            )
            rm = QPushButton("Eliminar")
            rm.setProperty("secundario", True)
            rm.clicked.connect(
                lambda _=False, aid=a["id"]: (self.repositorio.eliminar_alerta(aid), self.actualizar())
            )
            self.table.setCellWidget(i, 3, rm)

    def comprobar(self) -> None:
        # refrescar precios de alertas activas
        def work():
            for a in self.repositorio.listar_alertas(solo_activas=True):
                try:
                    self.catalogo.obtener_producto(a["id_producto"], enriquecer=False)
                except Exception:  # noqa: BLE001
                    pass
            return self.repositorio.comprobar_alertas()

        ejecutar_en_hilo(
            work,
            lambda triggered: (
                self.actualizar(),
                self.msg.setText(
                    "Sin alertas disparadas."
                    if not triggered
                    else "¡Bajadas! " + ", ".join(
                        f"{t.get('nombre_producto') or t.get('product_name')} → {formatear_euros(t.get('precio_actual') if t.get('precio_actual') is not None else t.get('current_price'))}" for t in triggered
                    )
                ),
            ),
            lambda e: self.msg.setText(f"Error: {e}"),
        )


class PaginaEstadisticas(QWidget):
    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Estadísticas", objectName="TituloPagina"))
        self.insight = QLabel()
        self.insight.setWordWrap(True)
        layout.addWidget(self.insight)

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self.figure = Figure(figsize=(8, 6), tight_layout=True)
            self.canvas = FigureCanvasQTAgg(self.figure)
            layout.addWidget(self.canvas, 1)
            self._has_mpl = True
        except Exception:  # noqa: BLE001
            self._has_mpl = False
            layout.addWidget(QLabel("Matplotlib no disponible para gráficas."))

        btn = QPushButton("Actualizar")
        btn.setProperty("secundario", True)
        btn.clicked.connect(self.actualizar)
        layout.addWidget(btn, alignment=Qt.AlignLeft)

    def actualizar(self) -> None:
        self.insight.setText(self.repositorio.insight_gastos())
        if not self._has_mpl:
            return
        summary = self.repositorio.resumen_gastos()
        self.figure.clear()
        ax1 = self.figure.add_subplot(221)
        ax2 = self.figure.add_subplot(222)
        ax3 = self.figure.add_subplot(212)

        months = [m.get("mes") or m.get("month") for m in summary.get("mensual") or summary.get("monthly")]
        mvals = [m["total"] for m in summary.get("mensual") or summary.get("monthly")]
        if months:
            ax1.bar(months, mvals, color="#0f6b45")
            ax1.set_title("Gasto mensual")
            ax1.tick_params(axis="x", rotation=45)
        else:
            ax1.set_title("Gasto mensual (sin datos)")

        years = [y.get("anio") or y.get("year") for y in summary.get("anual") or summary.get("yearly")]
        yvals = [y["total"] for y in summary.get("anual") or summary.get("yearly")]
        if years:
            ax2.bar(years, yvals, color="#178a58")
            ax2.set_title("Gasto anual")
        else:
            ax2.set_title("Gasto anual (sin datos)")

        cats = [c.get("categoria") or c.get("category")[:18] for c in summary.get("por_categoria") or summary.get("by_category")[:8]]
        cvals = [c["total"] for c in summary.get("por_categoria") or summary.get("by_category")[:8]]
        if cats:
            ax3.barh(cats[::-1], cvals[::-1], color="#0a3d2a")
            ax3.set_title("Gasto por categoría")
        else:
            ax3.set_title("Gasto por categoría (sin datos)")

        # inflación simple de cesta: media de cambios de precio de productos con historial
        changes = []
        for p in self.repositorio.productos_con_historial(50):
            cmp_ = self.repositorio.comparar_precio(p["id"], dias_atras=180)
            if cmp_ and cmp_.get("cambio_pct") is not None:
                changes.append(cmp_["change_pct"])
        if changes:
            avg = sum(changes) / len(changes)
            self.insight.setText(
                self.insight.text()
                + f"\nInflación media de tu cesta (~6 meses): {avg:+.1f}% "
                f"({len(changes)} productos)."
            )

        self.canvas.draw_idle()


class PaginaIA(QWidget):
    def __init__(self, asistente, parent=None) -> None:
        super().__init__(parent)
        self.asistente = asistente
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("IA — CestIA", objectName="TituloPagina"))
        layout.addWidget(
            QLabel(
                "Opcional. Usa Google Gemini (clave en Configuración). "
                "Ejemplos: presupuesto semanal, dieta 2200 kcal, lista rica en proteínas.",
                objectName="Atenuado",
            )
        )
        self.prompts = QListWidget()
        for text in (
            "Tengo 25 €. ¿Qué puedo comprar para toda la semana?",
            "Diseña una dieta de 2200 kcal usando productos de Mercadona.",
            "Dame una lista de compra rica en proteínas y barata.",
        ):
            self.prompts.addItem(text)
        self.prompts.itemClicked.connect(lambda it: self.input.setPlainText(it.text()))
        layout.addWidget(self.prompts)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Escribe tu pregunta…")
        self.input.setFixedHeight(90)
        layout.addWidget(self.input)
        ask = QPushButton("Preguntar a la IA")
        ask.clicked.connect(self.preguntar)
        layout.addWidget(ask, alignment=Qt.AlignLeft)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)
        self.status = QLabel("")
        self.status.setObjectName("Atenuado")
        layout.addWidget(self.status)

    def preguntar(self) -> None:
        q = self.input.toPlainText().strip()
        if not q:
            return
        self.status.setText("Pensando…")
        self.output.setPlainText("")

        def work():
            ctx = self.asistente.construir_contexto()
            return self.asistente.preguntar(q, ctx)

        ejecutar_en_hilo(
            work,
            lambda text: (self.output.setPlainText(text), self.status.setText("Listo")),
            lambda e: self.status.setText(f"Error: {e}"),
        )


class PaginaEscaner(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, catalogo, parent=None) -> None:
        super().__init__(parent)
        self.catalogo = catalogo
        self._timer = None
        self._cap = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Escáner de códigos de barras", objectName="TituloPagina"))
        layout.addWidget(
            QLabel("Usa la webcam. También puedes escribir el EAN a mano.", objectName="Atenuado")
        )

        self.video = QLabel("Cámara apagada")
        self.video.setMinimumHeight(280)
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setStyleSheet("background:#0a3d2a; color:white; border-radius:14px;")
        layout.addWidget(self.video)

        row = QHBoxLayout()
        self.ean = QLineEdit()
        self.ean.setPlaceholderText("EAN / código de barras")
        self.ean.returnPressed.connect(self.consultar)
        go = QPushButton("Buscar EAN")
        go.clicked.connect(self.consultar)
        start = QPushButton("Iniciar cámara")
        start.clicked.connect(self.iniciar_camara)
        stop = QPushButton("Parar")
        stop.setProperty("secundario", True)
        stop.clicked.connect(self.parar_camara)
        row.addWidget(self.ean, 1)
        row.addWidget(go)
        row.addWidget(start)
        row.addWidget(stop)
        layout.addLayout(row)

        self.status = QLabel("")
        layout.addWidget(self.status)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        self._last_code = ""

    def consultar(self) -> None:
        code = self.ean.text().strip()
        if not code:
            return
        self.status.setText(f"Buscando {code}…")

        def work():
            return self.catalogo.obtener_por_ean(code, enriquecer=True)

        def ok(product):
            if not product:
                self.status.setText("No encontrado en Mercadona/local.")
                self.result.setText("")
                return
            self.status.setText("Encontrado")
            self.result.setText(
                f"<b>{product['name']}</b><br>"
                f"{formatear_euros(product.get('precio_unidad') if product.get('precio_unidad') is not None else product.get('unit_price'))} · "
                f"Nutri-Score {product.get('nutriscore') or '—'}<br>"
                f"{(product.get('ingredientes') or product.get('ingredients') or '')[:240]}"
            )
            self.abrir_producto.emit(product["id"])

        ejecutar_en_hilo(work, ok, lambda e: self.status.setText(f"Error: {e}"))

    def iniciar_camara(self) -> None:
        try:
            import cv2
            from PySide6.QtCore import QTimer
            from PySide6.QtGui import QImage, QPixmap
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"OpenCV no disponible: {exc}")
            return

        self._cv2 = cv2
        self._QImage = QImage
        self._QPixmap = QPixmap
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self.status.setText("No se pudo abrir la webcam.")
            return
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)
        self.status.setText("Cámara activa — acerca el código de barras")

    def parar_camara(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.video.setText("Cámara apagada")

    def _tick(self) -> None:
        if self._cap is None:
            return
        ok, frame = self._cap.read()
        if not ok:
            return
        # decode barcode
        try:
            from pyzbar import pyzbar

            for bar in pyzbar.decode(frame):
                code = bar.data.decode("utf-8")
                if code and code != self._last_code:
                    self._last_code = code
                    self.ean.setText(code)
                    self.consultar()
        except Exception:  # noqa: BLE001
            pass

        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = self._QImage(rgb.data, w, h, ch * w, self._QImage.Format_RGB888)
        self.video.setPixmap(
            self._QPixmap.fromImage(img).scaled(
                self.video.width(), self.video.height(), Qt.KeepAspectRatio
            )
        )

    def hideEvent(self, event) -> None:  # noqa: N802
        self.parar_camara()
        super().hideEvent(event)


class PaginaConfiguracion(QWidget):
    """Ajustes locales: clave Gemini, modelo y almacén."""

    def __init__(self, asistente, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.asistente = asistente
        self.repositorio = repositorio

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Configuración", objectName="TituloPagina"))
        layout.addWidget(
            QLabel(
                "La clave se guarda solo en este equipo (base de datos local).",
                objectName="Atenuado",
            )
        )

        form = QFormLayout()
        self.campo_clave = QLineEdit()
        self.campo_clave.setEchoMode(QLineEdit.Password)
        self.campo_clave.setPlaceholderText("Pega aquí tu API key de Google AI Studio")
        self.campo_clave.setClearButtonEnabled(True)

        self.ver_clave = QCheckBox("Mostrar clave")
        self.ver_clave.setChecked(False)
        self.ver_clave.stateChanged.connect(self._al_cambiar_ver_clave)

        self.campo_modelo = QComboBox()
        self.campo_modelo.setEditable(True)
        self.campo_modelo.setMaxVisibleItems(10)
        vista = self.campo_modelo.view()
        vista.setStyleSheet(
            "background-color:#ffffff; color:#14201a;"
            "selection-background-color:#0f6b45; selection-color:#ffffff;"
        )
        for modelo in (
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ):
            self.campo_modelo.addItem(modelo)

        form.addRow("Clave Gemini", self.campo_clave)
        form.addRow("", self.ver_clave)
        form.addRow("Modelo", self.campo_modelo)
        layout.addLayout(form)

        layout.addWidget(QLabel("Tiendas de búsqueda"))
        layout.addWidget(
            QLabel(
                "Activa o desactiva las fuentes al buscar productos.",
                objectName="Atenuado",
            )
        )
        self.check_mercadona = QCheckBox("Mercadona")
        self.check_carrefour = QCheckBox("Carrefour")
        tiendas_row = QHBoxLayout()
        tiendas_row.addWidget(self.check_mercadona)
        tiendas_row.addWidget(self.check_carrefour)
        tiendas_row.addStretch()
        layout.addLayout(tiendas_row)

        botones = QHBoxLayout()
        guardar = QPushButton("Guardar")
        guardar.clicked.connect(self.guardar)
        probar = QPushButton("Probar conexión")
        probar.setProperty("secundario", True)
        probar.clicked.connect(self.probar)
        abrir = QPushButton("Abrir AI Studio")
        abrir.setProperty("secundario", True)
        abrir.clicked.connect(self._abrir_studio)
        botones.addWidget(guardar)
        botones.addWidget(probar)
        botones.addWidget(abrir)
        botones.addStretch()
        layout.addLayout(botones)

        self.estado = QLabel("")
        self.estado.setObjectName("Atenuado")
        self.estado.setWordWrap(True)
        layout.addWidget(self.estado)
        layout.addStretch(1)

        ayuda = QLabel(
            "1. Entra en aistudio.google.com/apikey\n"
            "2. Crea una API key\n"
            "3. Pégala aquí y pulsa Guardar\n\n"
            "Las tiendas usan APIs no oficiales y pueden cambiar sin aviso."
        )
        ayuda.setObjectName("Atenuado")
        layout.addWidget(ayuda)

    def actualizar(self) -> None:
        from cestia.tiendas import carrefour_activo, mercadona_activo

        clave = self.asistente.obtener_clave()
        self.campo_clave.setText(clave)
        modelo = self.asistente.obtener_modelo()
        idx = self.campo_modelo.findText(modelo)
        if idx >= 0:
            self.campo_modelo.setCurrentIndex(idx)
        else:
            self.campo_modelo.setEditText(modelo)
        self.check_mercadona.setChecked(mercadona_activo(self.repositorio))
        self.check_carrefour.setChecked(carrefour_activo(self.repositorio))
        if clave:
            self.estado.setText("Hay una clave configurada.")
        else:
            self.estado.setText("Todavía no hay clave. Configúrala para usar la IA.")

    def _al_cambiar_ver_clave(self, estado) -> None:
        marcado = estado == Qt.CheckState.Checked
        self.campo_clave.setEchoMode(
            QLineEdit.Normal if marcado else QLineEdit.Password
        )

    def guardar(self) -> None:
        from cestia.tiendas import guardar_tiendas

        clave = self.campo_clave.text().strip()
        modelo = self.campo_modelo.currentText().strip() or "gemini-2.0-flash"
        self.asistente.guardar_clave(clave)
        self.asistente.guardar_modelo(modelo)
        if not self.check_mercadona.isChecked() and not self.check_carrefour.isChecked():
            QMessageBox.warning(
                self,
                "Configuración",
                "Debes dejar al menos una tienda activa (Mercadona o Carrefour).",
            )
            return
        guardar_tiendas(
            self.repositorio,
            mercadona=self.check_mercadona.isChecked(),
            carrefour=self.check_carrefour.isChecked(),
        )
        partes = []
        if clave:
            partes.append("Clave Gemini guardada.")
        else:
            partes.append("Clave Gemini vacía.")
        tiendas = []
        if self.check_mercadona.isChecked():
            tiendas.append("Mercadona")
        if self.check_carrefour.isChecked():
            tiendas.append("Carrefour")
        partes.append("Tiendas: " + ", ".join(tiendas))
        mensaje = " ".join(partes)
        QMessageBox.information(self, "Configuración", mensaje)
        self.estado.setText(mensaje)

    def probar(self) -> None:
        # Guardar primero lo que hay en pantalla para probar esa clave
        self.asistente.guardar_clave(self.campo_clave.text().strip())
        self.asistente.guardar_modelo(
            self.campo_modelo.currentText().strip() or "gemini-2.0-flash"
        )
        self.estado.setText("Comprobando conexión con Gemini…")

        def trabajo():
            return self.asistente.comprobar_conexion()

        def al_ok(resultado):
            ok, mensaje = resultado
            self.estado.setText(mensaje)
            if ok:
                QMessageBox.information(self, "Gemini", mensaje)
            else:
                QMessageBox.warning(self, "Gemini", mensaje)

        ejecutar_en_hilo(trabajo, al_ok, lambda e: self.estado.setText(f"Error: {e}"))

    def _abrir_studio(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl("https://aistudio.google.com/apikey"))


class PaginaAbout(QWidget):
    """Información sobre CestIA."""

    URL_GITHUB = "https://github.com/entreunosyceros/cestia"
    RUTA_LOGO = Path(__file__).resolve().parents[2] / "img" / "logo.png"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        layout.addWidget(QLabel("About", objectName="TituloPagina"), alignment=Qt.AlignHCenter)

        self.logo = QLabel()
        self.logo.setObjectName("LogoAbout")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setMinimumHeight(180)
        if self.RUTA_LOGO.exists():
            pixmap = QPixmap(str(self.RUTA_LOGO))
            if not pixmap.isNull():
                self.logo.setPixmap(
                    pixmap.scaled(
                        420,
                        220,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                self.logo.setText("CestIA")
        else:
            self.logo.setText("CestIA")
        layout.addWidget(self.logo, alignment=Qt.AlignHCenter)

        descripcion = QLabel(
            "CestIA analiza el precio de tu compra en Mercadona y Carrefour "
            "desde tu equipo. Los datos se guardan en local; las tiendas usan "
            "APIs no oficiales pensadas para uso personal."
        )
        descripcion.setObjectName("Atenuado")
        descripcion.setWordWrap(True)
        descripcion.setAlignment(Qt.AlignHCenter)
        descripcion.setMaximumWidth(560)
        layout.addWidget(descripcion, alignment=Qt.AlignHCenter)

        funciones_titulo = QLabel("Funcionalidades")
        funciones_titulo.setObjectName("TituloPagina")
        funciones_titulo.setStyleSheet("font-size: 18px;")
        funciones_titulo.setAlignment(Qt.AlignHCenter)
        layout.addWidget(funciones_titulo)

        funciones = QLabel(
            "• Búsqueda multi-tienda (Mercadona y Carrefour), activables en Configuración\n"
            "• Ficha de producto: precio, foto, ingredientes, alérgenos, Nutri-Score y macros\n"
            "• Historial de precios y alternativas más baratas\n"
            "• Cesta con coste total y resumen nutricional\n"
            "• Historial de compras e insights de gasto\n"
            "• Comparador de precios (evolución ~6 meses)\n"
            "• Alertas cuando un producto baja de un precio\n"
            "• Estadísticas: gasto mensual/anual/categoría e inflación de cesta\n"
            "• IA con Google Gemini (menús, presupuestos, listas)\n"
            "• Escáner de códigos de barras (webcam o EAN)\n"
            "• Configuración: clave Gemini, modelo y tiendas activas"
        )
        funciones.setObjectName("Atenuado")
        funciones.setWordWrap(True)
        funciones.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        funciones.setMaximumWidth(560)
        layout.addWidget(funciones, alignment=Qt.AlignHCenter)

        from cestia import __version__

        version = QLabel(f"Versión {__version__}")
        version.setObjectName("Atenuado")
        version.setAlignment(Qt.AlignHCenter)
        layout.addWidget(version)

        github = QPushButton("Ver en GitHub")
        github.setProperty("secundario", True)
        github.setCursor(Qt.PointingHandCursor)
        github.clicked.connect(self._abrir_github)
        layout.addWidget(github, alignment=Qt.AlignHCenter)

        layout.addStretch(1)

    def _abrir_github(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(self.URL_GITHUB))
