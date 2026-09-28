"""Saca las capturas del README sin abrir ventanas: `python tools/captura.py`."""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Sin pantalla Qt no encuentra las fuentes del sistema: se le dice dónde están.
if sys.platform == 'win32':
    os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from spc import tema
from spc.ventana import Ventana

DOCS = Path(__file__).resolve().parents[1] / 'docs'


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(tema.QSS)
    v = Ventana()
    v.resize(QSize(1360, 820))
    v.show()
    v.cargar_ejemplo()
    app.processEvents()
    senal = next(i for i, p in enumerate(v.grafica.puntos) if p.reglas)
    v.elegir(senal)
    app.processEvents()
    DOCS.mkdir(exist_ok=True)
    v.grab().save(str(DOCS / 'captura.png'))
    print('ok', DOCS / 'captura.png')


if __name__ == '__main__':
    main()
