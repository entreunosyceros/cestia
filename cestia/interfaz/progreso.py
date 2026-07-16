"""Indicador de progreso indeterminado para cargas en CestIA."""

from __future__ import annotations

from PySide6.QtWidgets import QProgressBar, QWidget


def crear_barra_progreso(parent: QWidget | None = None) -> QProgressBar:
    barra = QProgressBar(parent)
    barra.setRange(0, 0)  # indeterminada
    barra.setTextVisible(False)
    barra.setFixedHeight(6)
    barra.setObjectName("BarraProgreso")
    barra.hide()
    return barra


def mostrar_progreso(barra: QProgressBar, visible: bool) -> None:
    if visible:
        barra.setRange(0, 0)
        barra.show()
    else:
        barra.hide()
        barra.setRange(0, 1)
        barra.setValue(0)
