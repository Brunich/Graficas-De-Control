# Gráficas de control (SPC)

[![CI](https://github.com/Brunich/graficas-de-control/actions/workflows/ci.yml/badge.svg)](https://github.com/Brunich/graficas-de-control/actions/workflows/ci.yml)

*Saber si la máquina se está desajustando antes de que salga pieza mala.*

Subes las mediciones de una pieza y dice si el proceso está bajo control, qué puntos avisan que algo cambió y si alcanza la tolerancia (Cp y Cpk). En palabras, con qué revisar primero.

![Captura de Gráficas de control (SPC)](docs/captura.png)

**Pruébalo en vivo:** [bruno-portfolio-azure.vercel.app/proyectos/graficas-de-control](https://bruno-portfolio-azure.vercel.app/proyectos/graficas-de-control)

## Cómo funciona

1. **Sube.** Un CSV o Excel con las mediciones. Si trae una columna de muestra o subgrupo, arma la gráfica X̄-R; si no, la de individuales.
2. **Vigila.** Calcula los límites con un periodo estable y marca los puntos que rompen alguna de las cinco reglas: fuera de límite, tendencia, corrimiento…
3. **Decide.** Te dice qué suele significar cada señal y si el proceso cabe en la tolerancia, con Cp, Cpk y las piezas que ya salieron.

## Qué hay adentro

| Archivo | Qué hace |
| --- | --- |
| `src/spc-logic.ts` | Límites de control (constantes de Shewhart), las cinco reglas de Western Electric, Cp/Cpk/Pp/Ppk y el veredicto en palabras. Sin interfaz, con pruebas. |
| `src/Spc.tsx` | Subir mediciones, elegir columna, subgrupo y tolerancia; la gráfica de promedios y la de rangos en SVG, las señales con qué revisar y el histograma contra la tolerancia. |
| `src/csv.ts` | Lector de CSV compartido con el analizador. |

La lógica está separada de la interfaz, así se prueba sin navegador (`tests/`).

## Decisiones

- Con columna de muestra o subgrupo se arma X̄-R; sin ella, individuales y rango móvil (I-MR).
- Los límites pueden salir de un periodo base: si el cálculo incluye el problema, los límites se abren y lo esconden.
- Cp/Cpk usan la variación de corto plazo (la de la gráfica) y Pp/Ppk la total.
- Control y capacidad se reportan aparte: un proceso puede avisar que cambió y todavía cumplir la tolerancia.

## Correrlo

```bash
npm install
npm run dev
```

```bash
npm test        # pruebas de la lógica (node:test)
npm run build   # tipos + build de producción
```

Hecho con React 19, TypeScript y Vite. Necesita Node 22 o más nuevo (las pruebas corren TypeScript directo con Node).

## Lo que sigue

- Gráficas p y c para defectos por atributo.
- Exportar la gráfica como imagen para el reporte del turno.

---

Parte del [portafolio de Bruno Salas](https://bruno-portfolio-azure.vercel.app) · [GitHub](https://github.com/Brunich)
