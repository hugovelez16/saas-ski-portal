import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync, execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const script = fileURLToPath(new URL('../../.claude/hooks/proteger-ramas.mjs', import.meta.url));
let repo;
let fuera;

function escribir(file_path) {
  return spawnSync('node', [script], {
    input: JSON.stringify({ tool_name: 'Write', tool_input: { file_path } }),
    encoding: 'utf8',
  });
}

function bash(command) {
  return spawnSync('node', [script], {
    input: JSON.stringify({ tool_name: 'Bash', cwd: repo, tool_input: { command } }),
    encoding: 'utf8',
  });
}

before(() => {
  repo = mkdtempSync(join(tmpdir(), 'pp-repo-'));
  fuera = mkdtempSync(join(tmpdir(), 'pp-fuera-'));
  execFileSync('git', ['init', '-q', '-b', 'main', repo]);
});

after(() => {
  rmSync(repo, { recursive: true, force: true });
  rmSync(fuera, { recursive: true, force: true });
});

test('bloquea escribir en main', () => {
  const r = escribir(join(repo, 'a.md'));
  assert.equal(r.status, 2);
  assert.match(r.stderr, /\[ERROR\]/);
});

test('bloquea escribir en un directorio nuevo estando en main', () => {
  assert.equal(escribir(join(repo, 'nuevo', 'dir', 'b.md')).status, 2);
});

test('bloquea escribir en develop', () => {
  execFileSync('git', ['-C', repo, 'switch', '-q', '-c', 'develop']);
  assert.equal(escribir(join(repo, 'a.md')).status, 2);
});

for (const comando of ['sed -i s/a/b/ a.md', 'echo x > a.md', 'echo x >> a.md', 'echo x | tee a.md', 'git commit -m x']) {
  test(`Bash en develop bloquea: ${comando}`, () => {
    assert.equal(bash(comando).status, 2);
  });
}

for (const comando of ['git status', 'git fetch origin', 'git log --oneline -3', './bin/dev', 'echo x > /tmp/fuera.txt']) {
  test(`Bash en develop permite: ${comando}`, () => {
    assert.equal(bash(comando).status, 0);
  });
}

// Issue #74: `~`, `$HOME` y variables asignadas en el mismo comando.
test('Bash en develop permite escribir en ~ y $HOME (fuera del repo)', () => {
  assert.equal(bash('echo x > ~/pp-fuera-74.md').status, 0);
  assert.equal(bash('sed -i s/a/b/ ~/pp-fuera-74.md').status, 0);
  assert.equal(bash('echo x > $HOME/pp-fuera-74.md').status, 0);
});

test('Bash en develop resuelve variables asignadas en el mismo comando', () => {
  assert.equal(bash(`D=${fuera}; echo x > $D/f.md`).status, 0);
  assert.equal(bash(`D=${fuera}; echo x > "\${D}/f.md"`).status, 0);
  assert.equal(bash(`D=${repo}; echo x > $D/a.md`).status, 2);
});

function bashEn(cwd, command) {
  return spawnSync('node', [script], {
    input: JSON.stringify({ tool_name: 'Bash', cwd, tool_input: { command } }),
    encoding: 'utf8',
  });
}

test('cd con variable se resuelve o bloquea las escrituras siguientes', () => {
  assert.equal(bashEn(fuera, `D=${repo}; cd $D; echo x > f.md`).status, 2);
  assert.equal(bashEn(fuera, 'cd $SIN_DEFINIR; echo x > f.md').status, 2);
  assert.equal(bashEn(fuera, 'cd $SIN_DEFINIR; git commit -m x').status, 2);
  assert.equal(bashEn(fuera, 'cd $SIN_DEFINIR; git status').status, 0);
});

test('reasignaciones y asignaciones opacas dejan la variable sin resolver', () => {
  for (const c of [
    `D=${repo}; (D=/tmp; true); echo x > $D/f.md`,
    `D=${repo}; true || D=/tmp; echo x > $D/f.md`,
    `read D <<< ${repo}; echo x > $D/f.md`,
    `printf -v D ${repo}; echo x > $D/f.md`,
    `D=/tmp; D+=/x; echo x > $D/f.md`,
    'echo x > $SIN_DEFINIR/f.md',
  ]) {
    assert.equal(bashEn(fuera, c).status, 2, c);
  }
});

test('Bash en develop respeta HOME redefinido y no resuelve ~usuario', () => {
  assert.equal(bash(`HOME=${repo}; echo x > ~/a.md`).status, 2);
  assert.equal(bash(`HOME=${repo}; echo x > $HOME/a.md`).status, 2);
  assert.equal(bash('echo x > ~root/a.md').status, 2);
});

test('Bash en develop permite $TMPDIR y bloquea reasignar dentro de sh -c', () => {
  assert.equal(bash('echo x > $TMPDIR/pp-74.txt').status, 0);
  assert.equal(bashEn(fuera, `D=${repo}; sh -c "D=/tmp; echo x > $D/f.md"`).status, 2);
});

test('Bash en develop bloquea una variable sin resolver y pide la ruta literal', () => {
  const r = bash('echo x > $SIN_DEFINIR/f.md');
  assert.equal(r.status, 2);
  assert.match(r.stderr, /ruta literal/);
});

test('permite escribir en una rama de trabajo', () => {
  execFileSync('git', ['-C', repo, 'switch', '-q', '-c', 'feat/1-x']);
  assert.equal(escribir(join(repo, 'nuevo', 'dir', 'b.md')).status, 0);
});

test('Bash en una rama de trabajo permite redirigir al repo', () => {
  assert.equal(bash('echo x > a.md').status, 0);
});

test('permite escribir fuera de un repo', () => {
  assert.equal(escribir(join(fuera, 'c.md')).status, 0);
});
