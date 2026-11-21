import { test } from 'node:test';
import assert from 'node:assert/strict';
import { evaluarComando } from '../../.claude/hooks/lib/guardas-git.mjs';
import { spawnSync, execFileSync } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

function consultas({ rama = 'feat/1-x', ramas = {}, base = 'develop', verde = true, onPr } = {}) {
  return {
    ramaActual: (dir) => (dir !== undefined && dir in ramas ? ramas[dir] : rama),
    baseDelPr: (pr, repo) => {
      onPr?.(pr, repo);
      return base;
    },
    checksEnVerde: () => verde,
  };
}

const casos = [
  ['git push origin main', {}, true],
  ['git push origin HEAD:develop', {}, true],
  ['git push -u origin chore/3-x', { rama: 'chore/3-x' }, false],
  ['git push', { rama: 'main' }, true],
  ['git push', { rama: 'develop' }, true],
  ['git push', { rama: 'feat/4-y' }, false],
  ['git push --force origin feat/4-y', {}, true],
  ['git push -f origin feat/4-y', {}, true],
  ['git push --force-with-lease', {}, true],
  ['git push origin +feat/4-y', {}, true],
  ['echo ok && git push origin main', {}, true],
  ['git status; git push origin "main"', {}, true],
  ['gh pr merge 5 --merge', { base: 'main' }, true],
  ['gh pr merge 5 --merge', { base: 'develop', verde: false }, true],
  ['gh pr merge 5 --merge', { base: 'develop', verde: true }, false],
  ['gh pr merge 5 --squash', { base: 'develop', verde: true }, true],
  ['gh pr merge 5 --rebase', { base: 'develop', verde: true }, true],
  ['gh pr merge 5 -s', { base: 'develop', verde: true }, true],
  ['git status', {}, false],
  ['ls', {}, false],
  ['echo "git push origin main"', {}, false],
  // opciones globales y prefijos
  ['git -C ../otro push origin develop', {}, true],
  ['git -c core.x=1 push origin main', {}, true],
  ['git --no-pager push origin main', {}, true],
  ['env git push origin main', {}, true],
  ['FOO=1 git push origin main', {}, true],
  ['command git push origin main', {}, true],
  ['(git push origin main)', {}, true],
  ['bash -c "git push origin main"', {}, true],
  ["sh -c 'git push --force'", {}, true],
  ['gh pr -R hugovelez16/saas-ski-portal merge 40', { base: 'main' }, true],
  ['gh -R hugovelez16/saas-ski-portal pr merge 40', { base: 'main' }, true],
  // destinos y opciones de push
  ['git push origin HEAD', { rama: 'develop' }, true],
  ['git push origin @', { rama: 'main' }, true],
  ['git push origin HEAD:HEAD', { rama: 'develop' }, true],
  ['git push origin HEAD', { rama: 'feat/4-y' }, false],
  ['git push -uf origin feat/4-y', {}, true],
  ['git push --mirror', {}, true],
  ['git push --all origin', {}, true],
  ['git push -u origin feat/4-y', {}, false],
  ['git push --tags origin', {}, false],
  // directorio del comando
  ['cd ../wt && git push', { rama: 'develop', ramas: { '../wt': 'feat/9-z' } }, false],
  ['cd ../main && git push', { rama: 'feat/9-z', ramas: { '../main': 'develop' } }, true],
  ['git -C ../wt push', { rama: 'develop', ramas: { '../wt': 'feat/9-z' } }, false],
  // Segunda revision de seguridad.
  ['B=main; git push origin $B', {}, true],
  ['git push origin "$(echo main)"', {}, true],
  ['echo main | xargs git push origin', {}, true],
  ['gh api -X DELETE repos/o/r/branches/main/protection', {}, true],
  ['gh api -X PUT repos/o/r/branches/main/protection', {}, true],
  ['gh api -X POST repos/o/r/rulesets', {}, true],
  ['git -c alias.p=push p origin main', {}, true],
  ['git send-pack origin main', {}, true],
  ['gh api repos/o/r/branches/main', {}, false],
  ['git -c core.pager=cat log -1', {}, false],
  ['ls | xargs grep foo', {}, false],
];

for (const [comando, ctx, esperado] of casos) {
  test(`${esperado ? 'bloquea' : 'permite'}: ${comando} ${JSON.stringify(ctx)}`, () => {
    const r = evaluarComando(comando, consultas(ctx));
    assert.equal(r.bloquear, esperado, r.motivo);
    if (esperado) assert.match(r.motivo, /\S/);
  });
}

test('gh pr merge sin numero consulta el PR de la rama actual', () => {
  const vistos = [];
  const r = evaluarComando('gh pr merge --merge', consultas({ onPr: (pr) => vistos.push(pr) }));
  assert.equal(r.bloquear, false);
  assert.deepEqual(vistos, [undefined]);
});

test('gh pr merge salta los valores de opciones y pasa --repo', () => {
  const vistos = [];
  const r = evaluarComando(
    'gh pr merge --repo hugovelez16/saas-ski-portal -t "titulo con espacios" -b cuerpo 5 --merge',
    consultas({ onPr: (pr, repo) => vistos.push([pr, repo]) }),
  );
  assert.equal(r.bloquear, false);
  assert.deepEqual(vistos, [['5', 'hugovelez16/saas-ski-portal']]);
});

test('gh pr merge con numero pasa el numero a las consultas', () => {
  const vistos = [];
  evaluarComando('gh pr merge 12 --merge --delete-branch', consultas({ onPr: (pr) => vistos.push(pr) }));
  assert.deepEqual(vistos, ['12']);
});

// Issue #33, punto 1: el directorio inicial es el cwd de la sesion.
test('cd relativo se resuelve contra el cwd de la sesion', () => {
  const vistos = [];
  const c = { ...consultas(), ramaActual: (dir) => (vistos.push(dir), 'feat/1-x') };
  evaluarComando('cd ../wt && git push', c, '/sesion/sub');
  assert.deepEqual(vistos, ['/sesion/wt']);
});

const HOOK = fileURLToPath(new URL('../../.claude/hooks/guardas-git.mjs', import.meta.url));
function ejecutarHook(command, cwd) {
  return spawnSync('node', [HOOK], { input: JSON.stringify({ tool_input: { command }, cwd }), encoding: 'utf8' });
}

test('el hook usa datos.cwd como directorio inicial', () => {
  const repo = mkdtempSync(join(tmpdir(), 'guardas-'));
  execFileSync('git', ['init', '-q', '-b', 'main', repo]);
  const r = ejecutarHook('git push', repo);
  assert.equal(r.status, 2, r.stderr);
  assert.match(r.stderr, /rama protegida main/);
});

// Punto 2: si falla ramaActual el mensaje es generico.
test('si falla ramaActual el mensaje no habla del PR', () => {
  const r = ejecutarHook('git push', join(tmpdir(), 'no-existe-guardas-33'));
  assert.equal(r.status, 2, r.stderr);
  assert.doesNotMatch(r.stderr, /PR/);
});

// Punto 3: envoltorios.
const envoltorios = [
  ['bash -lc "git push origin main"', true],
  ['bash -ic "git push origin develop"', true],
  ['timeout 5 git push origin main', true],
  ['timeout -s KILL 5 git push origin develop', true],
  ['sudo -u x git push origin main', true],
  ['eval "git push origin main"', true],
  ['eval git push origin develop', true],
  ['echo main | xargs git push origin', true],
  ['xargs git push origin main', true],
  ['xargs -I{} git push origin develop', true],
  ['timeout 5 git push origin feat/4-y', false],
  ['sudo -u x git status', false],
  ['bash -lc "git status"', false],
];
for (const [comando, esperado] of envoltorios) {
  test(`${esperado ? 'bloquea' : 'permite'} envoltorio: ${comando}`, () => {
    const r = evaluarComando(comando, consultas());
    assert.equal(r.bloquear, esperado, r.motivo);
  });
}

// Punto 4: cuerpo de heredoc.
const heredocs = [
  ["cat <<'EOF'\n(git push origin main)\nEOF", false],
  ['cat <<EOF\ngh pr merge 1 --merge\nEOF', false],
  ['cat <<-EOF\n\tgh pr merge 1\n\tEOF', false],
  ['cat <<"EOF"\ngit push origin main\nEOF\ngit status', false],
  ["gh pr create --body-file - <<'EOF'\n(git push origin main)\nEOF", false],
  ["cat <<'EOF'\nx\nEOF\ngit push origin main", true],
  ["cat <<'EOF' && git push origin main\nx\nEOF", true],
  ['git push origin main', true],
  ['gh pr merge 1 --squash', true],
];
for (const [comando, esperado] of heredocs) {
  test(`${esperado ? 'bloquea' : 'permite'} heredoc: ${JSON.stringify(comando)}`, () => {
    const r = evaluarComando(comando, consultas({ base: 'main' }));
    assert.equal(r.bloquear, esperado, r.motivo);
  });
}
