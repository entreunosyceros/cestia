"""Trabajadores en hilo para no bloquear la interfaz."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class SenalesTrabajador(QObject):
    terminado = Signal(object)
    error = Signal(str)


class TrabajadorFuncion(QRunnable):
    def __init__(self, funcion: Callable[[], Any]) -> None:
        super().__init__()
        self.funcion = funcion
        self.senales = SenalesTrabajador()

    @Slot()
    def run(self) -> None:
        try:
            resultado = self.funcion()
            self.senales.terminado.emit(resultado)
        except Exception as exc:  # noqa: BLE001
            self.senales.error.emit(str(exc))


def ejecutar_en_hilo(funcion: Callable[[], Any], al_ok, al_error=None) -> None:
    trabajador = TrabajadorFuncion(funcion)
    trabajador.senales.terminado.connect(al_ok)
    if al_error:
        trabajador.senales.error.connect(al_error)
    QThreadPool.globalInstance().start(trabajador)
