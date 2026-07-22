"""Páginas principales de CestIA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cestia.interfaz.nutriscore import GraficoNutriScore
from cestia.interfaz.grafico_precio import GraficoPrecio
from cestia.interfaz.progreso import (
    ProgresoEspera,
    crear_barra_progreso,
    crear_barra_progreso_espera,
    mostrar_progreso,
)
from cestia.interfaz.tarjeta import TarjetaModerna
from cestia.interfaz.utilidades import (
    cargar_miniatura,
    formatear_euros,
    mostrar_respuesta_ia,
)
from cestia.interfaz.trabajadores import ejecutar_en_hilo
from cestia.logica.busqueda import (
    agrupar_multi_tienda,
    es_rebajado,
    filtrar_resultados,
)
from cestia.logica.cesta_optima import (
    calcular_cesta_optima_mezclada,
    calcular_cesta_por_tienda,
)
from cestia.tiendas import (
    alcampo_activo,
    carrefour_activo,
    dia_activo,
    eroski_activo,
    froiz_activo,
    gadis_activo,
    lidl_activo,
    mercadona_activo,
    nombre_tienda,
)


class PaginaBusqueda(QWidget):
    abrir_producto = Signal(str)

    def __init__(self, catalogo, repositorio=None, parent=None) -> None:
        super().__init__(parent)
        self.catalogo = catalogo
        self.repositorio = repositorio
        self._results: list[dict[str, Any]] = []
        self._raw_results: list[dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Productos", objectName="TituloPagina"))
        self.subtitulo = QLabel("Busca productos en las tiendas activas")
        self.subtitulo.setObjectName("Atenuado")
        layout.addWidget(self.subtitulo)

        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("leche, aceite, café… (Ctrl+F)")
        self.query.returnPressed.connect(self.buscar)
        btn = QPushButton("Buscar")
        btn.clicked.connect(self.buscar)
        row.addWidget(self.query, 1)
        row.addWidget(btn)
        layout.addLayout(row)

        filtros = QHBoxLayout()
        self.filtro_tienda = QComboBox()
        self.filtro_tienda.addItem("Todas las tiendas", "")
        for clave, etiqueta in [
            ("mercadona", "Mercadona"),
            ("carrefour", "Carrefour"),
            ("alcampo", "Alcampo"),
            ("froiz", "Froiz"),
            ("eroski", "Eroski"),
            ("lidl", "Lidl"),
            ("dia", "Dia"),
            ("gadis", "Gadis"),
        ]:
            self.filtro_tienda.addItem(etiqueta, clave)
        self.filtro_nutri = QComboBox()
        self.filtro_nutri.addItem("Nutri-Score: todos", "")
        for g in ("A", "B", "C", "D", "E"):
            self.filtro_nutri.addItem(f"Nutri-Score {g}", g)
        self.filtro_precio_min = QDoubleSpinBox()
        self.filtro_precio_min.setPrefix("Min ")
        self.filtro_precio_min.setSuffix(" €")
        self.filtro_precio_min.setMaximum(999)
        self.filtro_precio_max = QDoubleSpinBox()
        self.filtro_precio_max.setPrefix("Max ")
        self.filtro_precio_max.setSuffix(" €")
        self.filtro_precio_max.setMaximum(999)
        self.filtro_precio_max.setValue(999)
        self.check_rebajados = QCheckBox("Solo rebajados")
        self.check_sin_gluten = QCheckBox("Sin gluten")
        self.check_agrupar = QCheckBox("Comparar entre tiendas")
        self.check_agrupar.setChecked(True)
        for w in (
            self.filtro_tienda,
            self.filtro_nutri,
            self.filtro_precio_min,
            self.filtro_precio_max,
            self.check_rebajados,
            self.check_sin_gluten,
            self.check_agrupar,
        ):
            if isinstance(w, QCheckBox):
                w.stateChanged.connect(self._aplicar_filtros)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self._aplicar_filtros)
            elif isinstance(w, QDoubleSpinBox):
                w.valueChanged.connect(self._aplicar_filtros)
        filtros.addWidget(self.filtro_tienda)
        filtros.addWidget(self.filtro_nutri)
        filtros.addWidget(self.filtro_precio_min)
        filtros.addWidget(self.filtro_precio_max)
        filtros.addWidget(self.check_rebajados)
        filtros.addWidget(self.check_sin_gluten)
        filtros.addWidget(self.check_agrupar)
        filtros.addStretch()
        layout.addLayout(filtros)

        self.status = QLabel("")
        self.status.setObjectName("Atenuado")
        layout.addWidget(self.status)
        self.progreso = crear_barra_progreso()
        layout.addWidget(self.progreso)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                "Producto",
                "Supermercado",
                "Precio",
                "€/ud ref.",
                "Marca",
                "Oferta",
                "Comparación",
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 56)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in (2, 3, 4, 5, 6, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setCornerButtonEnabled(False)
        self.table.cellDoubleClicked.connect(self._open_row)
        layout.addWidget(self.table, 1)

    def enfocar_busqueda(self) -> None:
        self.query.setFocus()
        self.query.selectAll()

    def actualizar(self) -> None:
        if not self.repositorio:
            return
        activas = []
        if mercadona_activo(self.repositorio):
            activas.append("Mercadona")
        if carrefour_activo(self.repositorio):
            activas.append("Carrefour")
        if alcampo_activo(self.repositorio):
            activas.append("Alcampo")
        if froiz_activo(self.repositorio):
            activas.append("Froiz")
        if eroski_activo(self.repositorio):
            activas.append("Eroski")
        if lidl_activo(self.repositorio):
            activas.append("Lidl")
        if dia_activo(self.repositorio):
            activas.append("Dia")
        if gadis_activo(self.repositorio):
            activas.append("Gadis")
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
        mostrar_progreso(self.progreso, True)

        def work():
            return self.catalogo.buscar(q)

        def ok(results):
            mostrar_progreso(self.progreso, False)
            self._raw_results = results
            self._aplicar_filtros()

        def error(e):
            mostrar_progreso(self.progreso, False)
            self.status.setText(f"Error: {e}")

        ejecutar_en_hilo(work, ok, error)

    def _aplicar_filtros(self) -> None:
        if not self._raw_results:
            self._on_results([])
            return
        tienda = self.filtro_tienda.currentData()
        tiendas = {tienda} if tienda else None
        nutri = self.filtro_nutri.currentData()
        nutriscore = {nutri} if nutri else None
        pmin = self.filtro_precio_min.value()
        pmax = self.filtro_precio_max.value()
        historial_fn = None
        if self.repositorio and self.check_rebajados.isChecked():
            historial_fn = self.repositorio.historial_precios
        filtrados = filtrar_resultados(
            self._raw_results,
            tiendas=tiendas,
            precio_min=pmin if pmin > 0 else None,
            precio_max=pmax if pmax < 999 else None,
            nutriscore=nutriscore,
            solo_rebajados=self.check_rebajados.isChecked(),
            sin_gluten=self.check_sin_gluten.isChecked(),
            historial_fn=historial_fn,
        )
        if self.check_agrupar.isChecked():
            filtrados = agrupar_multi_tienda(filtrados)
        self._on_results(filtrados)

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
            nombre = p.get("nombre") or p.get("name") or ""
            if p.get("_grupo_tamano", 1) > 1:
                nombre += f"  ({p['_grupo_tamano']} tiendas)"
            self.table.setItem(i, 1, QTableWidgetItem(nombre))
            item_tienda = QTableWidgetItem(
                PaginaBusqueda._nombre_supermercado(p)
            )
            item_tienda.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, item_tienda)
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
            rebajado = es_rebajado(
                p,
                self.repositorio.historial_precios(p["id"])
                if self.repositorio
                else None,
            )
            oferta = QLabel("REBAJADO" if rebajado else "")
            if rebajado:
                oferta.setObjectName("BadgeOferta")
            oferta.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(i, 6, oferta)
            self.table.setItem(i, 7, QTableWidgetItem(self._texto_comparacion(p)))
            self.table.setRowHeight(i, 56)

    @staticmethod
    def _texto_comparacion(producto: dict[str, Any]) -> str:
        """Texto claro para la columna Comparación (multi-tienda)."""
        if producto.get("_grupo_tamano", 1) <= 1:
            return "—"
        if producto.get("_es_mejor"):
            return "✓ Más barato"
        ahorro = producto.get("_ahorro_vs_mejor")
        tienda = nombre_tienda(producto.get("_mejor_tienda"))
        precio = formatear_euros(producto.get("_mejor_precio"))
        if ahorro:
            return f"Más barato en {tienda}: {precio} (ahorras {formatear_euros(ahorro)})"
        if producto.get("_mejor_precio") is not None:
            return f"Más barato en {tienda}: {precio}"
        return "—"

    def _open_row(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._results):
            self.abrir_producto.emit(self._results[row]["id"])

    @staticmethod
    def _nombre_supermercado(producto: dict[str, Any]) -> str:
        return nombre_tienda(producto.get("tienda"), producto.get("id"))


class PaginaProducto(QWidget):
    anadir_a_cesta = Signal(str)
    crear_alerta = Signal(str, float)
    abrir_producto = Signal(str)
    comparar_producto = Signal(object)
    anadir_lista = Signal(str)

    def __init__(self, catalogo, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.catalogo = catalogo
        self.repositorio = repositorio
        self.product: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setObjectName("PaginaProducto")
        self.setAutoFillBackground(True)
        self._tema = "claro"
        self._widgets_paleta: list[QWidget] = [self]

        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 8)
        self.back = QPushButton("← Volver")
        self.back.setProperty("secundario", True)
        top.addWidget(self.back)
        top.addStretch()
        layout.addLayout(top)

        self.progreso = crear_barra_progreso()
        layout.addWidget(self.progreso)

        scroll = QScrollArea()
        scroll.setObjectName("ScrollFicha")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._widgets_paleta.append(scroll)
        layout.addWidget(scroll, 1)

        contenido = QWidget()
        contenido.setObjectName("FichaProducto")
        contenido.setAutoFillBackground(True)
        self._widgets_paleta.append(contenido)
        scroll.setWidget(contenido)
        viewport = scroll.viewport()
        if viewport is not None:
            viewport.setAutoFillBackground(True)
            self._widgets_paleta.append(viewport)
        self._aplicar_paleta(self._tema)
        ficha = QVBoxLayout(contenido)
        ficha.setContentsMargins(16, 4, 16, 24)
        ficha.setSpacing(12)

        body = QHBoxLayout()
        body.setSpacing(20)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        cargar_miniatura(self.image, None, 220)
        body.addWidget(self.image, 0, Qt.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(10)
        self.title = QLabel("Producto")
        self.title.setObjectName("TituloPagina")
        self.title.setWordWrap(True)
        self.meta = QLabel("")
        self.meta.setObjectName("Atenuado")
        self.meta.setWordWrap(True)
        self.price = QLabel("")
        self.price.setObjectName("Precio")
        self.badge_oferta = QLabel("")
        self.badge_oferta.setObjectName("BadgeOferta")
        self.badge_oferta.hide()
        self.bulk = QLabel("")
        self.bulk.setObjectName("Atenuado")
        self.nutri = GraficoNutriScore()
        self.compare = QLabel("")
        self.compare.setWordWrap(True)
        info.addWidget(self.title)
        info.addWidget(self.meta)
        info.addWidget(self.price)
        info.addWidget(self.badge_oferta)
        info.addWidget(self.bulk)
        info.addWidget(self.nutri)
        self.grafico_precio = GraficoPrecio()
        info.addWidget(self.grafico_precio)
        info.addWidget(self.compare)

        actions = QHBoxLayout()
        self.btn_cart = QPushButton("Añadir a la cesta")
        self.btn_cart.clicked.connect(self._cart)
        self.btn_fav = QPushButton("☆ Favorito")
        self.btn_fav.setProperty("secundario", True)
        self.btn_fav.clicked.connect(self._toggle_fav)
        self.btn_compare = QPushButton("Comparar")
        self.btn_compare.setProperty("secundario", True)
        self.btn_compare.clicked.connect(self._comparar)
        self.btn_lista = QPushButton("Guardar en lista")
        self.btn_lista.setProperty("secundario", True)
        self.btn_lista.clicked.connect(self._lista)
        self.alert_price = QDoubleSpinBox()
        self.alert_price.setPrefix("Alertar < ")
        self.alert_price.setSuffix(" €")
        self.alert_price.setMaximum(9999)
        self.alert_price.setDecimals(2)
        self.btn_alert = QPushButton("Crear alerta")
        self.btn_alert.setProperty("secundario", True)
        self.btn_alert.clicked.connect(self._alert)
        actions.addWidget(self.btn_cart)
        actions.addWidget(self.btn_fav)
        actions.addWidget(self.btn_compare)
        actions.addWidget(self.btn_lista)
        actions.addWidget(self.alert_price)
        actions.addWidget(self.btn_alert)
        actions.addStretch()
        info.addLayout(actions)

        self.ingredientes = QPlainTextEdit()
        self.ingredientes.setReadOnly(True)
        self.ingredientes.setMaximumHeight(120)
        info.addWidget(QLabel("Ingredientes"))
        info.addWidget(self.ingredientes)

        self.tarjeta_alergenos = TarjetaModerna(
            tipo="peligro",
            titulo="Alérgenos",
        )
        info.addWidget(self.tarjeta_alergenos)

        self.tarjeta_nutricion = TarjetaModerna(
            tipo="info",
            titulo="Nutrición (por 100 g)",
            pista=(
                "Valores de Open Food Facts cuando están disponibles. "
                "A veces pueden referirse al producto ya preparado/reconstituido."
            ),
        )
        info.addWidget(self.tarjeta_nutricion)

        panel_alts = QFrame()
        panel_alts.setObjectName("PanelAlternativas")
        alts_layout = QVBoxLayout(panel_alts)
        alts_layout.setContentsMargins(14, 12, 14, 12)
        alts_layout.setSpacing(6)
        titulo_alts = QLabel("Alternativas más baratas")
        titulo_alts.setObjectName("TituloAlternativas")
        pista_alts = QLabel("Pulsa un producto para abrir su ficha")
        pista_alts.setObjectName("PistaAlternativas")
        self.alts = QListWidget()
        self.alts.setObjectName("ListaEnlaces")
        self.alts.setMinimumHeight(120)
        self.alts.setMaximumHeight(220)
        self.alts.setCursor(Qt.PointingHandCursor)
        self.alts.itemClicked.connect(self._abrir_alternativa)
        self.alts.itemActivated.connect(self._abrir_alternativa)
        alts_layout.addWidget(titulo_alts)
        alts_layout.addWidget(pista_alts)
        alts_layout.addWidget(self.alts)
        info.addWidget(panel_alts)

        info.addStretch(1)
        body.addLayout(info, 1)
        ficha.addLayout(body)

    def cargar(self, id_producto: str) -> None:
        self.title.setText("Cargando…")
        mostrar_progreso(self.progreso, True)

        def work():
            product = self.catalogo.obtener_producto(id_producto, enriquecer=True)
            compare = self.repositorio.comparar_precio(id_producto, dias_atras=180)
            alts = self.catalogo.alternativas_mas_baratas(product)
            history = self.repositorio.historial_precios(id_producto)
            return product, compare, alts, history

        def ok(payload):
            mostrar_progreso(self.progreso, False)
            self._show(payload)

        def error(e):
            mostrar_progreso(self.progreso, False)
            self.title.setText(f"Error: {e}")

        ejecutar_en_hilo(work, ok, error)

    def _show(self, payload) -> None:
        product, compare, alts, history = payload
        self.product = product
        self.title.setText(product.get("nombre") or product.get("name") or "")
        meta_bits = [
            x
            for x in [
                PaginaBusqueda._nombre_supermercado(product),
                product.get("marca") or product.get("brand"),
                product.get("envase") or product.get("packaging"),
                product.get("ean"),
            ]
            if x
        ]
        self.meta.setText(" · ".join(meta_bits))
        cargar_miniatura(self.image, product.get("miniatura") or product.get("thumbnail"), 220)
        precio_unidad = product.get("precio_unidad")
        if precio_unidad is None:
            precio_unidad = product.get("unit_price")
        self.price.setText(formatear_euros(precio_unidad))
        if es_rebajado(product, history):
            self.badge_oferta.setText("  REBAJADO  ")
            self.badge_oferta.show()
        else:
            self.badge_oferta.hide()
        self.grafico_precio.establecer_historial(history)
        es_fav = self.repositorio.es_favorito(product["id"])
        self.btn_fav.setText("★ Favorito" if es_fav else "☆ Favorito")
        precio_bulto = product.get("precio_bulto")
        if precio_bulto is None:
            precio_bulto = product.get("bulk_price")
        if precio_bulto:
            formato = product.get("formato_tamano") or product.get("size_format") or "ud"
            self.bulk.setText(f"{formatear_euros(precio_bulto)}/{formato}")
        else:
            self.bulk.setText("")
        nutriscore = product.get("nutriscore")
        if nutriscore:
            self.nutri.establecer_grado(nutriscore)
        else:
            self.nutri.establecer_no_disponible()

        if precio_unidad is not None:
            self.alert_price.setValue(max(0.01, float(precio_unidad) * 0.9))

        precio_ant = compare.get("precio_antiguo") if compare else None
        precio_nue = compare.get("precio_nuevo") if compare else None
        if compare and precio_ant is not None and precio_nue is not None:
            pct = compare.get("cambio_pct")
            color = "BadgeSube" if (pct or 0) > 0 else "BadgeBaja"
            self.compare.setObjectName(color)
            if pct is not None:
                arrow = "▲" if pct > 0 else "▼"
                texto_compare = (
                    f"Hace ~6 meses: {formatear_euros(precio_ant)}  →  "
                    f"Hoy: {formatear_euros(precio_nue)}   {arrow} {pct:+.1f}%"
                )
            else:
                texto_compare = (
                    f"Histórico: {formatear_euros(precio_ant)} → "
                    f"{formatear_euros(precio_nue)}"
                )
            self.compare.setText(texto_compare)
            self.compare.style().unpolish(self.compare)
            self.compare.style().polish(self.compare)
        elif len(history) <= 1:
            self.compare.setText("Aún poco historial: vuelve otro día para ver la evolución del precio.")
        else:
            self.compare.setText("")

        self.ingredientes.setPlainText(product.get("ingredientes") or product.get("ingredients") or "Sin datos")
        self._mostrar_alergenos(
            product.get("alergenos") or product.get("allergens")
        )
        self._mostrar_nutricion(product)

        self.alts.clear()
        if not alts:
            vacio = QListWidgetItem("No hay alternativas más baratas guardadas")
            vacio.setFlags(Qt.NoItemFlags)
            self.alts.addItem(vacio)
        else:
            for a in alts:
                precio = formatear_euros(
                    a.get("precio_unidad")
                    if a.get("precio_unidad") is not None
                    else a.get("unit_price")
                )
                nombre = a.get("nombre") or a.get("name") or a.get("id")
                tienda = PaginaBusqueda._nombre_supermercado(a)
                item = QListWidgetItem(f"{precio} — {nombre} · {tienda}")
                item.setData(Qt.UserRole, a.get("id"))
                item.setToolTip("Abrir ficha del producto")
                self.alts.addItem(item)

    def _mostrar_alergenos(self, texto: str | None) -> None:
        from cestia.enriquecimiento import deduplicar_alergenos

        limpio = deduplicar_alergenos(texto)
        if not limpio or limpio.lower() in {"sin datos", "sin datos de alérgenos"}:
            self.tarjeta_alergenos.establecer_contenido(
                "Sin datos de alérgenos", vacio=True
            )
        else:
            self.tarjeta_alergenos.establecer_contenido(limpio, vacio=False)

    def _mostrar_nutricion(self, product: dict[str, Any]) -> None:
        mapping = [
            ("energia_kcal", "Energía", "kcal"),
            ("proteinas", "Proteínas", "g"),
            ("hidratos", "Hidratos", "g"),
            ("grasas", "Grasas", "g"),
            ("fibra", "Fibra", "g"),
            ("azucares", "Azúcares", "g"),
            ("sal", "Sal", "g"),
        ]
        filas = []
        for key, nombre, unidad in mapping:
            if product.get(key) is not None:
                filas.append(
                    f"<tr><td class='n'>{nombre}</td>"
                    f"<td class='v'><b>{product[key]:.1f}</b> {unidad}</td></tr>"
                )
        if filas:
            self.tarjeta_nutricion.establecer_contenido(
                "<table cellspacing='0' cellpadding='4'>"
                + "".join(filas)
                + "</table>",
                vacio=False,
            )
        else:
            self.tarjeta_nutricion.establecer_contenido(
                "Sin tabla nutricional (aún)", vacio=True
            )

    def _abrir_alternativa(self, item: QListWidgetItem) -> None:
        id_producto = item.data(Qt.UserRole)
        if id_producto:
            self.abrir_producto.emit(str(id_producto))

    def aplicar_tema(self, tema: str) -> None:
        clave = "oscuro" if (tema or "").strip().lower() in {
            "oscuro", "dark", "darko"
        } else "claro"
        self._tema = clave
        self._aplicar_paleta(clave)
        self.nutri.aplicar_tema(clave)

    def _aplicar_paleta(self, tema: str) -> None:
        if tema == "oscuro":
            fondo = QColor("#1a2820")
            base = QColor("#24352c")
            texto = QColor("#e8f0ec")
        else:
            fondo = QColor("#eef6f1")
            base = QColor("#ffffff")
            texto = QColor("#14201a")
        for widget in self._widgets_paleta:
            paleta = widget.palette()
            paleta.setColor(QPalette.Window, fondo)
            paleta.setColor(QPalette.Base, base)
            paleta.setColor(QPalette.Text, texto)
            paleta.setColor(QPalette.WindowText, texto)
            paleta.setColor(QPalette.ButtonText, texto)
            widget.setPalette(paleta)

    def _cart(self) -> None:
        if self.product:
            self.anadir_a_cesta.emit(self.product["id"])

    def _toggle_fav(self) -> None:
        if not self.product:
            return
        pid = self.product["id"]
        if self.repositorio.es_favorito(pid):
            self.repositorio.favorito_quitar(pid)
            self.btn_fav.setText("☆ Favorito")
        else:
            self.repositorio.favorito_anadir(pid)
            self.btn_fav.setText("★ Favorito")

    def _comparar(self) -> None:
        if self.product:
            self.comparar_producto.emit(self.product)

    def _lista(self) -> None:
        if self.product:
            self.anadir_lista.emit(self.product["id"])

    def _alert(self) -> None:
        if self.product:
            self.crear_alerta.emit(self.product["id"], float(self.alert_price.value()))


class PaginaCesta(QWidget):
    def __init__(self, repositorio, catalogo=None, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        self.catalogo = catalogo
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cesta de la compra", objectName="TituloPagina"))

        self.presupuesto = QLabel("")
        self.presupuesto.setWordWrap(True)
        layout.addWidget(self.presupuesto)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Producto", "Cant.", "Precio", "Subtotal", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        self.totals = QLabel()
        self.totals.setWordWrap(True)
        layout.addWidget(self.totals)

        self.optima = QLabel("")
        self.optima.setWordWrap(True)
        self.optima.setObjectName("Atenuado")
        layout.addWidget(self.optima)

        row = QHBoxLayout()
        save = QPushButton("Registrar gasto")
        save.clicked.connect(self.guardar_compra)
        calc = QPushButton("Calcular óptima")
        calc.setProperty("secundario", True)
        calc.clicked.connect(self._calcular_optima)
        clear = QPushButton("Vaciar")
        clear.setProperty("secundario", True)
        clear.clicked.connect(self.vaciar)
        refresh = QPushButton("Actualizar")
        refresh.setProperty("secundario", True)
        refresh.clicked.connect(self.actualizar)
        row.addWidget(save)
        row.addWidget(calc)
        row.addWidget(clear)
        row.addWidget(refresh)
        row.addStretch()
        layout.addLayout(row)

    def actualizar(self) -> None:
        items = self.repositorio.items_cesta()
        self.table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.table.setItem(i, 0, QTableWidgetItem(item["name"]))
            qty = QSpinBox()
            qty.setRange(1, 99)
            qty.setValue(
                max(1, int(round(float(item.get("cantidad") or item.get("quantity") or 1))))
            )
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
            f"Grasas: {t['grasas']:.1f} g · Fibra {t['fibra']:.1f} g · "
            f"Azúcar {t['azucares']:.1f} g · Sal {t['sal']:.2f} g"
        )
        self._mostrar_presupuesto(t["coste"])

    def _mostrar_presupuesto(self, total_cesta: float) -> None:
        res = self.repositorio.resumen_presupuesto()
        partes = []
        if res.get("presupuesto_semanal") is not None:
            rest = res.get("restante_semana")
            if rest is not None:
                rest -= total_cesta
            partes.append(
                f"Presupuesto semanal: {formatear_euros(res['presupuesto_semanal'])} · "
                f"gastado {formatear_euros(res['gasto_semana'])} · "
                f"restante ~{formatear_euros(rest if rest is not None else 0)}"
            )
        if res.get("presupuesto_mensual") is not None:
            rest_m = res.get("restante_mes")
            if rest_m is not None:
                rest_m -= total_cesta
            partes.append(
                f"Presupuesto mensual: {formatear_euros(res['presupuesto_mensual'])} · "
                f"gastado {formatear_euros(res['gasto_mes'])} · "
                f"restante ~{formatear_euros(rest_m if rest_m is not None else 0)}"
            )
        self.presupuesto.setText(" · ".join(partes) if partes else "")

    def _calcular_optima(self) -> None:
        items = self.repositorio.items_cesta()
        if not items:
            self.optima.setText("La cesta está vacía.")
            return
        alternativas: dict[str, list] = {}
        if self.catalogo:
            for item in items:
                try:
                    alts = self.catalogo.alternativas_mas_baratas(item, limite=8)
                    alternativas[item["id"]] = alts
                except Exception:  # noqa: BLE001
                    pass
        por_tienda = calcular_cesta_por_tienda(items, alternativas)
        mezclada = calcular_cesta_optima_mezclada(items, alternativas)
        lineas = ["<b>Cesta óptima multi-tienda</b>"]
        if por_tienda.get("mejor_tienda"):
            m = por_tienda["mejor_tienda"]
            lineas.append(
                f"Una sola tienda: {nombre_tienda(m['tienda'])} → "
                f"{formatear_euros(m['total'])} "
                f"({m['productos_cubiertos']}/{m['productos_total']} productos)"
            )
        lineas.append(
            f"Mezclando tiendas: {formatear_euros(mezclada['total'])}"
        )
        for tienda, sub in sorted(
            mezclada.get("tiendas_usadas", {}).items(), key=lambda x: -x[1]
        ):
            lineas.append(f"  · {nombre_tienda(tienda)}: {formatear_euros(sub)}")
        if por_tienda.get("ahorro_vs_peor"):
            lineas.append(
                f"Ahorro vs tienda más cara: {formatear_euros(por_tienda['ahorro_vs_peor'])}"
            )
        self.optima.setText("<br>".join(lineas))

    def guardar_compra(self) -> None:
        pid = self.repositorio.guardar_compra()
        if pid is None:
            QMessageBox.information(self, "Cesta", "La cesta está vacía.")
            return
        QMessageBox.information(
            self,
            "Gasto registrado",
            f"Gasto #{pid} guardado en el registro de gastos.",
        )
        self.actualizar()

    def vaciar(self) -> None:
        self.repositorio.cesta_vaciar()
        self.actualizar()


class PaginaRegistroGasto(QWidget):
    def __init__(self, repositorio, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Registro de gasto", objectName="TituloPagina"))
        layout.addWidget(
            QLabel(
                "Anota lo que gastaste al terminar una compra real "
                "(desde la cesta o desde una lista).",
                objectName="Atenuado",
            )
        )
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
        self._purchases: list[dict[str, Any]] = []
        self._id_gasto_seleccionado: int | None = None
        btns = QHBoxLayout()
        dup = QPushButton("Duplicar gasto")
        dup.clicked.connect(self._duplicar)
        eliminar = QPushButton("Eliminar gasto")
        eliminar.setProperty("secundario", True)
        eliminar.clicked.connect(self._eliminar)
        btn = QPushButton("Actualizar")
        btn.setProperty("secundario", True)
        btn.clicked.connect(self.actualizar)
        btns.addWidget(dup)
        btns.addWidget(eliminar)
        btns.addWidget(btn)
        btns.addStretch()
        layout.addLayout(btns)

    def _gasto_seleccionado(self) -> dict[str, Any] | None:
        compras = getattr(self, "_purchases", [])
        if self._id_gasto_seleccionado is not None:
            for compra in compras:
                if compra["id"] == self._id_gasto_seleccionado:
                    return compra
        row = self.list.currentRow()
        if row < 0 or row >= len(compras):
            return None
        return compras[row]

    def _duplicar(self) -> None:
        gasto = self._gasto_seleccionado()
        if gasto is None:
            QMessageBox.information(
                self, "Registro de gasto", "Selecciona un gasto registrado."
            )
            return
        pid = int(gasto["id"])
        nuevo_id = self.repositorio.duplicar_registro_gasto(pid)
        if nuevo_id is None:
            QMessageBox.warning(
                self,
                "Registro de gasto",
                f"No se pudo duplicar el gasto #{pid}: no tiene productos asociados.",
            )
            return
        self.actualizar()
        for i, compra in enumerate(self._purchases):
            if compra["id"] == nuevo_id:
                self.list.setCurrentRow(i)
                break
        QMessageBox.information(
            self,
            "Gasto duplicado",
            f"Se ha creado el gasto #{nuevo_id} como copia del #{pid}.",
        )

    def _eliminar(self) -> None:
        gasto = self._gasto_seleccionado()
        if gasto is None:
            QMessageBox.information(
                self, "Registro de gasto", "Selecciona un gasto registrado."
            )
            return
        total = formatear_euros(gasto.get("total"))
        if (
            QMessageBox.question(
                self,
                "Eliminar gasto",
                f"¿Eliminar el gasto #{gasto['id']} ({total})?",
            )
            != QMessageBox.Yes
        ):
            return
        self.repositorio.eliminar_registro_gasto(gasto["id"])
        self.actualizar()

    def actualizar(self) -> None:
        id_previo = self._id_gasto_seleccionado
        self.insight.setText(self.repositorio.insight_gastos())
        self._purchases = self.repositorio.listar_compras()
        self.list.blockSignals(True)
        self.list.clear()
        for p in self._purchases:
            self.list.addItem(
                f"#{p['id']}  {(p.get('comprado_en') or '')[:16]}  —  {formatear_euros(p['total'])}"
            )
        fila = 0
        if id_previo is not None:
            for i, compra in enumerate(self._purchases):
                if compra["id"] == id_previo:
                    fila = i
                    break
        if self._purchases:
            self.list.setCurrentRow(fila)
        else:
            self._id_gasto_seleccionado = None
            self.detail.clear()
        self.list.blockSignals(False)
        if self._purchases:
            self._show(self.list.currentRow())

    def _show(self, row: int) -> None:
        if row < 0 or row >= len(getattr(self, "_purchases", [])):
            self._id_gasto_seleccionado = None
            return
        p = self._purchases[row]
        self._id_gasto_seleccionado = int(p["id"])
        items = self.repositorio.lineas_de_compra(p["id"])
        lines = [
            f"Gasto #{p['id']} · {p.get('comprado_en')}",
            f"Total: {formatear_euros(p['total'])}",
        ]
        if p.get("notas"):
            lines.append(f"Notas: {p['notas']}")
        lines.append("")
        for it in items:
            lines.append(
                f"- {it['cantidad']:g} × {it['nombre']} @ {formatear_euros(it['precio_unidad'])} "
                f"= {formatear_euros(it['total_linea'])}"
            )
        self.detail.setPlainText("\n".join(lines))


class PaginaComparador(QWidget):
    abrir_producto = Signal(str)
    ir_a_busqueda = Signal()

    def __init__(self, repositorio, catalogo=None, parent=None) -> None:
        super().__init__(parent)
        self.repositorio = repositorio
        self.catalogo = catalogo
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Comparador de precios", objectName="TituloPagina"))
        layout.addWidget(
            QLabel(
                "Evolución del precio respecto a hace ~6 meses. "
                "Los productos entran solos al buscarlos y abrir su ficha.",
                objectName="Atenuado",
            )
        )
        ayuda = QLabel(
            "<b>Cómo añadir productos a esta lista</b><br>"
            "1. Ve a <b>Productos</b> y busca un artículo.<br>"
            "2. Abre su ficha (doble clic): CestIA guarda el precio en tu equipo.<br>"
            "3. Vuelve al <b>Comparador</b>: el producto aparecerá aquí.<br>"
            "4. Repite con el tiempo o pulsa <b>Refrescar precios</b> para ver si sube o baja.<br>"
            "<span>Nota: la pestaña <b>Comparar</b> sirve para ver dos productos "
            "lado a lado desde la ficha (botón «Comparar»).</span>"
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("Atenuado")
        layout.addWidget(ayuda)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Producto", "Antes", "Hoy", "Cambio", "ID"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setColumnHidden(4, True)
        self.table.cellDoubleClicked.connect(self._abrir_fila)
        layout.addWidget(self.table, 1)

        self.status = QLabel("")
        self.status.setObjectName("Atenuado")
        layout.addWidget(self.status)

        row = QHBoxLayout()
        buscar = QPushButton("Buscar productos")
        buscar.clicked.connect(self.ir_a_busqueda.emit)
        self.btn_actualizar = QPushButton("Refrescar precios")
        self.btn_actualizar.clicked.connect(self.actualizar_precios)
        row.addWidget(buscar)
        row.addWidget(self.btn_actualizar)
        row.addStretch()
        layout.addLayout(row)

    def actualizar(self) -> None:
        """Recarga la lista desde el historial local (al entrar en la página)."""
        self._mostrar_filas(self._filas_locales())

    def actualizar_precios(self) -> None:
        """Refresca precios en las tiendas y vuelve a cargar la comparación."""
        self.btn_actualizar.setEnabled(False)
        self.status.setText("Actualizando precios en las tiendas…")
        ids = [p["id"] for p in self.repositorio.productos_con_historial(80)]

        def work():
            if self.catalogo is not None:
                for id_producto in ids:
                    try:
                        self.catalogo.obtener_producto(id_producto, enriquecer=False)
                    except Exception:  # noqa: BLE001
                        continue
            return True

        def ok(_resultado) -> None:
            self.btn_actualizar.setEnabled(True)
            self._mostrar_filas(self._filas_locales())

        def error(mensaje: str) -> None:
            self.btn_actualizar.setEnabled(True)
            self._mostrar_filas(self._filas_locales())
            self.status.setText(f"Error al actualizar: {mensaje}")

        if self.catalogo is None or not ids:
            self.btn_actualizar.setEnabled(True)
            self._mostrar_filas(self._filas_locales())
            return

        ejecutar_en_hilo(work, ok, error)

    def _filas_locales(self) -> list:
        filas = []
        for p in self.repositorio.productos_con_historial(80):
            cmp_ = self.repositorio.comparar_precio(p["id"], dias_atras=180)
            if cmp_:
                filas.append(cmp_)
        return filas

    def _mostrar_filas(self, filas: list) -> None:
        self._rellenar(filas)
        seguimiento = len(self.repositorio.productos_con_historial(80))
        if filas:
            self.status.setText(
                f"{len(filas)} productos en seguimiento de precios "
                f"({seguimiento} con historial guardado). "
                "Doble clic en una fila para abrir la ficha."
            )
        else:
            self.status.setText(
                "Aún no hay productos en seguimiento. "
                "Pulsa «Buscar productos», abre fichas y vuelve aquí."
            )

    def _rellenar(self, filas: list) -> None:
        self.table.setRowCount(len(filas))
        for i, c in enumerate(filas):
            prod = c.get("producto") or c.get("product") or {}
            pct = c.get("cambio_pct")
            if pct is None:
                pct = c.get("change_pct")
            nombre = prod.get("nombre") or prod.get("name") or prod.get("id") or ""
            self.table.setItem(i, 0, QTableWidgetItem(str(nombre)))
            self.table.setItem(
                i,
                1,
                QTableWidgetItem(
                    formatear_euros(c.get("precio_antiguo"))
                    if c.get("precio_antiguo") is not None
                    else "—"
                ),
            )
            self.table.setItem(
                i,
                2,
                QTableWidgetItem(
                    formatear_euros(c.get("precio_nuevo"))
                    if c.get("precio_nuevo") is not None
                    else "—"
                ),
            )
            if pct is not None and pct != 0:
                flecha = "▲" if pct > 0 else "▼"
                badge = QLabel(f"{flecha} {pct:+.1f} %")
                badge.setObjectName("BadgeSube" if pct > 0 else "BadgeBaja")
                badge.setProperty("tablaComparador", True)
                badge.setAlignment(Qt.AlignCenter)
                badge.style().unpolish(badge)
                badge.style().polish(badge)
                self.table.setCellWidget(i, 3, badge)
            else:
                txt = f"{pct:+.1f} %" if pct is not None else "—"
                self.table.setItem(i, 3, QTableWidgetItem(txt))
            self.table.setItem(i, 4, QTableWidgetItem(str(prod.get("id") or "")))
            self.table.setRowHeight(i, 40)

    def _abrir_fila(self, fila: int, _col: int) -> None:
        item = self.table.item(fila, 4)
        if item and item.text():
            self.abrir_producto.emit(item.text())


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
            nombre = a.get("nombre_producto") or a.get("product_name") or ""
            objetivo = a.get("precio_objetivo") or a.get("target_price")
            activa = a.get("activa", a.get("active", 1))
            self.table.setItem(i, 0, QTableWidgetItem(nombre))
            self.table.setItem(i, 1, QTableWidgetItem(formatear_euros(objetivo)))
            self.table.setItem(
                i,
                2,
                QTableWidgetItem(
                    "Activa"
                    if activa
                    else f"Disparada {a.get('disparada_en') or a.get('triggered_at') or ''}"
                ),
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

            self.figure = Figure(figsize=(8, 6), dpi=100)
            self.canvas = FigureCanvasQTAgg(self.figure)
            layout.addWidget(self.canvas, 1)
            self._has_mpl = True
        except Exception:  # noqa: BLE001
            self._has_mpl = False
            layout.addWidget(QLabel("Matplotlib no disponible para gráficas."))

        layout.addWidget(QLabel("Gasto semanal de compra"))
        pista = QLabel("Semanas ISO (lunes–domingo), según los gastos registrados")
        pista.setObjectName("Atenuado")
        layout.addWidget(pista)

        self.tabla_semanal = QTableWidget(0, 5)
        self.tabla_semanal.setHorizontalHeaderLabels(
            ["Semana", "Desde", "Hasta", "Compras", "Gasto"]
        )
        header = self.tabla_semanal.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tabla_semanal.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_semanal.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_semanal.setMinimumHeight(160)
        self.tabla_semanal.setMaximumHeight(240)
        layout.addWidget(self.tabla_semanal)

        self.resumen_semanal = QLabel("")
        self.resumen_semanal.setObjectName("Atenuado")
        layout.addWidget(self.resumen_semanal)

        btn = QPushButton("Actualizar")
        btn.setProperty("secundario", True)
        btn.clicked.connect(self.actualizar)
        layout.addWidget(btn, alignment=Qt.AlignLeft)

    def actualizar(self) -> None:
        self.insight.setText(self.repositorio.insight_gastos())
        self._actualizar_tabla_semanal()
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

        self.figure.subplots_adjust(
            left=0.08, right=0.98, top=0.94, bottom=0.08, hspace=0.45, wspace=0.35
        )

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

    def _actualizar_tabla_semanal(self) -> None:
        semanas = self.repositorio.gasto_semanal(26)
        self.tabla_semanal.setRowCount(len(semanas))
        for i, s in enumerate(semanas):
            self.tabla_semanal.setItem(i, 0, QTableWidgetItem(s["semana"]))
            self.tabla_semanal.setItem(i, 1, QTableWidgetItem(self._fecha_es(s["desde"])))
            self.tabla_semanal.setItem(i, 2, QTableWidgetItem(self._fecha_es(s["hasta"])))
            self.tabla_semanal.setItem(i, 3, QTableWidgetItem(str(s["compras"])))
            self.tabla_semanal.setItem(
                i, 4, QTableWidgetItem(formatear_euros(s["total"]))
            )
        if not semanas:
            self.resumen_semanal.setText(
                "Aún no hay gastos registrados para calcular el gasto semanal."
            )
            return
        ultima = semanas[0]
        media = sum(float(s["total"]) for s in semanas) / len(semanas)
        self.resumen_semanal.setText(
            f"Última semana ({ultima['semana']}): {formatear_euros(ultima['total'])} · "
            f"Media de las {len(semanas)} semanas mostradas: {formatear_euros(media)}"
        )

    @staticmethod
    def _fecha_es(iso: str) -> str:
        try:
            anio, mes, dia = iso.split("-")
            return f"{dia}/{mes}/{anio}"
        except ValueError:
            return iso


class PaginaIA(QWidget):
    def __init__(self, asistente, parent=None) -> None:
        super().__init__(parent)
        self.asistente = asistente
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("IA — CestIA", objectName="TituloPagina"))
        layout.addWidget(
            QLabel(
                "Opcional. Usa Google Gemini (clave en Configuración). "
                "Compara precios y planifica la compra en varios supermercados.",
                objectName="Atenuado",
            )
        )
        self.prompts = QListWidget()
        for text in (
            "Tengo 25 €. ¿Qué puedo comprar para toda la semana?",
            "Diseña una dieta de 2200 kcal con productos de supermercado.",
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
        self.btn_preguntar = ask
        ask.clicked.connect(self.preguntar)
        layout.addWidget(ask, alignment=Qt.AlignLeft)
        self.progreso_ia = crear_barra_progreso_espera()
        self._progreso_ia = ProgresoEspera(self.progreso_ia)
        layout.addWidget(self.progreso_ia)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("La respuesta aparecerá aquí…")
        layout.addWidget(self.output, 1)
        self.status = QLabel("")
        self.status.setObjectName("Atenuado")
        layout.addWidget(self.status)

    def preguntar(self) -> None:
        q = self.input.toPlainText().strip()
        if not q:
            return
        self.btn_preguntar.setEnabled(False)
        self.status.setText("")
        self.output.clear()
        self._progreso_ia.iniciar()

        def work():
            ctx = self.asistente.construir_contexto()
            return self.asistente.preguntar(q, ctx)

        def al_ok(text):
            mostrar_respuesta_ia(self.output, text)
            self._progreso_ia.completar()
            self.btn_preguntar.setEnabled(True)
            self.status.setText("Listo")

        def al_error(exc):
            self._progreso_ia.cancelar()
            self.btn_preguntar.setEnabled(True)
            self.status.setText(f"Error: {exc}")

        ejecutar_en_hilo(work, al_ok, al_error)


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
    """Ajustes locales: clave Gemini, modelo, tiendas, presupuesto y tema."""

    tema_cambiado = Signal(str)

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
        layout.addWidget(
            QLabel(
                "Plan gratuito (claves nuevas): usa gemini-3.1-flash-lite o "
                "gemini-3.5-flash. Los modelos 2.0 y 2.5 ya no admiten proyectos nuevos.",
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
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
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
        self.check_alcampo = QCheckBox("Alcampo")
        self.check_froiz = QCheckBox("Froiz")
        self.check_eroski = QCheckBox("Eroski")
        self.check_lidl = QCheckBox("Lidl")
        self.check_dia = QCheckBox("Dia")
        self.check_gadis = QCheckBox("Gadis")
        tiendas_row = QHBoxLayout()
        tiendas_row.addWidget(self.check_mercadona)
        tiendas_row.addWidget(self.check_carrefour)
        tiendas_row.addWidget(self.check_alcampo)
        tiendas_row.addWidget(self.check_froiz)
        tiendas_row.addWidget(self.check_eroski)
        tiendas_row.addWidget(self.check_lidl)
        tiendas_row.addWidget(self.check_dia)
        tiendas_row.addWidget(self.check_gadis)
        tiendas_row.addStretch()
        layout.addLayout(tiendas_row)

        layout.addWidget(QLabel("Presupuesto de compra"))
        pres_row = QHBoxLayout()
        self.presupuesto_sem = QDoubleSpinBox()
        self.presupuesto_sem.setPrefix("Semanal ")
        self.presupuesto_sem.setSuffix(" €")
        self.presupuesto_sem.setMaximum(99999)
        self.presupuesto_sem.setSpecialValueText("Sin límite")
        self.presupuesto_mes = QDoubleSpinBox()
        self.presupuesto_mes.setPrefix("Mensual ")
        self.presupuesto_mes.setSuffix(" €")
        self.presupuesto_mes.setMaximum(999999)
        self.presupuesto_mes.setSpecialValueText("Sin límite")
        pres_row.addWidget(self.presupuesto_sem)
        pres_row.addWidget(self.presupuesto_mes)
        pres_row.addStretch()
        layout.addLayout(pres_row)

        layout.addWidget(QLabel("Apariencia"))
        self.combo_tema = QComboBox()
        self.combo_tema.addItem("Tema claro", "claro")
        self.combo_tema.addItem("Tema oscuro", "oscuro")
        layout.addWidget(self.combo_tema)

        layout.addWidget(
            QLabel(
                "Atajos: Ctrl+F buscar · Ctrl+1…9 navegar · Esc volver · "
                "Ctrl+Enter añadir a cesta",
                objectName="Atenuado",
            )
        )

        botones = QHBoxLayout()
        guardar = QPushButton("Guardar")
        guardar.clicked.connect(self.guardar)
        probar = QPushButton("Probar conexión")
        probar.setProperty("secundario", True)
        probar.clicked.connect(self.probar)
        abrir = QPushButton("Obtén tu clave Gemini aquí")
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
        from cestia.tiendas import (
            CLAVE_TEMA,
            alcampo_activo,
            carrefour_activo,
            dia_activo,
            eroski_activo,
            froiz_activo,
            gadis_activo,
            lidl_activo,
            mercadona_activo,
        )

        clave = self.asistente.obtener_clave()
        self.campo_clave.setText(clave)
        modelo = self.asistente.obtener_modelo()
        guardado = self.repositorio.obtener_ajuste("gemini_modelo", "").strip()
        if guardado and guardado != modelo:
            self.asistente.guardar_modelo(modelo)
        idx = self.campo_modelo.findText(modelo)
        if idx >= 0:
            self.campo_modelo.setCurrentIndex(idx)
        else:
            self.campo_modelo.setEditText(modelo)
        self.check_mercadona.setChecked(mercadona_activo(self.repositorio))
        self.check_carrefour.setChecked(carrefour_activo(self.repositorio))
        self.check_alcampo.setChecked(alcampo_activo(self.repositorio))
        self.check_froiz.setChecked(froiz_activo(self.repositorio))
        self.check_eroski.setChecked(eroski_activo(self.repositorio))
        self.check_lidl.setChecked(lidl_activo(self.repositorio))
        self.check_dia.setChecked(dia_activo(self.repositorio))
        self.check_gadis.setChecked(gadis_activo(self.repositorio))
        ps = self.repositorio.obtener_presupuesto_semanal()
        pm = self.repositorio.obtener_presupuesto_mensual()
        self.presupuesto_sem.setValue(ps if ps is not None else 0)
        self.presupuesto_mes.setValue(pm if pm is not None else 0)
        tema = self.repositorio.obtener_ajuste(CLAVE_TEMA, "claro")
        tidx = self.combo_tema.findData(tema)
        if tidx >= 0:
            self.combo_tema.setCurrentIndex(tidx)
        if clave:
            self.estado.setText("Hay una clave configurada.")
        else:
            self.estado.setText("Todavía no hay clave. Configúrala para usar la IA.")
        self._al_cambiar_ver_clave()

    def _al_cambiar_ver_clave(self, _estado=None) -> None:
        self.campo_clave.setEchoMode(
            QLineEdit.EchoMode.Normal
            if self.ver_clave.isChecked()
            else QLineEdit.EchoMode.Password
        )

    def guardar(self) -> None:
        from cestia.tiendas import CLAVE_TEMA, guardar_tiendas

        clave = self.campo_clave.text().strip()
        from cestia.asistente_ia import MODELO_POR_DEFECTO

        modelo = self.asistente.normalizar_modelo(
            self.campo_modelo.currentText().strip() or MODELO_POR_DEFECTO
        )
        self.asistente.guardar_clave(clave)
        self.asistente.guardar_modelo(modelo)
        activas = [
            self.check_mercadona.isChecked(),
            self.check_carrefour.isChecked(),
            self.check_alcampo.isChecked(),
            self.check_froiz.isChecked(),
            self.check_eroski.isChecked(),
            self.check_lidl.isChecked(),
            self.check_dia.isChecked(),
            self.check_gadis.isChecked(),
        ]
        if not any(activas):
            QMessageBox.warning(
                self,
                "Configuración",
                "Debes dejar al menos una tienda activa.",
            )
            return
        guardar_tiendas(
            self.repositorio,
            mercadona=self.check_mercadona.isChecked(),
            carrefour=self.check_carrefour.isChecked(),
            alcampo=self.check_alcampo.isChecked(),
            froiz=self.check_froiz.isChecked(),
            eroski=self.check_eroski.isChecked(),
            lidl=self.check_lidl.isChecked(),
            dia=self.check_dia.isChecked(),
            gadis=self.check_gadis.isChecked(),
        )
        ps = self.presupuesto_sem.value()
        pm = self.presupuesto_mes.value()
        self.repositorio.guardar_presupuestos(
            semanal=ps,
            mensual=pm,
        )
        tema = self.combo_tema.currentData() or "claro"
        self.repositorio.guardar_ajuste(CLAVE_TEMA, tema)
        self.tema_cambiado.emit(str(tema))
        partes = []
        if clave:
            partes.append("Clave Gemini guardada.")
        else:
            partes.append("Clave Gemini vacía.")
        tiendas = []
        for chk, nom in [
            (self.check_mercadona, "Mercadona"),
            (self.check_carrefour, "Carrefour"),
            (self.check_alcampo, "Alcampo"),
            (self.check_froiz, "Froiz"),
            (self.check_eroski, "Eroski"),
            (self.check_lidl, "Lidl"),
            (self.check_dia, "Dia"),
            (self.check_gadis, "Gadis"),
        ]:
            if chk.isChecked():
                tiendas.append(nom)
        partes.append("Tiendas: " + ", ".join(tiendas))
        partes.append(f"Tema: {tema}.")
        mensaje = " ".join(partes)
        QMessageBox.information(self, "Configuración", mensaje)
        self.estado.setText(mensaje)

    def probar(self) -> None:
        # Guardar primero lo que hay en pantalla para probar esa clave
        self.asistente.guardar_clave(self.campo_clave.text().strip())
        from cestia.asistente_ia import MODELO_POR_DEFECTO

        self.asistente.guardar_modelo(
            self.campo_modelo.currentText().strip() or MODELO_POR_DEFECTO
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
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        raiz.addWidget(scroll)

        contenido = QWidget()
        scroll.setWidget(contenido)
        layout = QVBoxLayout(contenido)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        layout.addWidget(
            QLabel("About", objectName="TituloPagina"), alignment=Qt.AlignHCenter
        )

        self.logo = QLabel()
        self.logo.setObjectName("LogoAbout")
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setMinimumHeight(160)
        if self.RUTA_LOGO.exists():
            pixmap = QPixmap(str(self.RUTA_LOGO))
            if not pixmap.isNull():
                self.logo.setPixmap(
                    pixmap.scaled(
                        420,
                        200,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                self.logo.setText("CestIA")
        else:
            self.logo.setText("CestIA")
        layout.addWidget(self.logo, alignment=Qt.AlignHCenter)

        descripcion = self._bloque_texto(
            "CestIA analiza el precio de tu compra en varios supermercados "
            "(Mercadona, Carrefour, Alcampo, Froiz, Eroski, Lidl, Dia y Gadis) "
            "desde tu equipo. Los datos se guardan en local. "
            "No está afiliada a ninguna cadena: consulta fuentes de acceso "
            "público pensadas para uso personal.",
            centrado=True,
        )
        layout.addWidget(descripcion, alignment=Qt.AlignHCenter)

        layout.addWidget(
            self._titulo_seccion("Funcionalidades"), alignment=Qt.AlignHCenter
        )
        funciones = self._bloque_texto(
            "• Búsqueda multi-tienda en paralelo (Mercadona, Carrefour, Alcampo, "
            "Froiz, Eroski, Lidl, Dia y Gadis), activables en Configuración\n"
            "• Comparación entre tiendas, filtros (precio, Nutri-Score, "
            "rebajados, sin gluten) y badge de oferta\n"
            "• Ficha de producto: foto, precio, ingredientes, alérgenos, "
            "Nutri-Score (ficha de tienda u Open Food Facts), nutrición, "
            "gráfico de evolución y alternativas más baratas\n"
            "• Favoritos y listas de la compra reutilizables\n"
            "• Comparador de evolución de precios (~6 meses; productos al abrir fichas)\n"
            "• Comparar: dos productos lado a lado desde la ficha\n"
            "• Cesta con totales nutricionales, presupuesto semanal/mensual "
            "y cálculo de cesta óptima multi-tienda\n"
            "• Registro de gasto con opción de duplicar o eliminar gastos\n"
            "• Alertas de precio y estadísticas de gasto "
            "(semanal, mensual, anual y por categoría)\n"
            "• IA opcional con Google Gemini: asistente de compras "
            "multi-supermercado, respuestas con Markdown y barra de progreso\n"
            "• Escáner de códigos de barras (webcam o EAN a mano)\n"
            "• Configuración: tiendas, clave Gemini (botón «Obtén tu clave "
            "Gemini aquí»), modelos 3.x, tema claro/oscuro y presupuesto\n"
            "• Tema claro/oscuro y atajos de teclado"
        )
        layout.addWidget(funciones, alignment=Qt.AlignHCenter)

        layout.addWidget(
            self._titulo_seccion("Limitaciones"), alignment=Qt.AlignHCenter
        )
        limitaciones = self._bloque_texto(
            "• No es una app oficial ni está afiliada a las tiendas; "
            "no vende, no hace pedidos ni sustituye sus webs o apps.\n"
            "• Los precios y el catálogo dependen de servicios públicos "
            "de cada cadena: pueden cambiar, fallar o desaparecer "
            "sin aviso.\n"
            "• La cobertura y la calidad de datos no es igual en todas "
            "las tiendas (fotos, marca, stock, zona geográfica).\n"
            "• Nutri-Score, alérgenos y nutrición pueden faltar. Cuando hay "
            "dato, puede venir de la ficha de la tienda (p. ej. Día) o de "
            "Open Food Facts (colaborativo, no oficial); si no hay, la app "
            "lo indica en la ficha.\n"
            "• El registro de gastos, el comparador y las estadísticas solo reflejan "
            "lo que hayas buscado y guardado en este equipo.\n"
            "• La «cesta óptima» y las marcas inferidas son orientativas; "
            "no garantizan el precio en caja ni la equivalencia exacta "
            "entre productos.\n"
            "• La IA (Gemini) puede equivocarse; usa modelos de la serie 3.x "
            "en claves nuevas. No sustituye el etiquetado del envase ni un "
            "ticket oficial.\n"
            "• Uso previsto: personal y local. Tú eres responsable de "
            "cumplir las condiciones de cada servicio de terceros.\n"
            "• El programa se ofrece «tal cual», sin garantía de exactitud "
            "de precios, disponibilidad ni continuidad del servicio."
        )
        layout.addWidget(limitaciones, alignment=Qt.AlignHCenter)

        from cestia import __version__

        version = QLabel(f"Versión {__version__} · GPL-3.0")
        version.setObjectName("Atenuado")
        version.setAlignment(Qt.AlignHCenter)
        layout.addWidget(version)

        github = QPushButton("Ver en GitHub")
        github.setProperty("secundario", True)
        github.setCursor(Qt.PointingHandCursor)
        github.clicked.connect(self._abrir_github)
        layout.addWidget(github, alignment=Qt.AlignHCenter)

        layout.addStretch(1)

    @staticmethod
    def _titulo_seccion(texto: str) -> QLabel:
        titulo = QLabel(texto)
        titulo.setObjectName("TituloPagina")
        titulo.setStyleSheet("font-size: 18px;")
        titulo.setAlignment(Qt.AlignHCenter)
        return titulo

    @staticmethod
    def _bloque_texto(texto: str, *, centrado: bool = False, ancho: int = 580) -> QLabel:
        """QLabel multilínea con altura correcta (evita cortar la última línea)."""
        from PySide6.QtGui import QTextDocument

        cuerpo = texto.rstrip() + "\n"
        etiqueta = QLabel(cuerpo)
        etiqueta.setObjectName("Atenuado")
        etiqueta.setWordWrap(True)
        etiqueta.setAlignment(
            Qt.AlignHCenter | Qt.AlignTop if centrado else Qt.AlignLeft | Qt.AlignTop
        )
        etiqueta.setFixedWidth(ancho)
        etiqueta.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        documento = QTextDocument()
        documento.setDefaultFont(etiqueta.font())
        documento.setPlainText(cuerpo)
        documento.setTextWidth(ancho)
        etiqueta.setMinimumHeight(int(documento.size().height()) + 16)
        return etiqueta

    def _abrir_github(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(self.URL_GITHUB))
