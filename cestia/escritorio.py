"""Arranque de la aplicación de escritorio CestIA."""

from __future__ import annotations

import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from cestia.interfaz.ventana_principal import VentanaPrincipal


def principal() -> int:
    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName("CestIA")
    aplicacion.setOrganizationName("CestIA")

    # Qt bloquea el manejador de SIGINT de Python; un timer deja procesarlo.
    def _cerrar_por_ctrl_c(*_args) -> None:
        print("\nCestIA: cerrando por Ctrl+C…", flush=True)
        aplicacion.quit()

    signal.signal(signal.SIGINT, _cerrar_por_ctrl_c)
    temporizador = QTimer()
    temporizador.start(150)
    temporizador.timeout.connect(lambda: None)

    ventana = VentanaPrincipal()
    ventana.show()
    codigo = aplicacion.exec()
    return int(codigo)
