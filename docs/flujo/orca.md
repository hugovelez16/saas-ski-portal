# Flujo con Orca

Una issue equivale a un worktree, una rama, un agente y un PR.

## CLI

- Fuera de las terminales de Orca, la CLI es `orca-ide`, o
  `$ORCA_CLI_COMMAND` si esta definida. En Linux, `orca` a secas es el lector
  de pantalla de GNOME.
- Dentro de las terminales de Orca, `orca` funciona.
- En los ejemplos, `ORCA="${ORCA_CLI_COMMAND:-orca-ide}"`. Si un flag falla,
  consulta `$ORCA <comando> --help` antes de reintentar.

## Donde viven los worktrees

Siempre fuera del checkout (`/home/usuario/00_datos/saas-ski-portal`):

| Como se crea | Donde |
|---|---|
| Orca (`/issue-start`) | El directorio de worktrees configurado en Orca |
| Terminal, sin Orca | `/home/usuario/00_datos/saas-ski-portal.worktrees/<n>-<descripcion>` |

El checkout principal se queda siempre en `develop` y solo se usa para
sincronizar (`/daily-sync`), hacer triaje (`/issue-triage`) y lanzar issues
(`/issue-start`). Los hooks impiden editarlo mientras este en `develop`.

## Configuracion (una vez)

```bash
$ORCA repo add --path /home/usuario/00_datos/saas-ski-portal
$ORCA repo set-base-ref --repo path:/home/usuario/00_datos/saas-ski-portal --ref origin/develop
git -C /home/usuario/00_datos/saas-ski-portal config core.hooksPath .githooks
```

## Ciclo de una issue

1. **Lanzar** (`/issue-start <n>`, desde el checkout principal):

   ```bash
   git fetch origin
   $ORCA worktree create \
     --repo path:/home/usuario/00_datos/saas-ski-portal \
     --name <n>-<descripcion> \
     --no-parent \
     --base-branch origin/develop \
     --branch <tipo>/<n>-<descripcion> \
     --issue <n> \
     --agent claude \
     --model <sonnet|opus> \
     --effort medium \
     --setup run \
     --prompt "/issue-work <n>" \
     --json
   ```

   `--setup run` ejecuta `./bin/orca-setup` (declarado en `orca.yaml`). Copia
   el `.env` del checkout principal sin mostrarlo y fija `COMPOSE_PROJECT_NAME`,
   `GATEWAY_PORT`, `POSTGRES_PORT`, `REDIS_PORT` y `ALLOWED_ORIGINS` propios
   del worktree (puertos deterministas por ruta, saltando los ocupados).
   `frontend/node_modules` no se comparte: lo crea cada contenedor de frontend
   en un volumen anonimo.

   Comprueba que el agente recibio el prompt. `handed-to-terminal` no lo
   garantiza:

   ```bash
   $ORCA terminal list --worktree path:<ruta-del-worktree> --json
   $ORCA terminal read --terminal <handle> --screen --json
   # Solo si /issue-work <n> no aparece en la pantalla:
   $ORCA terminal send --terminal <handle> --text "/issue-work <n>" \
     --enter --wait-submit 20 --json
   ```

   Si arranco: `scripts/project-estado.sh <n> "En curso"`.

   - Modelo: `sonnet` con esfuerzo `medium` por defecto; `opus` solo con la
     label `modelo/opus`.
   - Como maximo 2 issues en "En curso" a la vez, sin compartir "Ficheros
     probables" (salvo `CHANGELOG.md`). Dos issues con migracion Alembic no van
     en paralelo: generarian dos heads.

2. **Trabajar:** el agente sigue `/issue-work <n>`. Si necesita el stack:
   `./bin/dev && ./bin/migrate && ./bin/seed`.

3. **Otro agente en el mismo worktree** (revision, investigacion):

   ```bash
   $ORCA terminal create --worktree active --command claude
   ```

4. **Reanudar un agente cortado.** `/issue-work` deja commits locales
   `wip(<ambito>): <fase>` y al arrancar detecta el estado y continua. En la
   terminal del agente escribe `continua`, o en una terminal nueva del mismo
   worktree `claude "/issue-work <n>"`. Para pararlo sin perder nada,
   escribele `pausa`. No reanudes en otro worktree: los `wip` solo existen en
   local.

5. **Limpiar:** `/issue-work` archiva su propio worktree tras el merge, como
   ultima accion: `$ORCA worktree rm --worktree path:<ruta> --run-hooks
   --allow-failed-archive-hook --delete-branch --json`. Antes cierra la issue
   si sigue abierta, la mueve a "Hecho" y publica el informe como comentario.
   `--run-hooks` lanza `./bin/orca-archive`, que baja el stack del worktree con
   `down -v`. Tu solo archivas a mano (desde Orca) los worktrees sin merge
   (`NO APTO`, checks en rojo, migracion con paso previo) cuando ya no los
   necesites, o si Orca no estaba disponible. Para worktrees creados a mano,
   skill `workspace-clean`.

6. **Actualizar** el checkout principal: `/daily-sync`.

## Sin Orca (terminal)

```bash
git fetch origin
git worktree add --no-track -b <tipo>/<n>-<descripcion> \
  ../saas-ski-portal.worktrees/<n>-<descripcion> origin/develop
cd ../saas-ski-portal.worktrees/<n>-<descripcion>
ORCA_ROOT_PATH=/home/usuario/00_datos/saas-ski-portal ORCA_WORKTREE_PATH="$PWD" ./bin/orca-setup
claude "/issue-work <n>"
```

Limpieza, despues de confirmar que el PR esta fusionado:

```bash
git worktree remove ../saas-ski-portal.worktrees/<n>-<descripcion>
git branch -d <tipo>/<n>-<descripcion>
```

Con merge commit la rama queda integrada en `develop`, asi que basta `-d`.
