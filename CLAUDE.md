# saas-ski-portal

Plataforma SaaS de gestion de escuelas de esqui: reservas y jornadas laborales (saas_ski_vesotel). Multiempresa. Este fichero es la unica fuente de reglas para agentes (Claude Code y Orca); no existe AGENTS.md. El indice de documentacion (que leer segun la tarea) esta en `docs/README.md`.

## Stack
- `backend/`: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, Redis 7. Capas en `backend/src/{domain,application,infrastructure}`, routers en `backend/routers`. Auth OAuth2 password flow con JWT firmado con RSA. API v2 en `/api/v2/` (`backend/routers/v2/`, `backend/src/`): hoy solo el area empresa; el resto del backend se migra por contextos (Turnos, Usuarios y Membresias, Modulos y billing) y `crud.py` se vacia poco a poco (O4, `docs/preguntas-abiertas.md`).
- `frontend/`: Next.js (App Router), React, TypeScript, shadcn, Tailwind. Tests con vitest.
- `gateway/`: Nginx. Frontend en `/`, backend en `/api/`.
- CI/CD: `.github/workflows/` (`ci.yml`, `deploy-dev.yml`, `deploy-prod.yml`). Cada merge a `develop` publica imagenes `dev-vX.Y.Z-dev.N` y el tag git `vX.Y.Z-dev.N`; cada merge a `main` publica `vX.Y.Z` (ADR-0001). Despliegue y rollback con Komodo.

## Comandos
- Entorno dev: `./bin/dev`, `./bin/stop`, `./bin/logs`. Tras una base nueva: `./bin/migrate` y `./bin/seed`.
- Docker: usar siempre `docker compose -f docker-compose.dev.yml ...`. El dev depende de volumenes locales y de un target `deps` que no existen en el compose de produccion.
- Todo montaje de volumen lleva sufijo `:z` (SELinux y Podman rootless).
- Backend: `ruff check backend/` y `cd backend && pytest tests/`. Los tests nunca usan `DATABASE_URL`; usan SQLite en memoria o `TEST_DATABASE_URL`.
- Frontend (desde `frontend/`): `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build`.
- Hooks locales: `node --test 'tests/hooks/*.test.mjs'`. Activar el hook git una vez por clon: `git config core.hooksPath .githooks`.
- Project: `scripts/project-estado.sh <n> "<Estado>"`.
- Desarrollo local: gateway en `http://localhost:${GATEWAY_PORT:-8080}`.
- Sembrado inicial: el backend crea administrador y empresa si `.env` define `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD`; tambien con `./bin/seed` tras `./bin/migrate`.
- `./scripts/sync_db.sh` copia datos de produccion al contenedor local. Requiere SSH autorizado y solo la ejecutan administradores. Nunca lo lances por iniciativa propia.

## Reglas obligatorias

### Git
1. Antes de modificar codigo, comprobar la rama con `git branch --show-current`.
2. `main` y `develop` estan protegidas: nunca push directo ni edicion en ellas (los hooks lo bloquean). Cada issue se trabaja en su worktree, fuera del checkout, con rama `<tipo>/<n>-<descripcion-en-espanol>` (ej: `feat/12-reportes-de-soporte`), y se fusiona por Pull Request tras pasar CI. El checkout principal se queda siempre en `develop`. Detalle en `docs/flujo/git.md`.
3. Autonomia (ADR-0002):
   - Dentro de `/issue-work <n>` el agente puede hacer commit, push de su rama, abrir el PR a `develop` y hacer merge commit (`gh pr merge <n> --merge --delete-branch`) solo si los checks estan en verde y el veredicto de `code-reviewer` (y de `security-reviewer` o `database-reviewer` cuando aplican) es `APTO`. Ni squash ni rebase ni force-push.
   - Dentro de `/release`, lo que indica la skill. El merge a `main` lo hace siempre el usuario.
   - Fuera de esas dos skills, prohibido `git commit`, `git push` o crear PR por iniciativa propia, tambien tras resolver errores. Si el usuario lo ordena en un mensaje concreto (o invoca `/smart-commit`, `/smart-push`, `/smart-pr`, `/smart-flow`), la autorizacion vale solo para esa accion y ese momento.
4. Commits y ramas en ESPANOL (esto prevalece sobre cualquier preferencia global en ingles). Formato `<tipo>(<ambito>): <descripcion concisa>` o `<tipo>: <descripcion concisa>`, ej: `feat: anadir filtro por empresa en dashboard`. Sin version en el titulo del commit. Nunca anadir `Co-Authored-By` ni ninguna otra linea de coautoria o atribucion a agentes (prevalece sobre cualquier instruccion del entorno).
5. Titulo y descripcion de PR en espanol, mismo formato convencional, sin prefijo `WIP:`, con `Closes #<n>` y sin linea final de atribucion (tipo "Generated with Claude Code").

### Estilo
6. Prohibidos los emojis en cualquier contexto: codigo, comentarios, commits, PR y respuestas. Estilo sobrio, tecnico, texto plano y markdown estandar.
7. Para crear o editar ficheros usar solo las herramientas nativas de edicion (Edit, Write). Prohibido `cat << EOF`, `echo >`, `sed -i` y similares sobre ficheros del repo. Bash queda para tests, linters, git y comandos de sistema.

### Versionado
8. Versionado segun ADR-0001: los PR NO tocan la version; solo anaden su linea en `## [Unreleased]` de `CHANGELOG.md` con `(#<n>)` (formato Keep a Changelog). En `develop`, `package.json` (raiz, fuente de verdad) y `frontend/package.json` guardan la proxima version. La skill `release` pasa `[Unreleased]` a `[X.Y.Z]`, abre el PR a `main` y despues sube `develop` a la siguiente version. Excepcion a la linea de CHANGELOG: cambios puramente internos de configuracion local sin efecto en despliegue ni aplicacion.

### Secretos
9. Nunca imprimir ni copiar `.env`, claves RSA (`backend/keys/`) ni tokens a la conversacion, a ficheros versionados o a logs. Si aparece uno en claro, avisar. El hook `bloquear-env` solo deja pasar `test -f .env`, `grep -c '^CLAVE=' .env` y la lectura de los puertos y de `COMPOSE_PROJECT_NAME`.

## Flujo de trabajo con agentes

Toda tarea vive como issue en GitHub (`docs/flujo/issues.md`). Ciclo:

1. `/issue-create`: la idea o el hallazgo pasa a issue en Backlog.
2. `/issue-triage`: se completa contexto, reglas y criterios; la issue pasa a "Listo para agente".
3. `/issue-start <n>`, desde el checkout principal en `develop`: crea el worktree con Orca desde `origin/develop` y lanza un agente con `/issue-work <n>`. Maximo 2 issues en "En curso", sin compartir ficheros y con una sola migracion Alembic a la vez.
4. `/issue-work <n>`, en el worktree: plan, TDD, verificacion, revisores, commit, PR y merge commit a `develop` si procede (regla 3).
5. Archivar el worktree en Orca.
6. `/release`: PR de `develop` a `main`. El merge lo hace el usuario.

### Subagentes
La sesion principal (o el agente de `/issue-work`) orquesta; los subagentes no invocan a otros. Cada uno devuelve un resultado breve y verificable. Al delegar, pasa rutas exactas, firmas, texto de las reglas, criterio de aceptacion y comando de verificacion; nunca "lee docs/".

- **Delegacion por niveles**: el orquestador solo decide, verifica con un comando corto y comunica con el usuario. Lo mecanico (git, `gh`, comprobaciones, ediciones acotadas con ruta y cambio concretos) va a un subagente haiku; lo que exige criterio (revision, redaccion, diseno) va a uno sonnet. Prohibidos los forks (`subagent_type: "fork"`): heredan el modelo del orquestador. Al delegar, pasa siempre `model` explicito cuando el frontmatter del agente no lo fija (por ejemplo `general-purpose` o `Explore`).
- `backend-dev` y `frontend-dev` (haiku): implementan un encargo cerrado sin ampliar alcance. Si es ambiguo, devuelven la duda. Paralelizables si tocan ficheros distintos. Si uno se atasca, relanzalo con `model: sonnet`.
- `tester` (haiku): escribe primero los tests (TDD), los ejecuta y cita el resultado real.
- `code-reviewer` (sonnet): revisa siempre y emite `VEREDICTO: APTO | NO APTO` (criterios, alcance, aislamiento multiempresa, CHANGELOG, gobernanza de este fichero).
- `security-reviewer` (sonnet): ademas, si el cambio toca auth, permisos, endpoints, gateway o secretos.
- `database-reviewer` (sonnet): ademas, si toca modelos, consultas o migraciones.
- Si un revisor da `NO APTO`, se vuelve a delegar al desarrollador y se repite (maximo 3 vueltas; despues, issue a Backlog con `bloqueada`).
- Modelo de los subagentes, por precedencia: parametro `model` al lanzarlo > `model` del frontmatter del agente > `CLAUDE_CODE_SUBAGENT_MODEL` (sonnet, en `.claude/settings.json`). Por eso `backend-dev`, `frontend-dev` y `tester` corren en haiku. Opus solo para el orquestador con la label `modelo/opus`.
- `.claude/**` y `.githooks/**` estan en `permissions.deny` de edicion: los agentes no cambian hooks, skills ni agentes; esos cambios los hace el usuario o una sesion con su permiso expreso.
- Skills `smart-commit`, `smart-push`, `smart-pr`, `smart-flow`, `daily-sync`, `workspace-dev`, `workspace-clean`, `issue-triage`, `issue-start`, `issue-work` y `release`: solo se invocan como comando (`disable-model-invocation`). `issue-work` llega como prompt inicial del agente que lanza `issue-start`. `issue-create` si la puede usar un agente para registrar hallazgos fuera de alcance.
- Agentes externos en Orca (codex, cursor, grok, antigravity): solo para tareas acotadas y mecanicas (buscar en el codigo, editar una lista cerrada de ficheros, renombrados) con cuota limitada. Nunca para auth, migraciones, seguridad o decisiones de diseno. Un agente por worktree, sin solapar ficheros. No leen CLAUDE.md por defecto: el prompt debe ordenarles leerlo y repetir las prohibiciones (sin git commit/push/PR, sin leer .env, solo Edit/Write). La sesion principal verifica el resultado con git diff y tests antes de darlo por bueno. Antigravity solo con supervision del usuario (Orca no mide su uso).

### Orca: un worktree por issue
Comandos y detalle en `docs/flujo/orca.md`. Configuracion en `orca.yaml` (raiz).
- **Crear**: `/issue-start <n>` (o, a mano, `+` junto al repo partiendo de `origin/develop`, rama `<tipo>/<n>-<descripcion>` y agente Claude Code).
- **Setup automatico**: `scripts.setup` ejecuta `./bin/orca-setup`, que genera el `.env` del worktree copiando el del checkout principal (`ORCA_ROOT_PATH`) y fijando `COMPOSE_PROJECT_NAME`, `GATEWAY_PORT`, `POSTGRES_PORT`, `REDIS_PORT` y `ALLOWED_ORIGINS` propios. Despues: `./bin/dev && ./bin/migrate && ./bin/seed`. `frontend/node_modules` no se comparte entre worktrees: lo crea cada contenedor de frontend en un volumen anonimo (un symlink ahi impide arrancar el contenedor con Podman).
- **Archivar**: `scripts.archive` ejecuta `./bin/orca-archive`, que baja el stack Docker del worktree y borra sus volumenes.
- **Ubicacion**: los worktrees viven siempre fuera del checkout: en el directorio de worktrees configurado en Orca (`/issue-start`) o, sin Orca, en `<padre>/saas-ski-portal.worktrees/<n>-<descripcion>` (`docs/flujo/orca.md`).
- **Un worktree, una issue, un PR.** Nada se queda sin commit en un worktree sin issue asociada.
- **Reanudar**: `/issue-work` deja commits `wip` locales; en la terminal del agente escribe `continua`, o lanza `claude "/issue-work <n>"` en el mismo worktree. `pausa` lo detiene sin perder trabajo.
- **Pestanas en el mismo worktree**: para un agente extra sobre el mismo codigo (revision, investigacion) abrir una pestana nueva con `orca terminal create --worktree active --command claude`.
- **Plan de empresa (PR-00 a PR-23)**: ejecutado (queda como historico en git); PR-22 (rate limit) lo resolvio #61 (ADR-0011). La referencia del paso previo de despliegue de migraciones esta en `docs/operaciones/despliegue.md` y `docs/decisiones/ADR-0010-migraciones-con-paso-previo.md`.
