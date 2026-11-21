// Fuzz de clases de corchetes: todo patron que bash expande a un fichero
// protegido (.env, *.pem, *.key) debe ser bloqueado por el hook. Semilla fija.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { evaluarBash } from '../../.claude/hooks/lib/bloquear-env.mjs';

function mulberry32(a) {
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const L = '\x5b';
const R = '\x5d';
const TOKENS = [
  L, R, '\\', '\\\\', 'n', 'a', 'e', 'm', 'p', 'k', 'y', 'z', 'o', '-', '!', '^',
  '[:alpha:]', '[:lower:]', '[.n.]', '[=n=]', '\\]',
];
const FORMAS = [
  (c) => `.e${c}v`, (c) => `.${c}nv`, (c) => `.en${c}`, (c) => `.e${c}${c}`, (c) => `.e${c}${R}v`,
  (c) => `*.p${c}m`, (c) => `*.${c}em`, (c) => `*.pe${c}`,
  (c) => `*.k${c}y`, (c) => `*.${c}ey`, (c) => `*.ke${c}`,
];
const PROTEGIDOS = new Set(['.env', 'private.pem', 'server.key']);

test('glob-fuzz: lo que bash expande a un fichero protegido se bloquea', () => {
  const rnd = mulberry32(81);
  const pick = () => TOKENS[Math.floor(rnd() * TOKENS.length)];
  const patrones = [];
  for (let i = 0; i < 2000; i++) {
    let c = L;
    const k = 1 + Math.floor(rnd() * 5);
    for (let j = 0; j < k; j++) c += pick();
    if (rnd() < 0.9) c += R;
    patrones.push(FORMAS[Math.floor(rnd() * FORMAS.length)](c));
  }
  const dir = mkdtempSync(join(tmpdir(), 'glob-fuzz-'));
  const vacio = mkdtempSync(join(tmpdir(), 'glob-fuzz-vacio-'));
  try {
    for (const f of PROTEGIDOS) writeFileSync(join(dir, f), '');
    // Un solo bash para todos los patrones; cada linea va precedida de marcador.
    const guion = patrones.map((p, i) => `echo @@${i}\nprintf '%s\\n' ${p} ;`).join('\n');
    const r = spawnSync('bash', ['-O', 'nullglob', '-c', guion], { cwd: dir, encoding: 'utf8' });
    const expansiones = new Map();
    let actual = -1;
    for (const linea of r.stdout.split('\n')) {
      const m = /^@@(\d+)$/.exec(linea);
      if (m) actual = Number(m[1]);
      else if (actual >= 0 && linea) expansiones.set(actual, [...(expansiones.get(actual) ?? []), linea]);
    }
    let expanden = 0;
    const fallos = [];
    for (const [i, salida] of expansiones) {
      if (!salida.some((f) => PROTEGIDOS.has(f))) continue;
      expanden++;
      // cwd vacio: solo cuenta el analisis del patron, no la expansion en disco.
      if (!evaluarBash(`cat ${patrones[i]}`, vacio)) fallos.push(patrones[i]);
    }
    assert.ok(expanden > 20, `fuzz sin cobertura: solo ${expanden} patrones expanden`);
    assert.deepEqual(fallos.slice(0, 10), [], `bypasses: ${fallos.length}`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
    rmSync(vacio, { recursive: true, force: true });
  }
});
