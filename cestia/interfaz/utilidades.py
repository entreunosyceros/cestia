"""Utilidades de interfaz: euros, Nutri-Score y carga de miniaturas."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import QLabel

_gestor_red: QNetworkAccessManager | None = None
_cache_pixmaps: dict[str, QPixmap] = {}
# Evita que el recolector elimine el callback antes de tiempo
_respuestas_pendientes: set[object] = set()


def gestor_red() -> QNetworkAccessManager:
    global _gestor_red
    if _gestor_red is None:
        _gestor_red = QNetworkAccessManager()
    return _gestor_red


def formatear_euros(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def color_nutri(grado: str | None) -> str:
    g = (grado or "").upper()
    return {
        "A": "#038141",
        "B": "#85bb2f",
        "C": "#fecb02",
        "D": "#ee8100",
        "E": "#e63e11",
    }.get(g, "#5a6b62")


def cargar_miniatura(etiqueta: QLabel, url: str | None, tamano: int = 96) -> None:
    etiqueta.setFixedSize(tamano, tamano)
    etiqueta.setAlignment(Qt.AlignCenter)
    etiqueta.setStyleSheet(
        "background:#ffffff; border-radius:10px; border:1px solid #e3eee8;"
    )
    etiqueta.setScaledContents(False)

    if not url:
        etiqueta.clear()
        etiqueta.setText("·")
        return

    cache = _cache_pixmaps.get(url)
    if cache is not None and not cache.isNull():
        etiqueta.clear()
        etiqueta.setPixmap(
            cache.scaled(tamano, tamano, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        return

    etiqueta.clear()
    etiqueta.setText("…")

    peticion = QNetworkRequest(QUrl(url))
    peticion.setRawHeader(
        b"User-Agent",
        b"Mozilla/5.0 (compatible; CestIA/0.2; +uso-personal)",
    )
    peticion.setRawHeader(b"Referer", b"https://tienda.mercadona.es/")
    peticion.setRawHeader(b"Accept", b"image/*,*/*;q=0.8")
    peticion.setAttribute(
        QNetworkRequest.RedirectPolicyAttribute,
        QNetworkRequest.NoLessSafeRedirectPolicy,
    )

    respuesta = gestor_red().get(peticion)
    _respuestas_pendientes.add(respuesta)

    def al_terminar() -> None:
        _respuestas_pendientes.discard(respuesta)
        try:
            _ = etiqueta.objectName()
        except RuntimeError:
            respuesta.deleteLater()
            return

        if respuesta.error() != respuesta.NetworkError.NoError:
            etiqueta.setText("·")
            respuesta.deleteLater()
            return

        datos = respuesta.readAll()
        pix = QPixmap()
        if not pix.loadFromData(datos):
            etiqueta.setText("·")
            respuesta.deleteLater()
            return

        _cache_pixmaps[url] = pix
        etiqueta.clear()
        etiqueta.setPixmap(
            pix.scaled(tamano, tamano, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        respuesta.deleteLater()

    respuesta.finished.connect(al_terminar)
