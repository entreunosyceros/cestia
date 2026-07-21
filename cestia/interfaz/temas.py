"""Temas claro y oscuro para CestIA."""

from __future__ import annotations

from cestia.interfaz.estilos import HOJA_ESTILOS as HOJA_ESTILOS_CLARO

HOJA_ESTILOS_OSCURO = """
QWidget {
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 14px;
    color: #e8f0ec;
}
QMainWindow, QDialog { background: #121816; }
QStackedWidget { background: #121816; }
QScrollArea { background: #121816; border: none; }
QScrollArea > QWidget > QWidget { background: #121816; }
QScrollArea QWidget#qt_scrollarea_viewport { background: #121816; }
QWidget#FichaProducto {
    background: #121816;
    color: #e8f0ec;
}
QWidget#FichaProducto QLabel { color: #e8f0ec; background: transparent; }
QWidget#FichaProducto QLabel#TituloPagina { color: #7dcea0; }
QWidget#FichaProducto QLabel#Atenuado { color: #9aaba2; }
QWidget#FichaProducto QLabel#Precio { color: #7dcea0; }
QWidget#PaginaProducto { background: #121816; color: #e8f0ec; }
#BarraLateral {
    background: #0a3d2a;
    min-width: 200px;
    max-width: 220px;
}
#BarraLateral QPushButton {
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 10px;
    color: #e8f5ee;
    background: transparent;
    font-weight: 600;
}
#BarraLateral QPushButton:hover { background: rgba(255,255,255,0.10); }
#BarraLateral QPushButton[activo="true"] { background: rgba(255,255,255,0.18); }
#TituloMarca { color: white; font-size: 22px; font-weight: 800; padding: 18px 16px 8px; }
#SubtituloMarca { color: #9bc4ad; padding: 0 16px 16px; font-size: 12px; }
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background: #1e2824;
    color: #e8f0ec;
    border: 1px solid #3d5248;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #0f6b45;
    selection-color: #ffffff;
}
QComboBox {
    background: #1e2824;
    color: #e8f0ec;
    border: 1px solid #3d5248;
    border-radius: 10px;
    padding: 8px 10px;
}
QComboBox QAbstractItemView {
    background-color: #1e2824;
    color: #e8f0ec;
    border: 1px solid #3d5248;
    selection-background-color: #0f6b45;
}
QCheckBox { color: #e8f0ec; spacing: 10px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 2px solid #0f6b45;
    border-radius: 4px;
    background-color: #1e2824;
}
QCheckBox::indicator:checked { background-color: #0f6b45; }
QPushButton {
    background: #0f6b45;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 700;
}
QPushButton:hover { background: #128554; }
QPushButton[secundario="true"] {
    background: #1e2824;
    color: #7dcea0;
    border: 1px solid #0f6b45;
}
QTableWidget, QListWidget, QTreeWidget {
    background: #1e2824;
    color: #e8f0ec;
    border: 1px solid #3d5248;
    border-radius: 12px;
    gridline-color: #2a3832;
}
QHeaderView::section {
    background: #243029;
    color: #7dcea0;
    padding: 8px;
    border: none;
    font-weight: 700;
}
QTableCornerButton::section { background: #243029; border: none; }
QTableWidget::item { color: #e8f0ec; background: #1e2824; }
QTableWidget::item:selected { background: #2a4a38; color: #ffffff; }
QLabel#TituloPagina { font-size: 24px; font-weight: 800; color: #7dcea0; }
QLabel#Atenuado { color: #9aaba2; }
QLabel#Precio { font-size: 20px; font-weight: 800; color: #7dcea0; }
QLabel#BadgeSube { color: #f87171; font-weight: 700; }
QLabel#BadgeBaja { color: #4ade80; font-weight: 700; }
QLabel#BadgeOferta {
    color: #ffffff;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 6px;
    background: #dc2626;
}
QWidget#FichaProducto QFrame#TarjetaBase {
    background-color: #1e2824;
    border: 1px solid #3d5248;
    border-radius: 12px;
}
QWidget#FichaProducto QFrame#TarjetaBase QWidget#TarjetaCuerpo {
    background: transparent;
}
QWidget#FichaProducto QLabel#TarjetaTitulo {
    font-size: 14px;
    font-weight: 800;
    color: #e8f0ec;
    background: transparent;
}
QWidget#FichaProducto QLabel#TarjetaPista {
    font-size: 12px;
    color: #9aaba2;
    background: transparent;
}
QWidget#FichaProducto QLabel#TarjetaContenido {
    font-size: 13px;
    color: #c5d4cc;
    background: transparent;
}
QWidget#FichaProducto QLabel#TarjetaContenido[vacio="true"] {
    font-weight: 500;
    color: #7a8a82;
}
QWidget#FichaProducto QFrame#IndicadorLateral {
    background-color: #5a6b62;
    border-radius: 2px;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="peligro"] {
    background-color: #2a2418;
    border: 1px solid #b45309;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="peligro"] QFrame#IndicadorLateral {
    background-color: #D97706;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="peligro"] QLabel#TarjetaTitulo {
    color: #FBBF24;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="peligro"] QLabel#TarjetaContenido {
    color: #FDE68A;
    font-weight: 600;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="info"] {
    background-color: #1a2820;
    border: 1px solid #0f6b45;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="info"] QFrame#IndicadorLateral {
    background-color: #16A34A;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="info"] QLabel#TarjetaTitulo {
    color: #7dcea0;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="info"] QLabel#TarjetaPista {
    color: #9aaba2;
}
QWidget#FichaProducto QFrame#TarjetaBase[class="info"] QLabel#TarjetaContenido {
    color: #e8f0ec;
}
QFrame#PanelAlternativas {
    background: #1a2430;
    border: 2px solid #2563eb;
    border-radius: 12px;
}
QProgressBar#BarraProgreso {
    border: none;
    background: #2a3832;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}
QProgressBar#BarraProgreso::chunk {
    background: #0f6b45;
    border-radius: 3px;
}
QProgressBar#BarraProgresoEspera {
    border: 1px solid #2a3832;
    background: #1a2420;
    border-radius: 10px;
    min-height: 24px;
    max-height: 24px;
    padding: 2px;
    color: #c9e8d8;
    text-align: center;
}
QProgressBar#BarraProgresoEspera::chunk {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0f6b45, stop: 1 #128554
    );
    border-radius: 8px;
}
"""


def obtener_hoja_estilos(tema: str = "claro") -> str:
    if (tema or "claro").strip().lower() in {"oscuro", "dark", "darko"}:
        return HOJA_ESTILOS_OSCURO
    return HOJA_ESTILOS_CLARO
