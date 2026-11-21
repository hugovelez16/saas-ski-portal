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
