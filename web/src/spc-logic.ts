// Gráficas de control (SPC): con las mediciones de una pieza dice si el proceso está bajo control,
// qué puntos rompen las reglas y cuánto cumple la tolerancia (Cp y Cpk). Sin interfaz, para probarlo solo.
export type Mode = 'I-MR' | 'Xbar-R';
export type Rule = 1 | 2 | 3 | 4 | 5;
export type Point = { label: string; value: number; range: number | null; n: number; rules: Rule[] };
export type Chart = {
 mode: Mode; n: number; points: Point[]; base: number; // puntos usados para calcular los límites
 cl: number; ucl: number; lcl: number; sigma: number;          // gráfica de promedios (o individuales)
 rCl: number; rUcl: number; rLcl: number;                       // gráfica de rangos (o rangos móviles)
 rangeOut: number[];                                            // índices con el rango fuera de su límite
 mean: number; sd: number; count: number;                       // de todas las mediciones
};
export type Capability = { cp: number; cpk: number; pp: number; ppk: number; outside: number; outsidePct: number };

// Constantes de Shewhart para subgrupos de 2 a 10 piezas.
const K: Record<number, { A2: number; D3: number; D4: number; d2: number }> = {
 2: { A2: 1.88, D3: 0, D4: 3.267, d2: 1.128 }, 3: { A2: 1.023, D3: 0, D4: 2.574, d2: 1.693 }, 4: { A2: 0.729, D3: 0, D4: 2.282, d2: 2.059 },
 5: { A2: 0.577, D3: 0, D4: 2.114, d2: 2.326 }, 6: { A2: 0.483, D3: 0, D4: 2.004, d2: 2.534 }, 7: { A2: 0.419, D3: 0.076, D4: 1.924, d2: 2.704 },
 8: { A2: 0.373, D3: 0.136, D4: 1.864, d2: 2.847 }, 9: { A2: 0.337, D3: 0.184, D4: 1.816, d2: 2.97 }, 10: { A2: 0.308, D3: 0.223, D4: 1.777, d2: 3.078 },
};
export const RULES: Record<Rule, [string, string]> = {
 1: ['Un punto fuera de los límites de control', 'A point beyond the control limits'],
 2: ['2 de 3 puntos seguidos cerca del límite, del mismo lado', '2 of 3 points near the limit, same side'],
 3: ['4 de 5 puntos seguidos alejados del centro, del mismo lado', '4 of 5 points away from the center, same side'],
 4: ['8 puntos seguidos del mismo lado del centro', '8 points in a row on one side of the center'],
 5: ['6 puntos seguidos subiendo o bajando', '6 points in a row rising or falling'],
};
// Qué suele significar cada señal en el piso, para saber qué revisar primero.
export const MEANING: Record<Rule, [string, string]> = {
 1: ['Algo puntual: un cambio de material, un golpe, un error de medición.', 'Something one-off: a material change, a knock, a measuring error.'],
 2: ['El proceso se está yendo hacia un lado; revisa el ajuste antes de que salga pieza mala.', 'The process is drifting to one side; check the setting before a bad part comes out.'],
 3: ['Un corrimiento pequeño pero sostenido: desgaste, temperatura o un ajuste mal hecho.', 'A small but steady shift: wear, temperature or a bad adjustment.'],
 4: ['El centro del proceso se movió: otro lote de material, otro operador, otra herramienta.', 'The process center moved: another material batch, operator or tool.'],
 5: ['Tendencia: desgaste de herramienta o calentamiento de la máquina.', 'A trend: tool wear or the machine warming up.'],
};

const avg = (v: number[]) => v.reduce((s, x) => s + x, 0) / (v.length || 1);
const std = (v: number[]) => { const m = avg(v); return Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0) / Math.max(1, v.length - 1)); };

// Reglas de Western Electric sobre los puntos de la gráfica. Se marca el punto con el que se completa la señal.
export function applyRules(values: number[], cl: number, sigma: number): Rule[][] {
 const out: Rule[][] = values.map(() => []);
 if (!(sigma > 0)) return out;
 const z = values.map(v => (v - cl) / sigma), side = (x: number) => (x > 0 ? 1 : x < 0 ? -1 : 0);
 z.forEach((zi, i) => {
  if (Math.abs(zi) > 3) out[i].push(1);
  for (const s of [1, -1]) {
   const w3 = z.slice(Math.max(0, i - 2), i + 1);
   if (w3.length === 3 && side(zi) === s && Math.abs(zi) > 2 && w3.filter(x => side(x) === s && Math.abs(x) > 2).length >= 2 && !out[i].includes(2)) out[i].push(2);
   const w5 = z.slice(Math.max(0, i - 4), i + 1);
   if (w5.length === 5 && side(zi) === s && Math.abs(zi) > 1 && w5.filter(x => side(x) === s && Math.abs(x) > 1).length >= 4 && !out[i].includes(3)) out[i].push(3);
  }
  const w8 = z.slice(Math.max(0, i - 7), i + 1);
  if (w8.length === 8 && (w8.every(x => x > 0) || w8.every(x => x < 0))) out[i].push(4);
  const w6 = values.slice(Math.max(0, i - 5), i + 1);
  if (w6.length === 6 && (w6.every((x, k) => !k || x > w6[k - 1]) || w6.every((x, k) => !k || x < w6[k - 1]))) out[i].push(5);
 });
 return out;
}

// Una gráfica a partir de mediciones: cada grupo es un subgrupo (varias piezas del mismo momento) o una sola pieza.
// `base`: los límites salen de los primeros `base` puntos (un periodo estable) y con ellos se vigila el resto;
// sin `base`, de todos. Si el periodo de cálculo incluye el problema, los límites se abren y lo esconden.
export function buildChart(groups: { label: string; values: number[] }[], base?: number): Chart | null {
 const gs = groups.map(g => ({ label: g.label, values: g.values.filter(Number.isFinite) })).filter(g => g.values.length);
 const all = gs.flatMap(g => g.values);
 if (all.length < 5) return null;
 const sizes = gs.map(g => g.values.length), n = Math.round(avg(sizes));
 const stats = { mean: avg(all), sd: std(all), count: all.length };
 if (n <= 1 || gs.length < 5) {
  // Individuales y rango móvil: cada medición es un punto.
  const flat = gs.flatMap(g => g.values.map((v, k) => ({ label: g.values.length > 1 ? `${g.label}.${k + 1}` : g.label, v })));
  const mr = flat.map((p, i) => (i ? Math.abs(p.v - flat[i - 1].v) : null)), nb = base && base >= 5 ? Math.min(base, flat.length) : flat.length;
  const mrBar = avg(mr.slice(0, nb).filter((x): x is number => x !== null)), sigma = mrBar / 1.128, cl = avg(flat.slice(0, nb).map(p => p.v));
  const rules = applyRules(flat.map(p => p.v), cl, sigma), rUcl = 3.267 * mrBar;
  return { base: nb, mode: 'I-MR', n: 1, points: flat.map((p, i) => ({ label: p.label, value: p.v, range: mr[i], n: 1, rules: rules[i] })), cl, ucl: cl + 3 * sigma, lcl: cl - 3 * sigma, sigma, rCl: mrBar, rUcl, rLcl: 0, rangeOut: mr.flatMap((m, i) => (m !== null && m > rUcl ? [i] : [])), ...stats };
 }
 const k = K[Math.min(10, Math.max(2, n))];
 const means = gs.map(g => avg(g.values)), ranges = gs.map(g => Math.max(...g.values) - Math.min(...g.values));
 const nb = base && base >= 5 ? Math.min(base, gs.length) : gs.length;
 const cl = avg(means.slice(0, nb)), rBar = avg(ranges.slice(0, nb)), sigma = rBar / k.d2, se = sigma / Math.sqrt(n);
 const rules = applyRules(means, cl, se), rUcl = k.D4 * rBar, rLcl = k.D3 * rBar;
 return { base: nb, mode: 'Xbar-R', n, points: gs.map((g, i) => ({ label: g.label, value: means[i], range: ranges[i], n: g.values.length, rules: rules[i] })), cl, ucl: cl + k.A2 * rBar, lcl: cl - k.A2 * rBar, sigma, rCl: rBar, rUcl, rLcl, rangeOut: ranges.flatMap((r, i) => (r > rUcl || r < rLcl ? [i] : [])), ...stats };
}

// Capacidad contra la tolerancia: Cp/Cpk con la variación de corto plazo (la de la gráfica) y Pp/Ppk con la total.
export function capability(c: Chart, all: number[], lsl?: number, usl?: number): Capability | null {
 const hasL = Number.isFinite(lsl), hasU = Number.isFinite(usl);
 if (!hasL && !hasU) return null;
 const L = lsl as number, U = usl as number, s = c.sigma, S = c.sd || s, m = c.mean;
 const side = (sig: number) => Math.min(hasU ? (U - m) / (3 * sig) : Infinity, hasL ? (m - L) / (3 * sig) : Infinity);
 const outside = all.filter(v => (hasU && v > U) || (hasL && v < L)).length;
 return { cp: hasL && hasU ? (U - L) / (6 * s) : NaN, cpk: side(s), pp: hasL && hasU ? (U - L) / (6 * S) : NaN, ppk: side(S), outside, outsidePct: outside / (all.length || 1) };
}

// Veredicto en palabras: lo primero que lee el supervisor.
export function verdict(c: Chart, cap: Capability | null, es: boolean) {
 const signals = c.points.filter(p => p.rules.length).length + c.rangeOut.length;
 const control = signals === 0;
 const capable = cap ? cap.cpk >= 1.33 ? 'yes' : cap.cpk >= 1 ? 'tight' : 'no' : null;
 const a = control ? (es ? 'Bajo control' : 'In control') : (es ? `Fuera de control · ${signals} ${signals === 1 ? 'señal' : 'señales'}` : `Out of control · ${signals} signal${signals === 1 ? '' : 's'}`);
 // Control y capacidad son cosas distintas: un proceso puede avisar que cambió y todavía cumplir la tolerancia.
 const still = !control && capable !== 'no', and = still ? (es ? 'aunque todavía' : 'though it still') : (es ? 'y' : 'and');
 const b = capable === null ? '' : capable === 'yes' ? (es ? `${and} cumple la tolerancia con margen.` : `${and} meets the tolerance with room.`) : capable === 'tight' ? (es ? `${and} cumple la tolerancia, pero justo.` : `${and} meets the tolerance, barely.`) : (es ? 'y no alcanza la tolerancia: saldrán piezas malas.' : 'and cannot hold the tolerance: bad parts will come out.');
 return { control, capable, signals, text: b ? `${a} ${b}` : a };
}

// Ejemplo: diámetro de un buje, 25 muestras de 5 piezas cada hora; a partir de la 18 la herramienta se desgasta.
export function sampleCsv() {
 let seed = 7; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
 const gauss = () => { let s = 0; for (let i = 0; i < 6; i++) s += rnd(); return s - 3; };
 const rows = ['muestra,hora,diametro_mm'];
 for (let g = 1; g <= 25; g++) {
  const drift = g >= 18 ? (g - 17) * 0.0045 : 0, h = `${String(6 + Math.floor((g - 1) / 2)).padStart(2, '0')}:${g % 2 ? '00' : '30'}`;
  for (let k = 0; k < 5; k++) rows.push(`${g},${h},${(25 + drift + gauss() * 0.009).toFixed(3)}`);
 }
 return rows.join('\n');
}
export const SAMPLE_SPEC = { lsl: 24.95, usl: 25.05, unit: 'mm', name: 'Diámetro de buje', base: 15 };
