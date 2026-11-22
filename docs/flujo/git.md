# Flujo git

Las decisiones estan en ADR-0001 (versionado) y ADR-0002 (ramas, PR, merge y
autonomia del agente).

## Ramas

| Rama | Para que | Quien escribe |
|---|---|---|
| `main` | Produccion. Cada merge es una release | Solo el usuario, mediante un PR desde `develop` |
| `develop` | Integracion. Cada merge despliega en dev (Komodo) | Solo por PR con merge commit, que puede hacer el agente de `/issue-work` |
| `<tipo>/<n>-<descripcion>` | Una issue, un worktree | El agente o la persona que trabaja la issue |

`<tipo>` es uno de `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`
o `ci`. `<n>` es el numero de la issue. La descripcion va en espanol, en
minusculas, con guiones y sin tildes, por ejemplo
`feat/12-reportes-de-soporte`.

## Commits

Conventional Commits en espanol:

```text
<tipo>(<ambito>): <resumen en imperativo y minuscula>
```

Sin punto final y sin version en el titulo. Ejemplo:

```text
feat(empresa): anadir filtro por empresa en el dashboard
```

Commits atomicos: un cambio logico por commit. Sin lineas `Co-Authored-By` ni
pies de atribucion ("Generated with Claude Code" o similares) en commits ni PR.

## PR y merge

- Base: siempre `develop`, con la plantilla
  `.github/pull_request_template.md` y `Closes #<n>`.
- El PR anade su linea en `## [Unreleased]` del `CHANGELOG.md` con `(#<n>)` y
  no toca la version.
- Merge a `develop`: `gh pr merge <n> --merge --delete-branch`. Ni squash ni
  rebase (el hook `guardas-git` los bloquea).
- `develop` exige que la rama este al dia (checks en modo estricto). Si el PR
  esta `BEHIND` o `DIRTY`, se sincroniza con `git merge origin/develop` y push
  normal, nunca con rebase ni force-push. Reglas de resolucion por fichero en
  el paso "Sincronizacion" de `.claude/skills/issue-work/SKILL.md`.
- Release de `develop` a `main`: merge commit, que hace el usuario.

## Versionado (ADR-0001)

1. Tras la release `0.27.0`, `develop` pasa a `0.28.0` en `package.json` y
   `frontend/package.json`. Es la proxima version.
2. Cada merge a `develop` despliega `0.28.0-dev.N` (N = `github.run_number`):
   imagenes `dev-v0.28.0-dev.N` y tag git `v0.28.0-dev.N`.
3. `/release`:
   1. Crea una issue de release.
   2. Abre a `develop` el PR `chore(release): prepara v0.28.0`, que pasa
      `[Unreleased]` a `## [0.28.0] - <fecha>`.
   3. Abre el PR de `develop` a `main`. El usuario hace el merge y se publican
      `v0.28.0` y `latest`.
4. Un PR `chore/<n>-subir-version` lleva `develop` a `0.29.0`.

## Proteccion

En el servidor (GitHub): `develop` exige los checks de CI, rama al dia,
`enforce_admins` y prohibe force-push.

En local:

- Hooks de Claude (`.claude/settings.json`):
  - `proteger-ramas`: bloquea Edit y Write en `main` y `develop`.
  - `guardas-git`: bloquea `git push` a `main` o `develop`, el force-push y
    `gh pr merge` con base `main`, con checks que no esten en verde o con
    `--squash`/`--rebase`.
  - `bloquear-env`: bloquea la lectura de `.env*`. Solo deja pasar en Bash
    `test -f .env`, `grep -c '^CLAVE=' .env` y
    `grep -m1 '^(GATEWAY_PORT|POSTGRES_PORT|REDIS_PORT|COMPOSE_PROJECT_NAME)=' .env`.
- Hook git `.githooks/pre-push`: bloquea el push de `main` y `develop`. Se
  activa una vez por clon:

  ```bash
  git config core.hooksPath .githooks
  ```

- Tests de los hooks: `node --test 'tests/hooks/*.test.mjs'` (tambien en CI,
  job `frontend-qa`).

Los hooks son una red de seguridad contra errores, no la proteccion real. La
proteccion real es `permissions.deny` en `.claude/settings.json` (lectura de
`.env*`, `backend/keys/`, `*.pem` y `*.key`; edicion de `.claude/**` y
`.githooks/**`) mas la proteccion de ramas en GitHub. Todos los hooks fallan
cerrados: si la entrada no se puede analizar, bloquean.

Limites:

- `proteger-ramas` vigila Edit, Write y los Bash que escriben en el repo
  (`sed -i`, `>`, `>>`, `tee`, `cp`/`mv`/`touch`, `git commit`) en `main` y
  `develop`. Un comando que escriba por otra via no se detecta; el push
  posterior si queda bloqueado. Expande `~`, `$HOME` y las variables
  asignadas antes en el mismo comando (`D=/tmp/x; echo > $D/f`), tambien en
  `cd`. No sigue `read`, `declare`, `printf -v`, `for`, `+=`, subshells,
  `$(...)`, `||` ni `&&`, ni una variable asignada dos veces: en esos casos
  la variable queda sin resolver. Una escritura con expansion sin resolver
  solo se permite desde una rama de trabajo; en `main`, `develop` o fuera de
  un repo se bloquea y pide la ruta literal. `$TMPDIR` y `$TMP` se resuelven.
  Limite aceptado: desde un worktree en rama de trabajo, una variable opaca
  (`read D <<< <checkout principal>; echo > $D/f`) puede apuntar al checkout
  principal en `develop` y no se detecta. Ahi la barrera es la regla 3 y la
  proteccion de ramas en GitHub (el commit en `develop` no llega al remoto).
- `bloquear-env` es conservador: bloquea globs que puedan casar `.env` o claves,
  `docker compose config`, `docker exec ... env` y `grep -r` sobre la raiz.
  `ls .env` o `cp .env.example .env` los ejecuta el usuario con `!`. Los
  scripts (`./bin/orca-setup`, `./bin/dev`) leen `.env` por dentro y no se
  bloquean. El texto de `-m`, `--body` y `--title` no cuenta, ni los filtros
  jq (`gh ... --jq`, `--template` y el filtro de `jq`), donde `.estado` o
  `.env` son campos JSON.
- `guardas-git` evalua `git push` en la rama del directorio del comando (`cd` y
  `git -C` incluidos), tambien dentro de heredocs y tuberias hacia un shell.
  Bloquea `gh pr merge` con squash, rebase o `--admin`, y `gh api` de escritura
  sobre merges, refs, contenidos, `/branches` (incluida su proteccion),
  rulesets y reviews. Tambien bloquea destinos de push con `$` o comillas
  invertidas, `xargs` con git o gh, `git -c alias.*` y `send-pack`. Si no
  puede consultar un PR, bloquea el merge.
- Son listas negras: hay escrituras en `develop` por Bash (`git reset`,
  `git checkout --`, `rm`, `patch`...) y lecturas indirectas
  (`cat $(ls -A | head -3)`) que no detectan. Ahi la barrera es
  `permissions.deny`, la proteccion de ramas en GitHub y la regla 3.
- Para crear el `.env` de un worktree usa `./bin/orca-setup`, nunca
  `cp .env.example .env` (el hook lo bloquea).
