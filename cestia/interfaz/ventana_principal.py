from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cestia.asistente_ia import AsistenteIA
from cestia.base_datos import conectar
from cestia.base_datos.repositorio import Repositorio
from cestia.catalogo import ServicioCatalogo
from cestia.interfaz.estilos import HOJA_ESTILOS
from cestia.interfaz.paginas import (
    PaginaAbout,
    PaginaAlertas,
    PaginaBusqueda,
    PaginaCesta,
    PaginaComparador,
    PaginaConfiguracion,
    PaginaEscaner,
    PaginaEstadisticas,
    PaginaHistorial,
    PaginaIA,
    PaginaProducto,
)

RUTA_LOGO_MINI = Path(__file__).resolve().parents[2] / "img" / "logomini.png"


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CestIA")
        self.resize(1180, 760)
        self.setStyleSheet(HOJA_ESTILOS)

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
        self.pagina_cesta = PaginaCesta(self.repositorio)
        self.pagina_historial = PaginaHistorial(self.repositorio)
        self.pagina_comparador = PaginaComparador(self.repositorio, self.catalogo)
        self.pagina_alertas = PaginaAlertas(self.repositorio, self.catalogo)
        self.pagina_estadisticas = PaginaEstadisticas(self.repositorio)
        self.pagina_ia = PaginaIA(self.asistente)
        self.pagina_escaner = PaginaEscaner(self.catalogo)
        self.pagina_configuracion = PaginaConfiguracion(
            self.asistente, self.repositorio
        )
        self.pagina_about = PaginaAbout()

        paginas = [
            ("Productos", self.pagina_busqueda),
            ("Cesta", self.pagina_cesta),
            ("Historial", self.pagina_historial),
            ("Comparador", self.pagina_comparador),
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
        envoltorio.addWidget(self.pila, 1)

        self.pagina_busqueda.abrir_producto.connect(self.mostrar_producto)
        self.pagina_comparador.abrir_producto.connect(self.mostrar_producto)
        self.pagina_escaner.abrir_producto.connect(self.mostrar_producto)
        self.pagina_producto.abrir_producto.connect(self.mostrar_producto)
        self.pagina_producto.back.clicked.connect(
            lambda: self._ir_a(0, self.pagina_busqueda)
        )
        self.pagina_producto.anadir_a_cesta.connect(self._anadir_cesta)
        self.pagina_producto.crear_alerta.connect(self._anadir_alerta)

        self._ir_a(0, self.pagina_busqueda)
        self._comprobar_alertas_silencioso()

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
        self.pila.setCurrentWidget(pagina)
        for i, boton in enumerate(self.botones_nav):
            boton.setProperty("activo", "true" if i == indice_nav else "false")
            boton.style().unpolish(boton)
            boton.style().polish(boton)
        if hasattr(pagina, "actualizar"):
            pagina.actualizar()

    def mostrar_producto(self, id_producto: str) -> None:
        self.pila.setCurrentWidget(self.pagina_producto)
        for boton in self.botones_nav:
            boton.setProperty("activo", "false")
            boton.style().unpolish(boton)
            boton.style().polish(boton)
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

    def _comprobar_alertas_silencioso(self) -> None:
        disparadas = self.repositorio.comprobar_alertas()
        if disparadas:
            texto = "\n".join(
                f"• {t.get('nombre_producto')}: {t.get('precio_actual'):.2f} € "
                f"(objetivo {t.get('precio_objetivo'):.2f} €)"
                for t in disparadas
            )
            QMessageBox.information(self, "Alertas disparadas", texto)
