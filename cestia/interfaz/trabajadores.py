"""Trabajadores en hilo para no bloquear la interfaz."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot


class SenalesTrabajador(QObject):
    terminado = Signal(object)
    error = Signal(str)


class TrabajadorFuncion(QRunnable):
    def __init__(self, funcion: Callable[[], Any], puente: SenalesTrabajador) -> None:
        super().__init__()
        self.funcion = funcion
        self.puente = puente
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            resultado = self.funcion()
            self.puente.terminado.emit(resultado)
        except Exception as exc:  # noqa: BLE001
            self.puente.error.emit(str(exc))


def ejecutar_en_hilo(funcion: Callable[[], Any], al_ok, al_error=None) -> None:
    """Ejecuta ``funcion`` en segundo plano y llama a los callbacks en el hilo GUI."""
    puente = SenalesTrabajador()
    # Mantener vivo el puente hasta que terminen las señales
    _puentes_activos.add(puente)

    def _limpiar(*_args: Any) -> None:
        _puentes_activos.discard(puente)
        puente.deleteLater()

    puente.terminado.connect(al_ok, Qt.ConnectionType.QueuedConnection)
    puente.terminado.connect(_limpiar, Qt.ConnectionType.QueuedConnection)
    if al_error:
        puente.error.connect(al_error, Qt.ConnectionType.QueuedConnection)
    puente.error.connect(_limpiar, Qt.ConnectionType.QueuedConnection)

    trabajador = TrabajadorFuncion(funcion, puente)
    QThreadPool.globalInstance().start(trabajador)


_puentes_activos: set[SenalesTrabajador] = set()
