// Logica del hook proteger-ramas (CLAUDE.md regla 2). Decide si un comando Bash
// escribe ficheros de un repositorio cuya rama activa es main o develop.
// Consulta inyectada para poder probar: ramaDe(dir) -> rama o null si `dir`
// no esta en un repositorio git.
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { SHELLS, analizarShell, nombreComando, quitarPrefijos, segmentar, unirDir } from './bash.mjs';

export const RAMAS_PROTEGIDAS = new Set(['main', 'develop']);
const GIT_OPCIONES_CON_VALOR = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path']);
const GIT_ESCRITURA = new Set(['commit', 'cherry-pick', 'revert', 'am', 'apply']);

function directorioExistente(ruta) {
  let d = ruta;
  while (!existsSync(d) && dirname(d) !== d) d = dirname(d);
  return d;
}

// Expande `~`, `$HOME` y las variables asignadas antes en el mismo comando
// (`D=/tmp/x; echo > $D/f`). Devuelve null si queda una expansion sin resolver.
function expandirRuta(ruta, vars) {
  // Si el propio comando redefine HOME, `~` y `$HOME` apuntan ahi.
  const home = Object.hasOwn(vars, 'HOME') ? vars.HOME : homedir();
  // `~usuario/` no se resuelve: se trata como expansion sin resolver.
  if (/^~[^/]/.test(ruta)) return null;
  let r = ruta.replace(/^~(?=\/|$)/, home);
  r = r.replace(/\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)/g, (m, a, b) => {
    const nombre = a ?? b;
    if (Object.hasOwn(vars, nombre)) return vars[nombre];
    if (nombre === 'HOME') return home;
    if (nombre === 'TMPDIR' || nombre === 'TMP') return process.env[nombre] ?? '/tmp';
    return m;
  });
  return /[$`]/.test(r) ? null : r;
}

function ramaProtegidaDeRuta(ruta, cwd, ramaDe, vars = {}) {
  const base = cwd ?? process.cwd();
  const expandida = expandirRuta(ruta, vars);
  if (expandida === null) {
    // Sin resolver no se sabe donde escribe. Solo se permite si el directorio
    // actual esta en una rama de trabajo (el worktree del propio agente);
    // en main, develop o fuera de un repo se bloquea.
    const rama = ramaDe(directorioExistente(base));
    return rama && !RAMAS_PROTEGIDAS.has(rama) ? null : { rama: rama ?? 'desconocida', sinResolver: true };
  }
  const abs = resolve(base, expandida);
  const dir = directorioExistente(existsSync(abs) ? dirname(abs) : abs);
  const rama = ramaDe(dir);
  return rama && RAMAS_PROTEGIDAS.has(rama) ? { rama, sinResolver: false } : null;
}

function motivoRuta(accion, ruta, r) {
  return r.sinResolver
    ? `${accion} '${ruta}' con una expansion que no se puede resolver, fuera de una rama de trabajo (rama ${r.rama}). Escribe la ruta literal`
    : `${accion} '${ruta}' en la rama protegida ${r.rama}`;
}

// Formas de asignar o de ejecutar condicionalmente que el hook no sigue:
// read, declare, printf -v, for, `+=`, subshells y `$(...)`, `||`, `&&`.
// Si aparece alguna, ninguna variable se da por resuelta.
const ASIGNACION_OPACA =
  /\b(read|declare|typeset|local|readonly|mapfile|readarray|for|select|eval|let)\b|printf\s+-v|\+=|\(|\|\||&&/;

// Asignaciones al inicio de un segmento (`D=/x` o `export D=/x`). Una variable
// asignada dos veces queda indeterminada.
function registrarAsignaciones(tokens, vars, vistas) {
  let i = nombreComando(tokens[0] ?? '') === 'export' ? 1 : 0;
  for (; i < tokens.length; i++) {
    const m = /^([A-Za-z_]\w*)=(.*)$/.exec(tokens[i]);
    if (!m) break;
    const nombre = m[1];
    const valor = expandirRuta(m[2], vars);
    if (vistas.has(nombre) || valor === null) delete vars[nombre];
    else vars[nombre] = valor;
    vistas.add(nombre);
  }
}

// Destinos de redirecciones (> y >>) sin comillas; ignora duplicados de fd (>&2).
function destinosRedireccion(tokens) {
  const destinos = [];
  for (let i = 0; i < tokens.length; i++) {
    if (tokens.citado?.[i]) continue;
    const t = tokens[i];
    const idx = t.indexOf('>');
    if (idx < 0) continue;
    let destino = t.slice(idx).replace(/^>>?\|?/, '');
    if (destino === '') destino = tokens[i + 1] ?? '';
    if (destino === '' || destino.startsWith('&')) continue;
    destinos.push(destino);
  }
  return destinos;
}

function ficherosDe(cmd, args) {
  const posicionales = args.filter((a) => !a.startsWith('-'));
  if (cmd === 'sed') {
    const enSitio = args.some((a) => a === '--in-place' || a.startsWith('--in-place=') || /^-[a-zA-Z]*i/.test(a));
    if (!enSitio) return [];
    const conScript = args.some((a) => a === '-e' || a === '-f' || a.startsWith('--expression'));
    return conScript ? posicionales : posicionales.slice(1);
  }
  if (cmd === 'tee') return posicionales;
  if (cmd === 'cp' || cmd === 'mv' || cmd === 'install') return posicionales.slice(-1);
  if (cmd === 'touch' || cmd === 'truncate') return posicionales;
  return [];
}

function evaluarGit(args, dir, ramaDe) {
  let i = 0;
  while (i < args.length && args[i].startsWith('-')) {
    if (args[i] === '-C') dir = unirDir(dir, args[i + 1] ?? '');
    if (GIT_OPCIONES_CON_VALOR.has(args[i])) i++;
    i++;
  }
  const sub = args[i];
  const escribe = GIT_ESCRITURA.has(sub) || (sub === 'merge' && !args.includes('--ff-only') && !args.includes('--abort'));
  if (!escribe) return null;
  const rama = ramaDe(dir ?? process.cwd());
  return rama && RAMAS_PROTEGIDAS.has(rama) ? `git ${sub} en la rama protegida ${rama}` : null;
}

// `vistasExternas`: variables ya asignadas en el shell exterior. Si el codigo
// interior (`sh -c "D=/tmp; echo > $D/f"`) las reasigna, quedan sin resolver,
// porque con comillas dobles el exterior las expande antes.
export function evaluarBash(comando, cwdInicial, ramaDe, profundidad = 0, vistasExternas = []) {
  if (profundidad > 5) return 'anidamiento de shells demasiado profundo';
  let cwd = cwdInicial;
  const vars = {};
  const vistas = new Set(vistasExternas);
  const fiable = !ASIGNACION_OPACA.test(comando);
  let cwdDesconocido = false;
  for (const crudo of segmentar(comando)) {
    if (fiable) registrarAsignaciones(crudo, vars, vistas);
    const tokens = quitarPrefijos(crudo);
    for (const destino of destinosRedireccion(crudo)) {
      if (cwdDesconocido && !/^[/~$]/.test(destino)) return `redireccion a '${destino}' tras un cd sin resolver. Escribe la ruta literal`;
      const r = ramaProtegidaDeRuta(destino, cwd, ramaDe, vars);
      if (r) return motivoRuta('redireccion a', destino, r);
    }
    if (tokens.length === 0) continue;
    const cmd = nombreComando(tokens[0]);
    const args = tokens.slice(1).filter((a, i) => !/>/.test(a) || tokens.citado?.[i + 1]);
    if (cmd === 'cd') {
      const destino = expandirRuta(args[0] ?? '', vars);
      if (destino === null) cwdDesconocido = true;
      else cwd = unirDir(cwd, destino);
      continue;
    }
    const gitEscribe = cmd === 'git' && evaluarGit(args, cwd, () => 'develop') !== null;
    if (cwdDesconocido && (gitEscribe || ficherosDe(cmd, args).length > 0)) {
      return `${cmd} tras un cd sin resolver: no se sabe en que rama escribe. Escribe la ruta literal`;
    }
    if (SHELLS.has(cmd)) {
      const shell = analizarShell(args);
      const codigos = shell.tipo === 'c' || shell.tipo === 'herestring' ? [shell.codigo] : shell.tipo === 'stdin' ? tokens.heredocs : [];
      for (const codigo of codigos) {
        const motivo = evaluarBash(codigo, cwd, ramaDe, profundidad + 1, [...vistas]);
        if (motivo) return motivo;
      }
      continue;
    }
    if (cmd === 'git') {
      const motivo = evaluarGit(args, cwd, ramaDe);
      if (motivo) return motivo;
      continue;
    }
    for (const fichero of ficherosDe(cmd, args)) {
      const r = ramaProtegidaDeRuta(fichero, cwd, ramaDe, vars);
      if (r) return motivoRuta(`${cmd} escribe`, fichero, r);
    }
  }
  return null;
}
