"""Dibuja el icono de la app (una gráfica de control pequeña) y lo guarda en assets/: `python tools/icono.py`."""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter, QPainterPath, QPen

from spc import tema

ASSETS = Path(__file__).resolve().parents[1] / 'assets'


def dibujar(lado: int) -> QImage:
    img = QImage(lado, lado, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = lado / 256
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(tema.c(tema.PANEL_2))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 56 * s, 56 * s)
    p.setPen(QPen(tema.c(tema.MAL, 220), 7 * s, Qt.PenStyle.DashLine))
    for y in (78, 178):
        p.drawLine(QPointF(40 * s, y * s), QPointF(216 * s, y * s))
    p.setPen(QPen(tema.c(tema.ACENTO, 160), 5 * s))
    p.drawLine(QPointF(40 * s, 128 * s), QPointF(216 * s, 128 * s))
    pts = [(46, 138), (78, 116), (110, 142), (142, 120), (174, 104), (208, 58)]
    camino = QPainterPath(QPointF(pts[0][0] * s, pts[0][1] * s))
    for x, y in pts[1:]:
        camino.lineTo(x * s, y * s)
    p.setPen(QPen(tema.c(tema.TEXTO), 11 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(camino)
    p.setPen(QPen(tema.c(tema.MAL), 9 * s))
    p.setBrush(tema.c(tema.PANEL_2))
    p.drawEllipse(QPointF(208 * s, 58 * s), 17 * s, 17 * s)
    p.end()
    return img


if __name__ == '__main__':
    app = QGuiApplication(sys.argv)
    ASSETS.mkdir(exist_ok=True)
    dibujar(256).save(str(ASSETS / 'icono.png'))
    dibujar(256).save(str(ASSETS / 'icono.ico'))
    print('ok')
