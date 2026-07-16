HOJA_ESTILOS = """
QWidget {
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 14px;
    color: #14201a;
}
QMainWindow, QDialog { background: #eef6f1; }
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
"""
