"""Gráfico explicativo de la escala Nutri-Score (A–E)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cestia.interfaz.utilidades import color_nutri

# Significados oficiales simplificados (calidad nutricional global)
SIGNIFICADOS: dict[str, str] = {
    "A": "Muy buena",
    "B": "Buena",
    "C": "Media",
    "D": "Baja",
    "E": "Muy baja",
}

DESCRIPCIONES: dict[str, str] = {
    "A": "Muy buena calidad nutricional",
    "B": "Buena calidad nutricional",
    "C": "Calidad nutricional media",
    "D": "Baja calidad nutricional",
    "E": "Muy baja calidad nutricional",
}

GRADOS = ("A", "B", "C", "D", "E")

_TEMAS = {
    "claro": {
        "fondo": "#eef6f1",
        "titulo": "#0a3d2a",
        "texto": "#5a6b62",
        "texto_activo": "#0a3d2a",
        "borde_activo": "#0a3d2a",
        "resumen": "#5a6b62",
    },
    "oscuro": {
        "fondo": "#1a2820",
        "titulo": "#7dcea0",
        "texto": "#9aaba2",
        "texto_activo": "#e8f0ec",
        "borde_activo": "#7dcea0",
        "resumen": "#9aaba2",
    },
}


class GraficoNutriScore(QWidget):
    """Escala A–E con el grado del producto resaltado y el significado de cada letra."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grado: str | None = None
        self._tema = "claro"
        self.setObjectName("GraficoNutriScore")
        self.setMinimumHeight(148)
        self.setMaximumHeight(168)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.setAutoFillBackground(True)

        self._titulo = QLabel("Nutri-Score")
        layout.addWidget(self._titulo)

        self._lienzo = _EscalaNutriScore(self)
        layout.addWidget(self._lienzo)

        fila = QHBoxLayout()
        fila.setSpacing(4)
        self._etiquetas: dict[str, QLabel] = {}
        for letra in GRADOS:
            lab = QLabel(f"<b>{letra}</b><br>{SIGNIFICADOS[letra]}")
            lab.setAlignment(Qt.AlignCenter)
            lab.setWordWrap(True)
            self._etiquetas[letra] = lab
            fila.addWidget(lab, 1)
        layout.addLayout(fila)

        self._resumen = QLabel("")
        self._resumen.setWordWrap(True)
        layout.addWidget(self._resumen)

        self.aplicar_tema("claro")

    def aplicar_tema(self, tema: str) -> None:
        clave = "oscuro" if (tema or "").strip().lower() in {
            "oscuro", "dark", "darko"
        } else "claro"
        self._tema = clave
        colores = _TEMAS[clave]

        paleta = self.palette()
        paleta.setColor(QPalette.Window, QColor(colores["fondo"]))
        paleta.setColor(QPalette.WindowText, QColor(colores["texto_activo"]))
        paleta.setColor(QPalette.Base, QColor(colores["fondo"]))
        paleta.setColor(QPalette.Text, QColor(colores["texto_activo"]))
        self.setPalette(paleta)
        self.setStyleSheet(
            f"QWidget#GraficoNutriScore {{ background: {colores['fondo']}; "
            f"border-radius: 10px; }}"
        )

        self._titulo.setStyleSheet(
            f"font-weight: 800; color: {colores['titulo']}; "
            f"font-size: 13px; background: transparent;"
        )
        self._resumen.setStyleSheet(
            f"color: {colores['resumen']}; background: transparent;"
        )
        self._lienzo.establecer_tema(clave)
        self._refrescar_etiquetas()
        if self._grado:
            self.establecer_grado(self._grado)
        elif self.isVisible():
            self.establecer_no_disponible()
        self.update()

    def establecer_grado(self, grado: str | None) -> None:
        g = (grado or "").strip().upper()
        if g not in DESCRIPCIONES:
            self.establecer_no_disponible()
            return
        self._grado = g
        self._lienzo.establecer_grado(g)
        self._refrescar_etiquetas()
        colores = _TEMAS[self._tema]
        self._resumen.setText(
            f"Este producto: <b style='color:{colores['texto_activo']}'>"
            f"Nutri-Score {g}</b> — {DESCRIPCIONES[g]} "
            "(de A mejor a E peor)."
        )
        self.show()
        self.update()

    def establecer_no_disponible(
        self,
        mensaje: str | None = None,
    ) -> None:
        """Muestra la escala sin grado y explica por qué no hay Nutri-Score."""
        self._grado = None
        self._lienzo.establecer_grado(None)
        self._refrescar_etiquetas()
        colores = _TEMAS[self._tema]
        texto = mensaje or (
            "Nutri-Score no disponible: no consta en la ficha de la tienda "
            "ni en Open Food Facts."
        )
        self._resumen.setText(
            f"<span style='color:{colores['resumen']}'>{texto}</span>"
        )
        self.show()
        self.update()

    def _refrescar_etiquetas(self) -> None:
        colores = _TEMAS[self._tema]
        for letra, lab in self._etiquetas.items():
            if self._grado and letra == self._grado:
                lab.setStyleSheet(
                    f"QLabel {{ color: {colores['texto_activo']}; font-size: 10px; "
                    f"padding: 2px; font-weight: 700; background: transparent; "
                    f"border-bottom: 2px solid {color_nutri(letra)}; }}"
                )
            else:
                lab.setStyleSheet(
                    f"QLabel {{ color: {colores['texto']}; font-size: 10px; "
                    f"padding: 2px; background: transparent; }}"
                )


class _EscalaNutriScore(QWidget):
    """Dibuja la franja clásica A–E tipo etiqueta Nutri-Score."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grado: str | None = None
        self._tema = "claro"
        self.setMinimumHeight(52)
        self.setMaximumHeight(58)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setAutoFillBackground(False)

    def establecer_tema(self, tema: str) -> None:
        self._tema = "oscuro" if tema == "oscuro" else "claro"
        self.update()

    def establecer_grado(self, grado: str | None) -> None:
        self._grado = grado if grado in DESCRIPCIONES else None
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fondo acorde al tema (evita restos claros detrás de las letras)
        fondo = QColor(_TEMAS[self._tema]["fondo"])
        painter.fillRect(self.rect(), fondo)

        w = self.width()
        h = self.height()
        margen = 2.0
        n = len(GRADOS)
        hueco = 3.0
        ancho = (w - 2 * margen - hueco * (n - 1)) / n
        y = margen
        alto_base = h - 2 * margen
        punta = min(12.0, ancho * 0.22)
        borde = QColor(_TEMAS[self._tema]["borde_activo"])

        for i, letra in enumerate(GRADOS):
            x = margen + i * (ancho + hueco)
            activo = letra == self._grado
            alto = alto_base if activo else alto_base * 0.78
            yi = y + (alto_base - alto) / 2

            path = QPainterPath()
            path.moveTo(QPointF(x, yi))
            path.lineTo(QPointF(x + ancho - punta, yi))
            path.lineTo(QPointF(x + ancho, yi + alto / 2))
            path.lineTo(QPointF(x + ancho - punta, yi + alto))
            path.lineTo(QPointF(x, yi + alto))
            path.closeSubpath()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color_nutri(letra)))
            painter.drawPath(path)

            if activo:
                painter.setPen(QPen(borde, 2.2))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)

            painter.setPen(QColor("#ffffff" if letra != "C" else "#1a1a1a"))
            font = QFont()
            font.setBold(True)
            font.setPixelSize(22 if activo else 15)
            painter.setFont(font)
            painter.drawText(
                QRectF(x, yi, ancho - punta * 0.4, alto),
                Qt.AlignCenter,
                letra,
            )

        painter.end()
