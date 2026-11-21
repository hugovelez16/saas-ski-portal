#!/usr/bin/env node
// Hook PreToolUse (Edit, Write, NotebookEdit, Bash): impide modificar ficheros
// de un repositorio cuya rama activa es main o develop (CLAUDE.md regla 2).
// - Edit/Write: se evalua la rama del directorio del fichero, no la de la
//   sesion, de modo que se puede editar un worktree desde el checkout principal.
// - Bash: bloquea sed -i, redirecciones > y >>, tee, cp/mv/touch hacia el repo
//   y git commit/cherry-pick/revert/am/apply/merge (salvo --ff-only) en
//   main/develop. git fetch/pull/status/log/worktree, ./bin/*, tests y la
//   escritura fuera del repo (scratchpad, /tmp) no se bloquean.
// Fail-closed: si la entrada no se puede evaluar, bloquea.
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname } from 'node:path';
import { RAMAS_PROTEGIDAS, evaluarBash } from './lib/proteger-ramas.mjs';

const cache = new Map();
const ramaDe = (dir) => {
  if (!cache.has(dir)) {
    let rama = null;
    try {
      rama = execFileSync('git', ['-C', dir, 'branch', '--show-current'], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim();
    } catch {
      rama = null; // fuera de un repositorio git: no aplica
    }
    cache.set(dir, rama);
  }
  return cache.get(dir);
};

const bloquear = (mensaje) => {
  process.stderr.write(
    `[ERROR] proteger-ramas: ${mensaje}. ` +
      'Trabaja en una rama <tipo>/<n>-<descripcion> dentro de un worktree (skills issue-start e issue-work).\n',
  );
  process.exit(2);
};

let entrada = '';
for await (const trozo of process.stdin) entrada += trozo;

try {
  const datos = JSON.parse(entrada);
  const params = datos.tool_input ?? {};

  if (datos.tool_name === 'Bash') {
    if (typeof params.command === 'string') {
      const motivo = evaluarBash(params.command, typeof datos.cwd === 'string' ? datos.cwd : undefined, ramaDe);
      if (motivo) bloquear(motivo);
    }
    process.exit(0);
  }

  const fichero = params.file_path ?? params.notebook_path;
  if (!fichero) process.exit(0);

  // El fichero puede no existir todavia: subir hasta el primer directorio existente.
  let directorio = dirname(fichero);
  while (!existsSync(directorio) && dirname(directorio) !== directorio) {
    directorio = dirname(directorio);
  }
  const rama = ramaDe(directorio);
  if (rama && RAMAS_PROTEGIDAS.has(rama)) {
    bloquear(`edicion bloqueada: '${directorio}' esta en la rama protegida '${rama}'`);
  }
} catch (e) {
  bloquear(`no se pudo evaluar la entrada (${String(e.message).split('\n')[0]})`);
}
