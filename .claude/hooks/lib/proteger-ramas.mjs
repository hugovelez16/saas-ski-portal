// Logica del hook proteger-ramas (CLAUDE.md regla 2). Decide si un comando Bash
// escribe ficheros de un repositorio cuya rama activa es main o develop.
// Consulta inyectada para poder probar: ramaDe(dir) -> rama o null si `dir`
// no esta en un repositorio git.
import { existsSync } from 'node:fs';
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

function ramaProtegidaDeRuta(ruta, cwd, ramaDe) {
  const abs = resolve(cwd ?? process.cwd(), ruta);
  const dir = directorioExistente(existsSync(abs) ? dirname(abs) : abs);
  const rama = ramaDe(dir);
  return rama && RAMAS_PROTEGIDAS.has(rama) ? rama : null;
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

export function evaluarBash(comando, cwdInicial, ramaDe, profundidad = 0) {
  if (profundidad > 5) return 'anidamiento de shells demasiado profundo';
  let cwd = cwdInicial;
  for (const crudo of segmentar(comando)) {
    const tokens = quitarPrefijos(crudo);
    for (const destino of destinosRedireccion(crudo)) {
      const rama = ramaProtegidaDeRuta(destino, cwd, ramaDe);
      if (rama) return `redireccion a '${destino}' en la rama protegida ${rama}`;
    }
    if (tokens.length === 0) continue;
    const cmd = nombreComando(tokens[0]);
    const args = tokens.slice(1).filter((a, i) => !/>/.test(a) || tokens.citado?.[i + 1]);
    if (cmd === 'cd') {
      cwd = unirDir(cwd, args[0] ?? '');
      continue;
    }
    if (SHELLS.has(cmd)) {
      const shell = analizarShell(args);
      const codigos = shell.tipo === 'c' || shell.tipo === 'herestring' ? [shell.codigo] : shell.tipo === 'stdin' ? tokens.heredocs : [];
      for (const codigo of codigos) {
        const motivo = evaluarBash(codigo, cwd, ramaDe, profundidad + 1);
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
      const rama = ramaProtegidaDeRuta(fichero, cwd, ramaDe);
      if (rama) return `${cmd} escribe '${fichero}' en la rama protegida ${rama}`;
    }
  }
  return null;
}
