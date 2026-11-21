import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const hook = fileURLToPath(new URL('../../.githooks/pre-push', import.meta.url));
const SHA = 'a'.repeat(40);

function empujar(refRemota) {
  return spawnSync('bash', [hook, 'origin', 'https://example.invalid/r.git'], {
    input: `refs/heads/x ${SHA} ${refRemota} ${SHA}\n`,
    encoding: 'utf8',
  });
}

test('rechaza push a develop', () => {
  const r = empujar('refs/heads/develop');
  assert.equal(r.status, 1);
  assert.match(r.stderr, /\[ERROR\] push directo a develop bloqueado/);
});

test('rechaza push a main', () => {
  assert.equal(empujar('refs/heads/main').status, 1);
});

test('permite push a una rama de trabajo', () => {
  assert.equal(empujar('refs/heads/feat/2-z').status, 0);
});
