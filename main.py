"""Gráficas de control: app de escritorio. `python main.py [archivo.csv]`"""
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from spc import tema
from spc.ventana import Ventana


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Gráficas de control')
    app.setStyle('Fusion')
    app.setStyleSheet(tema.QSS)
    # Empaquetada con PyInstaller, los archivos viven en _MEIPASS; en desarrollo, junto a main.py.
    raiz = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    app.setWindowIcon(QIcon(str(raiz / 'assets' / 'icono.png')))
    v = Ventana()
    if len(sys.argv) > 1:
        v.cargar_ruta(sys.argv[1])
    v.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
