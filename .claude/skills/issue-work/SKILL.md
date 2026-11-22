---
name: issue-work
description: Lleva una issue de principio a fin dentro de su worktree - lee la issue y el contexto que cita, implementa con TDD delegando en subagentes, verifica, pasa code-reviewer (y security-reviewer o database-reviewer si aplica), hace commit, push y PR a develop con Closes #n, y hace merge commit a develop solo si los checks estan en verde y el veredicto es APTO. Usar con "/issue-work <n>" (lo lanza issue-start).
disable-model-invocation: true
---

# issue-work

La issue es la especificacion. No necesitas la conversacion que la origino.
Eres el orquestador: delegas la implementacion y las pruebas en subagentes y
decides tu.

## Autorizacion (ADR-0002)

Ejecutar esta skill sobre una issue en "Listo para agente" autoriza, solo para
esa issue y su rama: hacer commits, `git push -u origin <rama>`, abrir un PR a
`develop`, sincronizarla con `git merge origin/develop` y hacer merge commit a
`develop` si se cumplen las condiciones del paso 6.7. Tras el merge, cerrar esa
misma issue si sigue abierta y archivar su propio worktree (paso 6.8).

No autoriza: push a `main` o `develop`, force-push, merge a `main`, squash o
rebase, tocar otras ramas o issues, ejecutar `./scripts/sync_db.sh`, leer
`.env`, ni salirse del alcance de la issue. Los hooks bloquean lo peor, pero la
responsabilidad es tuya.

## Checkpoints, reanudacion y pausa

- **Checkpoint.** Al terminar cada fase (plan, tests en rojo, implementacion
  en verde, verificacion), haz un commit local `wip(<ambito>): <fase>`. Si no
  hay cambios (por ejemplo, en el plan), usa `git commit --allow-empty` con el
  plan en el cuerpo. Los `wip` no se suben: el paso 6.2 los compone en commits
  atomicos antes del primer push. Desde el primer push no hagas mas `wip`.
- **Pausa.** Si recibes "pausa": haz un checkpoint (con `git add` solo de
  ficheros de la issue), comenta en la issue la fase y el siguiente paso, y
  para.
- **Reanudar.** Al arrancar, antes del paso 1, detecta el estado y continua
  desde ahi. Nunca empieces de cero si hay rastro:

  ```bash
  git status -s
  git log --oneline origin/develop..HEAD
  git ls-remote --heads origin <rama>
  gh pr list --repo hugovelez16/saas-ski-portal --head <rama> --state all \
    --json number,state,mergedAt
  gh issue view <n> --repo hugovelez16/saas-ski-portal --comments
  ```

  | Estado | Continua en |
  |---|---|
  | Cambios sin commit | Fase de esos cambios; haz su checkpoint |
  | Ultimo `wip` de plan | Paso 3 |
  | Ultimo `wip` de tests en rojo | Paso 3, implementacion |
  | Ultimo `wip` de implementacion | Paso 4 |
  | Ultimo `wip` de verificacion | Paso 5 |
  | Sin `wip`, rama en el remoto | Paso 6.4 (hay PR?) |
  | PR abierta | Paso 6.5 en adelante |
  | PR fusionada | Paso 6.8 (cierre y archivado), con el informe del paso 7 |

  Si el estado no encaja con ninguna fila, para y comenta en la issue.
- **Efectos externos idempotentes.** Antes de crear un PR o un comentario,
  comprueba si ya existe. Firma tus comentarios con `[issue-work #<n>] <fase>`.

## Flujo

### 1. Contexto (solo lectura)

1. `gh issue view <n> --repo hugovelez16/saas-ski-portal --comments`.
2. Lee `CLAUDE.md` y SOLO las rutas de "Contexto a leer" y "Ficheros
   probables". No explores el repo entero.
3. Comprueba que `git branch --show-current` es `<tipo>/<n>-...`. Si no, para.
4. Si falta contexto o hay una regla ambigua: comenta la duda en la issue,
   mueve la issue a "Backlog" con `scripts/project-estado.sh` y para.
5. Si "Ficheros probables" incluye `.claude/**` o `.githooks/**`, para sin
   tocar nada: esas rutas estan en `permissions.deny` y las cambia el usuario.
   Comentalo en la issue y muevela a "Backlog" con la label `bloqueada`.

### 2. Plan

Plan corto: que ficheros, que tests y en que orden, cubriendo cada criterio de
aceptacion. Indica si hay migracion Alembic. No lo pidas aprobar: la issue ya
es el encargo. Checkpoint: `wip(<ambito>): plan`.

### 3. Implementacion

- Delega con el contexto exacto (rutas, firmas, texto de las reglas citadas,
  criterio de aceptacion y comando de verificacion). Nunca "lee docs/":
  - `tester` (haiku): escribe primero los tests y los ve fallar. Checkpoint
    `wip(<ambito>): tests en rojo`.
  - `backend-dev` y `frontend-dev` (haiku): implementan. En paralelo solo si
    no tocan los mismos ficheros. Si uno se atasca dos veces, relanzalo con
    `model: sonnet`.
  - Migraciones: skill `database-migrations` (reversible, sin editar
    migraciones aplicadas, un solo head).
- Cuando todo este en verde: checkpoint `wip(<ambito>): implementacion`.
- Solo docs: escribe el contenido tu y haz el checkpoint.
- Lo que encuentres fuera del alcance no lo arregles: registralo con
  `/issue-create` y citalo en el PR.

### 4. Verificacion

Desde la raiz del worktree:

```bash
ruff check backend/
(cd backend && pytest tests/)
(cd frontend && npm run lint && npx tsc --noEmit && npm test && npm run build)
node --test 'tests/hooks/*.test.mjs'   # solo si tocas .claude/hooks o .githooks
```

- Los tests del backend nunca usan `DATABASE_URL` (SQLite en memoria o
  `TEST_DATABASE_URL`). Si necesitan el PostgreSQL del worktree:
  `docker compose -f docker-compose.dev.yml exec backend pytest tests/`.
- Si `frontend/node_modules` no existe en el worktree, ejecuta los comandos
  de frontend en su contenedor:
  `docker compose -f docker-compose.dev.yml exec frontend npm run lint` (y
  los demas).
- Ejecuta solo lo que el cambio afecta (backend, frontend o ambos), mas lo que
  pida la issue. Comprueba cada criterio con su comando y guarda la salida
  resumida. Checkpoint: `wip(<ambito>): verificacion`.
- Como maximo 3 vueltas de correccion. Si tras 3 sigue fallando, no hagas
  push: comenta en la issue que falla, ejecuta
  `scripts/project-estado.sh <n> "Backlog"`, anade la label `bloqueada` y para.

### 5. Revision

Lanza `code-reviewer` con el numero de la issue, la salida de
`git diff origin/develop...HEAD` y el texto de las reglas citadas. Ademas:

- `security-reviewer` si el diff toca auth, tokens, permisos, endpoints,
  aislamiento por empresa, gateway o secretos.
- `database-reviewer` si toca `backend/models.py`, `crud.py`, consultas o
  `backend/migrations/`.

El veredicto final es `APTO` solo si todos los revisores lanzados dan `APTO`.
Con `NO APTO`, corrige y vuelve al paso 4. Cada correccion cuenta como vuelta.

### 6. Entrega

1. **CHANGELOG.** Anade tu linea en `## [Unreleased]` de `CHANGELOG.md`, bajo
   el subtitulo que toque (`### Anadido`, `### Cambiado`, `### Corregido`,
   `### Eliminado`, `### Seguridad`), con `(#<n>)` al final. No toques `package.json` ni
   `frontend/package.json` (ADR-0001).
2. **Commits.** Sigue `docs/flujo/git.md`: commits atomicos, en espanol, sin
   emojis y sin `Co-Authored-By` ni pies de atribucion. Revisa antes
   `git status -s` y no metas ficheros ajenos a la issue. Compon los `wip`
   (con merge commit llegarian tal cual a `develop`):

   ```bash
   git reset --soft "$(git merge-base origin/develop HEAD)"
   # despues, commits atomicos con git add de los ficheros de cada uno
   ```

   Es seguro solo si la rama no esta en el remoto.
3. **Push.** Comprueba que `git log origin/develop..HEAD --format=%s` no
   contiene `wip(`. Si lo contiene, vuelve al paso 6.2. Despues
   `git push -u origin <rama>`.
4. **PR.** Si ya existe
   (`gh pr list --repo hugovelez16/saas-ski-portal --head <rama> --state open`),
   reutilizalo. Si no, escribe el cuerpo en el scratchpad con las secciones de
   `.github/pull_request_template.md`, `Closes #<n>` y la verificacion real:

   ```bash
   gh pr create --repo hugovelez16/saas-ski-portal --base develop \
     --title "<tipo>(<ambito>): <descripcion>" --body-file <fichero>
   scripts/project-estado.sh <n> "En revision"
   ```

5. **Checks.** `gh pr checks <pr> --watch`. Si alguno falla, diagnostica con
   `gh run view <id> --log-failed`, corrige, commit normal, push y vuelve a
   mirar. Cuenta como vuelta.
6. **Sincronizacion.** `develop` exige rama al dia. Mira
   `gh pr view <pr> --json mergeable,mergeStateStatus`. Si es `DIRTY` o
   `BEHIND`: `git fetch origin && git merge origin/develop`. Nunca rebase ni
   force-push. Conflictos:
   - `CHANGELOG.md`: conserva las dos partes en `[Unreleased]`.
   - `backend/migrations/versions/`: si `develop` trae otra migracion, no
     edites la suya; ajusta `down_revision` de la tuya para que quede un solo
     head y comprueba con `alembic heads`.
   - Otro fichero: para y comenta en el PR.

   Repite la verificacion del paso 4, commit del merge y push normal. Espera a
   que los checks pasen otra vez.
7. **Merge.** Solo si los checks estan en verde y el veredicto es `APTO`:

   ```bash
   gh pr merge <pr> --repo hugovelez16/saas-ski-portal --merge --delete-branch
   gh pr view <pr> --repo hugovelez16/saas-ski-portal --json state,mergedAt
   ```

   Desde un worktree, `--delete-branch` puede terminar con error porque no
   puede hacer checkout de `develop` (lo ocupa el checkout principal) aunque el
   merge remoto se haya hecho. No te fies del codigo de salida: si `state` es
   `MERGED`, sigue con el paso 6.8; si no, comenta el error en el PR y para.

   Si no se cumplen las dos condiciones, comenta en el PR que falta y para.
   Si el PR lleva migracion con paso previo de despliegue (backup o script de
   reparacion), no hagas merge: comenta los pasos y deja la decision al
   usuario.
8. **Cierre.** Solo con `state` `MERGED` confirmado. Si no hubo merge (`NO APTO`,
   checks en rojo, migracion con paso previo, error), no hagas nada de esto: el
   worktree se queda para retomarlo y lo archiva el usuario a mano.
   1. `scripts/project-estado.sh <n> "Hecho"`.
   2. `Closes #<n>` solo actua con merge a la rama por defecto, y aqui el merge
      es a `develop`. Comprueba y cierra la issue si sigue abierta:

      ```bash
      gh issue view <n> --repo hugovelez16/saas-ski-portal --json state
      gh issue close <n> --repo hugovelez16/saas-ski-portal \
        --comment "Hecho en #<pr> (fusionado en develop)."
      ```

      El `close` solo se ejecuta si `state` no es `CLOSED`.
   3. Publica el informe del paso 7 como comentario en la issue, firmado
      `[issue-work #<n>] informe`, con el cuerpo en un fichero del scratchpad:

      ```bash
      gh issue comment <n> --repo hugovelez16/saas-ski-portal --body-file <fichero>
      ```

      Hazlo antes de archivar: archivar mata la terminal del agente y despues
      ya no puedes publicar ni responder nada.
   4. **Archivar el worktree. Es la ultima accion: no hagas nada despues y
      ningun paso posterior puede depender del worktree.** Obten la ruta
      absoluta con `git rev-parse --show-toplevel` y ejecuta:

      ```bash
      "${ORCA_CLI_COMMAND:-orca-ide}" worktree rm --worktree path:<ruta absoluta> \
        --run-hooks --allow-failed-archive-hook --delete-branch --json
      ```

      Usa siempre `path:<ruta>`: Orca rechaza `--worktree current` y
      `--worktree active` en `worktree rm`. `--run-hooks` ejecuta
      `./bin/orca-archive` (baja el stack y borra sus volumenes) y
      `--allow-failed-archive-hook` evita que un fallo del hook bloquee el
      archivado. Si Orca no esta disponible, no borres nada a mano (ni
      `git worktree remove` ni `rm`): dilo en el informe y deja que lo archive
      el usuario.

### 7. Informe

Devuelve la URL de la issue y la del PR, si se hizo merge o no y por que, la
verificacion (comando y resultado), las issues creadas durante el trabajo y el
veredicto de cada revisor. Con merge, este mismo informe es el que se publica
en la issue en el paso 6.8.3, antes de archivar. Anade si el archivado se hara
(o si Orca no estaba disponible y lo debe hacer el usuario).
