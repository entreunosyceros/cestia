from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from cestia.asistente_ia import AsistenteIA
from cestia.base_datos import conectar
from cestia.base_datos.repositorio import Repositorio
from cestia.catalogo import ServicioCatalogo
from cestia.interfaz.paginas import (
    PaginaAbout,
    PaginaAlertas,
    PaginaBusqueda,
    PaginaCesta,
    PaginaComparador,
    PaginaConfiguracion,
    PaginaEscaner,
    PaginaEstadisticas,
    PaginaRegistroGasto,
    PaginaIA,
    PaginaProducto,
)
from cestia.interfaz.paginas_extras import (
    PaginaCompararProductos,
    PaginaFavoritos,
    PaginaListas,
)
from cestia.interfaz.progreso import crear_barra_progreso, mostrar_progreso
from cestia.interfaz.temas import obtener_hoja_estilos
from cestia.tiendas import CLAVE_TEMA

RUTA_LOGO_MINI = Path(__file__).resolve().parents[2] / "img" / "logomini.png"


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CestIA")
        self.resize(1180, 760)

        self.conexion = conectar()
        self.repositorio = Repositorio(self.conexion)
        self.catalogo = ServicioCatalogo(self.repositorio)
        self.asistente = AsistenteIA(self.repositorio)

        raiz = QWidget()
        self.setCentralWidget(raiz)
        envoltorio = QHBoxLayout(raiz)
        envoltorio.setContentsMargins(0, 0, 0, 0)
        envoltorio.setSpacing(0)

        barra = QWidget(objectName="BarraLateral")
        lateral = QVBoxLayout(barra)
        lateral.addWidget(self._crear_logo_lateral())
        sub = QLabel("Analiza el precio de tu compra")
        sub.setObjectName("SubtituloMarca")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignHCenter)
        lateral.addWidget(sub)

        self.pila = QStackedWidget()
        self.pagina_busqueda = PaginaBusqueda(self.catalogo, self.repositorio)
        self.pagina_producto = PaginaProducto(self.catalogo, self.repositorio)
        self.pagina_cesta = PaginaCesta(self.repositorio, self.catalogo)
        self.pagina_registro_gasto = PaginaRegistroGasto(self.repositorio)
        self.pagina_comparador = PaginaComparador(self.repositorio, self.catalogo)
        self.pagina_alertas = PaginaAlertas(self.repositorio, self.catalogo)
        self.pagina_estadisticas = PaginaEstadisticas(self.repositorio)
        self.pagina_ia = PaginaIA(self.asistente)
        self.pagina_escaner = PaginaEscaner(self.catalogo)
        self.pagina_favoritos = PaginaFavoritos(self.repositorio)
        self.pagina_listas = PaginaListas(self.repositorio)
        self.pagina_comparar = PaginaCompararProductos(self.repositorio)
        self.pagina_configuracion = PaginaConfiguracion(
            self.asistente, self.repositorio
        )
        self.pagina_about = PaginaAbout()

        paginas = [
            ("Productos", self.pagina_busqueda),
            ("Cesta", self.pagina_cesta),
            ("Favoritos", self.pagina_favoritos),
            ("Listas", self.pagina_listas),
            ("Registro de gasto", self.pagina_registro_gasto),
            ("Comparador", self.pagina_comparador),
            ("Comparar", self.pagina_comparar),
            ("Alertas", self.pagina_alertas),
            ("Estadísticas", self.pagina_estadisticas),
            ("IA", self.pagina_ia),
            ("Escáner", self.pagina_escaner),
            ("Configuración", self.pagina_configuracion),
            ("About", self.pagina_about),
        ]
        for _, pagina in paginas:
            self.pila.addWidget(pagina)
        self.pila.addWidget(self.pagina_producto)

        self.botones_nav: list[QPushButton] = []
        for indice, (etiqueta, pagina) in enumerate(paginas):
            boton = QPushButton(etiqueta)
            boton.clicked.connect(
                lambda _=False, i=indice, p=pagina: self._ir_a(i, p)
            )
            lateral.addWidget(boton)
            self.botones_nav.append(boton)
        lateral.addStretch()
        envoltorio.addWidget(barra)
        contenido = QWidget()
        columna = QVBoxLayout(contenido)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        self.progreso = crear_barra_progreso()
        columna.addWidget(self.progreso)
        columna.addWidget(self.pila, 1)
        envoltorio.addWidget(contenido, 1)

        self.pagina_busqueda.abrir_producto.connect(self.mostrar_producto)
        self.pagina_comparador.abrir_producto.connect(self.mostrar_producto)
        self.pagina_comparador.ir_a_busqueda.connect(
            lambda: self._ir_a(0, self.pagina_busqueda)
        )
        self.pagina_escaner.abrir_producto.connect(self.mostrar_producto)
        self.pagina_favoritos.abrir_producto.connect(self.mostrar_producto)
        self.pagina_listas.abrir_producto.connect(self.mostrar_producto)
        self.pagina_producto.abrir_producto.connect(self.mostrar_producto)
        self.pagina_producto.back.clicked.connect(
            lambda: self._ir_a(0, self.pagina_busqueda)
        )
        self.pagina_producto.anadir_a_cesta.connect(self._anadir_cesta)
        self.pagina_producto.crear_alerta.connect(self._anadir_alerta)
        self.pagina_producto.comparar_producto.connect(self._comparar_producto)
        self.pagina_producto.anadir_lista.connect(self._anadir_a_lista)
        self.pagina_configuracion.tema_cambiado.connect(self._aplicar_tema)
        self._aplicar_tema(self.repositorio.obtener_ajuste(CLAVE_TEMA, "claro"))

        self._configurar_atajos()
        self._ir_a(0, self.pagina_busqueda)
        self._comprobar_alertas_silencioso()
        self._cerrando = False
        self._configurar_bandeja_sistema()

    def _icono_aplicacion(self) -> QIcon:
        if RUTA_LOGO_MINI.exists():
            icono = QIcon(str(RUTA_LOGO_MINI))
            if not icono.isNull():
                return icono
        return self.windowIcon()

    def _configurar_bandeja_sistema(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icono = self._icono_aplicacion()
        if not icono.isNull():
            self.setWindowIcon(icono)
        self.bandeja = QSystemTrayIcon(icono, self)
        self.bandeja.setToolTip("CestIA")

        menu = QMenu()
        self.accion_ventana = menu.addAction("Ocultar ventana")
        self.accion_ventana.triggered.connect(self._alternar_ventana)
        menu.addSeparator()
        accion_salir = menu.addAction("Salir")
        accion_salir.triggered.connect(self._salir_aplicacion)
        self.bandeja.setContextMenu(menu)
        self.bandeja.activated.connect(self._bandeja_activada)
        self.bandeja.show()
        self._actualizar_menu_bandeja()

        app = QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(False)

    def _actualizar_menu_bandeja(self) -> None:
        if hasattr(self, "accion_ventana"):
            self.accion_ventana.setText(
                "Ocultar ventana" if self.isVisible() else "Mostrar ventana"
            )

    def _alternar_ventana(self) -> None:
        if self.isVisible():
            self._ocultar_ventana()
        else:
            self._mostrar_ventana()

    def _mostrar_ventana(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._actualizar_menu_bandeja()

    def _ocultar_ventana(self) -> None:
        self.hide()
        self._actualizar_menu_bandeja()

    def _bandeja_activada(self, motivo: QSystemTrayIcon.ActivationReason) -> None:
        if motivo == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._mostrar_ventana()

    def _salir_aplicacion(self) -> None:
        self._cerrando = True
        if hasattr(self, "bandeja"):
            self.bandeja.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._cerrando or not hasattr(self, "bandeja"):
            event.accept()
            return
        event.ignore()
        self._ocultar_ventana()
        self.bandeja.showMessage(
            "CestIA",
            "La aplicación sigue en la bandeja del sistema.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _aplicar_tema(self, tema: str) -> None:
        self.setStyleSheet(obtener_hoja_estilos(tema))
        self.pagina_producto.aplicar_tema(tema)

    def _atajo_anadir_cesta(self) -> None:
        if self.pila.currentWidget() == self.pagina_producto:
            self.pagina_producto.btn_cart.click()

    def _configurar_atajos(self) -> None:
        QShortcut(QKeySequence("Ctrl+F"), self, self.pagina_busqueda.enfocar_busqueda)
        QShortcut(QKeySequence("Escape"), self, self._esc_volver)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._atajo_anadir_cesta)
        for i in range(min(9, len(self.botones_nav))):
            QShortcut(
                QKeySequence(f"Ctrl+{i + 1}"),
                self,
                lambda idx=i: self._ir_a(
                    idx,
                    self.pila.widget(idx),  # type: ignore[arg-type]
                ),
            )

    def _esc_volver(self) -> None:
        if self.pila.currentWidget() == self.pagina_producto:
            self._ir_a(0, self.pagina_busqueda)

    def _crear_logo_lateral(self) -> QLabel:
        logo = QLabel()
        logo.setObjectName("LogoMarca")
        logo.setAlignment(Qt.AlignHCenter)
        if RUTA_LOGO_MINI.exists():
            pixmap = QPixmap(str(RUTA_LOGO_MINI))
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(
                        160,
                        64,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
                return logo
        logo.setText("CestIA")
        logo.setObjectName("TituloMarca")
        logo.setAlignment(Qt.AlignHCenter)
        return logo

    def _ir_a(self, indice_nav: int, pagina: QWidget) -> None:
        mostrar_progreso(self.progreso, True)
        try:
            self.pila.setCurrentWidget(pagina)
            for i, boton in enumerate(self.botones_nav):
                boton.setProperty("activo", "true" if i == indice_nav else "false")
                boton.style().unpolish(boton)
                boton.style().polish(boton)
            if hasattr(pagina, "actualizar"):
                pagina.actualizar()
        finally:
            mostrar_progreso(self.progreso, False)

    def mostrar_producto(self, id_producto: str) -> None:
        mostrar_progreso(self.progreso, True)
        self.pila.setCurrentWidget(self.pagina_producto)
        for boton in self.botones_nav:
            boton.setProperty("activo", "false")
            boton.style().unpolish(boton)
            boton.style().polish(boton)
        mostrar_progreso(self.progreso, False)
        self.pagina_producto.cargar(id_producto)

    def _anadir_cesta(self, id_producto: str) -> None:
        self.repositorio.cesta_anadir(id_producto, 1)
        QMessageBox.information(self, "Cesta", "Producto añadido a la cesta.")
        self.pagina_cesta.actualizar()

    def _anadir_alerta(self, id_producto: str, objetivo: float) -> None:
        producto = self.repositorio.obtener_producto(id_producto)
        nombre = producto["nombre"] if producto else id_producto
        self.repositorio.anadir_alerta(id_producto, nombre, objetivo)
        QMessageBox.information(
            self,
            "Alerta",
            f"Te avisaré cuando «{nombre}» baje de {objetivo:.2f} €.",
        )
        self.pagina_alertas.actualizar()

    def _comparar_producto(self, producto: object) -> None:
        self.pagina_comparar.establecer_producto(producto)  # type: ignore[arg-type]
        self._ir_a(6, self.pagina_comparar)

    def _anadir_a_lista(self, id_producto: str) -> None:
        listas = self.repositorio.listar_listas_compra()
        if not listas:
            nombre, ok = QInputDialog.getText(
                self, "Lista de la compra", "Nombre de la nueva lista:"
            )
            if not ok or not nombre.strip():
                return
            id_lista = self.repositorio.crear_lista_compra(nombre.strip())
        else:
            nombres = [f"{l['nombre']} ({l.get('num_items', 0)})" for l in listas]
            nombre, ok = QInputDialog.getItem(
                self,
                "Lista de la compra",
                "Elige una lista:",
                nombres,
                0,
                False,
            )
            if not ok:
                return
            idx = nombres.index(nombre)
            id_lista = listas[idx]["id"]
        self.repositorio.lista_anadir_producto(id_lista, id_producto, 1)
        QMessageBox.information(self, "Lista", "Producto guardado en la lista.")
        self.pagina_listas.actualizar()

    def _comprobar_alertas_silencioso(self) -> None:
        disparadas = self.repositorio.comprobar_alertas()
        if disparadas:
            texto = "\n".join(
                f"• {t.get('nombre_producto')}: {t.get('precio_actual'):.2f} € "
                f"(objetivo {t.get('precio_objetivo'):.2f} €)"
                for t in disparadas
            )
            QMessageBox.information(self, "Alertas disparadas", texto)
