HOJA_ESTILOS = """
QWidget {
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 14px;
    color: #14201a;
}
QMainWindow, QDialog { background: #eef6f1; }
QStackedWidget {
    background: #eef6f1;
}
QScrollArea {
    background: #eef6f1;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: #eef6f1;
}
QScrollArea QWidget#qt_scrollarea_viewport {
    background: #eef6f1;
}
QWidget#FichaProducto {
    background: #eef6f1;
    color: #14201a;
}
QWidget#FichaProducto QLabel {
    color: #14201a;
    background: transparent;
}
QWidget#FichaProducto QLabel#TituloPagina {
    color: #0a3d2a;
}
QWidget#FichaProducto QLabel#Atenuado {
    color: #5a6b62;
}
QWidget#FichaProducto QLabel#Precio {
    color: #0a3d2a;
}
QWidget#FichaProducto QLabel#BadgeSube {
    color: #b42318;
}
QWidget#FichaProducto QLabel#BadgeBaja {
    color: #0f6b45;
}
QWidget#FichaProducto QPlainTextEdit {
    background: #ffffff;
    color: #14201a;
}
QWidget#FichaProducto QDoubleSpinBox {
    background: #ffffff;
    color: #14201a;
}
QWidget#PaginaProducto {
    background: #eef6f1;
    color: #14201a;
}
#BarraLateral {
    background: #0f6b45;
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
#BarraLateral QPushButton:hover { background: rgba(255,255,255,0.12); }
#BarraLateral QPushButton[activo="true"] { background: rgba(255,255,255,0.22); }
#TituloMarca {
    color: white;
    font-size: 22px;
    font-weight: 800;
    padding: 18px 16px 8px;
}
#LogoMarca {
    padding: 18px 16px 6px;
    background: transparent;
}
#LogoAbout {
    background: transparent;
    padding: 8px;
}
#SubtituloMarca {
    color: #c9e8d8;
    padding: 0 16px 16px;
    font-size: 12px;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background: #ffffff;
    color: #14201a;
    border: 1px solid #c5ddd0;
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: #0f6b45;
    selection-color: #ffffff;
}
QComboBox {
    background: #ffffff;
    color: #14201a;
    border: 1px solid #c5ddd0;
    border-radius: 10px;
    padding: 8px 10px;
    min-height: 20px;
}
QComboBox:editable {
    background: #ffffff;
    color: #14201a;
}
QComboBox:!editable, QComboBox::drop-down:editable {
    background: #ffffff;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #0f6b45;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #14201a;
    border: 1px solid #c5ddd0;
    outline: 0;
    selection-background-color: #0f6b45;
    selection-color: #ffffff;
    padding: 4px;
}
QComboBox QLineEdit {
    background: #ffffff;
    color: #14201a;
    border: none;
    padding: 0 4px;
    selection-background-color: #0f6b45;
    selection-color: #ffffff;
}
QCheckBox {
    color: #14201a;
    spacing: 10px;
    background: transparent;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #0f6b45;
    border-radius: 4px;
    background-color: #ffffff;
}
QCheckBox::indicator:hover {
    border-color: #128554;
}
QCheckBox::indicator:checked {
    background-color: #0f6b45;
    border-color: #0a3d2a;
}
QCheckBox::indicator:checked:hover {
    background-color: #128554;
}
QPushButton {
    background: #0f6b45;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 700;
}
QPushButton:hover { background: #128554; }
QPushButton:disabled { background: #9bb8a9; }
QPushButton[secundario="true"] {
    background: white;
    color: #0f6b45;
    border: 1px solid #0f6b45;
}
QTableWidget, QListWidget {
    background: white;
    border: 1px solid #c5ddd0;
    border-radius: 12px;
    gridline-color: #e3eee8;
}
QHeaderView::section {
    background: #e6f4ec;
    padding: 8px;
    border: none;
    font-weight: 700;
}
QLabel#TituloPagina {
    font-size: 24px;
    font-weight: 800;
    color: #0a3d2a;
}
QLabel#Atenuado { color: #5a6b62; }
QLabel#Precio {
    font-size: 20px;
    font-weight: 800;
    color: #0a3d2a;
}
QLabel#BadgeSube { color: #b42318; font-weight: 700; }
QLabel#BadgeBaja { color: #0f6b45; font-weight: 700; }
QLabel#Nutri {
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 8px;
    background: #e6f4ec;
}
QFrame#PanelAlergenos {
    background: #fff8eb;
    border: 2px solid #e6a23c;
    border-radius: 12px;
}
QFrame#PanelAlergenos QLabel#TituloAlergenos {
    font-size: 15px;
    font-weight: 800;
    color: #8a5a00;
    background: transparent;
}
QFrame#PanelAlergenos QLabel#TextoAlergenos {
    font-size: 14px;
    font-weight: 700;
    color: #5c3d00;
    background: transparent;
}
QFrame#PanelAlergenos QLabel#TextoAlergenos[vacio="true"] {
    font-weight: 500;
    color: #8a7350;
}
QFrame#PanelNutricion {
    background: #e8f6ef;
    border: 2px solid #0f6b45;
    border-radius: 12px;
}
QFrame#PanelNutricion QLabel#TituloNutricion {
    font-size: 15px;
    font-weight: 800;
    color: #0a3d2a;
    background: transparent;
}
QFrame#PanelNutricion QLabel#PistaNutricion {
    font-size: 12px;
    color: #3d6b54;
    background: transparent;
}
QFrame#PanelNutricion QLabel#TextoNutricion {
    font-size: 14px;
    color: #14201a;
    background: #ffffff;
    border-radius: 8px;
    padding: 8px 10px;
}
QFrame#PanelNutricion QLabel#TextoNutricion[vacio="true"] {
    color: #5a6b62;
    font-weight: 500;
}
QFrame#PanelAlternativas {
    background: #eaf3fb;
    border: 2px solid #2b7bb9;
    border-radius: 12px;
}
QFrame#PanelAlternativas QLabel#TituloAlternativas {
    font-size: 15px;
    font-weight: 800;
    color: #0b4f7a;
    background: transparent;
}
QFrame#PanelAlternativas QLabel#PistaAlternativas {
    font-size: 12px;
    color: #3a6a8a;
    background: transparent;
}
QListWidget#ListaEnlaces {
    background: #ffffff;
    color: #0b5cab;
    border: 1px solid #b7d3ea;
    border-radius: 10px;
    padding: 4px;
    outline: none;
}
QListWidget#ListaEnlaces::item {
    color: #0b5cab;
    background: #ffffff;
    padding: 10px 12px;
    border-radius: 8px;
}
QListWidget#ListaEnlaces::item:hover {
    background: #e8f2fb;
    color: #084a8a;
}
QListWidget#ListaEnlaces::item:selected {
    background: #d6e9f8;
    color: #063a6d;
}
"""
