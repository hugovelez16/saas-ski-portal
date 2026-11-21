#!/usr/bin/env node
// Hook PreToolUse (Bash): bloquea push a main/develop, force-push, gh pr merge
// con base main, con checks sin verde, con squash/rebase o --admin, y gh api
// que escriba refs, contenidos o merges. Fail-closed: ante un error, bloquea.
import { execFileSync } from 'node:child_process';
import { evaluarComando } from './lib/guardas-git.mjs';

let entrada = '';
for await (const trozo of process.stdin) entrada += trozo;

let datos;
try {
  datos = JSON.parse(entrada);
} catch {
  process.stderr.write('[ERROR] guardas-git: entrada del hook no es JSON valido; se bloquea por seguridad.\n');
  process.exit(2);
}

const comando = datos.tool_input?.command;
if (typeof comando !== 'string') process.exit(0);

const ejecutar = (bin, args) =>
  execFileSync(bin, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
const conPr = (pr, repo, resto) => [...(pr ? [pr] : []), ...(repo ? ['--repo', repo] : []), ...resto];

const consultas = {
  ramaActual: (dir) => ejecutar('git', [...(dir ? ['-C', dir] : []), 'branch', '--show-current']),
  baseDelPr: (pr, repo) =>
    ejecutar('gh', ['pr', 'view', ...conPr(pr, repo, ['--json', 'baseRefName', '-q', '.baseRefName'])]),
  checksEnVerde: (pr, repo) => {
    let salida;
    try {
      salida = ejecutar('gh', ['pr', 'checks', ...conPr(pr, repo, ['--json', 'bucket'])]);
    } catch (e) {
      // gh pr checks sale con codigo != 0 si hay checks fallidos o pendientes.
      salida = e.stdout?.toString().trim() ?? '';
    }
    const checks = JSON.parse(salida || '[]');
    return checks.length > 0 && checks.every((c) => c.bucket === 'pass' || c.bucket === 'skipping');
  },
};

let resultado;
try {
  resultado = evaluarComando(comando, consultas, typeof datos.cwd === 'string' ? datos.cwd : undefined);
} catch (e) {
  resultado = { bloquear: true, motivo: `no se pudo evaluar el comando (${e.message.split('\n')[0]})` };
}

if (resultado.bloquear) {
  process.stderr.write(`[ERROR] Comando bloqueado por guardas-git: ${resultado.motivo}. Ver CLAUDE.md reglas 2 y 3.\n`);
  process.exit(2);
}
