// Logica del hook bloquear-env (CLAUDE.md regla 9). Red de seguridad: la
// barrera real es permissions.deny de .claude/settings.json.
// Protege .env* (salvo .env.example), backend/keys/, *.pem, *.key y claves SSH.
import { existsSync, readdirSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { isAbsolute, join, relative, resolve } from 'node:path';
import { SHELLS, analizarShell, nombreComando, quitarPrefijos, segmentar, unirDir } from './bash.mjs';

const NOMBRES_CLAVE = /^(id_rsa|id_ecdsa|id_ed25519|id_dsa)$/;

export function esSensible(ruta) {
  const limpia = String(ruta).replace(/^["']|["']$/g, '');
  const segs = limpia.split(/[\\/]+/).filter(Boolean);
  const nombre = segs.at(-1) ?? '';
  if (/^\.env([.*?[].*)?$/.test(nombre) && nombre !== '.env.example') return true;
  if (/\.(pem|key|p12|pfx)$/i.test(nombre) || NOMBRES_CLAVE.test(nombre)) return true;
  for (let i = 0; i < segs.length; i++) {
    if (segs[i] === 'keys' && (i === 0 || segs[i - 1] === 'backend')) return true;
  }
  return false;
}

// Glob de shell (por segmento, sin globstar) a expresion regular. Un segmento
// que empieza por comodin no casa con un nombre que empieza por punto.
function segmentoARegex(seg, { punto = false } = {}) {
  let r = '';
  for (let i = 0; i < seg.length; i++) {
    const c = seg[i];
    if (c === '*') r += '[^/]*';
    else if (c === '?') r += '[^/]';
    else if (c === '[') {
      const fin = seg.indexOf(']', i + 2);
      if (fin < 0) r += '\\[';
      else {
        let clase = seg.slice(i + 1, fin);
        if (clase.startsWith('!')) clase = '^' + clase.slice(1);
        r += `[${clase.replace(/\\/g, '\\\\')}]`;
        i = fin;
      }
    } else r += c.replace(/[.+^${}()|\\]/g, '\\$&');
  }
  const prefijo = !punto && /^[*?[]/.test(seg) ? '(?!\\.)' : '';
  return new RegExp(`^${prefijo}${r}$`);
}

const tieneComodin = (t) => /[*?[]/.test(t);

// Muestras de rutas protegidas contra las que se prueba un glob aunque no
// existan en disco (otro worktree o el checkout principal si las tiene).
const MUESTRAS = [
  '.env', '.env.local', '.env.production.local', '.env.swarm',
  'backend/.env', 'frontend/.env', 'frontend/.env.local',
  'backend/keys', 'backend/keys/private.pem', 'backend/keys/jwt_private.pem',
];

function globCasaMuestra(patron, { punto = false, globstar = false } = {}) {
  const limpio = patron.replace(/^\.\//, '');
  const partes = limpio.split('/').filter(Boolean);
  if (partes.length === 0) return false;
  for (const muestra of MUESTRAS) {
    const ms = muestra.split('/');
    if (globstar) {
      const re = new RegExp(
        '^' +
          partes
            .map((p) => (p === '**' ? '.*' : segmentoARegex(p, { punto }).source.replace(/^\^|\$$/g, '')))
            .join('/') +
          '$',
      );
      if (re.test(muestra) || re.test(ms.at(-1))) return true;
      continue;
    }
    if (ms.length !== partes.length) continue;
    if (partes.every((p, i) => segmentoARegex(p, { punto }).test(ms[i]))) return true;
  }
  return false;
}

// Expande un glob contra el disco (como bash, sin dotglob ni globstar) y dice
// si alguna coincidencia es sensible. Limitado para no recorrer el disco.
function globCasaEnDisco(patron, cwd) {
  const absoluto = isAbsolute(patron);
  const partes = patron.split('/').filter((p) => p && p !== '.');
  let actuales = [absoluto ? '/' : cwd ?? process.cwd()];
  let visitados = 0;
  for (const p of partes) {
    const siguientes = [];
    for (const dir of actuales) {
      if (!tieneComodin(p)) {
        const ruta = join(dir, p);
        if (existsSync(ruta)) siguientes.push(ruta);
        continue;
      }
      let entradas = [];
      try {
        entradas = readdirSync(dir);
      } catch {
        continue;
      }
      const re = segmentoARegex(p);
      for (const e of entradas) {
        if (++visitados > 5000) return true;
        if (re.test(e)) siguientes.push(join(dir, e));
      }
    }
    actuales = siguientes;
    if (actuales.length === 0) return false;
  }
  return actuales.some((r) => esSensible(r));
}

// Ruta protegida incrustada en un token mayor, p. ej. el codigo de
// `python3 -c 'open(".env")'` o `node -e 'fs.readFileSync(".env")'`.
const INCRUSTADA = /(^|[^\w.-])\.env(?!\.example)(?![\w-])|backend\/keys\/|\.pem(?![\w.])|\/proc\/[^\s'"]*\/environ/;

export function tokenProtegido(token, cwd, { punto = false } = {}) {
  if (INCRUSTADA.test(String(token))) return String(token);
  for (const pieza of [token, ...String(token).split(/[=:,<>]+/)]) {
    if (!pieza) continue;
    if (esSensible(pieza)) return pieza;
    if (tieneComodin(pieza) && (globCasaMuestra(pieza, { punto }) || globCasaEnDisco(pieza, cwd))) return pieza;
  }
  return null;
}

const expandirHome = (r) => (r === '~' || r.startsWith('~/') ? join(homedir(), r.slice(1)) : r);

// Un directorio es peligroso para busquedas recursivas si es el cwd o un
// ancestro suyo, o si contiene alguna ruta protegida conocida.
export function directorioPeligroso(ruta, cwd) {
  const base = cwd ?? process.cwd();
  const abs = resolve(base, expandirHome(ruta || '.'));
  const rel = relative(abs, base);
  if (rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))) return true;
  if (esSensible(abs)) return true;
  for (const m of ['.env', '.env.local', 'backend/.env', 'frontend/.env', 'frontend/.env.local', 'backend/keys', 'keys']) {
    if (existsSync(join(abs, m))) return true;
  }
  return false;
}

const esDirectorio = (ruta, cwd) => {
  try {
    return statSync(resolve(cwd ?? process.cwd(), expandirHome(ruta))).isDirectory();
  } catch {
    return false;
  }
};

// Indices de tokens cuyo valor es texto libre (mensajes), no rutas.
function indicesIgnorados(tokens) {
  const ign = new Set();
  const cmd = nombreComando(tokens[0] ?? '');
  const sub = tokens.slice(1).filter((t) => !t.startsWith('-'));
  let conValor = null;
  if (cmd === 'git' && sub.some((t) => ['commit', 'tag', 'notes', 'stash', 'merge'].includes(t))) {
    conValor = { cortas: ['-m'], largas: ['--message'] };
  } else if (cmd === 'gh' && sub.some((t) => ['pr', 'issue', 'release', 'repo'].includes(t))) {
    conValor = { cortas: ['-b', '-t', '-n', '--notes'], largas: ['--body', '--title', '--notes'] };
  }
  if (!conValor) return ign;
  for (let i = 1; i < tokens.length; i++) {
    const t = tokens[i];
    if (conValor.cortas.includes(t) || conValor.largas.includes(t)) {
      ign.add(i + 1);
    } else if (conValor.largas.some((l) => t.startsWith(`${l}=`)) || /^-m./.test(t)) {
      ign.add(i);
    }
  }
  return ign;
}

const PUERTOS = /^\^(GATEWAY_PORT|POSTGRES_PORT|REDIS_PORT|COMPOSE_PROJECT_NAME)=$/;

// Comprobaciones permitidas sobre .env: existencia, conteo de una clave y
// lectura de puertos o del proyecto Compose.
function segmentoPermitido(t) {
  const cmd = nombreComando(t[0] ?? '');
  const env = (x) => x === '.env' || x === './.env';
  if ((cmd === 'test' && t.length === 3) && /^-[ef]$/.test(t[1]) && env(t[2])) return true;
  if (cmd === '[' && t.length === 4 && /^-[ef]$/.test(t[1]) && env(t[2]) && t[3] === ']') return true;
  if (cmd === 'grep' && t.length === 4 && t[1] === '-c' && /^\^[A-Z][A-Z0-9_]*=$/.test(t[2]) && env(t[3])) return true;
  if (cmd === 'grep' && t.length === 4 && t[1] === '-m1' && PUERTOS.test(t[2]) && env(t[3])) return true;
  return false;
}

function evaluarDocker(cmd, args) {
  const compose = cmd.endsWith('compose') || args.includes('compose');
  if (compose && args.includes('config')) return 'docker compose config imprime la configuracion con secretos';
  if (args.includes('inspect')) return 'docker inspect muestra variables de entorno';
  const i = args.findIndex((a) => a === 'exec' || a === 'run');
  if (i >= 0) {
    const resto = args.slice(i + 1).map((a) => nombreComando(a));
    if (resto.some((a) => ['env', 'printenv', 'sh', 'bash', 'zsh', 'dash', 'ash', 'export', 'declare'].includes(a))) {
      return 'shell o volcado de entorno dentro de un contenedor';
    }
    const interprete = resto.findIndex((a) => /^(python3?|node|perl|ruby)$/.test(a));
    if (interprete >= 0 && resto.slice(interprete + 1).some((a) => a === '-c' || a === '-e')) {
      return 'codigo en linea dentro de un contenedor';
    }
    if (args.some((a) => /\/proc\/[^ ]*environ/.test(a))) return 'lectura de /proc/*/environ';
  }
  return null;
}

// find/fd comparan patrones sin la regla del punto inicial de bash: '*env'
// casa con .env. Se bloquea cualquier patron que case con una ruta protegida.
function evaluarFind(cmd, args) {
  const patrones = [];
  for (let i = 0; i < args.length; i++) {
    if (/^-(i?name|i?path|wholename|iwholename|regex|iregex|g|glob)$/.test(args[i])) patrones.push(args[++i] ?? '');
    else if (cmd !== 'find' && !args[i].startsWith('-')) patrones.push(args[i]);
  }
  for (const p of patrones) {
    if (esSensible(p) || /env|keys|pem/i.test(p) || globCasaMuestra(p, { punto: true, globstar: true })) {
      return `${cmd} con patron '${p}' que casa con ficheros protegidos`;
    }
  }
  return null;
}

// Filtros que dejan fuera las rutas protegidas en grep -r / rg.
function grepConExclusion(args) {
  const valores = (re) =>
    args.flatMap((a, i) => {
      const m = re.exec(a);
      if (!m) return [];
      return [m[2] ?? args[i + 1] ?? ''];
    });
  const includes = valores(/^(--include)(?:=(.*))?$/);
  if (includes.length && includes.every((g) => !globCasaMuestra(g, { punto: true }))) return true;
  const excl = valores(/^(--exclude)(?:=(.*))?$/);
  const exclDir = valores(/^(--exclude-dir)(?:=(.*))?$/);
  return excl.some((g) => /\.env|\.e\*|^\.\*|^\*$/.test(g)) && exclDir.some((g) => /keys|^\*$/.test(g));
}

function rgConExclusion(args) {
  const globs = args.flatMap((a, i) => {
    const m = /^(-g|--glob|--iglob)(?:=(.*))?$/.exec(a);
    if (m) return [m[2] ?? args[i + 1] ?? ''];
    if (/^-g./.test(a)) return [a.slice(2)];
    return [];
  });
  if (args.some((a) => /^(-t|--type)(=|$)/.test(a) || /^-t./.test(a))) return true;
  const positivos = globs.filter((g) => !g.startsWith('!'));
  if (positivos.length && positivos.every((g) => !globCasaMuestra(g, { punto: true, globstar: true }))) return true;
  const negativos = globs.filter((g) => g.startsWith('!')).map((g) => g.slice(1));
  return negativos.some((g) => /\.env|\.e\*|^\.\*/.test(g)) && negativos.some((g) => /keys/.test(g));
}

function evaluarBusqueda(cmd, args, cwd) {
  const recursivo =
    cmd === 'rg' ||
    args.some((a) => a === '--recursive' || a === '-d' || /^-[A-Za-z]*[rR][A-Za-z]*$/.test(a) || a === '--directories=recurse');
  if (!recursivo) return null;
  const opcionesConValor = new Set(['-e', '-f', '-m', '-A', '-B', '-C', '-g', '--glob', '-t', '--type', '-T', '--type-not', '--include', '--exclude', '--exclude-dir', '-d']);
  const posicionales = [];
  let patronDado = args.some((a) => a === '-e' || a === '-f' || a.startsWith('--regexp') || a.startsWith('--file'));
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (opcionesConValor.has(a)) {
      i++;
      continue;
    }
    if (a.startsWith('-')) continue;
    if (!patronDado) {
      patronDado = true;
      continue;
    }
    posicionales.push(a);
  }
  const rutas = posicionales.length ? posicionales : ['.'];
  const peligrosas = rutas.filter((r) => esDirectorio(r, cwd) && directorioPeligroso(r, cwd));
  if (peligrosas.length === 0) return null;
  const excluye = cmd === 'rg' ? rgConExclusion(args) : grepConExclusion(args);
  if (excluye) return null;
  return `busqueda recursiva sobre '${peligrosas[0]}' sin excluir .env* y backend/keys`;
}

export function evaluarBash(comando, cwdInicial) {
  let cwd = cwdInicial;
  const segmentos = segmentar(comando);
  const revisable = [];
  for (const crudo of segmentos) {
    const tokens = quitarPrefijos(crudo);
    // `env` a secas: quitarPrefijos lo trata como prefijo y no deja comando.
    if (tokens.length === 0 && tokens.prefijos?.includes('env')) return 'env sin comando vuelca el entorno (tokens)';
    const desfase = crudo.length - tokens.length;
    const ignorados = indicesIgnorados(tokens);
    const relevantes = crudo.filter((_, i) => !ignorados.has(i - desfase));
    revisable.push(...relevantes);
    if (tokens.length && nombreComando(tokens[0]) === 'cd') cwd = unirDir(cwd, tokens[1] ?? '');
    if (segmentoPermitido(tokens)) continue;
    for (const t of relevantes) {
      const objetivo = tokenProtegido(t, cwd);
      if (objetivo) return `acceso a '${objetivo}'`;
    }
    if (tokens.length) {
      const cmd = nombreComando(tokens[0]);
      const args = tokens.slice(1);
      let motivo = null;
      if (/^(docker|podman)(-compose)?$/.test(cmd)) motivo = evaluarDocker(cmd, args);
      else if (cmd === 'find' || cmd === 'fd' || cmd === 'fdfind' || cmd === 'locate') motivo = evaluarFind(cmd, args);
      else if (cmd === 'grep' || cmd === 'egrep' || cmd === 'fgrep' || cmd === 'rg') motivo = evaluarBusqueda(cmd, args, cwd);
      else if ((cmd === 'env' || cmd === 'printenv') && args.length === 0) motivo = `${cmd} sin argumentos vuelca el entorno (tokens)`;
      if (motivo) return motivo;
    }
    // El cuerpo de un heredoc solo se ejecuta si lo lee un shell (bash <<EOF).
    if (tokens.length && SHELLS.has(nombreComando(tokens[0]))) {
      for (const cuerpo of crudo.heredocs ?? []) {
        const motivo = evaluarBash(cuerpo, cwd);
        if (motivo) return `heredoc: ${motivo}`;
      }
      // `bash -c '...'` y here-strings: el codigo llega como un solo token y
      // hay que evaluarlo como comando (globs incluidos).
      const shell = analizarShell(tokens.slice(1));
      if ((shell.tipo === 'c' || shell.tipo === 'herestring') && shell.codigo) {
        const motivo = evaluarBash(shell.codigo, cwd);
        if (motivo) return `${nombreComando(tokens[0])} -c: ${motivo}`;
      }
      // Shell que lee de stdin sin heredoc visible (tuberia, here-string): no se
      // puede revisar lo que ejecuta. Mismo criterio que guardas-git.
      if (shell.tipo === 'stdin' && (crudo.heredocs ?? []).length === 0) {
        return `${nombreComando(tokens[0])} leyendo comandos de stdin no se puede revisar`;
      }
    }
  }
  const texto = revisable.join(' ');
  if (/[$`]/.test(texto) && /\.e|\benv\b|keys|\.pem/i.test(texto)) {
    return 'expansion de shell ($ o comillas invertidas) junto a una ruta protegida';
  }
  return null;
}

export function evaluarGrepTool(params, cwd) {
  const { path: ruta, glob, type } = params;
  if (typeof ruta === 'string' && esSensible(ruta)) return `acceso a '${ruta}'`;
  if (typeof glob === 'string' && glob) {
    if (esSensible(glob) || globCasaMuestra(glob, { punto: true, globstar: true })) return `glob '${glob}' casa con ficheros protegidos`;
    return null;
  }
  if (typeof type === 'string' && type) return null;
  const objetivo = typeof ruta === 'string' && ruta ? ruta : '.';
  if (esDirectorio(objetivo, cwd) && directorioPeligroso(objetivo, cwd)) {
    return `Grep sobre '${objetivo}' sin glob ni type que excluya .env* y backend/keys`;
  }
  return null;
}

export function evaluarEntrada(datos) {
  const { tool_name: herramienta, tool_input: params = {} } = datos;
  const cwd = typeof datos.cwd === 'string' ? datos.cwd : undefined;
  if (herramienta === 'Read' && typeof params.file_path === 'string') {
    return esSensible(params.file_path) ? `acceso a '${params.file_path}'` : null;
  }
  if (herramienta === 'Grep') return evaluarGrepTool(params, cwd);
  if (herramienta === 'Bash' && typeof params.command === 'string') return evaluarBash(params.command, cwd);
  return null;
}
