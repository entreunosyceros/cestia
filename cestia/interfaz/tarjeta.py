"""Tarjetas visuales modernas para la ficha de producto."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class TarjetaModerna(QFrame):
    """Caja con sombra, indicador lateral y tipografía clara.

    ``tipo``: ``peligro`` (alérgenos), ``info`` (nutrición), u otros.
    """

    def __init__(
        self,
        tipo: str = "info",
        titulo: str = "",
        contenido: str = "",
        pista: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TarjetaBase")
        self.setProperty("class", tipo)
        self.setAttribute(Qt.WA_StyledBackground, True)

        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(15)
        sombra.setColor(QColor(0, 0, 0, 25))
        sombra.setOffset(0, 4)
        self.setGraphicsEffect(sombra)

        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(16, 16, 16, 16)
        layout_principal.setSpacing(12)

        self.indicador = QFrame()
        self.indicador.setObjectName("IndicadorLateral")
        self.indicador.setFixedWidth(5)
        self.indicador.setMinimumHeight(36)
        layout_principal.addWidget(self.indicador)

        contenedor_texto = QWidget()
        contenedor_texto.setObjectName("TarjetaCuerpo")
        layout_texto = QVBoxLayout(contenedor_texto)
        layout_texto.setContentsMargins(0, 0, 0, 0)
        layout_texto.setSpacing(6)

        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setObjectName("TarjetaTitulo")

        self.lbl_pista: QLabel | None = None
        if pista:
            self.lbl_pista = QLabel(pista)
            self.lbl_pista.setObjectName("TarjetaPista")
            self.lbl_pista.setWordWrap(True)

        self.lbl_contenido = QLabel(contenido)
        self.lbl_contenido.setObjectName("TarjetaContenido")
        self.lbl_contenido.setWordWrap(True)
        self.lbl_contenido.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_contenido.setTextFormat(Qt.RichText)

        layout_texto.addWidget(self.lbl_titulo)
        if self.lbl_pista is not None:
            layout_texto.addWidget(self.lbl_pista)
        layout_texto.addWidget(self.lbl_contenido)
        layout_principal.addWidget(contenedor_texto, stretch=1)

        self.style().unpolish(self)
        self.style().polish(self)

    def establecer_contenido(self, texto: str, *, vacio: bool = False) -> None:
        self.lbl_contenido.setText(texto)
        self.lbl_contenido.setProperty("vacio", "true" if vacio else "false")
        self.lbl_contenido.style().unpolish(self.lbl_contenido)
        self.lbl_contenido.style().polish(self.lbl_contenido)
