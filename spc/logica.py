"""Gráficas de control (SPC): con las mediciones de una pieza dice si el proceso está bajo control,
qué puntos rompen las reglas y cuánto cumple la tolerancia (Cp y Cpk). Sin interfaz, para probarlo solo."""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

# Constantes de Shewhart para subgrupos de 2 a 10 piezas: (A2, D3, D4, d2).
K = {
    2: (1.88, 0, 3.267, 1.128), 3: (1.023, 0, 2.574, 1.693), 4: (0.729, 0, 2.282, 2.059),
    5: (0.577, 0, 2.114, 2.326), 6: (0.483, 0, 2.004, 2.534), 7: (0.419, 0.076, 1.924, 2.704),
    8: (0.373, 0.136, 1.864, 2.847), 9: (0.337, 0.184, 1.816, 2.97), 10: (0.308, 0.223, 1.777, 3.078),
}

REGLAS = {
    1: 'Un punto fuera de los límites de control',
    2: '2 de 3 puntos seguidos cerca del límite, del mismo lado',
    3: '4 de 5 puntos seguidos alejados del centro, del mismo lado',
    4: '8 puntos seguidos del mismo lado del centro',
    5: '6 puntos seguidos subiendo o bajando',
}
# Qué suele significar cada señal en el piso, para saber qué revisar primero.
SIGNIFICA = {
    1: 'Algo puntual: un cambio de material, un golpe, un error de medición.',
    2: 'El proceso se está yendo hacia un lado; revisa el ajuste antes de que salga pieza mala.',
    3: 'Un corrimiento pequeño pero sostenido: desgaste, temperatura o un ajuste mal hecho.',
    4: 'El centro del proceso se movió: otro lote de material, otro operador, otra herramienta.',
    5: 'Tendencia: desgaste de herramienta o calentamiento de la máquina.',
}

# Versiones cortas, para las tarjetas: el texto largo queda en el apartado del punto.
REGLAS_CORTO = {1: 'Fuera de límites', 2: '2 de 3 cerca del límite', 3: '4 de 5 alejados del centro',
                4: '8 del mismo lado', 5: '6 subiendo o bajando'}
REVISAR = {
    1: 'material, un golpe o la medición',
    2: 'el ajuste, antes de que salga pieza mala',
    3: 'desgaste, temperatura o el último ajuste',
    4: 'lote de material, operador o herramienta',
    5: 'desgaste de herramienta o máquina calentándose',
}


@dataclass
class Punto:
    etiqueta: str
    valor: float
    rango: float | None
    n: int
    reglas: list[int] = field(default_factory=list)


@dataclass
class Grafica:
    modo: str  # 'I-MR' o 'Xbar-R'
    n: int
    puntos: list[Punto]
    base: int  # puntos usados para calcular los límites
    lc: float
    lsc: float
    lic: float
    sigma: float  # gráfica de promedios (o individuales)
    r_lc: float
    r_lsc: float
    r_lic: float  # gráfica de rangos (o rangos móviles)
    rango_fuera: list[int]  # índices con el rango fuera de su límite
    media: float
    de: float
    cuenta: int  # de todas las mediciones


@dataclass
class Capacidad:
    cp: float
    cpk: float
    pp: float
    ppk: float
    fuera: int
    fuera_pct: float


@dataclass
class Veredicto:
    control: bool
    capaz: str | None  # 'si', 'justo', 'no' o None sin tolerancia
    senales: int
    texto: str
    titulo: str = ''  # «Fuera de control»
    detalle: str = ''  # «6 señales · cumple la tolerancia con margen»


def promedio(v: list[float]) -> float:
    return sum(v) / (len(v) or 1)


def desviacion(v: list[float]) -> float:
    m = promedio(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / max(1, len(v) - 1))


def aplicar_reglas(valores: list[float], lc: float, sigma: float) -> list[list[int]]:
    """Reglas de Western Electric. Se marca el punto con el que se completa la señal."""
    out: list[list[int]] = [[] for _ in valores]
    if not sigma > 0:
        return out
    z = [(v - lc) / sigma for v in valores]
    lado = lambda x: 1 if x > 0 else -1 if x < 0 else 0
    for i, zi in enumerate(z):
        if abs(zi) > 3:
            out[i].append(1)
        for s in (1, -1):
            w3 = z[max(0, i - 2): i + 1]
            if len(w3) == 3 and lado(zi) == s and abs(zi) > 2 and sum(lado(x) == s and abs(x) > 2 for x in w3) >= 2 and 2 not in out[i]:
                out[i].append(2)
            w5 = z[max(0, i - 4): i + 1]
            if len(w5) == 5 and lado(zi) == s and abs(zi) > 1 and sum(lado(x) == s and abs(x) > 1 for x in w5) >= 4 and 3 not in out[i]:
                out[i].append(3)
        w8 = z[max(0, i - 7): i + 1]
        if len(w8) == 8 and (all(x > 0 for x in w8) or all(x < 0 for x in w8)):
            out[i].append(4)
        w6 = valores[max(0, i - 5): i + 1]
        if len(w6) == 6 and (all(b > a for a, b in zip(w6, w6[1:])) or all(b < a for a, b in zip(w6, w6[1:]))):
            out[i].append(5)
    return out


def construir(grupos: list[tuple[str, list[float]]], base: int | None = None) -> Grafica | None:
    """Una gráfica a partir de mediciones: cada grupo es un subgrupo (varias piezas del mismo momento) o una sola pieza.

    `base`: los límites salen de los primeros `base` puntos (un periodo estable) y con ellos se vigila el resto;
    sin `base`, de todos. Si el periodo de cálculo incluye el problema, los límites se abren y lo esconden.
    """
    gs = [(e, [v for v in vs if math.isfinite(v)]) for e, vs in grupos]
    gs = [(e, vs) for e, vs in gs if vs]
    todos = [v for _, vs in gs for v in vs]
    if len(todos) < 5:
        return None
    n = round(promedio([len(vs) for _, vs in gs]))
    stats = dict(media=promedio(todos), de=desviacion(todos), cuenta=len(todos))
    if n <= 1 or len(gs) < 5:
        # Individuales y rango móvil: cada medición es un punto.
        plano = [(f'{e}.{k + 1}' if len(vs) > 1 else e, v) for e, vs in gs for k, v in enumerate(vs)]
        mr = [abs(v - plano[i - 1][1]) if i else None for i, (_, v) in enumerate(plano)]
        nb = min(base, len(plano)) if base and base >= 5 else len(plano)
        mr_bar = promedio([x for x in mr[:nb] if x is not None])
        sigma, lc = mr_bar / 1.128, promedio([v for _, v in plano[:nb]])
        reglas, r_lsc = aplicar_reglas([v for _, v in plano], lc, sigma), 3.267 * mr_bar
        puntos = [Punto(e, v, mr[i], 1, reglas[i]) for i, (e, v) in enumerate(plano)]
        return Grafica('I-MR', 1, puntos, nb, lc, lc + 3 * sigma, lc - 3 * sigma, sigma, mr_bar, r_lsc, 0,
                       [i for i, m in enumerate(mr) if m is not None and m > r_lsc], **stats)
    a2, d3, d4, d2 = K[min(10, max(2, n))]
    medias = [promedio(vs) for _, vs in gs]
    rangos = [max(vs) - min(vs) for _, vs in gs]
    nb = min(base, len(gs)) if base and base >= 5 else len(gs)
    lc, r_bar = promedio(medias[:nb]), promedio(rangos[:nb])
    sigma = r_bar / d2
    reglas = aplicar_reglas(medias, lc, sigma / math.sqrt(n))
    r_lsc, r_lic = d4 * r_bar, d3 * r_bar
    puntos = [Punto(e, medias[i], rangos[i], len(vs), reglas[i]) for i, (e, vs) in enumerate(gs)]
    return Grafica('Xbar-R', n, puntos, nb, lc, lc + a2 * r_bar, lc - a2 * r_bar, sigma, r_bar, r_lsc, r_lic,
                   [i for i, r in enumerate(rangos) if r > r_lsc or r < r_lic], **stats)


def capacidad(g: Grafica, todos: list[float], lie: float | None = None, lse: float | None = None) -> Capacidad | None:
    """Capacidad contra la tolerancia: Cp/Cpk con la variación de corto plazo (la de la gráfica) y Pp/Ppk con la total."""
    if lie is None and lse is None:
        return None
    s, S, m = g.sigma, g.de or g.sigma, g.media
    lado = lambda sig: min((lse - m) / (3 * sig) if lse is not None else math.inf, (m - lie) / (3 * sig) if lie is not None else math.inf)
    fuera = sum(1 for v in todos if (lse is not None and v > lse) or (lie is not None and v < lie))
    ambos = lie is not None and lse is not None
    return Capacidad((lse - lie) / (6 * s) if ambos else math.nan, lado(s), (lse - lie) / (6 * S) if ambos else math.nan,
                     lado(S), fuera, fuera / (len(todos) or 1))


def veredicto(g: Grafica, cap: Capacidad | None) -> Veredicto:
    """Lo primero que lee el supervisor, en palabras."""
    senales = sum(1 for p in g.puntos if p.reglas) + len(g.rango_fuera)
    control = senales == 0
    capaz = None if cap is None else 'si' if cap.cpk >= 1.33 else 'justo' if cap.cpk >= 1 else 'no'
    a = 'Bajo control' if control else f"Fuera de control · {senales} {'señal' if senales == 1 else 'señales'}"
    # Control y capacidad son cosas distintas: un proceso puede avisar que cambió y todavía cumplir la tolerancia.
    y = ', aunque todavía' if not control and capaz != 'no' else ' y'
    b = {None: '', 'si': f'{y} cumple la tolerancia con margen.', 'justo': f'{y} cumple la tolerancia, pero justo.',
         'no': ' y no alcanza la tolerancia: saldrán piezas malas.'}[capaz]
    titulo = 'Bajo control' if control else 'Fuera de control'
    partes = [] if control else [f"{senales} {'señal' if senales == 1 else 'señales'}"]
    partes += [{None: '', 'si': 'cumple la tolerancia con margen', 'justo': 'cumple la tolerancia, pero justo',
                'no': 'no alcanza la tolerancia'}[capaz]]
    return Veredicto(control, capaz, senales, a + b, titulo, ' · '.join(p for p in partes if p) or 'sin tolerancia puesta')


# Cuál regla explica mejor lo que pasa: un patrón (tendencia, corrimiento) dice la causa; un punto fuera sólo avisa.
PRIORIDAD = [5, 4, 3, 2, 1]


def regla_principal(reglas: list[int]) -> int | None:
    return next((r for r in PRIORIDAD if r in reglas), None)


def resumen(g: Grafica) -> str:
    """Una frase con lo que pasa y qué revisar: «Desde la muestra 20 sube sin parar. Revisa desgaste…»."""
    marcados = [i for i, p in enumerate(g.puntos) if p.reglas]
    if not marcados:
        return 'Ningún patrón raro: sigue midiendo con los mismos límites.' if not g.rango_fuera else             'Hay muestras con piezas dispares: revisa sujeción, material o medición.'
    todas = [r for i in marcados for r in g.puntos[i].reglas]
    r = regla_principal(todas)
    desde = g.puntos[marcados[0]]
    arriba = sum(g.puntos[i].valor > g.lc for i in marcados) >= len(marcados) / 2
    frase = {5: 'sube sin parar' if arriba else 'baja sin parar', 4: 'se corrió hacia ' + ('arriba' if arriba else 'abajo'),
             3: 'se corrió un poco hacia ' + ('arriba' if arriba else 'abajo'), 2: 'se acerca al límite',
             1: 'hay puntos fuera de los límites'}[r]
    quien = 'muestra' if g.modo == 'Xbar-R' else 'medición'
    return f'Desde la {quien} {desde.etiqueta} {frase}. Revisa {REVISAR[r]}.'


def csv_ejemplo() -> str:
    """Diámetro de un buje, 25 muestras de 5 piezas cada hora; a partir de la 18 la herramienta se desgasta.

    Mismo generador que la versión web (aritmética de dobles), así las dos dan las mismas mediciones."""
    semilla = 7.0

    def rnd() -> float:
        nonlocal semilla
        semilla = math.fmod(semilla * 1103515245 + 12345, 2147483648)
        return semilla / 2147483648

    def gauss() -> float:
        return sum(rnd() for _ in range(6)) - 3

    filas = ['muestra,hora,diametro_mm']
    for g in range(1, 26):
        desgaste = (g - 17) * 0.0045 if g >= 18 else 0
        h = f"{6 + (g - 1) // 2:02d}:{'00' if g % 2 else '30'}"
        for _ in range(5):
            filas.append(f'{g},{h},{25 + desgaste + gauss() * 0.009:.3f}')
    return '\n'.join(filas)


EJEMPLO = dict(lie=24.95, lse=25.05, unidad='mm', nombre='Diámetro de buje', base=15)

__all__ = ['Grafica', 'Punto', 'Capacidad', 'Veredicto', 'REGLAS', 'SIGNIFICA', 'REGLAS_CORTO', 'REVISAR', 'regla_principal', 'resumen', 'EJEMPLO', 'aplicar_reglas',
           'construir', 'capacidad', 'veredicto', 'csv_ejemplo', 'replace']
