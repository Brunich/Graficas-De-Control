"""La ventana: datos a la izquierda, veredicto arriba, las dos gráficas al centro y las señales a la derecha."""
from __future__ import annotations

import csv
import math
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox,
                               QSplitter, QVBoxLayout, QWidget)

from . import tema
from .datos import Tabla, columnas_numericas, grupos, leer_archivo, leer_texto, sugerir
from .graficas import GraficaControl, Histograma, fmt
from .logica import EJEMPLO, REGLAS, SIGNIFICA, capacidad, construir, csv_ejemplo, veredicto

SIN_GRUPO = 'Sin subgrupo · cada fila es un punto'


def seccion(texto: str) -> QLabel:
    lbl = QLabel(texto.upper())
    lbl.setObjectName('seccion')
    return lbl


def tenue(texto: str) -> QLabel:
    lbl = QLabel(texto)
    lbl.setProperty('tenue', True)
    lbl.setWordWrap(True)
    return lbl


class Dato(QFrame):
    """Un número con su nombre debajo: Cp, Cpk, piezas fuera…"""

    def __init__(self, nombre: str, ayuda: str):
        super().__init__()
        self.setObjectName('dato')
        self.setToolTip(ayuda)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(0)
        self.valor = QLabel('—')
        self.valor.setObjectName('datoValor')
        n = QLabel(nombre)
        n.setObjectName('datoNombre')
        lay.addWidget(self.valor)
        lay.addWidget(n)

    def poner(self, texto: str, color: str = tema.TEXTO):
        self.valor.setText(texto)
        self.valor.setStyleSheet(f'color: {color}')


class Ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Gráficas de control')
        self.setAcceptDrops(True)
        self.tabla: Tabla | None = None
        self.grafica = None
        self.ajustes = QSettings('Brunich', 'GraficasDeControl')
        self._construir()
        self._acciones()
        self.resize(self.ajustes.value('tamano', QSize(1360, 820)))
        self.statusBar().showMessage('Arrastra aquí un CSV o Excel con mediciones, o usa el ejemplo.')

    # --- armado ---
    def _construir(self):
        raiz = QWidget(objectName='raiz')
        self.setCentralWidget(raiz)
        fila = QHBoxLayout(raiz)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)
        fila.addWidget(self._lateral())

        centro = QVBoxLayout()
        centro.setContentsMargins(18, 16, 18, 16)
        centro.setSpacing(14)
        centro.addWidget(self._veredicto())

        partir = QSplitter(Qt.Orientation.Horizontal)
        partir.setChildrenCollapsible(False)
        graficas = QFrame(objectName='tarjeta')
        gl = QVBoxLayout(graficas)
        gl.setContentsMargins(10, 10, 10, 10)
        self.g_valor, self.g_rango = GraficaControl('valor'), GraficaControl('rango')
        partir_v = QSplitter(Qt.Orientation.Vertical)
        partir_v.addWidget(self.g_valor)
        partir_v.addWidget(self.g_rango)
        partir_v.setSizes([600, 380])
        gl.addWidget(partir_v)
        for g in (self.g_valor, self.g_rango):
            g.elegido.connect(self.elegir)
        partir.addWidget(graficas)
        partir.addWidget(self._panel_senales())
        partir.setSizes([900, 340])
        partir.setStretchFactor(0, 1)
        centro.addWidget(partir, 1)
        fila.addLayout(centro, 1)

    def _lateral(self) -> QWidget:
        lat = QFrame(objectName='lateral')
        lat.setFixedWidth(290)
        lay = QVBoxLayout(lat)
        lay.setContentsMargins(20, 22, 20, 18)
        lay.setSpacing(8)
        t = QLabel('Gráficas de control', objectName='titulo')
        lay.addWidget(t)
        lay.addWidget(tenue('Saber si la máquina se está desajustando antes de que salga pieza mala.'))

        lay.addWidget(seccion('Datos'))
        self.b_abrir = QPushButton('Abrir archivo…   Ctrl+O', objectName='primario')
        self.b_abrir.clicked.connect(self.abrir)
        self.b_ejemplo = QPushButton('Usar el ejemplo del buje')
        self.b_ejemplo.clicked.connect(self.cargar_ejemplo)
        self.l_archivo = tenue('Ningún archivo abierto.')
        for w in (self.b_abrir, self.b_ejemplo, self.l_archivo):
            lay.addWidget(w)

        lay.addWidget(seccion('Qué graficar'))
        lay.addWidget(tenue('Medición'))
        self.c_medida = QComboBox()
        lay.addWidget(self.c_medida)
        lay.addWidget(tenue('Agrupar piezas por'))
        self.c_grupo = QComboBox()
        lay.addWidget(self.c_grupo)

        lay.addWidget(seccion('Tolerancia'))
        tol = QGridLayout()
        tol.setHorizontalSpacing(8)
        self.k_lie, self.k_lse = QCheckBox('Mínimo'), QCheckBox('Máximo')
        self.s_lie, self.s_lse = QDoubleSpinBox(), QDoubleSpinBox()
        for s in (self.s_lie, self.s_lse):
            s.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            s.setDecimals(3)
            s.setRange(-1e9, 1e9)
            s.setSingleStep(0.01)
            s.setKeyboardTracking(False)
        tol.addWidget(self.k_lie, 0, 0)
        tol.addWidget(self.s_lie, 0, 1)
        tol.addWidget(self.k_lse, 1, 0)
        tol.addWidget(self.s_lse, 1, 1)
        lay.addLayout(tol)

        lay.addWidget(seccion('Límites de control'))
        lay.addWidget(tenue('Calcularlos con las primeras muestras (un periodo estable). 0 = con todas.'))
        self.s_base = QSpinBox()
        self.s_base.setRange(0, 100000)
        self.s_base.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.s_base.setKeyboardTracking(False)
        lay.addWidget(self.s_base)

        lay.addStretch(1)
        self.b_png = QPushButton('Exportar reporte (PNG)')
        self.b_png.clicked.connect(self.exportar_png)
        self.b_csv = QPushButton('Exportar señales (CSV)')
        self.b_csv.clicked.connect(self.exportar_csv)
        for b in (self.b_png, self.b_csv):
            b.setEnabled(False)
            lay.addWidget(b)

        for w in (self.c_medida, self.c_grupo):
            w.currentIndexChanged.connect(self.recalcular)
        for w in (self.s_lie, self.s_lse, self.s_base):
            w.valueChanged.connect(self.recalcular)
        for w in (self.k_lie, self.k_lse):
            w.toggled.connect(self.recalcular)
        return lat

    def _veredicto(self) -> QWidget:
        tarjeta = QFrame(objectName='tarjeta')
        self.tarjeta = tarjeta
        lay = QHBoxLayout(tarjeta)
        lay.setContentsMargins(20, 14, 16, 14)
        lay.setSpacing(12)
        txt = QVBoxLayout()
        txt.setSpacing(2)
        self.l_modo = tenue('')
        self.l_veredicto = QLabel('Sin datos todavía', objectName='veredicto')
        self.l_veredicto.setWordWrap(True)
        txt.addWidget(self.l_modo)
        txt.addWidget(self.l_veredicto)
        lay.addLayout(txt, 1)
        self.d_cp = Dato('Cp', 'Cuánto cabe la variación en la tolerancia (corto plazo). 1.33 o más es holgado.')
        self.d_cpk = Dato('Cpk', 'Como Cp, pero castiga si el proceso está corrido hacia un lado.')
        self.d_ppk = Dato('Ppk', 'Con toda la variación, no sólo la de corto plazo.')
        self.d_fuera = Dato('piezas fuera', 'Mediciones que ya salieron de la tolerancia.')
        for d in (self.d_cp, self.d_cpk, self.d_ppk, self.d_fuera):
            d.setMinimumWidth(92)
            lay.addWidget(d)
        return tarjeta

    def _panel_senales(self) -> QWidget:
        panel = QFrame(objectName='tarjeta')
        panel.setMinimumWidth(300)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 14, 14, 10)
        cab = QHBoxLayout()
        cab.addWidget(QLabel('<b>Señales</b>'))
        self.l_cuantas = tenue('')
        self.l_cuantas.setAlignment(Qt.AlignmentFlag.AlignRight)
        cab.addWidget(self.l_cuantas)
        lay.addLayout(cab)
        self.lista = QListWidget()
        self.lista.setSpacing(0)
        self.lista.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.currentRowChanged.connect(self._desde_lista)
        self.lista.setAccessibleName('Señales encontradas')
        lay.addWidget(self.lista, 1)
        self.hist = Histograma()
        lay.addWidget(self.hist)
        return panel

    def _acciones(self):
        for tecla, fn in ((QKeySequence.StandardKey.Open, self.abrir), (QKeySequence('Ctrl+E'), self.exportar_png),
                          (QKeySequence('Ctrl+Shift+E'), self.exportar_csv)):
            a = QAction(self)
            a.setShortcut(tecla)
            a.triggered.connect(fn)
            self.addAction(a)

    # --- datos ---
    def abrir(self):
        carpeta = self.ajustes.value('carpeta', str(Path.home()))
        ruta, _ = QFileDialog.getOpenFileName(self, 'Abrir mediciones', carpeta, 'Mediciones (*.csv *.txt *.xlsx *.xlsm)')
        if ruta:
            self.ajustes.setValue('carpeta', str(Path(ruta).parent))
            self.cargar_ruta(ruta)

    def cargar_ruta(self, ruta: str):
        try:
            t = leer_archivo(ruta)
        except Exception as e:  # un archivo dañado no debe tumbar la app
            QMessageBox.warning(self, 'No se pudo abrir', f'{Path(ruta).name}: {e}')
            return
        if not columnas_numericas(t):
            QMessageBox.information(self, 'Sin mediciones', f'{t.nombre} no trae ninguna columna con números.')
            return
        self.cargar(t)

    def cargar_ejemplo(self):
        self.cargar(leer_texto(csv_ejemplo(), 'ejemplo · diámetro de buje'), ejemplo=True)

    def cargar(self, t: Tabla, ejemplo: bool = False):
        self.tabla = t
        medida, grupo = sugerir(t)
        nums = columnas_numericas(t)
        widgets = (self.c_medida, self.c_grupo, self.s_lie, self.s_lse, self.s_base, self.k_lie, self.k_lse)
        for w in widgets:
            w.blockSignals(True)
        self.c_medida.clear()
        for i in nums:
            self.c_medida.addItem(t.columnas[i], i)
        self.c_medida.setCurrentIndex(max(0, nums.index(medida)) if medida in nums else 0)
        self.c_grupo.clear()
        self.c_grupo.addItem(SIN_GRUPO, None)
        for i, nombre in enumerate(t.columnas):
            self.c_grupo.addItem(nombre, i)
        self.c_grupo.setCurrentIndex(0 if grupo is None else grupo + 1)
        if ejemplo:
            self.k_lie.setChecked(True)
            self.k_lse.setChecked(True)
            self.s_lie.setValue(EJEMPLO['lie'])
            self.s_lse.setValue(EJEMPLO['lse'])
            self.s_base.setValue(EJEMPLO['base'])
        else:
            self.k_lie.setChecked(False)
            self.k_lse.setChecked(False)
            self.s_base.setValue(0)
        for w in widgets:
            w.blockSignals(False)
        self.l_archivo.setText(f'{t.nombre} · {len(t.filas)} filas')
        self.recalcular()

    def recalcular(self):
        if not self.tabla or self.c_medida.currentData() is None:
            return
        medida, grupo = self.c_medida.currentData(), self.c_grupo.currentData()
        gs = grupos(self.tabla, medida, grupo)
        todos = [v for _, vs in gs for v in vs]
        dec = min(4, max((len(str(v).split('.')[1]) if '.' in str(v) else 0) for v in todos[:200])) if todos else 3
        base = self.s_base.value() or None
        g = construir(gs, base)
        self.grafica = g
        if g is None:
            self.l_veredicto.setText('Hacen falta al menos 5 mediciones.')
            for w in (self.g_valor, self.g_rango):
                w.poner(None)
            self.lista.clear()
            return
        lie = self.s_lie.value() if self.k_lie.isChecked() else None
        lse = self.s_lse.value() if self.k_lse.isChecked() else None
        cap = capacidad(g, todos, lie, lse)
        ver = veredicto(g, cap)
        # Si se agrupa por una columna con un valor distinto en cada fila, no hay subgrupos: avisarlo.
        modo = f'X̄-R · subgrupos de {g.n} piezas' if g.modo == 'Xbar-R' else 'Individuales y rango móvil (I-MR)'
        self.l_modo.setText(f'{modo} · {g.cuenta} mediciones · {len(g.puntos)} puntos')
        self.l_veredicto.setText(ver.texto)
        color = tema.BIEN if ver.control and ver.capaz in ('si', None) else tema.MAL if ver.capaz == 'no' else tema.AVISO
        self.l_veredicto.setStyleSheet(f'color: {color}')
        self.tarjeta.setStyleSheet(f'#tarjeta {{ border-left: 4px solid {color}; }}')
        cp_col = lambda v: tema.TENUE if not math.isfinite(v) else tema.BIEN if v >= 1.33 else tema.AVISO if v >= 1 else tema.MAL
        if cap:
            self.d_cp.poner(fmt(cap.cp, 2), cp_col(cap.cp))
            self.d_cpk.poner(fmt(cap.cpk, 2), cp_col(cap.cpk))
            self.d_ppk.poner(fmt(cap.ppk, 2), cp_col(cap.ppk))
            self.d_fuera.poner(f'{cap.fuera}', tema.MAL if cap.fuera else tema.BIEN)
        else:
            for d in (self.d_cp, self.d_cpk, self.d_ppk, self.d_fuera):
                d.poner('—', tema.TENUE)
        self.g_valor.poner(g, dec)
        self.g_rango.poner(g, dec)
        self.hist.poner(todos, lie, lse, dec)
        self._llenar_senales(g)
        for b in (self.b_png, self.b_csv):
            b.setEnabled(True)
        self.statusBar().showMessage(f'{self.tabla.nombre}: límites con {g.base} de {len(g.puntos)} puntos. '
                                     'Clic en un punto o en una señal para revisarla; flechas para moverte.')

    def senales(self):
        g = self.grafica
        out = []
        for i, p in enumerate(g.puntos):
            for r in p.reglas:
                out.append((i, p.etiqueta, f'Regla {r}', REGLAS[r], SIGNIFICA[r]))
            if i in g.rango_fuera:
                out.append((i, p.etiqueta, 'Rango', 'La variación dentro de la muestra se sale de su límite',
                            'Algo hizo que las piezas de ese momento salieran dispares: sujeción, material o medición.'))
        return out

    def _llenar_senales(self, g):
        self.lista.blockSignals(True)
        self.lista.clear()
        s = self.senales()
        puntos = len({i for i, *_ in s})
        self.l_cuantas.setText(f"{puntos} {'punto' if puntos == 1 else 'puntos'} · {len(s)} {'regla' if len(s) == 1 else 'reglas'}" if s else 'ninguna')
        if not s:
            item = QListWidgetItem(self.lista)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            w = self._tarjeta_senal('Todo en orden', 'Ningún punto rompe las reglas.',
                                    'Sigue midiendo con los mismos límites; si cambias herramienta o material, recalcúlalos.', tema.BIEN)
            item.setSizeHint(w.sizeHint())
            self.lista.setItemWidget(item, w)
        # Una tarjeta por punto: si rompe varias reglas se juntan, y lo que revisar es lo de la regla más grave.
        por_punto: dict[int, list] = {}
        for fila in s:
            por_punto.setdefault(fila[0], []).append(fila)
        quien = 'Muestra' if g.modo == 'Xbar-R' else 'Medición'
        for i, filas in por_punto.items():
            item = QListWidgetItem(self.lista)
            item.setData(Qt.ItemDataRole.UserRole, i)
            reglas = ', '.join(f[2].replace('Regla ', '') if f[2].startswith('Regla') else f[2].lower() for f in filas)
            titulo = f"{quien} {filas[0][1]} · {'regla' if len(filas) == 1 and filas[0][2].startswith('Regla') else 'reglas' if filas[0][2].startswith('Regla') else ''} {reglas}".replace('  ', ' ')
            w = self._tarjeta_senal(titulo, chr(10).join(f[3] for f in filas), filas[0][4], tema.MAL)
            item.setSizeHint(w.sizeHint())
            self.lista.setItemWidget(item, w)
        self.lista.blockSignals(False)

    def _tarjeta_senal(self, titulo: str, que: str, significa: str, color: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 9, 12, 10)
        lay.setSpacing(3)
        t = QLabel(f'<span style="color:{color}">●</span>&nbsp; <b>{titulo}</b>')
        q = QLabel(que)
        q.setWordWrap(True)
        s = tenue(significa)
        for x in (t, q, s):
            lay.addWidget(x)
        ancho = max(240, self.lista.viewport().width() - 4)
        w.setFixedWidth(ancho)
        # Con texto que se parte en renglones, la altura depende del ancho: se le pregunta al layout.
        w.setFixedHeight(lay.totalHeightForWidth(ancho))
        return w

    # --- selección compartida ---
    def elegir(self, i: int):
        for g in (self.g_valor, self.g_rango):
            g.seleccionar(i)
        self.lista.blockSignals(True)
        fila = next((k for k in range(self.lista.count()) if self.lista.item(k).data(Qt.ItemDataRole.UserRole) == i), -1)
        self.lista.setCurrentRow(fila)
        if fila >= 0:
            self.lista.scrollToItem(self.lista.item(fila))
        self.lista.blockSignals(False)
        p = self.grafica.puntos[i]
        self.statusBar().showMessage(f'{p.etiqueta}: {fmt(p.valor, self.g_valor.dec)}'
                                     + (f' · rango {fmt(p.rango, self.g_valor.dec)}' if p.rango is not None else ''))

    def _desde_lista(self, fila: int):
        if fila >= 0:
            i = self.lista.item(fila).data(Qt.ItemDataRole.UserRole)
            if i is not None:
                self.elegir(i)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.grafica:
            QTimer.singleShot(0, lambda: self._llenar_senales(self.grafica))

    # --- exportar ---
    def exportar_png(self):
        if not self.grafica:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar reporte', str(Path(self.ajustes.value('carpeta', str(Path.home()))) / 'reporte-spc.png'), 'Imagen (*.png)')
        if ruta:
            self.centralWidget().grab().save(ruta)
            self.statusBar().showMessage(f'Reporte guardado en {ruta}')

    def exportar_csv(self):
        if not self.grafica:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar señales', str(Path(self.ajustes.value('carpeta', str(Path.home()))) / 'senales-spc.csv'), 'CSV (*.csv)')
        if ruta:
            with open(ruta, 'w', newline='', encoding='utf-8-sig') as f:
                w = csv.writer(f)
                w.writerow(['punto', 'valor', 'rango', 'señal', 'qué pasa', 'qué revisar'])
                for i, etiqueta, regla, que, significa in self.senales():
                    p = self.grafica.puntos[i]
                    w.writerow([etiqueta, p.valor, '' if p.rango is None else p.rango, regla, que, significa])
            self.statusBar().showMessage(f'Señales guardadas en {ruta}')

    # --- arrastrar y soltar ---
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.cargar_ruta(urls[0])

    def closeEvent(self, e):
        self.ajustes.setValue('tamano', self.size())
        super().closeEvent(e)
