"""Indicadores de progreso para cargas en CestIA."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QProgressBar, QWidget


def crear_barra_progreso(parent: QWidget | None = None) -> QProgressBar:
    barra = QProgressBar(parent)
    barra.setRange(0, 0)  # indeterminada
    barra.setTextVisible(False)
    barra.setFixedHeight(6)
    barra.setObjectName("BarraProgreso")
    barra.hide()
    return barra


def crear_barra_progreso_espera(parent: QWidget | None = None) -> QProgressBar:
    """Barra determinada (0–100 %) para esperas largas, p. ej. respuestas de IA."""
    barra = QProgressBar(parent)
    barra.setRange(0, 100)
    barra.setValue(0)
    barra.setTextVisible(True)
    barra.setFormat("Pensando… %p%")
    barra.setFixedHeight(24)
    barra.setObjectName("BarraProgresoEspera")
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


class ProgresoEspera:
    """Avanza la barra mientras dura una tarea en segundo plano."""

    _TOPE = 92

    def __init__(self, barra: QProgressBar) -> None:
        self.barra = barra
        self._timer = QTimer(barra)
        self._timer.timeout.connect(self._avanzar)
        self._valor = 0
        self._activo = False

    def iniciar(self, mensaje: str = "Pensando…") -> None:
        self._activo = True
        self._valor = 0
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        self.barra.setFormat(f"{mensaje} %p%")
        self.barra.setTextVisible(True)
        self.barra.show()
        self._timer.start(140)

    def _avanzar(self) -> None:
        if not self._activo or self._valor >= self._TOPE:
            return
        if self._valor < 45:
            paso = 3
        elif self._valor < 70:
            paso = 2
        else:
            paso = 1
        self._valor = min(self._valor + paso, self._TOPE)
        self.barra.setValue(self._valor)

    def completar(self) -> None:
        self._activo = False
        self._timer.stop()
        self.barra.setValue(100)
        QTimer.singleShot(450, self._ocultar)

    def cancelar(self) -> None:
        self._activo = False
        self._timer.stop()
        self._ocultar()

    def _ocultar(self) -> None:
        self.barra.hide()
        self.barra.setValue(0)
