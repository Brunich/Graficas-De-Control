"""Las gráficas, dibujadas a mano con QPainter: así se controla cada línea, cada zona y cada punto marcado.

Cuatro vistas del mismo proceso, para quien las lea: control (X̄ y R), tendencia pieza por pieza,
reparto contra la tolerancia y cajas por muestra. Todas comparten el punto elegido y entran animadas."""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from . import tema
from .logica import REGLAS_CORTO, Grafica


def fmt(v: float | None, dec: int = 3) -> str:
    return '—' if v is None or not math.isfinite(v) else f'{v:.{dec}f}'


def cuartiles(v: list[float]) -> tuple[float, float, float]:
    s = sorted(v)

    def q(p: float) -> float:
        k = (len(s) - 1) * p
        a, b = math.floor(k), math.ceil(k)
        return s[a] + (s[b] - s[a]) * (k - a)

    return q(0.25), q(0.5), q(0.75)


class Lienzo(QWidget):
    """Lo común a las cuatro vistas: animación de entrada, franja del punto elegido y márgenes."""

    elegido = Signal(int)
    MARGEN = dict(izq=64, der=78, arr=40, aba=30)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.g: Grafica | None = None
        self.gs: list[tuple[str, list[float]]] = []
        self.lie = self.lse = None
        self.dec = 3
        self.sel = -1
        self.sobre = -1
        self._t = 1.0
        self._banda = -1.0
        self.setMouseTracking(True)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._entrada = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=800)
        self._entrada.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._entrada.valueChanged.connect(self._paso)
        self._mover = QVariantAnimation(self, duration=240)
        self._mover.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._mover.valueChanged.connect(self._paso_banda)

    def _paso(self, v):
        self._t = float(v)
        self.update()

    def _paso_banda(self, v):
        self._banda = float(v)
        self.update()

    def poner(self, g: Grafica | None, gs=None, lie=None, lse=None, dec: int = 3):
        self.g, self.gs, self.lie, self.lse, self.dec = g, gs or [], lie, lse, dec
        self.sel, self.sobre, self._banda = -1, -1, -1.0
        self.setAccessibleName(self.titulo())
        self.animar()

    def animar(self):
        self._entrada.stop()
        self._t = 0.0
        self._entrada.start()

    def seleccionar(self, i: int):
        self.sel = i
        self._mover.stop()
        if self._banda < 0 or i < 0:
            self._banda = float(i)
            self.update()
        else:
            self._mover.setStartValue(self._banda)
            self._mover.setEndValue(float(i))
            self._mover.start()

    def titulo(self) -> str:
        return ''

    def n(self) -> int:
        return len(self.g.puntos) if self.g else 0

    # --- geometría ---
    def area(self) -> QRectF:
        m = self.MARGEN
        return QRectF(m['izq'], m['arr'], self.width() - m['izq'] - m['der'], self.height() - m['arr'] - m['aba'])

    def x(self, i: float) -> float:
        a = self.area()
        return a.left() + a.width() * (i + 0.5) / max(1, self.n())

    def indice_en(self, px: float) -> int:
        a = self.area()
        if not self.g or not (a.left() - 8 <= px <= a.right() + 8):
            return -1
        return max(0, min(self.n() - 1, int((px - a.left()) / a.width() * self.n())))

    # --- piezas de dibujo ---
    def fuente(self, pt: float, negrita: bool = False) -> QFont:
        f = QFont(self.font())
        f.setPointSizeF(pt)
        f.setBold(negrita)
        return f

    def fondo(self, p: QPainter) -> bool:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), tema.c(tema.PANEL))
        if not self.g:
            p.setPen(tema.c(tema.TENUE))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Abre un archivo o usa el ejemplo')
            return False
        a = self.area()
        p.setFont(self.fuente(10.5, True))
        p.setPen(tema.c(tema.TEXTO))
        p.drawText(QRectF(a.left(), 8, a.width(), 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.titulo())
        return True

    def banda(self, p: QPainter):
        a, w = self.area(), self.area().width() / max(1, self.n())
        if 0 <= self.sobre < self.n():
            p.fillRect(QRectF(self.x(self.sobre) - w / 2, a.top(), w, a.height()), tema.c(tema.ACENTO, 18))
        if self._banda >= 0:
            grad = QLinearGradient(0, a.top(), 0, a.bottom())
            grad.setColorAt(0, tema.c(tema.ACENTO, 10))
            grad.setColorAt(0.5, tema.c(tema.ACENTO, 46))
            grad.setColorAt(1, tema.c(tema.ACENTO, 10))
            p.fillRect(QRectF(self.x(self._banda) - w / 2, a.top(), w, a.height()), grad)

    def linea_h(self, p: QPainter, y: float, nombre: str, valor: float, color: str, estilo=Qt.PenStyle.DashLine, ancho=1.2):
        a = self.area()
        alfa = int(220 * min(1.0, self._t * 1.6))
        p.setPen(QPen(tema.c(color, alfa), ancho, estilo))
        p.drawLine(QPointF(a.left(), y), QPointF(a.right(), y))
        p.setFont(self.fuente(8))
        p.setPen(tema.c(color, alfa))
        p.drawText(QRectF(a.right() + 6, y - 9, 76, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f'{nombre} {fmt(valor, self.dec)}')

    def eje_y(self, p: QPainter, lo: float, hi: float, y):
        a = self.area()
        p.setFont(self.fuente(8))
        p.setPen(tema.c(tema.TENUE))
        for v in (lo, (lo + hi) / 2, hi):
            p.drawText(QRectF(0, y(v) - 9, a.left() - 8, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt(v, self.dec))

    def eje_x(self, p: QPainter):
        a = self.area()
        p.setFont(self.fuente(8))
        p.setPen(tema.c(tema.TENUE))
        paso = max(1, math.ceil(self.n() / max(1, a.width() / 46)))
        for i in range(0, self.n(), paso):
            p.drawText(QRectF(self.x(i) - 23, a.bottom() + 6, 46, 18), Qt.AlignmentFlag.AlignCenter, self.g.puntos[i].etiqueta)

    def marco_foco(self, p: QPainter):
        if self.hasFocus():
            p.setPen(QPen(tema.c(tema.ACENTO, 110), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)

    # --- interacción ---
    def mouseMoveEvent(self, e):
        i = self.indice_en(e.position().x())
        if i != self.sobre:
            self.sobre = i
            self.update()
        texto = self.texto_punto(i) if i >= 0 else ''
        QToolTip.showText(e.globalPosition().toPoint(), texto, self) if texto else QToolTip.hideText()

    def leaveEvent(self, _):
        self.sobre = -1
        self.update()

    def mousePressEvent(self, e):
        i = self.indice_en(e.position().x())
        if i >= 0:
            self.elegido.emit(i)

    def keyPressEvent(self, e):
        if self.g and e.key() in (Qt.Key.Key_Right, Qt.Key.Key_Left):
            d = 1 if e.key() == Qt.Key.Key_Right else -1
            self.elegido.emit(max(0, min(self.n() - 1, (self.sel if self.sel >= 0 else -d) + d)))
        else:
            super().keyPressEvent(e)

    def texto_punto(self, i: int) -> str:
        pt = self.g.puntos[i]
        filas = [f'<b>{"Muestra" if self.g.modo == "Xbar-R" else "Medición"} {pt.etiqueta}</b>',
                 f'{fmt(pt.valor, self.dec)}' + (f' · rango {fmt(pt.rango, self.dec)}' if pt.rango is not None else '')]
        filas += [f'<span style="color:{tema.MAL}">{REGLAS_CORTO[r]}</span>' for r in pt.reglas]
        return '<br>'.join(filas)


class GraficaControl(Lienzo):
    """Promedios (o individuales) o rangos, con límites, zonas y señales."""

    def __init__(self, tipo: str, parent=None):
        super().__init__(parent)
        self.tipo = tipo  # 'valor' o 'rango'

    def titulo(self) -> str:
        if not self.g:
            return ''
        if self.tipo == 'valor':
            return 'Promedio de cada muestra (X̄)' if self.g.modo == 'Xbar-R' else 'Cada medición (I)'
        return 'Rango de cada muestra (R)' if self.g.modo == 'Xbar-R' else 'Rango móvil (MR)'

    def serie(self) -> list[float | None]:
        return [p.valor if self.tipo == 'valor' else p.rango for p in self.g.puntos]

    def limites(self):
        g = self.g
        return (g.lc, g.lsc, g.lic) if self.tipo == 'valor' else (g.r_lc, g.r_lsc, g.r_lic)

    def marcado(self, i: int) -> bool:
        return bool(self.g.puntos[i].reglas) if self.tipo == 'valor' else i in self.g.rango_fuera

    def escala(self):
        lc, lsc, lic = self.limites()
        vals = [v for v in self.serie() if v is not None] + [lsc, lic]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.12 or 1
        # Un rango nunca es negativo: el eje de rangos empieza en cero.
        return (max(0.0, lo - pad) if self.tipo == 'rango' else lo - pad), hi + pad

    def y(self, v: float) -> float:
        a, (lo, hi) = self.area(), self.escala()
        return a.bottom() - (v - lo) / (hi - lo) * a.height()

    def paintEvent(self, _):
        p = QPainter(self)
        if not self.fondo(p):
            return
        a, g = self.area(), self.g
        lc, lsc, lic = self.limites()
        serie = self.serie()

        # Zonas: cerca del centro es lo normal; hacia los límites se tiñe de arena y luego de rosa.
        if self.tipo == 'valor':
            s = (lsc - lc) / 3
            for k, color, alfa in ((3, tema.MAL, 12), (2, tema.AVISO, 12), (1, tema.SERIE, 12)):
                top, bot = max(a.top(), self.y(lc + k * s)), min(a.bottom(), self.y(lc - k * s))
                p.fillRect(QRectF(a.left(), top, a.width(), bot - top), tema.c(color, alfa))
        else:
            p.fillRect(QRectF(a.left(), self.y(lsc), a.width(), self.y(lic) - self.y(lsc)), tema.c(tema.SERIE, 10))

        # Periodo base: la franja con la que se calcularon los límites.
        if g.base < self.n():
            xb = a.left() + a.width() * g.base / self.n()
            p.setPen(QPen(tema.c(tema.ACENTO, 110), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(xb, a.top()), QPointF(xb, a.bottom()))
            p.setFont(self.fuente(8))
            p.setPen(tema.c(tema.TENUE))
            p.drawText(QRectF(a.left() + 6, a.top() + 3, xb - a.left() - 10, 16), Qt.AlignmentFlag.AlignLeft, f'límites con las primeras {g.base}')
            p.drawText(QRectF(xb + 6, a.top() + 3, a.right() - xb - 10, 16), Qt.AlignmentFlag.AlignLeft, 'vigilando')

        self.banda(p)
        self.linea_h(p, self.y(lsc), 'LSC', lsc, tema.MAL)
        self.linea_h(p, self.y(lc), 'LC', lc, tema.ACENTO, Qt.PenStyle.SolidLine)
        if not (self.tipo == 'rango' and lic <= 0):
            self.linea_h(p, self.y(lic), 'LIC', lic, tema.MAL)
        self.eje_y(p, *self.escala(), self.y)
        self.eje_x(p)

        # La serie entra de izquierda a derecha.
        hasta = self._t * (self.n() - 1)
        pts = [(i, QPointF(self.x(i), self.y(v))) for i, v in enumerate(serie) if v is not None and i <= hasta + 1e-9]
        if len(pts) >= 2:
            ult_i, ult = pts[-1]
            sig = next(((i, v) for i, v in enumerate(serie) if i > ult_i and v is not None), None)
            fin = ult
            if sig and hasta > ult_i:
                f = (hasta - ult_i) / (sig[0] - ult_i)
                fin = QPointF(ult.x() + (self.x(sig[0]) - ult.x()) * f, ult.y() + (self.y(sig[1]) - ult.y()) * f)
            camino = QPainterPath(pts[0][1])
            for _, q in pts[1:]:
                camino.lineTo(q)
            camino.lineTo(fin)
            relleno = QPainterPath(camino)
            relleno.lineTo(fin.x(), self.y(lc))
            relleno.lineTo(pts[0][1].x(), self.y(lc))
            relleno.closeSubpath()
            grad = QLinearGradient(0, a.top(), 0, a.bottom())
            grad.setColorAt(0, tema.c(tema.SERIE, 46))
            grad.setColorAt(0.5, tema.c(tema.SERIE, 8))
            grad.setColorAt(1, tema.c(tema.SERIE, 46))
            p.fillPath(relleno, grad)
            p.setPen(QPen(tema.c(tema.SERIE, 215), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(camino)
        for i, pt in pts:
            mal, grande = self.marcado(i), i in (self.sobre, self.sel)
            if mal:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(tema.c(tema.MAL, 40))
                p.drawEllipse(pt, 11, 11)
                p.setPen(QPen(tema.c(tema.MAL), 2))
                p.setBrush(tema.c(tema.PANEL))
                p.drawEllipse(pt, 6.5, 6.5)
            r = 4.8 if grande else 3.4
            p.setPen(QPen(tema.c(tema.PANEL), 1.2) if not mal else Qt.PenStyle.NoPen)
            p.setBrush(tema.c(tema.MAL if mal else tema.SERIE))
            p.drawEllipse(pt, r, r)
        self.marco_foco(p)


class Tendencia(Lienzo):
    """Cada pieza en el orden en que se midió, contra la tolerancia: lo que vería el operador en la báscula."""

    def titulo(self) -> str:
        return 'Cada pieza contra la tolerancia'

    def escala(self):
        vals = [v for _, vs in self.gs for v in vs] + [x for x in (self.lie, self.lse) if x is not None]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.1 or 1
        return lo - pad, hi + pad

    def y(self, v: float) -> float:
        a, (lo, hi) = self.area(), self.escala()
        return a.bottom() - (v - lo) / (hi - lo) * a.height()

    def paintEvent(self, _):
        p = QPainter(self)
        if not self.fondo(p):
            return
        a, w = self.area(), self.area().width() / max(1, self.n())
        # Franjas alternadas: una por muestra, para ver qué piezas salieron juntas.
        for i in range(0, self.n(), 2):
            p.fillRect(QRectF(self.x(i) - w / 2, a.top(), w, a.height()), tema.c(tema.TEXTO, 5))
        if self.lie is not None and self.lse is not None:
            p.fillRect(QRectF(a.left(), self.y(self.lse), a.width(), self.y(self.lie) - self.y(self.lse)), tema.c(tema.BIEN, 9))
        self.banda(p)
        for nombre, lim in (('LSE', self.lse), ('LIE', self.lie)):
            if lim is not None:
                self.linea_h(p, self.y(lim), nombre, lim, tema.AVISO)
        self.linea_h(p, self.y(self.g.lc), 'LC', self.g.lc, tema.ACENTO, Qt.PenStyle.SolidLine)
        self.eje_y(p, *self.escala(), self.y)
        self.eje_x(p)

        hasta = self._t * self.n()
        medias = []
        for i, (_, vs) in enumerate(self.gs[: self.n()]):
            if i > hasta:
                break
            k = len(vs)
            for j, v in enumerate(vs):
                xx = self.x(i) + (j - (k - 1) / 2) * min(7.0, w * 0.7 / max(1, k))
                fuera = (self.lse is not None and v > self.lse) or (self.lie is not None and v < self.lie)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(tema.c(tema.MAL if fuera else tema.SERIE, 235 if fuera else 170))
                p.drawEllipse(QPointF(xx, self.y(v)), 2.9, 2.9)
            medias.append(QPointF(self.x(i), self.y(sum(vs) / k)))
        if len(medias) >= 2:
            camino = QPainterPath(medias[0])
            for q in medias[1:]:
                camino.lineTo(q)
            p.setPen(QPen(tema.c(tema.ACENTO, 200), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(camino)
        self.marco_foco(p)

    def texto_punto(self, i: int) -> str:
        e, vs = self.gs[i]
        return f'<b>Muestra {e}</b><br>' + ' · '.join(fmt(v, self.dec) for v in vs)


class Cajas(Lienzo):
    """Una caja por muestra: dónde cae la mitad de las piezas, la mediana y los extremos."""

    def titulo(self) -> str:
        return 'Cómo se reparte cada muestra'

    escala = Tendencia.escala
    y = Tendencia.y

    def paintEvent(self, _):
        p = QPainter(self)
        if not self.fondo(p):
            return
        a, w = self.area(), self.area().width() / max(1, self.n())
        self.banda(p)
        for nombre, lim in (('LSE', self.lse), ('LIE', self.lie)):
            if lim is not None:
                self.linea_h(p, self.y(lim), nombre, lim, tema.AVISO)
        self.linea_h(p, self.y(self.g.lc), 'LC', self.g.lc, tema.ACENTO, Qt.PenStyle.SolidLine)
        self.eje_y(p, *self.escala(), self.y)
        self.eje_x(p)
        ancho = min(22.0, w * 0.56)
        for i, (_, vs) in enumerate(self.gs[: self.n()]):
            crece = max(0.0, min(1.0, self._t * 1.6 - i / max(1, self.n()) * 0.6))
            if crece <= 0:
                continue
            q1, med, q3 = cuartiles(vs)
            mal = bool(self.g.puntos[i].reglas) or i in self.g.rango_fuera
            color = tema.MAL if mal else tema.SERIE
            centro = lambda v: self.y(med) + (self.y(v) - self.y(med)) * crece
            xx = self.x(i)
            p.setPen(QPen(tema.c(color, 170), 1.2))
            p.drawLine(QPointF(xx, centro(min(vs))), QPointF(xx, centro(max(vs))))
            for v in (min(vs), max(vs)):
                p.drawLine(QPointF(xx - ancho / 4, centro(v)), QPointF(xx + ancho / 4, centro(v)))
            caja = QRectF(xx - ancho / 2, centro(q3), ancho, max(1.5, centro(q1) - centro(q3)))
            p.setBrush(tema.c(color, 70 if i != self.sel else 120))
            p.setPen(QPen(tema.c(color, 230), 1.3))
            p.drawRoundedRect(caja, 3, 3)
            p.setPen(QPen(tema.c(tema.TEXTO, 230), 2))
            p.drawLine(QPointF(caja.left() + 2, self.y(med)), QPointF(caja.right() - 2, self.y(med)))
        self.marco_foco(p)

    def texto_punto(self, i: int) -> str:
        e, vs = self.gs[i]
        q1, med, q3 = cuartiles(vs)
        return f'<b>Muestra {e}</b><br>mediana {fmt(med, self.dec)} · mitad entre {fmt(q1, self.dec)} y {fmt(q3, self.dec)}'


class Histograma(Lienzo):
    """Cómo se reparten todas las piezas contra la tolerancia, con la curva normal encima."""

    MARGEN = dict(izq=24, der=24, arr=40, aba=34)

    def titulo(self) -> str:
        return 'Reparto de todas las piezas contra la tolerancia'

    def n(self) -> int:
        return 0  # no tiene puntos por muestra: no se elige nada aquí

    def texto_punto(self, i: int) -> str:
        return ''

    def paintEvent(self, _):
        p = QPainter(self)
        if not self.fondo(p):
            return
        v = [x for _, vs in self.gs for x in vs]
        if len(v) < 2:
            return
        a = self.area()
        extremos = v + [x for x in (self.lie, self.lse) if x is not None]
        lo, hi = min(extremos), max(extremos)
        pad = (hi - lo) * 0.08 or 1
        lo, hi = lo - pad, hi + pad
        n_bins = max(8, min(24, int(math.sqrt(len(v)) * 1.3)))
        ancho = (max(v) - min(v)) / n_bins or 1
        cuentas = [0] * n_bins
        for x in v:
            cuentas[min(n_bins - 1, int((x - min(v)) / ancho))] += 1
        tope = max(cuentas)
        X = lambda val: a.left() + (val - lo) / (hi - lo) * a.width()
        alto = a.height() * 0.86

        if self.lie is not None and self.lse is not None:
            p.fillRect(QRectF(X(self.lie), a.top(), X(self.lse) - X(self.lie), a.height()), tema.c(tema.BIEN, 10))
        for k, n in enumerate(cuentas):
            x0, x1 = X(min(v) + k * ancho), X(min(v) + (k + 1) * ancho)
            h = n / tope * alto * self._t
            medio = min(v) + (k + 0.5) * ancho
            fuera = (self.lse is not None and medio > self.lse) or (self.lie is not None and medio < self.lie)
            grad = QLinearGradient(0, a.bottom() - h, 0, a.bottom())
            col = tema.MAL if fuera else tema.SERIE
            grad.setColorAt(0, tema.c(col, 200))
            grad.setColorAt(1, tema.c(col, 60))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(x0 + 1.5, a.bottom() - h, max(1, x1 - x0 - 3), h), 3, 3)

        m = sum(v) / len(v)
        s = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) or 1
        esperado = len(v) * ancho / (s * math.sqrt(2 * math.pi))
        camino = QPainterPath()
        for k in range(161):
            xv = lo + (hi - lo) * k / 160
            yv = a.bottom() - math.exp(-0.5 * ((xv - m) / s) ** 2) * esperado / tope * alto * self._t
            camino.moveTo(X(xv), yv) if k == 0 else camino.lineTo(X(xv), yv)
        p.setPen(QPen(tema.c(tema.ACENTO, 220), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(camino)
        p.setPen(QPen(tema.c(tema.ACENTO, 150), 1, Qt.PenStyle.DotLine))
        p.drawLine(QPointF(X(m), a.top() + 18), QPointF(X(m), a.bottom()))

        p.setFont(self.fuente(8.5))
        for nombre, lim in (('LIE', self.lie), ('LSE', self.lse)):
            if lim is None:
                continue
            p.setPen(QPen(tema.c(tema.AVISO), 1.4, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(X(lim), a.top()), QPointF(X(lim), a.bottom()))
            p.setPen(tema.c(tema.AVISO))
            p.drawText(QRectF(X(lim) - 60, a.bottom() + 6, 120, 18), Qt.AlignmentFlag.AlignCenter, f'{nombre} {fmt(lim, self.dec)}')
        p.setPen(tema.c(tema.TENUE))
        p.drawText(QRectF(a.left(), 10, a.width(), 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   f'media {fmt(m, self.dec)} · desviación {fmt(s, self.dec + 1)} · {len(v)} piezas')
        p.setPen(QPen(tema.c(tema.BORDE), 1))
        p.drawLine(QPointF(a.left(), a.bottom()), QPointF(a.right(), a.bottom()))
