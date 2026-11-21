// Parser de shell minimo compartido por los hooks (guardas-git, bloquear-env,
// proteger-ramas). No es un shell completo: es una red de seguridad. La
// proteccion real es permissions.deny de .claude/settings.json y la proteccion
// de ramas de GitHub (docs/flujo/git.md).
import { basename, isAbsolute, join } from 'node:path';

export const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh', 'fish']);
const PREFIJOS = new Set(['env', 'command', 'sudo', 'time', 'nohup', 'exec', 'builtin', 'timeout', 'nice', 'xargs', 'doas', 'stdbuf']);
// Opciones de cada prefijo que consumen el token siguiente.
const PREFIJOS_OPCIONES_CON_VALOR = {
  sudo: new Set(['-u', '-g', '-C', '-h', '-p', '-U', '-T', '-D', '-R']),
  env: new Set(['-u', '-C', '-S']),
  timeout: new Set(['-s', '-k', '--signal', '--kill-after']),
  nice: new Set(['-n']),
  xargs: new Set(['-I', '-n', '-P', '-d', '-E', '-L', '-s', '-a', '-l']),
};

// Nombre normalizado de un comando: sin barra invertida inicial y sin ruta
// (`\git`, `/usr/bin/git` -> `git`).
export const nombreComando = (t) => basename(String(t).replace(/^\\+/, ''));

export const unirDir = (dir, ruta) => (isAbsolute(ruta) || dir === undefined ? ruta : join(dir, ruta));

// Divide en segmentos por &&, ||, ;, |, ( y ) fuera de comillas, y tokeniza
// cada uno. Cada segmento es un array de tokens (comillas ya resueltas) con
// dos propiedades:
//   citado[i]  true si el token i llevaba comillas (no es un operador)
//   heredocs   cuerpos de los heredocs que alimentan al segmento
//   operador   operador que precede al segmento ('|' si recibe una tuberia)
export function segmentar(comando) {
  const segmentos = [];
  let tokens = [];
  let citado = [];
  let heredocsSeg = [];
  let operadorPrevio = null;
  let actual = '';
  let enToken = false;
  let conComillas = false;
  let comilla = null;
  const cerrarToken = () => {
    if (enToken) {
      tokens.push(actual);
      citado.push(conComillas);
    }
    actual = '';
    enToken = false;
    conComillas = false;
  };
  const cerrarSegmento = (siguienteOperador = null) => {
    cerrarToken();
    if (tokens.length || heredocsSeg.length) {
      tokens.citado = citado;
      tokens.heredocs = heredocsSeg;
      tokens.operador = operadorPrevio;
      segmentos.push(tokens);
    }
    tokens = [];
    citado = [];
    heredocsSeg = [];
    operadorPrevio = siguienteOperador;
  };
  let pendientes = [];
  for (let i = 0; i < comando.length; i++) {
    const c = comando[i];
    if (!comilla && c === '<' && comando[i + 1] === '<' && comando[i + 2] !== '<') {
      const m = /^<<(-?)[ \t]*(?:'([^']*)'|"([^"]*)"|\\?([^\s;|&<>()'"]+))/.exec(comando.slice(i));
      if (m) {
        cerrarToken();
        tokens.push('<<');
        citado.push(false);
        pendientes.push({ guion: m[1] === '-', marca: m[2] ?? m[3] ?? m[4], segmento: tokens });
        i += m[0].length - 1;
        continue;
      }
    }
    if (!comilla && c === '\n' && pendientes.length) {
      // El cuerpo de cada heredoc se guarda aparte: no son comandos del shell
      // actual, pero si los lee un shell (bash <<EOF) hay que evaluarlos.
      const segActual = tokens;
      cerrarToken();
      let pos = i + 1;
      for (const { guion, marca, segmento } of pendientes) {
        const lineas = [];
        while (pos < comando.length) {
          let fin = comando.indexOf('\n', pos);
          if (fin < 0) fin = comando.length;
          const linea = comando.slice(pos, fin);
          pos = fin + 1;
          if ((guion ? linea.replace(/^\t+/, '') : linea) === marca) break;
          lineas.push(linea);
        }
        if (segmento === segActual) heredocsSeg.push(lineas.join('\n'));
        else (segmento.heredocs ??= []).push(lineas.join('\n'));
      }
      pendientes = [];
      cerrarSegmento();
      i = pos - 1;
      continue;
    }
    if (comilla) {
      if (c === comilla) comilla = null;
      else if (c === '\\' && comilla === '"' && '$`"\\\n'.includes(comando[i + 1] ?? '')) {
        if (comando[++i] !== '\n') actual += comando[i];
      } else actual += c;
    } else if (c === '\\' && i + 1 < comando.length) {
      // Fuera de comillas, \x es x y \<salto> continua la linea.
      if (comando[++i] !== '\n') {
        actual += comando[i];
        enToken = true;
      }
    } else if (c === '"' || c === "'") {
      comilla = c;
      enToken = true;
      conComillas = true;
    } else if (';|&\n()'.includes(c)) {
      const doble = (c === '&' || c === '|') && comando[i + 1] === c;
      if (doble) i++;
      // `2>&1` o `&>`: el & forma parte de una redireccion, no separa.
      if (c === '&' && !doble && (/[<>]$/.test(actual) || comando[i + 1] === '>')) {
        actual += c;
        enToken = true;
        continue;
      }
      cerrarSegmento(c === '|' && !doble ? '|' : null);
    } else if (/\s/.test(c)) {
      cerrarToken();
    } else {
      actual += c;
      enToken = true;
    }
  }
  if (comilla) throw new Error('comillas sin cerrar');
  cerrarSegmento();
  return segmentos;
}

// Quita prefijos (env, sudo, VAR=valor...) y devuelve el resto del segmento.
// Conserva la marca de comillas en `citado`.
export function quitarPrefijos(tokens) {
  let i = 0;
  let prefijo = null;
  let duracionPendiente = false;
  const prefijos = [];
  while (i < tokens.length) {
    const t = nombreComando(tokens[i]);
    if (PREFIJOS.has(t) && !tokens.citado?.[i]) {
      prefijo = t;
      prefijos.push(t);
      duracionPendiente = t === 'timeout';
      i++;
    } else if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[i])) {
      i++;
    } else if (prefijo && tokens[i].startsWith('-')) {
      i += PREFIJOS_OPCIONES_CON_VALOR[prefijo]?.has(tokens[i]) ? 2 : 1;
    } else if (duracionPendiente && /^\d/.test(tokens[i])) {
      duracionPendiente = false;
      i++;
    } else break;
  }
  const resto = tokens.slice(i);
  resto.citado = (tokens.citado ?? []).slice(i);
  resto.heredocs = tokens.heredocs ?? [];
  resto.operador = tokens.operador ?? null;
  // Prefijos quitados (env, xargs...): los hooks los necesitan para decidir.
  resto.prefijos = prefijos;
  return resto;
}

// Analiza un shell (bash, sh...) del segmento. Devuelve:
//   { tipo: 'c', codigo }      bash -c "<codigo>"
//   { tipo: 'herestring', codigo }  bash <<< "<codigo>"
//   { tipo: 'script' }         bash fichero.sh (o -n: solo sintaxis)
//   { tipo: 'stdin' }          lee comandos de stdin (tuberia, heredoc, -s, -)
export function analizarShell(args, segmento) {
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '<<<') return { tipo: 'herestring', codigo: args[i + 1] ?? '' };
    if (a.startsWith('<<<')) return { tipo: 'herestring', codigo: a.slice(3) };
    if (/^-[A-Za-z]*c[A-Za-z]*$/.test(a)) return { tipo: 'c', codigo: args[i + 1] ?? '' };
    if (a === '-s' || a === '-' || a === '--') return { tipo: 'stdin' };
    if (a === '-o' || a === '+o' || a === '-O' || a === '+O') {
      i++;
      continue;
    }
    if (a.startsWith('-') || a.startsWith('+')) continue;
    if (a === '<<') return { tipo: 'stdin' };
    if (/^\d*</.test(a)) return { tipo: 'stdin' };
    return { tipo: 'script' };
  }
  void segmento;
  return { tipo: 'stdin' };
}
