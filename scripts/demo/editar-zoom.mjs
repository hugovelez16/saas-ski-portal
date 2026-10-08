// Aplica zoom suave a los dialogos del video grabado y lo exporta.
// Los instantes de apertura/cierre se leen del propio video: grabar-demo.mjs pinta un marcador
// magenta de 4x4 px en la esquina mientras hay un dialogo abierto.
// Uso: node editar-zoom.mjs   (variables: FORMATO=webm|mp4, OFFSET_MS, TRANSICION_MS)
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const DIR = process.env.OUT_DIR ?? 'videos';
const ENTRADA = `${DIR}/demo-presentacion.webm`;
const FORMATO = process.env.FORMATO ?? 'webm'; // webm (VP9) por defecto; FORMATO=mp4 para la exportacion final
const SALIDA = `${DIR}/demo-presentacion-zoom.${FORMATO}`;
const W = 1920;
const H = 1080;
const OFFSET = Number(process.env.OFFSET_MS ?? 0) / 1000;
const TRANS = Number(process.env.TRANSICION_MS ?? 700) / 1000;

const { eventos } = JSON.parse(readFileSync(`${DIR}/demo-presentacion.zoom.json`, 'utf8'));
const entradas = eventos.filter((e) => e.tipo === 'in');

// Lee el marcador fotograma a fotograma: VAVG alto (magenta) = dialogo abierto
const sonda = spawnSync(
  'ffmpeg',
  [
    '-v', 'error', '-i', ENTRADA,
    '-vf', 'crop=2:2:1:1,signalstats,metadata=print:key=lavfi.signalstats.VAVG:file=-',
    '-an', '-f', 'null', '-',
  ],
  { encoding: 'utf8', maxBuffer: 1 << 28 },
);
const aperturas = [];
const cierres = [];
{
  let tiempo = 0;
  let abierto = false;
  for (const linea of sonda.stdout.split('\n')) {
    const mt = linea.match(/pts_time:([0-9.]+)/);
    if (mt) tiempo = parseFloat(mt[1]);
    const mv = linea.match(/VAVG=([0-9.]+)/);
    if (!mv) continue;
    const ahoraAbierto = parseFloat(mv[1]) > 190;
    if (ahoraAbierto && !abierto) aperturas.push(tiempo);
    if (!ahoraAbierto && abierto) cierres.push(tiempo);
    abierto = ahoraAbierto;
  }
}
console.log(`[INFO] marcador: ${aperturas.length} aperturas, ${cierres.length} cierres; eventos: ${entradas.length}`);
if (aperturas.length !== entradas.length || cierres.length !== entradas.length) {
  console.error('[ERROR] el numero de dialogos detectados en el video no coincide con los eventos grabados');
  process.exit(1);
}

// Cada zoom arranca un instante despues de abrirse el dialogo y termina al cerrarse
const tramos = entradas.map((e, i) => ({ ...e, a: aperturas[i] + 0.2 + OFFSET, b: cierres[i] + OFFSET }));
for (const s of tramos) console.log(`[INFO] zoom ${s.a.toFixed(2)} s -> ${s.b.toFixed(2)} s`);

// smoothstep acotado: 0 antes de x0, 1 despues de x0+d
const ss = (x0, d) => `(clip((t-${x0.toFixed(3)})/${d},0,1)*clip((t-${x0.toFixed(3)})/${d},0,1)*(3-2*clip((t-${x0.toFixed(3)})/${d},0,1)))`;
// Peso 0..1 del tramo: sube en [a, a+TRANS], baja en [b, b+TRANS]
const peso = (s) => `(${ss(s.a, TRANS)}-${ss(s.b, TRANS)})`;

const zExpr = tramos.length ? `1${tramos.map((s) => `+${(s.z - 1).toFixed(3)}*${peso(s)}`).join('')}` : '1';
const cxExpr = `${W / 2}${tramos.map((s) => `+${s.cx - W / 2}*${peso(s)}`).join('')}`;
const cyExpr = `${H / 2}${tramos.map((s) => `+${s.cy - H / 2}*${peso(s)}`).join('')}`;

// Escala por frame y recorta centrando el punto de interes.
// El maximo de x/y se calcula con la expresion de zoom: `iw` en crop se fija al iniciar el filtro.
const filtro =
  `fps=30,scale=w='${W}*(${zExpr})':h='${H}*(${zExpr})':eval=frame:flags=bicubic,` +
  `crop=${W}:${H}:x='clip((${cxExpr})*(${zExpr})-${W / 2},0,${W}*((${zExpr})-1))':` +
  `y='clip((${cyExpr})*(${zExpr})-${H / 2},0,${H}*((${zExpr})-1))',format=yuv420p`;

const scriptPath = `${DIR}/filtro-zoom.txt`;
writeFileSync(scriptPath, filtro);

const codec =
  FORMATO === 'mp4'
    ? ['-c:v', 'libopenh264', '-profile:v', 'high', '-b:v', '8M', '-g', '30', '-movflags', '+faststart']
    : ['-c:v', 'libvpx-vp9', '-crf', '30', '-b:v', '0', '-row-mt', '1', '-cpu-used', '4'];

const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', ENTRADA, '-filter_script:v', scriptPath, ...codec, SALIDA], {
  stdio: 'inherit',
});
if (r.status !== 0) process.exit(r.status ?? 1);
console.log(`OK ${SALIDA} (${tramos.length} zooms)`);
