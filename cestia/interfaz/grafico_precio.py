"""Gráfico de evolución de precios (matplotlib)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class GraficoPrecio(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel("Sin historial de precios")
        self._placeholder.setObjectName("Atenuado")
        layout.addWidget(self._placeholder)
        self._canvas = None
        self._figure = None

    def establecer_historial(self, historial: list[dict[str, Any]]) -> None:
        if not historial:
            self._mostrar_placeholder("Sin historial de precios")
            return
        precios: list[tuple[datetime, float]] = []
        for h in historial:
            if h.get("precio_unidad") is None:
                continue
            bruto = (h.get("registrado_en") or "")[:10]
            try:
                cuando = datetime.strptime(bruto, "%Y-%m-%d")
            except ValueError:
                continue
            precios.append((cuando, float(h["precio_unidad"])))
        if len(precios) < 2:
            self._mostrar_placeholder("Aún poco historial para graficar")
            return
        try:
            import matplotlib.dates as mdates
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            self._mostrar_placeholder("Matplotlib no disponible")
            return

        if self._canvas is None:
            self._figure = Figure(figsize=(6, 2.4), dpi=100)
            self._canvas = FigureCanvasQTAgg(self._figure)
            self.layout().replaceWidget(self._placeholder, self._canvas)
            self._placeholder.hide()

        fechas = [p[0] for p in precios]
        valores = [p[1] for p in precios]
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.plot(fechas, valores, marker="o", color="#0f6b45", linewidth=2)
        ax.set_title("Evolución del precio", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        ax.tick_params(axis="x", rotation=35, labelsize=8)
        ax.grid(True, alpha=0.3)
        # Márgenes fijos: evita el aviso de tight_layout con fechas rotadas.
        self._figure.subplots_adjust(left=0.1, right=0.99, top=0.82, bottom=0.28)
        self._canvas.draw_idle()
        self.show()

    def _mostrar_placeholder(self, texto: str) -> None:
        if self._canvas is not None:
            self._canvas.hide()
        self._placeholder.setText(texto)
        self._placeholder.show()
