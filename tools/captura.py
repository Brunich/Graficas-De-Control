"""Saca las capturas del README sin abrir ventanas: `python tools/captura.py`."""
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Sin pantalla Qt no encuentra las fuentes del sistema: se le dice dónde están.
if sys.platform == 'win32':
    os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')
os.environ['SPC_AJUSTES'] = str(Path(tempfile.gettempdir()) / 'spc-captura.ini')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from spc import tema
from spc.ventana import Ventana

DOCS = Path(__file__).resolve().parents[1] / 'docs'


def esperar(app, s=1.0):
    """Deja correr las animaciones para fotografiar el cuadro final."""
    fin = time.time() + s
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.01)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(tema.QSS)
    v = Ventana()
    v.resize(QSize(1400, 860))
    v.show()
    v.cargar_ejemplo()
    v.seg_vista.poner(0)
    esperar(app)
    senal = next(i for i, p in enumerate(v.grafica.puntos) if p.reglas)
    v.elegir(senal + 1, abrir_punto=True)
    esperar(app)
    DOCS.mkdir(exist_ok=True)
    v.grab().save(str(DOCS / 'captura.png'))
    for k, nombre, apartado in ((1, 'tendencia', 0), (2, 'cajas', 3), (3, 'reparto', 2)):
        v.seg_vista.poner(k)
        v.seg_apartado.poner(apartado)
        esperar(app)
        v.grab().save(str(DOCS / f'vista-{nombre}.png'))
    print('ok', DOCS)


if __name__ == '__main__':
    main()
