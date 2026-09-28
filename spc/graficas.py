"""Las gráficas, dibujadas a mano con QPainter: así se controla cada línea, cada zona y cada punto marcado."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from . import tema
from .logica import REGLAS, Grafica


def fmt(v: float, dec: int = 3) -> str:
    return '—' if v is None or not math.isfinite(v) else f'{v:.{dec}f}'


class GraficaControl(QWidget):
    """Una gráfica de control: promedios (o individuales) o rangos.

    Comparte el punto seleccionado con la otra gráfica y con la lista de señales mediante `elegido`."""

    elegido = Signal(int)
    MARGEN = dict(izq=64, der=74, arr=34, aba=30)

    def __init__(self, tipo: str, parent=None):
        super().__init__(parent)
        self.tipo = tipo  # 'valor' o 'rango'
        self.g: Grafica | None = None
        self.sel = -1
        self.sobre = -1
        self.dec = 3
        self.setMouseTracking(True)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # --- datos ---
    def poner(self, g: Grafica | None, dec: int = 3):
        self.g, self.dec, self.sel, self.sobre = g, dec, -1, -1
        self.setAccessibleName(self.titulo())
        self.update()

    def seleccionar(self, i: int):
        self.sel = i
        self.update()

    def titulo(self) -> str:
        if not self.g:
            return ''
        if self.tipo == 'valor':
            return 'Promedio de cada muestra (X̄)' if self.g.modo == 'Xbar-R' else 'Cada medición (I)'
        return 'Rango de cada muestra (R)' if self.g.modo == 'Xbar-R' else 'Rango móvil (MR)'

    def serie(self) -> list[float | None]:
        if not self.g:
            return []
        return [p.valor if self.tipo == 'valor' else p.rango for p in self.g.puntos]

    def limites(self):
        g = self.g
        return (g.lc, g.lsc, g.lic) if self.tipo == 'valor' else (g.r_lc, g.r_lsc, g.r_lic)

    def marcado(self, i: int) -> bool:
        return bool(self.g.puntos[i].reglas) if self.tipo == 'valor' else i in self.g.rango_fuera

    # --- geometría ---
    def area(self) -> QRectF:
        m = self.MARGEN
        return QRectF(m['izq'], m['arr'], self.width() - m['izq'] - m['der'], self.height() - m['arr'] - m['aba'])

    def escala(self):
        lc, lsc, lic = self.limites()
        vals = [v for v in self.serie() if v is not None] + [lsc, lic]
        lo, hi = min(vals), max(vals)
        pad = (hi - lo) * 0.12 or 1
        # Un rango nunca es negativo: el eje de rangos empieza en cero.
        return (max(0.0, lo - pad) if self.tipo == 'rango' else lo - pad), hi + pad

    def x(self, i: int) -> float:
        a, n = self.area(), len(self.g.puntos)
        return a.left() + (a.width() * (i + 0.5) / n)

    def y(self, v: float) -> float:
        a, (lo, hi) = self.area(), self.escala()
        return a.bottom() - (v - lo) / (hi - lo) * a.height()

    def indice_en(self, px: float) -> int:
        if not self.g:
            return -1
        a = self.area()
        if not a.adjusted(-8, 0, 8, 0).contains(QPointF(px, a.center().y())):
            return -1
        return max(0, min(len(self.g.puntos) - 1, int((px - a.left()) / a.width() * len(self.g.puntos))))

    # --- dibujo ---
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), tema.c(tema.PANEL))
        if not self.g:
            p.setPen(tema.c(tema.TENUE))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'Abre un archivo o usa el ejemplo')
            return
        a, g = self.area(), self.g
        lc, lsc, lic = self.limites()
        serie = self.serie()

        titulo = QFont(self.font())
        titulo.setPointSizeF(10)
        titulo.setBold(True)
        p.setFont(titulo)
        p.setPen(tema.c(tema.TEXTO))
        p.drawText(QRectF(a.left(), 6, a.width(), 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.titulo())

        # Periodo base: la franja con la que se calcularon los límites.
        if g.base < len(g.puntos):
            xb = a.left() + a.width() * g.base / len(g.puntos)
            p.fillRect(QRectF(a.left(), a.top(), xb - a.left(), a.height()), tema.c(tema.ACENTO, 16))
            p.setPen(QPen(tema.c(tema.ACENTO, 90), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(xb, a.top()), QPointF(xb, a.bottom()))
            chico = QFont(self.font())
            chico.setPointSizeF(8)
            p.setFont(chico)
            p.setPen(tema.c(tema.TENUE))
            p.drawText(QRectF(a.left() + 6, a.top() + 2, xb - a.left() - 8, 16), Qt.AlignmentFlag.AlignLeft,
                       f'Límites con las primeras {g.base}')

        # Zonas de 1σ y 2σ (sólo en la de promedios, que es donde miran las reglas 2 y 3).
        if self.tipo == 'valor':
            s = (lsc - lc) / 3
            for k in (1, 2):
                p.setPen(QPen(tema.c(tema.BORDE), 1, Qt.PenStyle.DotLine))
                for yv in (lc + k * s, lc - k * s):
                    p.drawLine(QPointF(a.left(), self.y(yv)), QPointF(a.right(), self.y(yv)))

        # Línea central y límites, con su etiqueta a la derecha.
        chico = QFont(self.font())
        chico.setPointSizeF(8)
        p.setFont(chico)
        for nombre, v, col, estilo in (('LSC', lsc, tema.MAL, Qt.PenStyle.DashLine), ('LC', lc, tema.ACENTO, Qt.PenStyle.SolidLine),
                                       ('LIC', lic, tema.MAL, Qt.PenStyle.DashLine)):
            if self.tipo == 'rango' and nombre == 'LIC' and v <= 0:
                continue
            yy = self.y(v)
            p.setPen(QPen(tema.c(col, 200), 1.2, estilo))
            p.drawLine(QPointF(a.left(), yy), QPointF(a.right(), yy))
            p.setPen(tema.c(col))
            p.drawText(QRectF(a.right() + 6, yy - 9, 70, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f'{nombre} {fmt(v, self.dec)}')

        # Eje Y: tres valores de referencia.
        p.setPen(tema.c(tema.TENUE))
        lo, hi = self.escala()
        for v in (lo, (lo + hi) / 2, hi):
            p.drawText(QRectF(0, self.y(v) - 9, a.left() - 8, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, fmt(v, self.dec))

        # Eje X: etiquetas espaciadas para que no se encimen.
        paso = max(1, math.ceil(len(g.puntos) / max(1, a.width() / 46)))
        for i in range(0, len(g.puntos), paso):
            p.drawText(QRectF(self.x(i) - 23, a.bottom() + 6, 46, 18), Qt.AlignmentFlag.AlignCenter, g.puntos[i].etiqueta)

        # El punto que se revisa: una franja vertical que se ve en las dos gráficas.
        for i, alfa in ((self.sobre, 20), (self.sel, 40)):
            if 0 <= i < len(g.puntos):
                w = a.width() / len(g.puntos)
                p.fillRect(QRectF(self.x(i) - w / 2, a.top(), w, a.height()), tema.c(tema.ACENTO, alfa))

        # La serie.
        camino, primero = QPainterPath(), True
        for i, v in enumerate(serie):
            if v is None:
                primero = True
                continue
            pt = QPointF(self.x(i), self.y(v))
            camino.moveTo(pt) if primero else camino.lineTo(pt)
            primero = False
        p.setPen(QPen(tema.c(tema.TEXTO, 170), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(camino)
        for i, v in enumerate(serie):
            if v is None:
                continue
            pt, mal = QPointF(self.x(i), self.y(v)), self.marcado(i)
            if mal:
                p.setPen(QPen(tema.c(tema.MAL), 2))
                p.setBrush(tema.c(tema.PANEL))
                p.drawEllipse(pt, 7, 7)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tema.c(tema.MAL if mal else tema.ACENTO))
            p.drawEllipse(pt, 3.6 if not mal else 3.2, 3.6 if not mal else 3.2)

        if self.hasFocus():
            p.setPen(QPen(tema.c(tema.ACENTO, 120), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 8, 8)

    # --- interacción ---
    def mouseMoveEvent(self, e):
        i = self.indice_en(e.position().x())
        if i != self.sobre:
            self.sobre = i
            self.update()
        if i >= 0:
            QToolTip.showText(e.globalPosition().toPoint(), self.texto_punto(i), self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, _):
        self.sobre = -1
        self.update()

    def mousePressEvent(self, e):
        i = self.indice_en(e.position().x())
        if i >= 0:
            self.elegido.emit(i)

    def keyPressEvent(self, e):
        if not self.g:
            return super().keyPressEvent(e)
        if e.key() in (Qt.Key.Key_Right, Qt.Key.Key_Left):
            d = 1 if e.key() == Qt.Key.Key_Right else -1
            self.elegido.emit(max(0, min(len(self.g.puntos) - 1, (self.sel if self.sel >= 0 else -d) + d)))
        else:
            super().keyPressEvent(e)

    def texto_punto(self, i: int) -> str:
        pt, g = self.g.puntos[i], self.g
        filas = [f'<b>Muestra {pt.etiqueta}</b>' if g.modo == 'Xbar-R' else f'<b>Medición {pt.etiqueta}</b>']
        if g.modo == 'Xbar-R':
            filas.append(f'Promedio {fmt(pt.valor, self.dec)} · rango {fmt(pt.rango, self.dec)} · {pt.n} piezas')
        else:
            filas.append(f'Valor {fmt(pt.valor, self.dec)} · rango móvil {fmt(pt.rango, self.dec)}')
        for r in pt.reglas:
            filas.append(f'<span style="color:{tema.MAL}">Regla {r}: {REGLAS[r]}</span>')
        if i in g.rango_fuera:
            filas.append(f'<span style="color:{tema.MAL}">El rango se sale de su límite</span>')
        return '<br>'.join(filas)


class Histograma(QWidget):
    """Cómo se reparten las piezas contra la tolerancia, con la curva normal encima."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.valores: list[float] = []
        self.lie = self.lse = None
        self.dec = 3
        self.setMinimumHeight(170)
        self.setAccessibleName('Histograma contra la tolerancia')

    def poner(self, valores: list[float], lie: float | None, lse: float | None, dec: int = 3):
        self.valores, self.lie, self.lse, self.dec = valores, lie, lse, dec
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), tema.c(tema.PANEL))
        v = self.valores
        if len(v) < 2:
            return
        a = QRectF(14, 30, self.width() - 28, self.height() - 58)
        f = QFont(self.font())
        f.setPointSizeF(10)
        f.setBold(True)
        p.setFont(f)
        p.setPen(tema.c(tema.TEXTO))
        p.drawText(QRectF(a.left(), 4, a.width(), 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 'Reparto contra la tolerancia')

        extremos = v + [x for x in (self.lie, self.lse) if x is not None]
        lo, hi = min(extremos), max(extremos)
        pad = (hi - lo) * 0.08 or 1
        lo, hi = lo - pad, hi + pad
        n_bins = max(6, min(24, int(math.sqrt(len(v)) * 1.6)))
        ancho = (max(v) - min(v)) / n_bins or 1
        cuentas = [0] * n_bins
        for x in v:
            cuentas[min(n_bins - 1, int((x - min(v)) / ancho))] += 1
        tope = max(cuentas)
        X = lambda val: a.left() + (val - lo) / (hi - lo) * a.width()

        for k, n in enumerate(cuentas):
            x0, x1 = X(min(v) + k * ancho), X(min(v) + (k + 1) * ancho)
            h = n / tope * a.height() * 0.92
            fuera = (self.lse is not None and min(v) + (k + 0.5) * ancho > self.lse) or (self.lie is not None and min(v) + (k + 0.5) * ancho < self.lie)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tema.c(tema.MAL if fuera else tema.ACENTO, 150))
            p.drawRoundedRect(QRectF(x0 + 1, a.bottom() - h, max(1, x1 - x0 - 2), h), 2, 2)

        # Curva normal con la media y la desviación de todas las piezas.
        m = sum(v) / len(v)
        s = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) or 1
        pico = 1 / (s * math.sqrt(2 * math.pi))
        esperado = len(v) * ancho * pico
        camino = QPainterPath()
        for k in range(121):
            xv = lo + (hi - lo) * k / 120
            yv = a.bottom() - (math.exp(-0.5 * ((xv - m) / s) ** 2) * esperado) / tope * a.height() * 0.92
            camino.moveTo(X(xv), yv) if k == 0 else camino.lineTo(X(xv), yv)
        p.setPen(QPen(tema.c(tema.TEXTO, 150), 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(camino)

        chico = QFont(self.font())
        chico.setPointSizeF(8)
        p.setFont(chico)
        for nombre, lim in (('LIE', self.lie), ('LSE', self.lse)):
            if lim is None:
                continue
            p.setPen(QPen(tema.c(tema.AVISO), 1.4, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(X(lim), a.top() - 4), QPointF(X(lim), a.bottom()))
            p.setPen(tema.c(tema.AVISO))
            p.drawText(QRectF(X(lim) - 50, a.bottom() + 4, 100, 18), Qt.AlignmentFlag.AlignCenter, f'{nombre} {fmt(lim, self.dec)}')
        p.setPen(QPen(tema.c(tema.BORDE), 1))
        p.drawLine(QPointF(a.left(), a.bottom()), QPointF(a.right(), a.bottom()))
