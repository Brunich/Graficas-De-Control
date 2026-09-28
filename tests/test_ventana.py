"""La ventana sin pantalla: carga el ejemplo, las gráficas y la lista se ponen de acuerdo."""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if sys.platform == 'win32':
    os.environ.setdefault('QT_QPA_FONTDIR', r'C:\Windows\Fonts')

import pytest
from PySide6.QtWidgets import QApplication

from spc import tema
from spc.ventana import Ventana


@pytest.fixture(scope='module')
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(tema.QSS)
    return a


def test_ejemplo_llena_todo(app, tmp_path):
    v = Ventana()
    v.show()
    v.cargar_ejemplo()
    app.processEvents()
    assert v.c_medida.currentText() == 'diametro_mm' and v.c_grupo.currentText() == 'muestra'
    assert v.l_veredicto.text().startswith('Fuera de control')
    assert v.lista.count() == 6
    # Elegir una señal en la lista marca el mismo punto en las dos gráficas.
    v.lista.setCurrentRow(2)
    i = v.lista.item(2).data(0x0100)
    assert v.g_valor.sel == v.g_rango.sel == i
    # Sin periodo base el desgaste se esconde en los límites y aparecen señales falsas al principio.
    v.s_base.setValue(0)
    assert any(v.lista.item(k).data(0x0100) < 15 for k in range(v.lista.count()))
    v.close()


def test_archivo_sin_subgrupos(app, tmp_path):
    ruta = tmp_path / 'espesor.csv'
    ruta.write_text('pieza;espesor\n' + '\n'.join(f'{k};{2.5 + (k % 3) * 0.01:.2f}'.replace('.', ',') for k in range(1, 31)), encoding='utf-8')
    v = Ventana()
    v.cargar_ruta(str(ruta))
    assert v.grafica.modo == 'I-MR' and len(v.grafica.puntos) == 30
    assert v.l_veredicto.text().startswith('Bajo control')
    v.close()
