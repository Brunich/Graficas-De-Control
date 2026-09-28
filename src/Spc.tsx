import { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle, WarningOctagon, UploadSimple, Copy } from '@phosphor-icons/react';
import { parseCsv } from './csv';
import { readTable, TABLE_ACCEPT } from './read-file';
import { toNumber } from './quality';
import { buildChart, capability, verdict, sampleCsv, SAMPLE_SPEC, RULES, MEANING } from './spc-logic';
import type { Chart, Rule } from './spc-logic';
import './spc.css';

// Gráficas de control: sube las mediciones de una pieza, elige la columna y la tolerancia,
// y dice si el proceso está bajo control, qué puntos avisan y si alcanza la tolerancia.
type Grid = { headers: string[]; rows: string[][] };
const fold = (s: string) => s.toLocaleLowerCase('es').normalize('NFD').replace(/[̀-ͯ]/g, '');

function guess(g: Grid) {
 const numeric = g.headers.map((_, i) => g.rows.length > 0 && g.rows.filter(r => (r[i] ?? '').trim()).every(r => Number.isFinite(toNumber(r[i]))));
 const measure = numeric.lastIndexOf(true);
 const group = g.headers.findIndex((h, i) => i !== measure && /^(muestra|subgrupo|grupo|sample|subgroup|lote|hora)/.test(fold(h)) && new Set(g.rows.map(r => r[i])).size < g.rows.length);
 return { measure, group };
}
const fmt = (n: number, d = 3) => Number.isFinite(n) ? n.toLocaleString('es-MX', { minimumFractionDigits: d, maximumFractionDigits: d }) : '—';

function ControlChart({ c, kind, lsl, usl, es }: { c: Chart; kind: 'x' | 'r'; lsl?: number; usl?: number; es: boolean }) {
 const W = 760, H = kind === 'x' ? 280 : 130, L = 56, R = 64, T = 14, B = 26;
 const vals = kind === 'x' ? c.points.map(p => p.value) : c.points.map(p => p.range ?? NaN);
 const lines = kind === 'x' ? { cl: c.cl, ucl: c.ucl, lcl: c.lcl } : { cl: c.rCl, ucl: c.rUcl, lcl: c.rLcl };
 const specs = kind === 'x' ? [lsl, usl].filter((v): v is number => Number.isFinite(v)) : [];
 const pool = [...vals.filter(Number.isFinite), lines.ucl, lines.lcl, ...specs];
 let lo = Math.min(...pool), hi = Math.max(...pool); const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
 const x = (i: number) => L + (c.points.length > 1 ? i / (c.points.length - 1) : 0.5) * (W - L - R), y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
 const step = (W - L - R) / Math.max(1, c.points.length - 1);
 const s1 = (lines.ucl - lines.cl) / 3;
 const bad = (i: number) => kind === 'x' ? c.points[i].rules.length > 0 : c.rangeOut.includes(i);
 const path = vals.map((v, i) => Number.isFinite(v) ? `${i && Number.isFinite(vals[i - 1]) ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}` : '').join('');
 const label = (v: number, text: string, cls: string, key = cls) => <g key={key} className={cls}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)}/><text x={W - R + 6} y={y(v) + 4}>{text}</text></g>;
 return <svg className={`spc-chart k-${kind}`} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={kind === 'x' ? (es ? 'Gráfica de promedios con límites de control' : 'Means chart with control limits') : (es ? 'Gráfica de rangos' : 'Range chart')}>
  {c.base < c.points.length && <g className="spc-base"><rect x={L - step / 2} y={T} width={Math.max(0, x(c.base - 1) - L + step)} height={H - T - B}/><text x={L - step / 2 + 6} y={H - B - 6}>{es ? 'cálculo de límites' : 'limits computed here'}</text></g>}
  {kind === 'x' && <><rect className="spc-z2" x={L} width={W - L - R} y={y(lines.cl + 2 * s1)} height={Math.max(0, y(lines.cl - 2 * s1) - y(lines.cl + 2 * s1))}/><rect className="spc-z1" x={L} width={W - L - R} y={y(lines.cl + s1)} height={Math.max(0, y(lines.cl - s1) - y(lines.cl + s1))}/></>}
  {specs.map((v, i) => label(v, `${v === lsl ? (es ? 'LIE' : 'LSL') : (es ? 'LSE' : 'USL')} ${fmt(v, 2)}`, 'spc-spec' + i))}
  {label(lines.ucl, `${es ? 'LSC' : 'UCL'} ${fmt(lines.ucl)}`, 'spc-lim', 'ucl')}
  {kind === 'x' || lines.lcl > 0 ? label(lines.lcl, `${es ? 'LIC' : 'LCL'} ${fmt(lines.lcl)}`, 'spc-lim', 'lcl') : null}
  {label(lines.cl, `${kind === 'x' ? (c.mode === 'I-MR' ? 'X̄' : 'X̿') : c.mode === 'I-MR' ? 'MR̄' : 'R̄'} ${fmt(lines.cl)}`, 'spc-cl')}
  <path className="spc-line" d={path} pathLength={1}/>
  {vals.map((v, i) => Number.isFinite(v) && <circle key={i} className={bad(i) ? 'bad' : ''} cx={x(i)} cy={y(v)} r={bad(i) ? 5.5 : 3.6} style={{ ['--i' as string]: i }}><title>{`${c.points[i].label}: ${fmt(v)}${kind === 'x' && c.points[i].rules.length ? ` · ${c.points[i].rules.map(r => RULES[r][es ? 0 : 1]).join('; ')}` : ''}`}</title></circle>)}
  {c.points.map((p, i) => (c.points.length <= 30 || i % Math.ceil(c.points.length / 25) === 0) && <text key={i} className="spc-x" x={x(i)} y={H - 8}>{p.label}</text>)}
 </svg>;
}

function Histogram({ values, lsl, usl, mean, es }: { values: number[]; lsl?: number; usl?: number; mean: number; es: boolean }) {
 const W = 360, H = 150, bins = 14;
 const pool = [...values, ...[lsl, usl].filter((v): v is number => Number.isFinite(v))];
 const lo = Math.min(...pool), hi = Math.max(...pool), span = hi - lo || 1;
 const counts = Array(bins).fill(0); values.forEach(v => counts[Math.min(bins - 1, Math.floor((v - lo) / span * bins))]++);
 const top = Math.max(...counts), x = (v: number) => 10 + (v - lo) / span * (W - 20);
 return <svg className="spc-hist" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Histograma">
  {counts.map((n, i) => <rect key={i} x={10 + i * (W - 20) / bins + 1} width={(W - 20) / bins - 2} y={H - 22 - n / top * (H - 40)} height={n / top * (H - 40)} rx={2}/>)}
  {[lsl, usl].map((v, i) => Number.isFinite(v) && <g key={i} className="spc-spec"><line x1={x(v!)} x2={x(v!)} y1={8} y2={H - 20}/><text x={x(v!)} y={H - 6}>{i ? (es ? 'LSE' : 'USL') : (es ? 'LIE' : 'LSL')}</text></g>)}
  <line className="spc-mean" x1={x(mean)} x2={x(mean)} y1={8} y2={H - 20}/>
 </svg>;
}

export default function Spc({ lang }: { lang: 'es' | 'en' }) {
 const es = lang === 'es', L = es ? 0 : 1, t = (a: string, b: string) => (es ? a : b);
 const [data, setData] = useState<{ grid: Grid; name: string; sample: boolean }>(() => ({ grid: parseCsv(sampleCsv()), name: 'buje_diametro.csv', sample: true }));
 const first = useMemo(() => guess(data.grid), [data]);
 const [measure, setMeasure] = useState<number | null>(null);
 const [group, setGroup] = useState<number | null>(null);
 const [lsl, setLsl] = useState(String(SAMPLE_SPEC.lsl)), [usl, setUsl] = useState(String(SAMPLE_SPEC.usl));
 const [base, setBase] = useState(SAMPLE_SPEC.base);
 const [err, setErr] = useState(''), [note, setNote] = useState('');
 const input = useRef<HTMLInputElement>(null), charts = useRef<HTMLDivElement>(null);
 const mi = measure ?? first.measure, gi = group ?? first.group;
 const groups = useMemo(() => {
  const g = data.grid, order: string[] = [], map = new Map<string, number[]>();
  g.rows.forEach((r, i) => { const k = gi >= 0 ? (r[gi] ?? '').trim() : String(i + 1); if (!map.has(k)) { map.set(k, []); order.push(k); } const v = toNumber(r[mi] ?? ''); if (Number.isFinite(v)) map.get(k)!.push(v); });
  return order.map(k => ({ label: k, values: map.get(k)! }));
 }, [data, mi, gi]);
 const all = groups.flatMap(g => g.values);
 const c = useMemo(() => mi >= 0 ? buildChart(groups, base || undefined) : null, [groups, base, mi]);
 const L1 = Number.isFinite(toNumber(lsl)) ? toNumber(lsl) : undefined, U1 = Number.isFinite(toNumber(usl)) ? toNumber(usl) : undefined;
 const cap = c ? capability(c, all, L1, U1) : null;
 const v = c ? verdict(c, cap, es) : null;
 const byRule = useMemo(() => { const m = new Map<Rule, string[]>(); c?.points.forEach(p => p.rules.forEach(r => m.set(r, [...(m.get(r) ?? []), p.label]))); return [...m].sort((a, b) => a[0] - b[0]); }, [c]);

 // En celular la gráfica se desliza: abre en lo más reciente, que es lo que se vigila.
 useEffect(() => { charts.current?.querySelectorAll('figure').forEach(f => { f.scrollLeft = f.scrollWidth; }); }, [c]);
 async function load(f: File | undefined) {
  if (!f) return;
  try { const g = await readTable(f); setData({ grid: { headers: g.headers, rows: g.rows }, name: f.name, sample: false }); setMeasure(null); setGroup(null); setLsl(''); setUsl(''); setBase(0); setErr(''); setNote(''); }
  catch { setErr(t(`No pude leer ${f.name}. Usa CSV o Excel.`, `Could not read ${f.name}. Use CSV or Excel.`)); }
 }
 function sample() { setData({ grid: parseCsv(sampleCsv()), name: 'buje_diametro.csv', sample: true }); setMeasure(null); setGroup(null); setLsl(String(SAMPLE_SPEC.lsl)); setUsl(String(SAMPLE_SPEC.usl)); setBase(SAMPLE_SPEC.base); setErr(''); setNote(''); }
 async function copy() {
  if (!c || !v) return;
  const lines = [`${data.grid.headers[mi]} · ${c.mode === 'I-MR' ? t('individuales', 'individuals') : t(`subgrupos de ${c.n}`, `subgroups of ${c.n}`)}`, v.text,
   `${t('Centro', 'Center')} ${fmt(c.cl)} · ${t('LSC', 'UCL')} ${fmt(c.ucl)} · ${t('LIC', 'LCL')} ${fmt(c.lcl)}`, cap ? `Cp ${fmt(cap.cp, 2)} · Cpk ${fmt(cap.cpk, 2)} · ${t('fuera de tolerancia', 'out of tolerance')}: ${cap.outside}` : '',
   ...byRule.map(([r, pts]) => `• ${RULES[r][L]}: ${pts.join(', ')}`)].filter(Boolean);
  try { await navigator.clipboard.writeText(lines.join('\n')); setNote(t('Resumen copiado.', 'Summary copied.')); } catch { setNote(''); }
 }

 return <div className="spc">
  <div className="spc-top">
   <div className="spc-file"><strong>{data.name}</strong><small>{all.length} {t('mediciones', 'measurements')}{data.sample ? t(' · ejemplo: diámetro de un buje, 5 piezas cada media hora', ' · sample: bushing diameter, 5 parts every half hour') : ''}</small></div>
   <div className="spc-actions"><input ref={input} type="file" accept={TABLE_ACCEPT} hidden onChange={e => { void load(e.target.files?.[0]); e.target.value = ''; }}/>
    <button className="dw-primary" onClick={() => input.current?.click()}><UploadSimple size={17}/>{t('Subir mediciones', 'Upload measurements')}</button>{!data.sample && <button onClick={sample}>{t('Volver al ejemplo', 'Back to sample')}</button>}</div>
  </div>
  {err && <p className="spc-err" role="alert">{err}</p>}
  <div className="spc-setup">
   <label>{t('Medición', 'Measurement')}<select value={mi} onChange={e => setMeasure(+e.target.value)}>{data.grid.headers.map((h, i) => <option key={i} value={i}>{h}</option>)}</select></label>
   <label>{t('Agrupar por', 'Group by')}<select value={gi} onChange={e => setGroup(+e.target.value)}><option value={-1}>{t('Cada fila es un punto', 'Each row is a point')}</option>{data.grid.headers.map((h, i) => i !== mi && <option key={i} value={i}>{h}</option>)}</select></label>
   <label>{t('Tolerancia mínima (LIE)', 'Lower spec (LSL)')}<input inputMode="decimal" value={lsl} placeholder="—" onChange={e => setLsl(e.target.value)}/></label>
   <label>{t('Tolerancia máxima (LSE)', 'Upper spec (USL)')}<input inputMode="decimal" value={usl} placeholder="—" onChange={e => setUsl(e.target.value)}/></label>
   <label>{t('Límites con', 'Limits from')}<select value={base} onChange={e => setBase(+e.target.value)}><option value={0}>{t('todos los puntos', 'all points')}</option>{[10, 15, 20, 25].filter(n => n < groups.length).map(n => <option key={n} value={n}>{t(`los primeros ${n}`, `the first ${n}`)}</option>)}</select></label>
  </div>
  {!c && <p className="spc-err">{t('Hacen falta al menos 5 mediciones numéricas en la columna elegida.', 'At least 5 numeric measurements are needed in the chosen column.')}</p>}
  {c && v && <>
   <section className={`spc-verdict ${v.control ? 'ok' : 'bad'}`}>
    <div className="spc-state">{v.control ? <CheckCircle size={30} weight="fill"/> : <WarningOctagon size={30} weight="fill"/>}<div><strong>{v.text}</strong><small>{c.mode === 'I-MR' ? t('Gráfica de individuales y rango móvil (I-MR)', 'Individuals and moving range chart (I-MR)') : t(`Gráfica X̄-R con subgrupos de ${c.n}`, `X̄-R chart, subgroups of ${c.n}`)}{c.base < c.points.length ? t(` · límites con los primeros ${c.base}`, ` · limits from the first ${c.base}`) : ''}</small></div></div>
    <dl className="spc-kpis">
     <div><dt>{t('Promedio', 'Mean')}</dt><dd>{fmt(c.mean)}</dd></div>
     <div><dt>σ</dt><dd>{fmt(c.sigma, 4)}</dd></div>
     {cap && <><div className={`cap-${cap.cpk >= 1.33 ? 'good' : cap.cpk >= 1 ? 'mid' : 'low'}`}><dt>Cpk</dt><dd>{fmt(cap.cpk, 2)}</dd></div>
      <div><dt>Cp</dt><dd>{fmt(cap.cp, 2)}</dd></div>
      <div className={cap.outside ? 'cap-low' : ''}><dt>{t('Fuera de tolerancia', 'Out of spec')}</dt><dd>{cap.outside}<small> / {all.length}</small></dd></div></>}
    </dl>
   </section>
   <div className="spc-charts" ref={charts}>
    <p className="spc-swipe">{t('Desliza la gráfica para ver las muestras anteriores.', 'Swipe the chart to see earlier samples.')}</p>
    <figure tabIndex={0} aria-label={t('Gráfica de control, se puede deslizar', 'Control chart, scrollable')}><figcaption>{c.mode === 'I-MR' ? t('Cada medición', 'Each measurement') : t('Promedio de cada muestra', 'Mean of each sample')}</figcaption><ControlChart c={c} kind="x" lsl={L1} usl={U1} es={es}/></figure>
    <figure tabIndex={0} aria-label={t('Gráfica de rangos, se puede deslizar', 'Range chart, scrollable')}><figcaption>{c.mode === 'I-MR' ? t('Rango móvil (cambio entre una pieza y la siguiente)', 'Moving range (change from one part to the next)') : t('Rango dentro de cada muestra', 'Range within each sample')}</figcaption><ControlChart c={c} kind="r" es={es}/></figure>
   </div>
   <div className="spc-split">
    <section className="spc-signals">
     <h3>{t('Qué avisa y qué revisar', 'What it flags and what to check')}</h3>
     {!byRule.length && !c.rangeOut.length && <p className="spc-okmsg"><CheckCircle size={18}/>{t('Ningún punto rompe las reglas: la variación es la normal del proceso.', 'No point breaks the rules: the variation is the process’s normal one.')}</p>}
     <ol>{byRule.map(([r, pts]) => <li key={r}><span className="spc-rule">{t('Regla', 'Rule')} {r}</span><div><strong>{RULES[r][L]}</strong><small>{t('Muestras', 'Samples')} {pts.join(', ')}</small><p>{MEANING[r][L]}</p></div></li>)}
      {c.rangeOut.length > 0 && <li><span className="spc-rule">R</span><div><strong>{t('Variación dentro de la muestra fuera de límite', 'Within-sample variation beyond its limit')}</strong><small>{t('Muestras', 'Samples')} {c.rangeOut.map(i => c.points[i].label).join(', ')}</small><p>{t('Las piezas de un mismo momento salieron muy distintas entre sí: sujeción floja, material disparejo o un error al medir.', 'Parts from the same moment came out very different: loose clamping, uneven material or a measuring error.')}</p></div></li>}</ol>
    </section>
    <section className="spc-dist">
     <h3>{t('Contra la tolerancia', 'Against the tolerance')}</h3>
     <Histogram values={all} lsl={L1} usl={U1} mean={c.mean} es={es}/>
     <p>{cap ? (cap.cpk >= 1.33 ? t('El proceso cabe en la tolerancia con margen (Cpk ≥ 1.33).', 'The process fits the tolerance with room (Cpk ≥ 1.33).') : cap.cpk >= 1 ? t('Cabe, pero justo: un corrimiento pequeño ya saca piezas (1 ≤ Cpk < 1.33).', 'It fits, barely: a small shift already produces bad parts (1 ≤ Cpk < 1.33).') : t('No cabe: aunque esté bajo control, saldrán piezas fuera de tolerancia (Cpk < 1).', 'It does not fit: even in control, parts will fall out of tolerance (Cpk < 1).')) : t('Escribe la tolerancia para saber si el proceso la alcanza.', 'Enter the tolerance to see if the process can hold it.')}</p>
     <button onClick={() => void copy()}><Copy size={16}/>{t('Copiar resumen', 'Copy summary')}</button>{note && <span className="spc-note" role="status">{note}</span>}
    </section>
   </div>
  </>}
 </div>;
}
