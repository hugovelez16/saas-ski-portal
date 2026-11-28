---
name: release
description: Prepara una release de saas-ski-portal - PR chore(release) que pasa [Unreleased] a [X.Y.Z] en el CHANGELOG, PR develop -> main que fusiona el usuario y, tras el merge, PR que sube develop a la siguiente version. Nunca hace el merge a main. Usar con "/release".
disable-model-invocation: true
---

# release

La decision esta en ADR-0001 y el detalle en `docs/flujo/git.md`. El merge a
`main` lo hace SIEMPRE el usuario (ADR-0002). El hook `guardas-git` lo bloquea
de todas formas.

## Delegacion (obligatoria)

La sesion que ejecuta esta skill orquesta: decide, pregunta al usuario
(AskUserQuestion) y verifica cada resultado con un comando corto. No ejecuta a
mano los pasos mecanicos, aunque sea Opus y la skill este cargada.

- Subagente haiku (`general-purpose` con `model: haiku`): comprobaciones de
  git y `gh`, crear issues, worktree y rama, editar `CHANGELOG.md` o los
  `package.json` con el cambio exacto, commit, push, PR, esperar checks, merge
  commit y estados del Project. Pasale rutas, comandos, texto exacto y
  criterio de exito.
- Sonnet: redactar el resumen SemVer o el cuerpo del PR cuando exija criterio.
- `code-reviewer`: revision antes de cada merge a `develop`.
- Prohibidos los forks (heredan el modelo del orquestador).

## 1. Comprobaciones

```bash
git fetch origin
git log --oneline origin/main..origin/develop
gh pr list --repo hugovelez16/saas-ski-portal --base develop --state open
```

- Si `develop` no tiene commits nuevos respecto a `main`, para.
- Si hay PR abiertos a `develop`, enumeralos y pregunta si se espera a ellos.
- Lee `docs/operaciones/tareas-manuales-release.md` y la seccion `[Unreleased]`:
  si hay migraciones con paso previo (backup, script de reparacion) o
  variables nuevas, enumeralos para el usuario.

## 2. Version

- La version es la de `package.json` en `origin/develop` (la proxima).
- Revisa `[Unreleased]`: si hay cambios incompatibles y la version no lo
  refleja, proponselo al usuario (MAJOR, MINOR o PATCH) y confirma.
- `package.json` y `frontend/package.json` tienen que coincidir.

## 3. PR de release

1. Crea la issue con `/issue-create`: titulo `chore(release): vX.Y.Z`, labels
   `tipo/chore`, `area/flujo` y `prioridad/alta`. Te da `<n>`.
2. Crea la rama `chore/<n>-release-vX-Y-Z` desde `origin/develop` en un
   worktree (`docs/flujo/orca.md`, bloque "Sin Orca").
3. En `CHANGELOG.md`:
   - renombra `## [Unreleased]` a `## [X.Y.Z] - <AAAA-MM-DD>`;
   - anade debajo `### Tipo de Cambio SemVer` con una linea (MAJOR, MINOR o
     PATCH y el resumen);
   - anade encima un `## [Unreleased]` vacio.

   Este PR no anade una linea nueva a `[Unreleased]`.
4. Commit: `chore(release): prepara vX.Y.Z`, sin `Co-Authored-By` ni pies de
   atribucion.
5. Push de la rama y PR a `develop` con `Closes #<n>`. Merge commit
   (`gh pr merge <pr> --merge --delete-branch`) solo si los checks estan en
   verde y `code-reviewer` da `APTO`. Mueve la issue a "En curso" al crear la
   rama y a "En revision" al abrir el PR. Tras el merge, comprueba
   `gh pr view <pr> --json state,mergedAt` (el codigo de salida de
   `--delete-branch` desde un worktree no es fiable) y, si `state` es `MERGED`,
   `scripts/project-estado.sh <n> "Hecho"`.
6. Abre el PR `develop` -> `main`:

   ```bash
   gh pr create --repo hugovelez16/saas-ski-portal --base main --head develop \
     --title "chore(release): publicar vX.Y.Z" --body-file <fichero>
   ```

   El cuerpo lleva la seccion `[X.Y.Z]` del CHANGELOG, los pasos manuales
   previos y la verificacion.
7. Avisa al usuario: "PR de release listo: <url>. El merge (merge commit) lo
   haces tu cuando los checks esten en verde."

## 4. Despues del merge (cuando el usuario lo confirme)

1. Comprueba el merge: `gh pr view <pr> --json state,mergedAt`.
2. `deploy-prod` publica `vX.Y.Z` y `latest`. Comprueba que el run termino
   bien (`gh run list --workflow deploy-prod.yml --limit 1`).
3. Sube `develop` a la siguiente version:
   1. Crea la issue `chore(release): sube develop a vX.Y+1.0` con
      `/issue-create`. Te da `<m>`.
   2. Rama `chore/<m>-subir-version` desde `origin/develop`.
   3. Sube `package.json` y `frontend/package.json` (y sus lockfiles si
      guardan la version) a la siguiente version. Por defecto el siguiente
      minor; pregunta si es un patch.
   4. PR a `develop` con `Closes #<m>`. No anade linea de CHANGELOG. Merge
      commit con checks en verde y `APTO`.

## 5. Informe

Devuelve la version publicada, la URL del PR de release, la del PR a `main` y
la del PR de la siguiente version, si lo hubo.
