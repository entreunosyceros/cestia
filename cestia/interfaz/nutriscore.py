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


class GraficoNutriScore(QWidget):
    """Escala A–E con el grado del producto resaltado y el significado de cada letra."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grado: str | None = None
        self.setMinimumHeight(148)
        self.setMaximumHeight(168)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)
        self.setAutoFillBackground(True)
        paleta = self.palette()
        paleta.setColor(QPalette.Window, QColor("#eef6f1"))
        paleta.setColor(QPalette.WindowText, QColor("#14201a"))
        self.setPalette(paleta)

        self._titulo = QLabel("Nutri-Score")
        self._titulo.setStyleSheet(
            "font-weight: 800; color: #0a3d2a; font-size: 13px; background: transparent;"
        )
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
            lab.setStyleSheet(
                "QLabel { color: #5a6b62; font-size: 10px; padding: 2px; }"
            )
            self._etiquetas[letra] = lab
            fila.addWidget(lab, 1)
        layout.addLayout(fila)

        self._resumen = QLabel("")
        self._resumen.setObjectName("Atenuado")
        self._resumen.setWordWrap(True)
        layout.addWidget(self._resumen)

    def establecer_grado(self, grado: str | None) -> None:
        g = (grado or "").strip().upper()
        if g not in DESCRIPCIONES:
            self._grado = None
            self.hide()
            return
        self._grado = g
        self._lienzo.establecer_grado(g)
        for letra, lab in self._etiquetas.items():
            if letra == g:
                lab.setStyleSheet(
                    f"QLabel {{ color: #0a3d2a; font-size: 10px; padding: 2px; "
                    f"font-weight: 700; border-bottom: 2px solid {color_nutri(letra)}; }}"
                )
            else:
                lab.setStyleSheet(
                    "QLabel { color: #5a6b62; font-size: 10px; padding: 2px; }"
                )
        self._resumen.setText(
            f"Este producto: <b>Nutri-Score {g}</b> — {DESCRIPCIONES[g]} "
            "(de A mejor a E peor)."
        )
        self.show()
        self.update()


class _EscalaNutriScore(QWidget):
    """Dibuja la franja clásica A–E tipo etiqueta Nutri-Score."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grado: str | None = None
        self.setMinimumHeight(52)
        self.setMaximumHeight(58)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def establecer_grado(self, grado: str) -> None:
        self._grado = grado
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margen = 2.0
        n = len(GRADOS)
        hueco = 3.0
        ancho = (w - 2 * margen - hueco * (n - 1)) / n
        y = margen
        alto_base = h - 2 * margen
        punta = min(12.0, ancho * 0.22)

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
                painter.setPen(QPen(QColor("#0a3d2a"), 2.2))
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
