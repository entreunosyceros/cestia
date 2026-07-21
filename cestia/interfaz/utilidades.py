"""Utilidades de interfaz: euros, Nutri-Score y carga de miniaturas."""

from __future__ import annotations

from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QPalette, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QLabel, QTextEdit

_gestor_red: QNetworkAccessManager | None = None
_cache_pixmaps: dict[str, QPixmap] = {}
_respuestas_pendientes: set[QNetworkReply] = set()
_PROP_URL = "_cestia_img_url"
_PROP_REPLY = "_cestia_img_reply"


class _PuenteMiniatura(QObject):
    """Mantiene viva la conexión finished → callback sin cierres prematuros."""

    terminado = Signal(object)

    def __init__(self, respuesta: QNetworkReply) -> None:
        super().__init__(respuesta)
        self.respuesta = respuesta
        respuesta.finished.connect(self._emitir)

    def _emitir(self) -> None:
        self.terminado.emit(self.respuesta)


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


def _referer_para(url: str) -> bytes:
    host = (urlparse(url).hostname or "").lower()
    if "dia.es" in host:
        return b"https://www.dia.es/"
    if "eroski" in host:
        return b"https://supermercado.eroski.es/"
    if "lidl" in host:
        return b"https://www.lidl.es/"
    if "carrefour" in host:
        return b"https://www.carrefour.es/"
    if "alcampo" in host or "compraonline" in host:
        return b"https://www.compraonline.alcampo.es/"
    if "froiz" in host:
        # Las miniaturas van por froiz.com (CDN); el referer del súper online basta.
        return b"https://supermercado.froiz.com/"
    if "gadis" in host:
        return b"https://www.gadisline.com/"
    return b"https://tienda.mercadona.es/"


def _abortar_respuesta_previa(etiqueta: QLabel) -> None:
    previa = etiqueta.property(_PROP_REPLY)
    if previa is None:
        return
    try:
        if isinstance(previa, QNetworkReply) and previa.isRunning():
            previa.abort()
    except RuntimeError:
        pass
    etiqueta.setProperty(_PROP_REPLY, None)


def _aplicar_pixmap(etiqueta: QLabel, pix: QPixmap, tamano: int) -> None:
    try:
        etiqueta.clear()
        etiqueta.setPixmap(
            pix.scaled(tamano, tamano, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
    except RuntimeError:
        pass


def cargar_miniatura(etiqueta: QLabel, url: str | None, tamano: int = 96) -> None:
    etiqueta.setFixedSize(tamano, tamano)
    etiqueta.setAlignment(Qt.AlignCenter)
    etiqueta.setStyleSheet(
        "background:#ffffff; border-radius:10px; border:1px solid #e3eee8;"
    )
    etiqueta.setScaledContents(False)

    _abortar_respuesta_previa(etiqueta)

    if not url:
        etiqueta.setProperty(_PROP_URL, "")
        etiqueta.clear()
        etiqueta.setText("·")
        return

    etiqueta.setProperty(_PROP_URL, url)

    cache = _cache_pixmaps.get(url)
    if cache is not None and not cache.isNull():
        _aplicar_pixmap(etiqueta, cache, tamano)
        return

    etiqueta.clear()
    etiqueta.setText("…")

    peticion = QNetworkRequest(QUrl(url))
    peticion.setRawHeader(
        b"User-Agent",
        b"Mozilla/5.0 (compatible; CestIA/0.3; +uso-personal)",
    )
    peticion.setRawHeader(b"Referer", _referer_para(url))
    # Preferir JPEG/PNG: CDNs como Froiz sirven AVIF/WebP si los pedimos y QPixmap puede fallar.
    peticion.setRawHeader(
        b"Accept",
        b"image/jpeg,image/png,*/*;q=0.5",
    )
    peticion.setAttribute(
        QNetworkRequest.RedirectPolicyAttribute,
        QNetworkRequest.NoLessSafeRedirectPolicy,
    )
    # Evita reutilizar sockets SSL a medias (reduce el aviso QSslSocket)
    peticion.setAttribute(QNetworkRequest.Http2AllowedAttribute, False)
    peticion.setTransferTimeout(20_000)

    respuesta = gestor_red().get(peticion)
    etiqueta.setProperty(_PROP_REPLY, respuesta)
    _respuestas_pendientes.add(respuesta)
    puente = _PuenteMiniatura(respuesta)

    def al_terminar(reply: QNetworkReply) -> None:
        _respuestas_pendientes.discard(reply)
        try:
            url_actual = etiqueta.property(_PROP_URL)
            reply_actual = etiqueta.property(_PROP_REPLY)
        except RuntimeError:
            reply.deleteLater()
            return

        if reply_actual is reply:
            etiqueta.setProperty(_PROP_REPLY, None)

        # Respuesta antigua: la etiqueta ya pide otra URL
        if url_actual != url:
            reply.deleteLater()
            return

        error = reply.error()
        if error != QNetworkReply.NetworkError.NoError:
            if error != QNetworkReply.NetworkError.OperationCanceledError:
                try:
                    etiqueta.setText("·")
                except RuntimeError:
                    pass
            reply.deleteLater()
            return

        # Leer solo del buffer en memoria; no tocar el socket si ya cerró
        try:
            disponibles = int(reply.bytesAvailable())
            if disponibles <= 0 and not reply.isOpen():
                etiqueta.setText("·")
                reply.deleteLater()
                return
            datos = bytes(reply.readAll())
        except (RuntimeError, OSError, ValueError):
            try:
                etiqueta.setText("·")
            except RuntimeError:
                pass
            reply.deleteLater()
            return

        reply.deleteLater()

        if not datos:
            try:
                etiqueta.setText("·")
            except RuntimeError:
                pass
            return

        pix = QPixmap()
        if not pix.loadFromData(datos):
            try:
                etiqueta.setText("·")
            except RuntimeError:
                pass
            return

        _cache_pixmaps[url] = pix
        if etiqueta.property(_PROP_URL) == url:
            _aplicar_pixmap(etiqueta, pix, tamano)

    puente.terminado.connect(al_terminar)


def mostrar_respuesta_ia(salida: QTextEdit, texto: str) -> None:
    """Muestra la respuesta del asistente interpretando Markdown."""
    paleta = salida.palette()
    color_texto = paleta.color(QPalette.Text).name()
    color_fondo = paleta.color(QPalette.Base).name()
    color_acento = paleta.color(QPalette.Highlight).name()
    color_atenuado = paleta.color(QPalette.PlaceholderText).name()
    salida.document().setDefaultStyleSheet(
        f"""
        body {{ color: {color_texto}; background-color: {color_fondo}; }}
        h1, h2, h3, h4 {{ color: {color_texto}; margin: 10px 0 6px; font-weight: 700; }}
        p {{ margin: 6px 0; }}
        ul, ol {{ margin: 6px 0 6px 18px; }}
        li {{ margin: 2px 0; }}
        strong {{ font-weight: 700; }}
        em {{ font-style: italic; }}
        code {{
            font-family: "Consolas", "DejaVu Sans Mono", monospace;
            background-color: rgba(127, 127, 127, 0.18);
            padding: 1px 4px;
            border-radius: 4px;
        }}
        pre {{
            font-family: "Consolas", "DejaVu Sans Mono", monospace;
            background-color: rgba(127, 127, 127, 0.14);
            padding: 8px 10px;
            border-radius: 8px;
            white-space: pre-wrap;
        }}
        blockquote {{
            color: {color_atenuado};
            border-left: 3px solid {color_acento};
            margin: 8px 0;
            padding-left: 10px;
        }}
        a {{ color: {color_acento}; text-decoration: none; }}
        hr {{ border: none; border-top: 1px solid rgba(127, 127, 127, 0.35); margin: 10px 0; }}
        """
    )
    salida.setMarkdown((texto or "").strip())
