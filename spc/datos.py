"""Leer las mediciones (CSV o Excel) y adivinar qué columna se mide y cuál agrupa las piezas."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Tabla:
    columnas: list[str]
    filas: list[list[str]]
    nombre: str = ''


def numero(texto: str) -> float | None:
    """'25,013' y '25.013' valen lo mismo; lo que no es número da None."""
    t = str(texto).strip().replace(' ', '')
    if not t:
        return None
    if ',' in t and '.' not in t:
        t = t.replace(',', '.')
    try:
        return float(t)
    except ValueError:
        return None


def leer_texto(texto: str, nombre: str = '') -> Tabla:
    texto = texto.lstrip('﻿')
    try:
        dialecto = csv.Sniffer().sniff(texto[:4000], delimiters=',;\t|')
    except csv.Error:
        dialecto = csv.excel
    filas = [f for f in csv.reader(io.StringIO(texto), dialecto) if any(c.strip() for c in f)]
    if not filas:
        return Tabla([], [], nombre)
    cab, resto = [c.strip() for c in filas[0]], filas[1:]
    ancho = len(cab)
    return Tabla(cab, [(f + [''] * ancho)[:ancho] for f in resto], nombre)


def leer_archivo(ruta: str | Path) -> Tabla:
    ruta = Path(ruta)
    if ruta.suffix.lower() in ('.xlsx', '.xlsm'):
        from openpyxl import load_workbook
        hoja = load_workbook(ruta, read_only=True, data_only=True).worksheets[0]
        filas = [['' if c is None else str(c) for c in f] for f in hoja.iter_rows(values_only=True)]
        filas = [f for f in filas if any(c.strip() for c in f)]
        if not filas:
            return Tabla([], [], ruta.name)
        ancho = len(filas[0])
        return Tabla([c.strip() for c in filas[0]], [(f + [''] * ancho)[:ancho] for f in filas[1:]], ruta.name)
    crudo = ruta.read_bytes()
    for cod in ('utf-8-sig', 'cp1252'):
        try:
            return leer_texto(crudo.decode(cod), ruta.name)
        except UnicodeDecodeError:
            continue
    return leer_texto(crudo.decode('latin-1'), ruta.name)


def columnas_numericas(t: Tabla) -> list[int]:
    """Columnas donde al menos el 80 % de las celdas con algo son números."""
    out = []
    for i in range(len(t.columnas)):
        llenas = [f[i] for f in t.filas if f[i].strip()]
        if llenas and sum(numero(x) is not None for x in llenas) >= 0.8 * len(llenas):
            out.append(i)
    return out


AGRUPA = re.compile(r'muestra|subgrupo|sample|subgroup|grupo|lote|batch', re.I)
MIDE = re.compile(r'diam|medid|medic|espesor|largo|ancho|peso|mm|valor|value|measure', re.I)


def sugerir(t: Tabla) -> tuple[int | None, int | None]:
    """(columna medida, columna de subgrupo o None). La medida es numérica con decimales o nombre de medida."""
    nums = columnas_numericas(t)
    grupo = next((i for i, c in enumerate(t.columnas) if AGRUPA.search(c)), None)
    candidatas = [i for i in nums if i != grupo]
    medida = next((i for i in candidatas if MIDE.search(t.columnas[i])), None)
    if medida is None:
        # La que tenga más valores distintos: un número de muestra se repite, una medición casi no.
        medida = max(candidatas, key=lambda i: len({f[i] for f in t.filas}), default=None)
    return medida, grupo


def grupos(t: Tabla, medida: int, grupo: int | None) -> list[tuple[str, list[float]]]:
    """Agrupa conservando el orden de aparición; sin columna de grupo cada fila es su propio punto."""
    if grupo is None:
        return [(str(k + 1), [v]) for k, v in enumerate(numero(f[medida]) for f in t.filas) if v is not None]
    orden: dict[str, list[float]] = {}
    for f in t.filas:
        v = numero(f[medida])
        if v is not None:
            orden.setdefault(f[grupo].strip() or '—', []).append(v)
    return list(orden.items())
