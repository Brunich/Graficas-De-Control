import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyRules, buildChart, capability, verdict, sampleCsv, SAMPLE_SPEC } from '../src/spc-logic.ts';
import { parseCsv } from '../src/csv.ts';

const close = (a: number, b: number, eps = 1e-3) => assert.ok(Math.abs(a - b) < eps, `${a} ≈ ${b}`);

test('individuales: límites con el rango móvil (2.66 × MR̄)', () => {
 const v = [10, 12, 11, 13, 12, 11, 10, 12];
 const c = buildChart(v.map((x, i) => ({ label: String(i + 1), values: [x] })))!;
 assert.equal(c.mode, 'I-MR');
 const mr = [2, 1, 2, 1, 1, 1, 2], mrBar = mr.reduce((a, b) => a + b) / mr.length, mean = v.reduce((a, b) => a + b) / v.length;
 close(c.cl, mean); close(c.ucl, mean + 2.66 * mrBar, 0.01); close(c.rUcl, 3.267 * mrBar);
});

test('subgrupos de 5: X̄-R con A2 = 0.577 y D4 = 2.114', () => {
 const groups = Array.from({ length: 6 }, (_, g) => ({ label: String(g + 1), values: [10, 11, 12, 11, 10].map(x => x + (g % 2) * 0.2) }));
 const c = buildChart(groups)!;
 assert.equal(c.mode, 'Xbar-R');
 assert.equal(c.n, 5);
 close(c.rCl, 2); close(c.ucl, c.cl + 0.577 * 2); close(c.rUcl, 2.114 * 2);
});

test('cada regla salta con su patrón y no con ruido', () => {
 const r = (v: number[]) => applyRules(v, 0, 1);
 assert.ok(r([0, 0.5, -0.2, 3.4])[3].includes(1));
 assert.ok(r([0, 2.3, 0.1, 2.5])[3].includes(2));
 assert.ok(r([1.2, 1.4, 0.2, 1.1, 1.5])[4].includes(3));
 assert.ok(r([0.2, 0.4, 0.1, 0.3, 0.6, 0.2, 0.5, 0.1])[7].includes(4));
 assert.ok(r([-1, -0.6, -0.2, 0.1, 0.5, 0.9])[5].includes(5));
 assert.deepEqual(r([0.3, -0.4, 0.8, -0.2, 0.5, -0.9, 0.1, -0.3]).flat(), []);
});

test('Cp y Cpk: centrado da Cp = Cpk; corrido baja el Cpk', () => {
 const groups = Array.from({ length: 10 }, (_, g) => ({ label: String(g), values: [9.9, 10, 10.1, 10, 10].map(x => x + (g % 2 ? 0.01 : -0.01)) }));
 const c = buildChart(groups)!, all = groups.flatMap(g => g.values);
 const cap = capability(c, all, 9.4, 10.6)!;
 close(cap.cp, cap.cpk, 0.05);
 const shifted = capability({ ...c, mean: 10.3 }, all, 9.4, 10.6)!;
 assert.ok(shifted.cpk < cap.cpk);
 assert.equal(capability(c, all), null);
});

test('el ejemplo del buje detecta el desgaste de la herramienta al final', () => {
 const { rows } = parseCsv(sampleCsv());
 const groups = Array.from({ length: 25 }, (_, g) => ({ label: String(g + 1), values: rows.filter(r => r[0] === String(g + 1)).map(r => Number(r[2])) }));
 const c = buildChart(groups, SAMPLE_SPEC.base)!;
 const flagged = c.points.flatMap((p, i) => (p.rules.length ? [i + 1] : []));
 assert.ok(flagged.length > 0 && flagged.every(i => i >= 18), `señales en ${flagged}`);
 const v = verdict(c, capability(c, groups.flatMap(g => g.values), SAMPLE_SPEC.lsl, SAMPLE_SPEC.usl), true);
 assert.equal(v.control, false);
 // Con todas las muestras en el cálculo, el desgaste mueve el centro y ensucia el principio: por eso el periodo base.
 assert.ok(buildChart(groups)!.points.slice(0, 15).some(p => p.rules.length));
});
