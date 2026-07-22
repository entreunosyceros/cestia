"""Páginas adicionales: favoritos, listas y comparador de productos."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cestia.interfaz.utilidades import formatear_euros, cargar_miniatura
from cestia.tiendas import nombre_tienda


class PaginaFavoritos(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Favoritos", objectName="TituloPagina"))
        layout.addWidget(
            QLabel("Productos que marcas como habituales.", objectName="Atenuado")
        )
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["", "Producto", "Tienda", "Precio", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._abrir_fila)
        layout.addWidget(self.table, 1)
        btn = QPushButton("Actualizar")
        btn.setProperty("secundario", True)
        btn.clicked.connect(self.actualizar)
        layout.addWidget(btn, alignment=Qt.AlignLeft)
        self._items: list[dict[str, Any]] = []

    def actualizar(self) -> None:
        self._items = self.repositorio.listar_favoritos()
        self.table.setRowCount(len(self._items))
        for i, p in enumerate(self._items):
            thumb = QLabel()
            cargar_miniatura(thumb, p.get("miniatura") or p.get("thumbnail"), 40)
            self.table.setCellWidget(i, 0, thumb)
            self.table.setItem(
                i, 1, QTableWidgetItem(p.get("nombre") or p.get("name") or "")
            )
            self.table.setItem(
                i, 2, QTableWidgetItem(nombre_tienda(p.get("tienda"), p.get("id")))
            )
            self.table.setItem(
                i,
                3,
                QTableWidgetItem(
                    formatear_euros(p.get("precio_unidad") or p.get("unit_price"))
                ),
            )
            rm = QPushButton("Quitar")
            rm.setProperty("secundario", True)
            rm.clicked.connect(
                lambda _=False, pid=p["id"]: (
                    self.repositorio.favorito_quitar(pid),
                    self.actualizar(),
                )
            )
            self.table.setCellWidget(i, 4, rm)
            self.table.setRowHeight(i, 48)

    def _abrir_fila(self, fila: int, _col: int) -> None:
        if 0 <= fila < len(self._items):
            self.abrir_producto.emit(self._items[fila]["id"])


class PaginaListas(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Listas de la compra", objectName="TituloPagina"))
        layout.addWidget(
            QLabel("Plantillas reutilizables para tus compras.", objectName="Atenuado")
        )
        layout.addWidget(
            QLabel(
                "«Cargar en cesta» lleva los productos de la lista a la cesta. "
                "«Copiar cesta a esta lista» guarda la cesta actual en la plantilla. "
                "«Registrar gasto» anota el total de la lista en el registro de gastos.",
                objectName="Atenuado",
            )
        )
        split = QSplitter()
        izq = QWidget()
        izq_l = QVBoxLayout(izq)
        self.listas = QListWidget()
        self.listas.currentRowChanged.connect(self._mostrar_lista)
        izq_l.addWidget(self.listas)
        btns = QHBoxLayout()
        nueva = QPushButton("Nueva lista")
        nueva.clicked.connect(self._nueva)
        borrar = QPushButton("Eliminar lista")
        borrar.setProperty("secundario", True)
        borrar.clicked.connect(self._eliminar)
        btns.addWidget(nueva)
        btns.addWidget(borrar)
        izq_l.addLayout(btns)
        split.addWidget(izq)
        der = QWidget()
        der_l = QVBoxLayout(der)
        self.detalle = QTableWidget(0, 4)
        self.detalle.setHorizontalHeaderLabels(
            ["Producto", "Cant.", "Precio", "Quitar"]
        )
        cabecera = self.detalle.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.detalle.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detalle.setSelectionBehavior(QTableWidget.SelectRows)
        self.detalle.verticalHeader().setVisible(False)
        self.detalle.cellDoubleClicked.connect(self._abrir_producto_lista)
        atajo_quitar = QShortcut(QKeySequence(Qt.Key_Delete), self.detalle)
        atajo_quitar.activated.connect(self._quitar_producto_seleccionado)
        der_l.addWidget(self.detalle, 1)
        self.total_lista = QLabel("")
        self.total_lista.setWordWrap(True)
        der_l.addWidget(self.total_lista)
        acc = QHBoxLayout()
        cargar = QPushButton("Cargar en cesta")
        cargar.clicked.connect(self._cargar_cesta)
        guardar = QPushButton("Copiar cesta a esta lista")
        guardar.setProperty("secundario", True)
        guardar.clicked.connect(self._guardar_cesta)
        quitar_prod = QPushButton("Quitar producto")
        quitar_prod.setProperty("secundario", True)
        quitar_prod.clicked.connect(self._quitar_producto_seleccionado)
        registrar = QPushButton("Registrar gasto")
        registrar.clicked.connect(self._registrar_gasto)
        acc.addWidget(cargar)
        acc.addWidget(guardar)
        acc.addWidget(registrar)
        acc.addWidget(quitar_prod)
        acc.addStretch()
        der_l.addLayout(acc)
        split.addWidget(der)
        split.setStretchFactor(1, 2)
        layout.addWidget(split, 1)
        self._listas: list[dict[str, Any]] = []
        self._items: list[dict[str, Any]] = []

    def actualizar(self) -> None:
        fila = self.listas.currentRow()
        self._listas = self.repositorio.listar_listas_compra()
        self.listas.clear()
        for l in self._listas:
            self.listas.addItem(
                f"{l['nombre']} ({l.get('num_items', 0)} productos)"
            )
        if 0 <= fila < len(self._listas):
            self.listas.setCurrentRow(fila)
        elif self._listas:
            self.listas.setCurrentRow(0)
        else:
            self.detalle.setRowCount(0)
            self.total_lista.setText("")

    def _actualizar_total_lista(self, id_lista: int) -> None:
        if not self._items:
            self.total_lista.setText("Lista vacía.")
            return
        totales = self.repositorio.totales_lista_compra(id_lista)
        texto = (
            f"<b>Total estimado: {formatear_euros(totales['coste'])}</b> "
            f"({totales['productos']} productos)"
        )
        sin_precio = int(totales.get("sin_precio") or 0)
        if sin_precio:
            texto += (
                f"<br><span>Nota: {sin_precio} producto(s) sin precio guardado "
                f"no se incluyen en el total.</span>"
            )
        self.total_lista.setText(texto)

    def _abrir_producto_lista(self, fila: int, _col: int) -> None:
        if 0 <= fila < len(self._items):
            self.abrir_producto.emit(self._items[fila]["id"])

    def _quitar_producto_seleccionado(self) -> None:
        fila_lista = self.listas.currentRow()
        fila_prod = self.detalle.currentRow()
        if fila_lista < 0 or fila_prod < 0 or fila_prod >= len(self._items):
            QMessageBox.information(
                self,
                "Lista",
                "Selecciona un producto en la tabla para quitarlo de la lista.",
            )
            return
        item = self._items[fila_prod]
        nombre = item.get("nombre") or item.get("name") or "este producto"
        if (
            QMessageBox.question(
                self,
                "Quitar producto",
                f"¿Quitar «{nombre}» de la lista?",
            )
            != QMessageBox.Yes
        ):
            return
        self.repositorio.lista_quitar_producto(
            self._listas[fila_lista]["id"], item["id"]
        )
        self.actualizar()

    def _quitar_producto_fila(self, id_lista: int, id_producto: str) -> None:
        self.repositorio.lista_quitar_producto(id_lista, id_producto)
        self.actualizar()

    def _nueva(self) -> None:
        nombre, ok = QInputDialog.getText(self, "Nueva lista", "Nombre:")
        if ok and nombre.strip():
            self.repositorio.crear_lista_compra(nombre.strip())
            self.actualizar()

    def _eliminar(self) -> None:
        row = self.listas.currentRow()
        if row < 0 or row >= len(self._listas):
            return
        lista = self._listas[row]
        if (
            QMessageBox.question(
                self,
                "Eliminar lista",
                f"¿Eliminar «{lista['nombre']}»?",
            )
            == QMessageBox.Yes
        ):
            self.repositorio.eliminar_lista_compra(lista["id"])
            self.actualizar()
            self.detalle.setRowCount(0)
            self.total_lista.setText("")

    def _mostrar_lista(self, row: int) -> None:
        if row < 0 or row >= len(self._listas):
            self.detalle.setRowCount(0)
            self.total_lista.setText("")
            return
        id_lista = self._listas[row]["id"]
        self._items = self.repositorio.items_lista_compra(id_lista)
        self.detalle.setRowCount(len(self._items))
        for i, item in enumerate(self._items):
            self.detalle.setItem(
                i, 0, QTableWidgetItem(item.get("nombre") or item.get("name") or "")
            )
            qty = QSpinBox()
            qty.setRange(1, 99)
            qty.setValue(max(1, int(round(float(item.get("cantidad") or 1)))))
            qty.valueChanged.connect(
                lambda v, lid=id_lista, pid=item["id"]: (
                    self.repositorio.lista_fijar_cantidad(lid, pid, v),
                    self._mostrar_lista(self.listas.currentRow()),
                )
            )
            self.detalle.setCellWidget(i, 1, qty)
            self.detalle.setItem(
                i,
                2,
                QTableWidgetItem(
                    formatear_euros(item.get("precio_unidad") or item.get("unit_price"))
                ),
            )
            rm = QPushButton("Quitar")
            rm.setProperty("secundario", True)
            rm.clicked.connect(
                lambda _=False, lid=id_lista, pid=item["id"]: self._quitar_producto_fila(
                    lid, pid
                )
            )
            self.detalle.setCellWidget(i, 3, rm)
            self.detalle.setRowHeight(i, 48)
        self._actualizar_total_lista(id_lista)

    def _cargar_cesta(self) -> None:
        row = self.listas.currentRow()
        if row < 0:
            return
        n = self.repositorio.cargar_lista_en_cesta(self._listas[row]["id"])
        QMessageBox.information(self, "Cesta", f"{n} productos añadidos a la cesta.")

    def _registrar_gasto(self) -> None:
        row = self.listas.currentRow()
        if row < 0:
            return
        lista = self._listas[row]
        totales = self.repositorio.totales_lista_compra(lista["id"])
        if not totales["productos"]:
            QMessageBox.information(self, "Lista", "La lista está vacía.")
            return
        total_txt = formatear_euros(totales["coste"])
        mensaje = (
            f"¿Registrar un gasto de {total_txt} por la lista "
            f"«{lista['nombre']}»?"
        )
        sin_precio = int(totales.get("sin_precio") or 0)
        if sin_precio:
            mensaje += (
                f"\n\nNota: {sin_precio} producto(s) sin precio no se incluyen "
                f"en el total."
            )
        if QMessageBox.question(self, "Registrar gasto", mensaje) != QMessageBox.Yes:
            return
        id_gasto = self.repositorio.guardar_lista_en_registro(lista["id"])
        if id_gasto is None:
            QMessageBox.warning(self, "Registrar gasto", "No se pudo registrar el gasto.")
            return
        QMessageBox.information(
            self,
            "Gasto registrado",
            f"Gasto #{id_gasto} registrado ({total_txt}).",
        )

    def _guardar_cesta(self) -> None:
        row = self.listas.currentRow()
        if row < 0:
            return
        n = self.repositorio.guardar_cesta_en_lista(self._listas[row]["id"])
        if n == 0:
            QMessageBox.warning(
                self,
                "Cesta vacía",
                "La cesta no tiene productos.\n\n"
                "Este botón copia la cesta actual a la lista seleccionada. "
                "Para llevar los productos de la lista a la cesta, usa "
                "«Cargar en cesta».",
            )
            return
        QMessageBox.information(
            self, "Lista", f"{n} productos de la cesta copiados a la lista."
        )
        self.actualizar()
        self._mostrar_lista(row)


class PaginaCompararProductos(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        self._a: dict[str, Any] | None = None
        self._b: dict[str, Any] | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Comparar productos", objectName="TituloPagina"))
        layout.addWidget(
            QLabel(
                "Selecciona dos productos desde la ficha (botón «Comparar»).",
                objectName="Atenuado",
            )
        )
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["", "Producto A", "Producto B"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        layout.addWidget(self.table, 1)
        row = QHBoxLayout()
        limpiar = QPushButton("Limpiar")
        limpiar.setProperty("secundario", True)
        limpiar.clicked.connect(self.limpiar)
        row.addWidget(limpiar)
        row.addStretch()
        layout.addLayout(row)

    def establecer_producto(self, producto: dict[str, Any]) -> None:
        if self._a is None:
            self._a = producto
        elif self._b is None and producto.get("id") != self._a.get("id"):
            self._b = producto
        else:
            self._a = producto
            self._b = None
        self._render()

    def limpiar(self) -> None:
        self._a = self._b = None
        self.table.setRowCount(0)

    def _render(self) -> None:
        if not self._a:
            self.table.setRowCount(0)
            return
        campos = [
            ("Nombre", "nombre", "name"),
            ("Tienda", "tienda", None),
            ("Precio", "precio_unidad", "unit_price"),
            ("Marca", "marca", "brand"),
            ("Nutri-Score", "nutriscore", None),
            ("Energía (kcal)", "energia_kcal", None),
            ("Proteínas (g)", "proteinas", None),
            ("Hidratos (g)", "hidratos", None),
            ("Grasas (g)", "grasas", None),
            ("Alérgenos", "alergenos", "allergens"),
        ]
        self.table.setRowCount(len(campos))
        for i, (etiq, k1, k2) in enumerate(campos):
            self.table.setItem(i, 0, QTableWidgetItem(etiq))
            self.table.setItem(i, 1, QTableWidgetItem(self._valor(self._a, k1, k2)))
            self.table.setItem(
                i,
                2,
                QTableWidgetItem(self._valor(self._b, k1, k2) if self._b else "—"),
            )

    @staticmethod
    def _valor(p: dict[str, Any] | None, k1: str, k2: str | None) -> str:
        if not p:
            return "—"
        if k1 == "tienda":
            return nombre_tienda(p.get("tienda"), p.get("id"))
        if k1 in {"precio_unidad"}:
            v = p.get(k1) if p.get(k1) is not None else (p.get(k2) if k2 else None)
            return formatear_euros(v) if v is not None else "—"
        v = p.get(k1)
        if v is None and k2:
            v = p.get(k2)
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.1f}"
        return str(v)
