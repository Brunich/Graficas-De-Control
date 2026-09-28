"""Colores y hoja de estilo: fondo oscuro, lavanda y verde agua apagados, nada chillón."""
from PySide6.QtGui import QColor

FONDO = '#110e17'
PANEL = '#1a1622'
PANEL_2 = '#231e2e'
BORDE = '#2e2739'
TEXTO = '#eee9f6'
TENUE = '#9d95b2'
ACENTO = '#b8a4ec'  # lavanda: línea central, lo elegido
SERIE = '#8ecfc6'  # verde agua: las mediciones
BIEN = '#94d1ae'
AVISO = '#e8cf96'  # arena: la tolerancia y lo justo
MAL = '#ec9fab'  # rosa: señales


def c(hexa: str, alfa: int = 255) -> QColor:
    col = QColor(hexa)
    col.setAlpha(alfa)
    return col


QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: {TEXTO}; }}
QMainWindow, #raiz {{ background: {FONDO}; }}
#lateral {{ background: {PANEL}; border-right: 1px solid {BORDE}; }}
#titulo {{ font-size: 20px; font-weight: 700; }}
QLabel[tenue="true"] {{ color: {TENUE}; }}
#seccion {{ color: {TENUE}; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-top: 14px; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDE}; border-radius: 8px; padding: 8px 12px; text-align: left; }}
QPushButton:hover {{ border-color: {ACENTO}; }}
QPushButton:disabled {{ color: #635c74; }}
QPushButton#primario {{ background: {ACENTO}; color: #1b1624; border: none; font-weight: 700; }}
QPushButton#primario:hover {{ background: #c8b8f1; }}
QPushButton[segmento="true"] {{ background: transparent; border: none; border-radius: 7px; padding: 6px 12px; color: {TENUE}; text-align: center; }}
QPushButton[segmento="true"]:hover {{ color: {TEXTO}; }}
QPushButton[segmento="true"]:checked {{ background: {PANEL_2}; color: {TEXTO}; font-weight: 600; }}
#segmentos {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 9px; }}
QComboBox, QDoubleSpinBox, QSpinBox {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 7px; padding: 6px 8px; min-height: 18px; }}
QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {ACENTO}; }}
QComboBox QAbstractItemView {{ background: {PANEL_2}; border: 1px solid {BORDE}; selection-background-color: #3a3150; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {BORDE}; background: {FONDO}; }}
QCheckBox::indicator:checked {{ background: {ACENTO}; border-color: {ACENTO}; }}
#tarjeta {{ background: {PANEL}; border: 1px solid {BORDE}; border-radius: 14px; }}
#vTitulo {{ font-size: 22px; font-weight: 700; }}
#vDetalle {{ font-size: 14px; color: {TEXTO}; }}
#dato {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 10px; }}
#datoValor {{ font-size: 18px; font-weight: 700; font-family: 'Cascadia Mono', 'Consolas', monospace; }}
#datoNombre {{ color: {TENUE}; font-size: 11px; }}
#bloque {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 10px; }}
#grande {{ font-size: 17px; font-weight: 700; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border: 1px solid {BORDE}; border-radius: 10px; margin: 0 0 6px 0; padding: 0; background: {FONDO}; }}
QListWidget::item:hover {{ border-color: #4a4060; }}
QListWidget::item:selected {{ border-color: {ACENTO}; background: #241e31; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDE}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QStatusBar {{ background: {PANEL}; color: {TENUE}; border-top: 1px solid {BORDE}; }}
QToolTip {{ background: {PANEL_2}; color: {TEXTO}; border: 1px solid {BORDE}; padding: 6px; }}
QSplitter::handle {{ background: transparent; }}
"""
