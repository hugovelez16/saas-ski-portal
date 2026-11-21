import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const script = fileURLToPath(new URL('../../.claude/hooks/bloquear-env.mjs', import.meta.url));

function ejecutar(entrada) {
  return spawnSync('node', [script], { input: JSON.stringify(entrada), encoding: 'utf8' });
}

const casos = [
  ['Read', { file_path: '/x/.env' }, 2],
  ['Read', { file_path: '/x/.env.local' }, 2],
  ['Read', { file_path: '/x/.env.example' }, 0],
  ['Read', { file_path: '/x/docs/env.md' }, 0],
  ['Bash', { command: 'cat .env' }, 2],
  ['Bash', { command: 'grep KEY .env.production' }, 2],
  ['Bash', { command: 'cp .env.example .env.tmp' }, 2],
  ['Bash', { command: 'cat ./apps/.env' }, 2],
  ['Bash', { command: 'cat ".env"' }, 2],
  ['Bash', { command: 'cat .env.example' }, 0],
  ['Bash', { command: 'echo hola' }, 0],
  ['Bash', { command: 'cat .env*' }, 2],
  ['Bash', { command: 'test -f .env && echo "existe" || echo "no existe"' }, 0],
  ['Bash', { command: "grep -c '^COMPOSE_PROJECT_NAME=' .env" }, 0],
  ['Bash', { command: "grep -m1 '^GATEWAY_PORT=' .env" }, 0],
  ['Bash', { command: "grep -m1 '^JWT_PRIVATE_KEY_PASSPHRASE=' .env" }, 2],
  ['Bash', { command: "grep '^INITIAL_ADMIN_PASSWORD=' .env" }, 2],
  ['Bash', { command: 'test -f .env && cat .env' }, 2],
  ['Bash', { command: "grep -c '^X=' .env; cat .env" }, 2],
  ['Bash', { command: './bin/orca-setup' }, 0],
  ['Grep', { pattern: 'KEY', path: '/x/.env' }, 2],
  ['Grep', { pattern: 'KEY', glob: '.env*' }, 2],
  ['Grep', { pattern: 'KEY', path: '/x/src', glob: '*.ts' }, 0],
  // Bypasses de la revision de seguridad: deben bloquearse.
  ['Bash', { command: 'cat .e?v' }, 2],
  ['Bash', { command: "cat '.e'nv" }, 2],
  ['Bash', { command: 'f=.en; cat ${f}v' }, 2],
  ['Bash', { command: 'source .env' }, 2],
  ['Bash', { command: 'cat backend/keys/private.pem' }, 2],
  ['Bash', { command: 'docker compose -f docker-compose.dev.yml config' }, 2],
  ['Bash', { command: 'docker compose exec backend printenv' }, 2],
  ['Bash', { command: 'grep -rn SECRET .' }, 2],
  ['Read', { file_path: '/x/backend/keys/private.pem' }, 2],
  ['Grep', { pattern: 'SECRET', path: process.cwd() }, 2],
  ['Bash', { command: `node -e 'fs.readFileSync(".env")'` }, 2],
  ['Bash', { command: `python3 -c 'print(open(".env").read())'` }, 2],
  ['Bash', { command: 'cat /proc/self/environ' }, 2],
  ['Bash', { command: 'printenv' }, 2],
  ['Bash', { command: 'env' }, 2],
  ['Bash', { command: "bash -c 'cat .e*'" }, 2],
  ['Bash', { command: 'bash <<< "cat .e*"' }, 2],
  ['Bash', { command: 'jq .x .env' }, 2],
  ['Bash', { command: 'jq -nf .env' }, 2],
  ['Bash', { command: 'jq -rf .env' }, 2],
  ['Bash', { command: 'jq -sf .env x.json' }, 2],
  ['Bash', { command: 'jq -f.env' }, 2],
  ['Bash', { command: 'jq --from-file .env' }, 2],
  ['Bash', { command: 'jq -n --rawfile a .env "$a"' }, 2],
  ['Bash', { command: "gh issue list --jq '.x' && cat .env" }, 2],
  // Falsos positivos: el flujo legitimo no se bloquea.
  // Issue #74: filtros jq con campos como `.estado` o `.env`.
  ['Bash', { command: `N=3; gh project item-list $N --format json --jq '.items[]|select(.estado=="X")'` }, 0],
  ['Bash', { command: "gh api repos/o/r --jq '.env'" }, 0],
  ['Bash', { command: "jq '.estado' datos.json" }, 0],
  ['Bash', { command: "bash -c 'ls docs'" }, 0],
  ['Bash', { command: 'env FOO=1 pytest' }, 0],
  ['Bash', { command: 'python3 -c "print(1)"' }, 0],
  ['Bash', { command: 'grep -rn envoltorio backend/src' }, 0],
  ['Bash', { command: 'git commit -m "docs: no leer .env"' }, 0],
  ['Bash', { command: 'gh issue comment 3 --body "revisa el .env"' }, 0],
  ['Bash', { command: './bin/migrate' }, 0],
  ['Bash', { command: 'cd backend && pytest tests/' }, 0],
  ['Bash', { command: 'grep -rn foo backend/src' }, 0],
];

for (const [tool_name, tool_input, codigo] of casos) {
  test(`${tool_name} ${JSON.stringify(tool_input)} -> exit ${codigo}`, () => {
    const r = ejecutar({ tool_name, tool_input });
    assert.equal(r.status, codigo, r.stderr);
    if (codigo === 2) assert.match(r.stderr, /\[ERROR\]/);
  });
}

test('JSON invalido se bloquea (fail-closed)', () => {
  const r = spawnSync('node', [script], { input: 'no-json', encoding: 'utf8' });
  assert.equal(r.status, 2);
});
