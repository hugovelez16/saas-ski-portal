// Logica pura del hook guardas-git (CLAUDE.md reglas 2 y 3, ADR-0002).
// Decide si un comando Bash debe bloquearse. Las consultas a git/gh se inyectan
// para poder probar sin red:
//   ramaActual(dir?)       rama de `dir` (o del directorio de la sesion)
//   baseDelPr(pr?, repo?)  rama base del PR
//   checksEnVerde(pr?, repo?)
// Es una red de seguridad, no una barrera completa (docs/flujo/git.md).
import { SHELLS, analizarShell, nombreComando, quitarPrefijos, segmentar, unirDir } from './bash.mjs';

export { segmentar };

const PROTEGIDAS = new Set(['main', 'develop']);
const GIT_OPCIONES_CON_VALOR = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path']);
const PUSH_OPCIONES_CON_VALOR = new Set(['--repo', '-o', '--push-option', '--receive-pack', '--exec']);
// Opciones largas de git push que nunca se permiten. git acepta abreviaturas
// no ambiguas (`--forc`, `--mir`), asi que se compara por prefijo.
const PUSH_PROHIBIDAS = ['force', 'force-with-lease', 'force-if-includes', 'mirror', 'all', 'branches'];
const MERGE_OPCIONES_CON_VALOR = new Set([
  '-R', '--repo', '-t', '--subject', '-b', '--body', '-F', '--body-file', '-A', '--author-email', '--match-head-commit',
]);
const GH_API_OPCIONES_CON_VALOR = new Set([
  '-X', '--method', '-f', '--raw-field', '-F', '--field', '-H', '--header', '--input', '-q', '--jq', '-t', '--template',
  '--hostname', '--cache', '-p', '--preview',
]);
// Escrituras que saltan la proteccion de ramas: merges, refs, contenidos,
// cualquier cambio sobre /branches (incluida su proteccion), rulesets y reviews.
const GH_API_RUTAS_PELIGROSAS =
  /\/(merge|merges)(\/|$|\?)|\/git\/refs|\/contents(\/|$|\?)|\/branches(\/|$|\?)|\/rulesets(\/|$|\?)|\/pulls\/\d+\/reviews/;
const GRAPHQL_PELIGROSAS =
  /mergePullRequest|updateRef|createRef|deleteRef|createCommitOnBranch|mergeBranch|enablePullRequestAutoMerge|BranchProtectionRule|Ruleset/;
// Subcomandos de git que empujan sin pasar por `git push`.
const GIT_PUSH_ALTERNATIVOS = new Set(['send-pack', 'http-push']);
// Expansiones que impiden saber el destino real del push.
const EXPANSION = /[$`]/;

function opcionPushProhibida(a) {
  const m = /^--([a-z-]+)(=.*)?$/.exec(a);
  if (!m) return false;
  const nombre = m[1];
  return nombre.length >= 2 && PUSH_PROHIBIDAS.some((p) => p.startsWith(nombre));
}

function evaluarPush(args, dir, consultas) {
  const posicionales = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (PUSH_OPCIONES_CON_VALOR.has(a)) {
      i++;
      continue;
    }
    if (opcionPushProhibida(a)) return `opcion de push prohibida (${a})`;
    if (/^-[A-Za-z]+$/.test(a) && a.includes('f')) return `force-push prohibido (${a})`;
    if (!a.startsWith('-')) posicionales.push(a);
  }
  for (const p of posicionales) {
    if (EXPANSION.test(p)) return `destino de push con expansion de shell (${p}); escribe la rama literal`;
  }
  const refspecs = posicionales.slice(1);
  for (const r of refspecs) {
    if (r.startsWith('+')) return `force-push prohibido (refspec ${r})`;
  }
  if (refspecs.length === 0) {
    const rama = consultas.ramaActual(dir);
    return PROTEGIDAS.has(rama) ? `push desde la rama protegida ${rama}` : null;
  }
  for (const r of refspecs) {
    let destino = (r.includes(':') ? r.split(':').pop() : r).replace(/^refs\/heads\//, '');
    if (destino.includes('*')) return `refspec con comodin prohibido (${r})`;
    if (destino === 'HEAD' || destino === '@') destino = consultas.ramaActual(dir);
    if (PROTEGIDAS.has(destino)) return `push directo a ${destino}`;
  }
  return null;
}

function evaluarGit(args, dir, consultas) {
  let i = 0;
  while (i < args.length && args[i].startsWith('-')) {
    if (args[i] === '-C') dir = unirDir(dir, args[i + 1] ?? '');
    if (args[i] === '-c' && /^alias\./i.test(args[i + 1] ?? '')) return 'alias de git en linea (-c alias.*) prohibido';
    if (GIT_OPCIONES_CON_VALOR.has(args[i])) i++;
    i++;
  }
  if (GIT_PUSH_ALTERNATIVOS.has(args[i])) return `git ${args[i]} prohibido: usa git push`;
  if (args[i] !== 'push') return null;
  return evaluarPush(args.slice(i + 1), dir, consultas);
}

function evaluarGhApi(args) {
  let metodo = null;
  let conCampos = false;
  let ruta = null;
  const valores = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const largo = /^(--[a-z-]+)=(.*)$/.exec(a);
    const opcion = largo ? largo[1] : a;
    const valorEnLinea = largo ? largo[2] : /^-X(.+)$/.exec(a)?.[1];
    if (opcion === '-X' || opcion === '--method' || /^-X./.test(a)) {
      metodo = (valorEnLinea ?? args[++i] ?? '').toUpperCase();
    } else if (['-f', '--raw-field', '-F', '--field', '--input'].includes(opcion)) {
      conCampos = true;
      valores.push(valorEnLinea ?? args[++i] ?? '');
    } else if (GH_API_OPCIONES_CON_VALOR.has(opcion)) {
      if (valorEnLinea === undefined) i++;
    } else if (!a.startsWith('-') && ruta === null) {
      ruta = a;
    }
  }
  if (ruta === null) return null;
  if (ruta === 'graphql') {
    return valores.some((v) => GRAPHQL_PELIGROSAS.test(v)) ? 'mutacion graphql de ramas o merge prohibida' : null;
  }
  const efectivo = metodo ?? (conCampos ? 'POST' : 'GET');
  if (efectivo !== 'GET' && efectivo !== 'HEAD' && GH_API_RUTAS_PELIGROSAS.test(ruta)) {
    return `gh api ${efectivo} sobre ${ruta} prohibido`;
  }
  return null;
}

function evaluarGh(args, consultas) {
  let repo;
  const resto = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-R' || args[i] === '--repo') repo = args[++i];
    else if (args[i].startsWith('--repo=')) repo = args[i].slice(7);
    else resto.push(args[i]);
  }
  if (resto[0] === 'api') return evaluarGhApi(resto.slice(1));
  if (resto[0] !== 'pr' || resto[1] !== 'merge') return null;
  let pr;
  const margs = resto.slice(2);
  for (let i = 0; i < margs.length; i++) {
    const a = margs[i];
    if (MERGE_OPCIONES_CON_VALOR.has(a)) i++;
    else if (/^--(squash|rebase)(=|$)/.test(a) || /^-[a-z]*[sr][a-z]*$/.test(a)) {
      return `solo se admite merge commit (--merge), no ${a} (ADR-0002)`;
    } else if (/^--admin(=|$)/.test(a)) {
      return '--admin salta la proteccion de ramas (ADR-0002)';
    } else if (!a.startsWith('-') && pr === undefined) pr = a;
  }
  if (consultas.baseDelPr(pr, repo) === 'main') return 'el merge a main lo hace solo el usuario (ADR-0002)';
  if (!consultas.checksEnVerde(pr, repo)) return 'hay checks que no estan en verde';
  return null;
}

export function evaluarComando(comando, consultas, dirInicial, profundidad = 0) {
  if (profundidad > 5) return { bloquear: true, motivo: 'anidamiento de shells demasiado profundo' };
  let dir = dirInicial;
  for (const crudo of segmentar(comando)) {
    const tokens = quitarPrefijos(crudo);
    if (tokens.length === 0) continue;
    const cmd = nombreComando(tokens[0]);
    const args = tokens.slice(1);
    let motivo = null;
    if (cmd === 'cd') {
      dir = unirDir(dir, args[0] ?? '');
    } else if (SHELLS.has(cmd)) {
      const shell = analizarShell(args);
      if (shell.tipo === 'c' || shell.tipo === 'herestring') {
        const r = evaluarComando(shell.codigo, consultas, dir, profundidad + 1);
        if (r.bloquear) return r;
      } else if (shell.tipo === 'stdin') {
        for (const cuerpo of tokens.heredocs) {
          const r = evaluarComando(cuerpo, consultas, dir, profundidad + 1);
          if (r.bloquear) return r;
        }
        if (tokens.heredocs.length === 0) motivo = `${cmd} leyendo comandos de stdin no se puede revisar`;
      }
    } else if (cmd === 'eval') {
      const r = evaluarComando(args.join(' '), consultas, dir, profundidad + 1);
      if (r.bloquear) return r;
    } else if ((cmd === 'git' || cmd === 'gh') && tokens.prefijos?.includes('xargs')) {
      motivo = 'xargs con git o gh: los argumentos no se pueden revisar';
    } else if (cmd === 'git') {
      motivo = evaluarGit(args, dir, consultas);
    } else if (cmd === 'gh') {
      motivo = evaluarGh(args, consultas);
    }
    if (motivo) return { bloquear: true, motivo };
  }
  return { bloquear: false };
}
