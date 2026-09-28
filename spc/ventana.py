"""La ventana: datos a la izquierda, veredicto arriba, la vista que elijas al centro y los apartados a la derecha."""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSettings, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QAction, QKeySequence, QPainter
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
                               QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox, QSplitter, QStackedWidget,
                               QVBoxLayout, QWidget)

from . import tema
from .datos import Tabla, columnas_numericas, grupos, leer_archivo, leer_texto, sugerir
from .graficas import Cajas, GraficaControl, Histograma, Tendencia, fmt
from .logica import (EJEMPLO, REGLAS, REGLAS_CORTO, REVISAR, SIGNIFICA, capacidad, construir, csv_ejemplo, regla_principal,
                     resumen, veredicto)

SIN_GRUPO = 'Sin subgrupo · cada fila es un punto'
VISTAS = ['Control', 'Tendencia', 'Cajas', 'Reparto']
APARTADOS = ['Señales', 'Punto', 'Capacidad', 'Guía']


def seccion(texto: str) -> QLabel:
    lbl = QLabel(texto.upper())
    lbl.setObjectName('seccion')
    return lbl


def tenue(texto: str) -> QLabel:
    lbl = QLabel(texto)
    lbl.setProperty('tenue', True)
    lbl.setWordWrap(True)
    return lbl


def texto(t: str, nombre: str = '') -> QLabel:
    lbl = QLabel(t)
    lbl.setWordWrap(True)
    if nombre:
        lbl.setObjectName(nombre)
    return lbl


def fundido(w: QWidget, ms: int = 260):
    """Aparece suave: para cambiar de vista o de veredicto sin saltos."""
    ef = QGraphicsOpacityEffect(w)
    w.setGraphicsEffect(ef)
    an = QPropertyAnimation(ef, b'opacity', w)
    an.setDuration(ms)
    an.setStartValue(0.0)
    an.setEndValue(1.0)
    an.setEasingCurve(QEasingCurve.Type.OutCubic)
    an.finished.connect(lambda: w.setGraphicsEffect(None))
    an.start()


def normal_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


class Segmentos(QFrame):
    """Botones de pestaña en una sola pieza: Control · Tendencia · …"""

    cambiado = Signal(int)

    def __init__(self, nombres: list[str]):
        super().__init__(objectName='segmentos')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.grupo = QButtonGroup(self)
        self.botones = []
        for i, n in enumerate(nombres):
            b = QPushButton(n)
            b.setProperty('segmento', True)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.grupo.addButton(b, i)
            self.botones.append(b)
            lay.addWidget(b)
        self.botones[0].setChecked(True)
        self.grupo.idClicked.connect(self.cambiado)

    def poner(self, i: int):
        self.botones[i].setChecked(True)
        self.cambiado.emit(i)

    def actual(self) -> int:
        return self.grupo.checkedId()


class Dato(QFrame):
    """Un número con su nombre debajo: Cp, Cpk, piezas fuera…"""

    def __init__(self, nombre: str, ayuda: str):
        super().__init__(objectName='dato')
        self.setToolTip(ayuda)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(0)
        self.valor = QLabel('—', objectName='datoValor')
        lay.addWidget(self.valor)
        lay.addWidget(QLabel(nombre, objectName='datoNombre'))

    def poner(self, t: str, color: str = tema.TEXTO):
        self.valor.setText(t)
        self.valor.setStyleSheet(f'color: {color}')


class Barra(QWidget):
    """Cp o Cpk como barra de 0 a 2, con marcas en 1 (justo) y 1.33 (holgado). Crece al aparecer."""

    def __init__(self, valor: float):
        super().__init__()
        self.valor, self._t = valor, 0.0
        self.setFixedHeight(14)
        an = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=700)
        an.setEasingCurve(QEasingCurve.Type.OutCubic)
        an.valueChanged.connect(lambda v: (setattr(self, '_t', float(v)), self.update()))
        an.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0, 3, 0, -3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tema.c(tema.PANEL_2))
        p.drawRoundedRect(r, 4, 4)
        v = self.valor if math.isfinite(self.valor) else 0
        col = tema.BIEN if v >= 1.33 else tema.AVISO if v >= 1 else tema.MAL
        p.setBrush(tema.c(col, 200))
        p.drawRoundedRect(QRectF(r.left(), r.top(), r.width() * max(0.0, min(1.0, v / 2)) * self._t, r.height()), 4, 4)
        p.setPen(tema.c(tema.TEXTO, 120))
        for m in (1, 1.33):
            x = r.left() + r.width() * m / 2
            p.drawLine(int(x), int(r.top() - 3), int(x), int(r.bottom() + 3))


class Ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Gráficas de control')
        self.setAcceptDrops(True)
        self.tabla: Tabla | None = None
        self.grafica = None
        self.gs: list[tuple[str, list[float]]] = []
        self.cap = None
        # Pruebas y capturas usan un .ini aparte para no tocar los ajustes de quien usa la app.
        ini = os.environ.get('SPC_AJUSTES')
        self.ajustes = QSettings(ini, QSettings.Format.IniFormat) if ini else QSettings('Brunich', 'GraficasDeControl')
        self._construir()
        self._acciones()
        self.resize(self.ajustes.value('tamano', QSize(1400, 860)))
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
        partir.setHandleWidth(14)
        partir.addWidget(self._vistas())
        partir.addWidget(self._apartados())
        partir.setSizes([900, 380])
        partir.setStretchFactor(0, 1)
        centro.addWidget(partir, 1)
        fila.addLayout(centro, 1)

    def _lateral(self) -> QWidget:
        lat = QFrame(objectName='lateral')
        lat.setFixedWidth(290)
        lay = QVBoxLayout(lat)
        lay.setContentsMargins(20, 22, 20, 18)
        lay.setSpacing(8)
        lay.addWidget(texto('Gráficas de control', 'titulo'))
        lay.addWidget(tenue('Saber si la máquina se desajusta antes de que salga pieza mala.'))

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
        lay.addWidget(tenue('Con cuántas muestras calcularlos (un periodo estable). 0 = todas.'))
        self.s_base = QSpinBox()
        self.s_base.setRange(0, 100000)
        self.s_base.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.s_base.setKeyboardTracking(False)
        lay.addWidget(self.s_base)

        lay.addStretch(1)
        self.b_png = QPushButton('Exportar reporte (PNG)   Ctrl+E')
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
        self.tarjeta = QFrame(objectName='tarjeta')
        lay = QHBoxLayout(self.tarjeta)
        lay.setContentsMargins(20, 14, 16, 14)
        lay.setSpacing(12)
        self.caja_txt = QWidget()
        txt = QVBoxLayout(self.caja_txt)
        txt.setContentsMargins(0, 0, 0, 0)
        txt.setSpacing(2)
        self.l_modo = tenue('')
        self.l_titulo = texto('Sin datos todavía', 'vTitulo')
        self.l_detalle = texto('Abre un archivo o usa el ejemplo.', 'vDetalle')
        self.l_resumen = texto('')
        self.l_resumen.setStyleSheet(f'color: {tema.ACENTO}')
        for w in (self.l_modo, self.l_titulo, self.l_detalle, self.l_resumen):
            txt.addWidget(w)
        lay.addWidget(self.caja_txt, 1)
        self.d_cp = Dato('Cp', 'Cuánto cabe la variación en la tolerancia. 1.33 o más es holgado.')
        self.d_cpk = Dato('Cpk', 'Como Cp, pero castiga si el proceso está corrido hacia un lado.')
        self.d_ppk = Dato('Ppk', 'Con toda la variación, no sólo la de corto plazo.')
        self.d_fuera = Dato('piezas fuera', 'Mediciones que ya salieron de la tolerancia.')
        for d in (self.d_cp, self.d_cpk, self.d_ppk, self.d_fuera):
            d.setMinimumWidth(92)
            lay.addWidget(d)
        return self.tarjeta

    def _vistas(self) -> QWidget:
        tarjeta = QFrame(objectName='tarjeta')
        lay = QVBoxLayout(tarjeta)
        lay.setContentsMargins(12, 12, 12, 10)
        cab = QHBoxLayout()
        self.seg_vista = Segmentos(VISTAS)
        cab.addWidget(self.seg_vista)
        cab.addStretch(1)
        self.l_pista = tenue('')
        self.l_pista.setWordWrap(False)
        cab.addWidget(self.l_pista)
        lay.addLayout(cab)

        self.pila = QStackedWidget()
        control = QSplitter(Qt.Orientation.Vertical)
        control.setHandleWidth(10)
        self.g_valor, self.g_rango = GraficaControl('valor'), GraficaControl('rango')
        control.addWidget(self.g_valor)
        control.addWidget(self.g_rango)
        control.setSizes([600, 380])
        self.g_tendencia, self.g_cajas, self.g_reparto = Tendencia(), Cajas(), Histograma()
        for w in (control, self.g_tendencia, self.g_cajas, self.g_reparto):
            self.pila.addWidget(w)
        for g in (self.g_valor, self.g_rango, self.g_tendencia, self.g_cajas):
            g.elegido.connect(lambda i: self.elegir(i, abrir_punto=True))
        lay.addWidget(self.pila, 1)
        self.seg_vista.cambiado.connect(self._cambiar_vista)
        self._pistas = {
            0: 'Arriba el centro del proceso, abajo cuánto varían las piezas.',
            1: 'Cada punto es una pieza; la línea lavanda, el promedio de su muestra.',
            2: 'La caja guarda la mitad de las piezas de cada muestra.',
            3: 'Si la campana cabe entre las líneas arena, el proceso cumple.',
        }
        return tarjeta

    def _apartados(self) -> QWidget:
        panel = QFrame(objectName='tarjeta')
        panel.setMinimumWidth(330)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        self.seg_apartado = Segmentos(APARTADOS)
        lay.addWidget(self.seg_apartado)
        self.pila_der = QStackedWidget()

        senales = QWidget()
        sl = QVBoxLayout(senales)
        sl.setContentsMargins(0, 0, 0, 0)
        self.l_cuantas = tenue('')
        sl.addWidget(self.l_cuantas)
        self.lista = QListWidget()
        self.lista.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.currentRowChanged.connect(self._desde_lista)
        self.lista.itemDoubleClicked.connect(lambda _: self.seg_apartado.poner(1))
        self.lista.setAccessibleName('Señales encontradas')
        sl.addWidget(self.lista, 1)
        self.pila_der.addWidget(senales)

        self.cuerpo_punto, self.cuerpo_cap, cuerpo_guia = QVBoxLayout(), QVBoxLayout(), QVBoxLayout()
        for cuerpo in (self.cuerpo_punto, self.cuerpo_cap, cuerpo_guia):
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            dentro = QWidget()
            dentro.setLayout(cuerpo)
            cuerpo.setContentsMargins(2, 2, 6, 2)
            cuerpo.setSpacing(10)
            area.setWidget(dentro)
            self.pila_der.addWidget(area)
        self._guia(cuerpo_guia)
        self._vacio(self.cuerpo_punto, 'Elige un punto en la gráfica o una señal de la lista.')
        self._vacio(self.cuerpo_cap, 'Pon la tolerancia en el panel izquierdo para ver si el proceso cumple.')
        lay.addWidget(self.pila_der, 1)
        self.seg_apartado.cambiado.connect(self._cambiar_apartado)
        return panel

    def _acciones(self):
        for tecla, fn in ((QKeySequence.StandardKey.Open, self.abrir), (QKeySequence('Ctrl+E'), self.exportar_png),
                          (QKeySequence('Ctrl+Shift+E'), self.exportar_csv)):
            a = QAction(self)
            a.setShortcut(tecla)
            a.triggered.connect(fn)
            self.addAction(a)
        for k in range(4):
            a = QAction(self)
            a.setShortcut(QKeySequence(f'Ctrl+{k + 1}'))
            a.triggered.connect(lambda _=False, k=k: self.seg_vista.poner(k))
            self.addAction(a)

    # --- apartados de texto ---
    @staticmethod
    def _limpiar(cuerpo: QVBoxLayout):
        while cuerpo.count():
            it = cuerpo.takeAt(0)
            w = it.widget()
            if w:
                # Se esconde ya: deleteLater llega hasta la siguiente vuelta y se encimaría con lo nuevo.
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _vacio(self, cuerpo: QVBoxLayout, t: str):
        self._limpiar(cuerpo)
        cuerpo.addWidget(tenue(t))
        cuerpo.addStretch(1)

    def _bloque(self, titulo: str, *filas: QWidget) -> QFrame:
        b = QFrame(objectName='bloque')
        lay = QVBoxLayout(b)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(4)
        lay.addWidget(seccion(titulo))
        for f in filas:
            lay.addWidget(f)
        return b

    def _guia(self, cuerpo: QVBoxLayout):
        cuerpo.addWidget(self._bloque('Cómo leerla',
                                      texto('La línea lavanda es el centro del proceso; las rosas, hasta dónde varía solo.'),
                                      texto('Un punto marcado es una señal: algo cambió. No siempre es pieza mala.'),
                                      texto('Las líneas arena son la tolerancia del cliente. Son otra cosa.')))
        reglas = [texto(f'<b>{r}. {REGLAS_CORTO[r]}</b><br><span style="color:{tema.TENUE}">Revisa {REVISAR[r]}.</span>') for r in REGLAS]
        cuerpo.addWidget(self._bloque('Las cinco reglas', *reglas))
        cuerpo.addWidget(self._bloque('Cp y Cpk',
                                      texto('<b>Cp</b>: si la variación cabe en la tolerancia.'),
                                      texto('<b>Cpk</b>: lo mismo, contando si está corrido a un lado.'),
                                      texto(f'<span style="color:{tema.TENUE}">1.33 o más: holgado · 1 a 1.33: justo · menos de 1: saldrá pieza mala.</span>')))
        cuerpo.addWidget(self._bloque('Atajos', tenue('Ctrl+O abrir · Ctrl+1…4 vistas · ← → moverte entre puntos · Ctrl+E exportar')))
        cuerpo.addStretch(1)

    def _llenar_punto(self, i: int):
        self._limpiar(self.cuerpo_punto)
        g, dec = self.grafica, self.g_valor.dec
        pt = g.puntos[i]
        quien = 'Muestra' if g.modo == 'Xbar-R' else 'Medición'
        extra = self._otras_columnas(pt.etiqueta)
        self.cuerpo_punto.addWidget(texto(f'{quien} {pt.etiqueta}', 'grande'))
        if extra:
            self.cuerpo_punto.addWidget(tenue(extra))
        estado = (f'<span style="color:{tema.MAL}">● {len(pt.reglas)} {"regla" if len(pt.reglas) == 1 else "reglas"}</span>' if pt.reglas
                  else f'<span style="color:{tema.BIEN}">● Dentro de lo normal</span>')
        self.cuerpo_punto.addWidget(texto(estado))
        cifras = f'{"Promedio" if g.modo == "Xbar-R" else "Valor"} <b>{fmt(pt.valor, dec)}</b> · LC {fmt(g.lc, dec)}'
        if pt.rango is not None:
            cifras += f'<br>{"Rango" if g.modo == "Xbar-R" else "Rango móvil"} <b>{fmt(pt.rango, dec)}</b> · límite {fmt(g.r_lsc, dec)}'
        self.cuerpo_punto.addWidget(self._bloque('Cifras', texto(cifras)))
        if g.modo == 'Xbar-R' and i < len(self.gs):
            lie, lse = self._tolerancia()
            piezas = ' · '.join(f'<span style="color:{tema.MAL if (lse is not None and v > lse) or (lie is not None and v < lie) else tema.TEXTO}">{fmt(v, dec)}</span>'
                                for v in self.gs[i][1])
            self.cuerpo_punto.addWidget(self._bloque(f'Sus {len(self.gs[i][1])} piezas', texto(piezas)))
        for r in pt.reglas:
            self.cuerpo_punto.addWidget(self._bloque(f'Regla {r}', texto(f'<b>{REGLAS[r]}</b>'), tenue(SIGNIFICA[r])))
        if i in g.rango_fuera:
            self.cuerpo_punto.addWidget(self._bloque('Rango', texto('<b>Las piezas de esa muestra salieron dispares.</b>'),
                                                     tenue('Revisa sujeción, material o el instrumento de medición.')))
        self.cuerpo_punto.addStretch(1)

    def _llenar_capacidad(self):
        if not self.cap:
            self._vacio(self.cuerpo_cap, 'Pon la tolerancia en el panel izquierdo para ver si el proceso cumple.')
            return
        self._limpiar(self.cuerpo_cap)
        cap, g, dec = self.cap, self.grafica, self.g_valor.dec
        for nombre, v, que in (('Cp', cap.cp, 'si la variación cabe en la tolerancia'),
                               ('Cpk', cap.cpk, 'igual, contando si está corrido'),
                               ('Pp', cap.pp, 'Cp con toda la variación'),
                               ('Ppk', cap.ppk, 'Cpk con toda la variación')):
            col = tema.TENUE if not math.isfinite(v) else tema.BIEN if v >= 1.33 else tema.AVISO if v >= 1 else tema.MAL
            fila = QWidget()
            fl = QVBoxLayout(fila)
            fl.setContentsMargins(0, 0, 0, 0)
            fl.setSpacing(3)
            fl.addWidget(texto(f'<b>{nombre}</b> <span style="color:{col}; font-family:Consolas">{fmt(v, 2)}</span>'
                               f' <span style="color:{tema.TENUE}">· {que}</span>'))
            if math.isfinite(v):
                fl.addWidget(Barra(v))
            self.cuerpo_cap.addWidget(fila)
        lie, lse = self._tolerancia()
        S = g.de or g.sigma
        ppm = ((normal_cdf((lie - g.media) / S) if lie is not None else 0) + (1 - normal_cdf((lse - g.media) / S) if lse is not None else 0)) * 1e6
        self.cuerpo_cap.addWidget(self._bloque('Piezas', texto(f'<b>{cap.fuera}</b> de {g.cuenta} ya fuera de tolerancia'),
                                               tenue(f'Esperadas por millón si sigue igual: {ppm:,.0f}')))
        self.cuerpo_cap.addWidget(self._bloque('El proceso', texto(f'Media <b>{fmt(g.media, dec)}</b>'),
                                               tenue(f'Variación de corto plazo {fmt(g.sigma, dec + 1)} · total {fmt(S, dec + 1)}')))
        self.cuerpo_cap.addWidget(tenue('Marcas de la barra: 1 (justo) y 1.33 (holgado).'))
        self.cuerpo_cap.addStretch(1)

    def _otras_columnas(self, etiqueta: str) -> str:
        """Lo demás que trae la fila (hora, operador…) para ubicar la muestra en el turno."""
        if not self.tabla:
            return ''
        medida, grupo = self.c_medida.currentData(), self.c_grupo.currentData()
        if grupo is None:
            try:
                fila = [f for f in self.tabla.filas if f[medida].strip()][int(etiqueta.split('.')[0]) - 1]
            except (ValueError, IndexError):
                return ''
        else:
            fila = next((f for f in self.tabla.filas if f[grupo].strip() == etiqueta), None)
            if fila is None:
                return ''
        return ' · '.join(f'{self.tabla.columnas[k]} {fila[k]}' for k in range(len(fila)) if k not in (medida, grupo) and fila[k].strip())[:120]

    def _tolerancia(self):
        return (self.s_lie.value() if self.k_lie.isChecked() else None, self.s_lse.value() if self.k_lse.isChecked() else None)

    def _cambiar_vista(self, i: int):
        self.pila.setCurrentIndex(i)
        self.l_pista.setText(self._pistas[i])
        fundido(self.pila.currentWidget())
        for g in ((self.g_valor, self.g_rango), (self.g_tendencia,), (self.g_cajas,), (self.g_reparto,))[i]:
            g.animar()
        self.ajustes.setValue('vista', i)

    def _cambiar_apartado(self, i: int):
        self.pila_der.setCurrentIndex(i)
        fundido(self.pila_der.currentWidget(), 200)

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
        self.c_medida.setCurrentIndex(nums.index(medida) if medida in nums else 0)
        self.c_grupo.clear()
        self.c_grupo.addItem(SIN_GRUPO, None)
        for i, nombre in enumerate(t.columnas):
            self.c_grupo.addItem(nombre, i)
        self.c_grupo.setCurrentIndex(0 if grupo is None else grupo + 1)
        self.k_lie.setChecked(ejemplo)
        self.k_lse.setChecked(ejemplo)
        if ejemplo:
            self.s_lie.setValue(EJEMPLO['lie'])
            self.s_lse.setValue(EJEMPLO['lse'])
        self.s_base.setValue(EJEMPLO['base'] if ejemplo else 0)
        for w in widgets:
            w.blockSignals(False)
        self.l_archivo.setText(f'{t.nombre} · {len(t.filas)} filas')
        self.recalcular()
        fundido(self.caja_txt, 420)

    def recalcular(self):
        if not self.tabla or self.c_medida.currentData() is None:
            return
        medida, grupo = self.c_medida.currentData(), self.c_grupo.currentData()
        self.gs = grupos(self.tabla, medida, grupo)
        todos = [v for _, vs in self.gs for v in vs]
        dec = min(4, max((len(str(v).split('.')[1]) if '.' in str(v) else 0) for v in todos[:200])) if todos else 3
        g = construir(self.gs, self.s_base.value() or None)
        self.grafica = g
        if g is None:
            self.l_titulo.setText('Faltan datos')
            self.l_detalle.setText('Hacen falta al menos 5 mediciones.')
            for w in (self.g_valor, self.g_rango, self.g_tendencia, self.g_cajas, self.g_reparto):
                w.poner(None)
            self.lista.clear()
            return
        lie, lse = self._tolerancia()
        self.cap = capacidad(g, todos, lie, lse)
        ver = veredicto(g, self.cap)
        modo = f'X̄-R · muestras de {g.n} piezas' if g.modo == 'Xbar-R' else 'Individuales (I-MR)'
        self.l_modo.setText(f'{modo} · {g.cuenta} mediciones · {len(g.puntos)} puntos')
        self.l_titulo.setText(ver.titulo)
        self.l_detalle.setText(ver.detalle[:1].upper() + ver.detalle[1:])
        self.l_resumen.setText(resumen(g))
        color = tema.BIEN if ver.control and ver.capaz in ('si', None) else tema.MAL if ver.capaz == 'no' else tema.AVISO
        self.l_titulo.setStyleSheet(f'color: {color}')
        self.tarjeta.setStyleSheet(f'#tarjeta {{ border-left: 4px solid {color}; }}')
        cp_col = lambda v: tema.TENUE if not math.isfinite(v) else tema.BIEN if v >= 1.33 else tema.AVISO if v >= 1 else tema.MAL
        if self.cap:
            self.d_cp.poner(fmt(self.cap.cp, 2), cp_col(self.cap.cp))
            self.d_cpk.poner(fmt(self.cap.cpk, 2), cp_col(self.cap.cpk))
            self.d_ppk.poner(fmt(self.cap.ppk, 2), cp_col(self.cap.ppk))
            self.d_fuera.poner(f'{self.cap.fuera}', tema.MAL if self.cap.fuera else tema.BIEN)
        else:
            for d in (self.d_cp, self.d_cpk, self.d_ppk, self.d_fuera):
                d.poner('—', tema.TENUE)
        for w in (self.g_valor, self.g_rango, self.g_tendencia, self.g_cajas, self.g_reparto):
            w.poner(g, self.gs, lie, lse, dec)
        # Las cajas por muestra sólo tienen sentido con subgrupos.
        self.seg_vista.botones[2].setEnabled(g.modo == 'Xbar-R')
        if g.modo != 'Xbar-R' and self.seg_vista.actual() == 2:
            self.seg_vista.poner(0)
        self._llenar_senales(g)
        self._llenar_capacidad()
        self._vacio(self.cuerpo_punto, 'Elige un punto en la gráfica o una señal de la lista.')
        for b in (self.b_png, self.b_csv):
            b.setEnabled(True)
        self.statusBar().showMessage(f'{self.tabla.nombre}: límites con {g.base} de {len(g.puntos)} puntos. '
                                     'Clic en un punto para ver su detalle; flechas para moverte.')

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
        por_punto: dict[int, list] = {}
        for fila in s:
            por_punto.setdefault(fila[0], []).append(fila)
        self.l_cuantas.setText(f'{len(por_punto)} {"punto" if len(por_punto) == 1 else "puntos"} con señal · doble clic para el detalle'
                               if s else 'Ninguna señal')
        if not s:
            item = QListWidgetItem(self.lista)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._poner_tarjeta(item, 'Todo en orden', '', 'Ningún punto rompe las reglas', 'sigue con los mismos límites', tema.BIEN)
        quien = 'Muestra' if g.modo == 'Xbar-R' else 'Medición'
        for i, filas in por_punto.items():
            item = QListWidgetItem(self.lista)
            item.setData(Qt.ItemDataRole.UserRole, i)
            reglas = [int(f[2].split()[1]) for f in filas if f[2].startswith('Regla')]
            grave = regla_principal(reglas)
            que = REGLAS_CORTO[grave] if grave else 'Piezas dispares'
            revisa = REVISAR[grave] if grave else 'sujeción, material o medición'
            cuantas = f'{len(filas)} reglas' if len(filas) > 1 else ''
            self._poner_tarjeta(item, f'{quien} {filas[0][1]}', cuantas, que, revisa, tema.MAL)
        self.lista.blockSignals(False)

    def _poner_tarjeta(self, item: QListWidgetItem, titulo: str, derecha: str, que: str, revisa: str, color: str):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 9)
        lay.setSpacing(2)
        cab = QHBoxLayout()
        cab.addWidget(QLabel(f'<b>{titulo}</b>'))
        cab.addStretch(1)
        d = tenue(derecha)
        d.setWordWrap(False)
        cab.addWidget(d)
        lay.addLayout(cab)
        lay.addWidget(texto(f'<span style="color:{color}">●</span>&nbsp; {que}'))
        lay.addWidget(tenue(f'Revisa {revisa}.'))
        ancho = max(260, self.lista.viewport().width() - 4)
        w.setFixedWidth(ancho)
        # Con texto que se parte en renglones, la altura depende del ancho: se le pregunta al layout.
        w.setFixedHeight(lay.totalHeightForWidth(ancho))
        item.setSizeHint(w.size())
        self.lista.setItemWidget(item, w)

    # --- selección compartida ---
    def elegir(self, i: int, abrir_punto: bool = False):
        for g in (self.g_valor, self.g_rango, self.g_tendencia, self.g_cajas):
            g.seleccionar(i)
        self.lista.blockSignals(True)
        fila = next((k for k in range(self.lista.count()) if self.lista.item(k).data(Qt.ItemDataRole.UserRole) == i), -1)
        self.lista.setCurrentRow(fila)
        if fila >= 0:
            self.lista.scrollToItem(self.lista.item(fila))
        self.lista.blockSignals(False)
        self._llenar_punto(i)
        if abrir_punto and self.seg_apartado.actual() != 1:
            self.seg_apartado.poner(1)
        p = self.grafica.puntos[i]
        self.statusBar().showMessage(f'{p.etiqueta}: {fmt(p.valor, self.g_valor.dec)}'
                                     + (f' · rango {fmt(p.rango, self.g_valor.dec)}' if p.rango is not None else ''))

    def _desde_lista(self, fila: int):
        if fila >= 0:
            i = self.lista.item(fila).data(Qt.ItemDataRole.UserRole)
            if i is not None:
                self.elegir(i)

    def showEvent(self, e):
        super().showEvent(e)
        self.seg_vista.poner(int(self.ajustes.value('vista', 0)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.grafica:
            QTimer.singleShot(0, lambda: self._llenar_senales(self.grafica))

    # --- exportar ---
    def exportar_png(self):
        if not self.grafica:
            return
        base = Path(self.ajustes.value('carpeta', str(Path.home())))
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar reporte', str(base / 'reporte-spc.png'), 'Imagen (*.png)')
        if ruta:
            self.centralWidget().grab().save(ruta)
            self.statusBar().showMessage(f'Reporte guardado en {ruta}')

    def exportar_csv(self):
        if not self.grafica:
            return
        base = Path(self.ajustes.value('carpeta', str(Path.home())))
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar señales', str(base / 'senales-spc.csv'), 'CSV (*.csv)')
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
