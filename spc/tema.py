"""Colores y hoja de estilo: fondo oscuro, morado apagado, nada chillón."""
from PySide6.QtGui import QColor

FONDO = '#16131d'
PANEL = '#1e1a27'
PANEL_2 = '#252031'
BORDE = '#312a3f'
TEXTO = '#ebe6f3'
TENUE = '#a59dba'
ACENTO = '#b9a3e3'
BIEN = '#9fcfb4'
AVISO = '#e3cd98'
MAL = '#e2a3ab'


def c(hexa: str, alfa: int = 255) -> QColor:
    col = QColor(hexa)
    col.setAlpha(alfa)
    return col


QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: {TEXTO}; }}
QMainWindow, #raiz {{ background: {FONDO}; }}
#lateral {{ background: {PANEL}; border-right: 1px solid {BORDE}; }}
#titulo {{ font-size: 20px; font-weight: 700; }}
#subtitulo, .tenue, QLabel[tenue="true"] {{ color: {TENUE}; }}
#seccion {{ color: {TENUE}; font-size: 11px; font-weight: 700; letter-spacing: 1px; margin-top: 14px; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDE}; border-radius: 8px; padding: 8px 12px; text-align: left; }}
QPushButton:hover {{ border-color: {ACENTO}; }}
QPushButton:disabled {{ color: #6d6680; }}
QPushButton#primario {{ background: {ACENTO}; color: #1b1624; border: none; font-weight: 700; }}
QPushButton#primario:hover {{ background: #c9b6ec; }}
QComboBox, QDoubleSpinBox, QSpinBox {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 7px; padding: 6px 8px; min-height: 18px; }}
QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {ACENTO}; }}
QComboBox QAbstractItemView {{ background: {PANEL_2}; border: 1px solid {BORDE}; selection-background-color: #3a3150; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {BORDE}; background: {FONDO}; }}
QCheckBox::indicator:checked {{ background: {ACENTO}; border-color: {ACENTO}; }}
#tarjeta {{ background: {PANEL}; border: 1px solid {BORDE}; border-radius: 14px; }}
#veredicto {{ font-size: 19px; font-weight: 700; }}
#dato {{ background: {FONDO}; border: 1px solid {BORDE}; border-radius: 10px; }}
#datoValor {{ font-size: 18px; font-weight: 700; font-family: 'Cascadia Mono', 'Consolas', monospace; }}
#datoNombre {{ color: {TENUE}; font-size: 11px; }}
QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ border: 1px solid {BORDE}; border-radius: 10px; margin: 0 0 8px 0; padding: 0; }}
QListWidget::item:selected {{ border-color: {ACENTO}; background: #2a2338; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDE}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QStatusBar {{ background: {PANEL}; color: {TENUE}; border-top: 1px solid {BORDE}; }}
QToolTip {{ background: {PANEL_2}; color: {TEXTO}; border: 1px solid {BORDE}; padding: 6px; }}
QSplitter::handle {{ background: {FONDO}; }}
"""
