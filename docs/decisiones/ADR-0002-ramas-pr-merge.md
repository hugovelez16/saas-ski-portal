# ADR-0002: Ramas, PR, merge y autonomia del agente

Estado: Aceptada (2026-11-21)

## Contexto

Quien implementa son agentes lanzados con Orca, uno por issue y worktree. Hasta
ahora la antigua regla 3 de `CLAUDE.md` prohibia al agente hacer commit, push o
PR sin una orden expresa en cada mensaje, lo que obligaba al usuario a
intervenir en cada paso.

GitHub protege `develop` en el servidor: checks obligatorios
`Backend QA (Ruff, Migraciones, Pytest)` y
`Frontend QA (Lint, Types, Tests, Build)`, modo estricto (la rama debe estar al
dia con `develop`), `enforce_admins` y sin force-push. Comprobado el
2026-11-21 con `gh api repos/hugovelez16/saas-ski-portal/branches/develop/protection`.

## Decision

- Ramas:
  - `main`: produccion.
  - `develop`: integracion y dev.
  - Ramas de trabajo: `<tipo>/<n>-<descripcion-en-espanol>`, una por issue.
- Commits en espanol con Conventional Commits. Codigo e identificadores en
  ingles.
- Los PR van siempre a `develop`, con `Closes #<n>`.
- Merge: **merge commit** (`gh pr merge <n> --merge --delete-branch`), tanto
  hacia `develop` como de `develop` a `main`. Ni squash ni rebase.
- Autonomia del agente dentro de `/issue-work <n>`, solo para esa issue y su
  rama:
  - puede hacer commits, push de su rama, abrir el PR y sincronizarla con
    `git merge origin/develop`;
  - puede hacer merge a `develop` solo si los checks estan en verde y
    `code-reviewer` da `APTO` (y `security-reviewer` o `database-reviewer`
    cuando aplican).
- A `main` solo hace merge el usuario.
- Fuera de `/issue-work` y de `/release`, commit, push y PR siguen
  necesitando una orden expresa del usuario.
- Proteccion local, ademas de la del servidor:
  - Hooks de Claude: `proteger-ramas` (no editar en `main` ni `develop`),
    `guardas-git` (no push a `main` ni `develop`, no force-push, no merge con
    base `main`, con checks sin verde, con squash ni con rebase) y
    `bloquear-env` (no leer `.env`).
  - Hook git `.githooks/pre-push`.

## Consecuencias

- Con merge commit los commits de la rama llegan a `develop` tal cual: los
  commits `wip` de checkpoint se componen en commits atomicos antes del primer
  push (ver `issue-work`).
- La rama fusionada queda como ancestro de `develop`: `git branch -d` funciona
  y no hace falta `-D` al limpiar.
- No se exigen aprobaciones en los PR: el agente usa el token del usuario y
  GitHub no deja aprobar un PR propio.
