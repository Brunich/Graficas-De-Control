import hashlib
import math

import pytest

from spc.datos import grupos, leer_texto, sugerir
from spc.logica import EJEMPLO, aplicar_reglas, capacidad, construir, csv_ejemplo, replace, veredicto

close = lambda a, b, eps=1e-3: abs(a - b) < eps


def test_individuales_limites_con_rango_movil():
    v = [10, 12, 11, 13, 12, 11, 10, 12]
    g = construir([(str(i + 1), [x]) for i, x in enumerate(v)])
    assert g.modo == 'I-MR'
    mr_bar, media = sum([2, 1, 2, 1, 1, 1, 2]) / 7, sum(v) / len(v)
    assert close(g.lc, media) and close(g.lsc, media + 2.66 * mr_bar, 0.01) and close(g.r_lsc, 3.267 * mr_bar)


def test_subgrupos_de_5_xbar_r():
    gs = [(str(k + 1), [x + (k % 2) * 0.2 for x in [10, 11, 12, 11, 10]]) for k in range(6)]
    g = construir(gs)
    assert (g.modo, g.n) == ('Xbar-R', 5)
    assert close(g.r_lc, 2) and close(g.lsc, g.lc + 0.577 * 2) and close(g.r_lsc, 2.114 * 2)


@pytest.mark.parametrize('valores, regla', [
    ([0, 0.5, -0.2, 3.4], 1), ([0, 2.3, 0.1, 2.5], 2), ([1.2, 1.4, 0.2, 1.1, 1.5], 3),
    ([0.2, 0.4, 0.1, 0.3, 0.6, 0.2, 0.5, 0.1], 4), ([-1, -0.6, -0.2, 0.1, 0.5, 0.9], 5),
])
def test_cada_regla_salta_con_su_patron(valores, regla):
    assert regla in aplicar_reglas(valores, 0, 1)[-1]


def test_el_ruido_no_dispara_reglas():
    assert not any(aplicar_reglas([0.3, -0.4, 0.8, -0.2, 0.5, -0.9, 0.1, -0.3], 0, 1))


def test_cp_cpk():
    gs = [(str(k), [x + (0.01 if k % 2 else -0.01) for x in [9.9, 10, 10.1, 10, 10]]) for k in range(10)]
    g, todos = construir(gs), [v for _, vs in gs for v in vs]
    cap = capacidad(g, todos, 9.4, 10.6)
    assert close(cap.cp, cap.cpk, 0.05)
    assert capacidad(replace(g, media=10.3), todos, 9.4, 10.6).cpk < cap.cpk
    assert capacidad(g, todos) is None
    assert math.isnan(capacidad(g, todos, None, 10.6).cp)


def test_ejemplo_detecta_el_desgaste_al_final():
    t = leer_texto(csv_ejemplo())
    medida, grupo = sugerir(t)
    assert (t.columnas[medida], t.columnas[grupo]) == ('diametro_mm', 'muestra')
    gs = grupos(t, medida, grupo)
    g = construir(gs, EJEMPLO['base'])
    marcadas = [i + 1 for i, p in enumerate(g.puntos) if p.reglas]
    assert marcadas and all(i >= 18 for i in marcadas), marcadas
    todos = [v for _, vs in gs for v in vs]
    assert not veredicto(g, capacidad(g, todos, EJEMPLO['lie'], EJEMPLO['lse'])).control
    # Con todas las muestras en el cálculo, el desgaste mueve el centro y ensucia el principio: por eso el periodo base.
    assert any(p.reglas for p in construir(gs).puntos[:15])


def test_ejemplo_igual_que_la_version_web():
    # Huella de lo que da la versión web (web/src/spc-logic.ts) con la misma semilla: mismas mediciones, byte a byte.
    assert hashlib.sha256(csv_ejemplo().encode()).hexdigest() == 'c23eb19c0e6e0a30ec9d21d8ecc0d1b1bfaa95e0991fc2bf45750f80a45a878b'


def test_comas_decimales_y_punto_y_coma():
    t = leer_texto('pieza;espesor\n1;2,51\n2;2,49\n3;2,50\n4;2,52\n5;2,48\n')
    medida, grupo = sugerir(t)
    assert t.columnas[medida] == 'espesor' and grupo is None
    assert [v for _, [v] in grupos(t, medida, grupo)] == [2.51, 2.49, 2.50, 2.52, 2.48]


def test_resumen_dice_la_causa_y_no_solo_el_aviso():
    t = leer_texto(csv_ejemplo())
    g = construir(grupos(t, *sugerir(t)), EJEMPLO['base'])
    from spc.logica import resumen
    # La regla 1 sólo avisa; la 4 (8 del mismo lado) dice que el centro se movió: esa manda en la frase.
    assert resumen(g) == 'Desde la muestra 20 se corrió hacia arriba. Revisa lote de material, operador o herramienta.'
