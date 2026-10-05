# saas-ski-portal

Plataforma SaaS de gestion de escuelas de esqui: reservas y jornadas laborales (saas_ski_vesotel). Multiempresa. Este fichero es la unica fuente de reglas para agentes (Claude Code y Orca); no existe AGENTS.md.

## Stack
- `backend/`: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, Redis 7. Capas en `backend/src/{domain,application,infrastructure}`, routers en `backend/routers`. Auth OAuth2 password flow con JWT firmado con RSA.
- `frontend/`: Next.js (App Router), React, TypeScript, shadcn, Tailwind. Tests con vitest.
- `gateway/`: Nginx. Frontend en `/`, backend en `/api/`.
- CI/CD: `.github/workflows/` (`ci.yml`, `deploy-dev.yml`, `deploy-prod.yml`). Cada merge a `develop` o `main` publica imagenes en GHCR con tag SemVer (`dev-vX.Y.Z` o `vX.Y.Z`); despliegue y rollback con Komodo.

## Comandos
- Entorno dev: `./bin/dev`, `./bin/stop`, `./bin/logs`. Tras una base nueva: `./bin/migrate` y `./bin/seed`.
- Docker: usar siempre `docker compose -f docker-compose.dev.yml ...`. El dev depende de volumenes locales y de un target `deps` que no existen en el compose de produccion.
- Todo montaje de volumen lleva sufijo `:z` (SELinux y Podman rootless).
- Backend: `ruff check backend/` y `cd backend && pytest tests/`.
- Frontend (desde `frontend/`): `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build`.
- Desarrollo local: gateway en `http://localhost:${GATEWAY_PORT:-8080}`.
- Sembrado inicial: el backend crea administrador y empresa si `.env` define `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD`; tambien con `./bin/seed` tras `./bin/migrate`.
- `./scripts/sync_db.sh` copia datos de produccion al contenedor local. Requiere SSH autorizado y solo la ejecutan administradores. Nunca lo lances por iniciativa propia.

## Reglas obligatorias

### Git
1. Antes de modificar codigo, comprobar la rama con `git branch --show-current`.
2. `main` y `develop` estan protegidas: nunca push directo. Todo cambio va en una rama `<tipo>/<descripcion-en-espanol>` (ej: `feature/reportes-diarios`, `fix/validador-tarifa`) y se fusiona por Pull Request tras pasar CI.
3. Prohibido ejecutar `git commit`, `git push` o crear PR por iniciativa propia, tambien tras resolver errores. Si el usuario lo ordena en un mensaje concreto (o invoca `/smart-commit`, `/smart-push`, `/smart-pr`, `/smart-flow`), la autorizacion vale solo para esa accion y ese momento. Nunca se arrastra a turnos posteriores: despues, limitarse a editar ficheros locales o reportar y esperar confirmacion.
4. Commits y ramas en ESPANOL (esto prevalece sobre cualquier preferencia global en ingles). Formato `<tipo>(<ambito>): <descripcion concisa>` o `<tipo>: <descripcion concisa>`, ej: `feat: anadir filtro por empresa en dashboard`. Sin version en el titulo del commit.
5. Titulo y descripcion de PR en espanol, mismo formato convencional, sin prefijo `WIP:`.

### Estilo
6. Prohibidos los emojis en cualquier contexto: codigo, comentarios, commits, PR y respuestas. Estilo sobrio, tecnico, texto plano y markdown estandar.
7. Para crear o editar ficheros usar solo las herramientas nativas de edicion (Edit, Write). Prohibido `cat << EOF`, `echo >`, `sed -i` y similares sobre ficheros del repo. Bash queda para tests, linters, git y comandos de sistema.

### Versionado
8. Todo PR con funcionalidad (minor), correccion (patch) o cambio estructural (major) incrementa la version SemVer `PRINCIPAL.MENOR.PARCHE` en tres ficheros: `package.json` (raiz, fuente de verdad), `frontend/package.json` y `CHANGELOG.md` (seccion nueva con version, fecha y resumen, formato Keep a Changelog). Sin incremento se pierde trazabilidad y rollback en Komodo. Excepcion: cambios puramente internos de configuracion local o tooling menor sin efecto en despliegue ni aplicacion.

### Secretos
9. Nunca imprimir ni copiar `.env`, claves RSA (`backend/keys/`) ni tokens a la conversacion, a ficheros versionados o a logs. Si aparece uno en claro, avisar.

## Flujo de trabajo con agentes

### Orquestacion
La sesion principal orquesta; los subagentes no pueden invocar a otros subagentes, asi que el encadenado lo hace la principal. Cada subagente devuelve un resultado breve y verificable.

1. `planner` (sonnet): plan por pasos, tan detallado que un modelo barato lo ejecute sin decidir: ficheros exactos, firmas, contratos de API, casos de prueba y comando de verificacion por paso. Las decisiones abiertas se devuelven como preguntas al usuario.
2. `backend-dev` y `frontend-dev` (haiku): implementan el plan sin ampliar alcance. Si es ambiguo o choca con el codigo, devuelven la duda. Paralelizables si tocan ficheros distintos.
3. `tester` (haiku): escribe y ejecuta pytest o vitest y cita el resultado real.
4. `code-reviewer` (sonnet) audita siempre; ademas `security-reviewer` (auth, endpoints, secretos) o `database-reviewer` (modelos, migraciones) segun el cambio. Solo lectura. `reviewer` valida ademas el cumplimiento de estas reglas.
5. Si un reviewer reporta fallos, se vuelve a delegar al desarrollador y se repite hasta aprobar.
- `devops` para compose, Nginx y workflows. `build-error-resolver` para fallos de build, lint o contenedores. `e2e-runner` para flujos de extremo a extremo (haiku). `b2b-monetization-strategist` para estrategia de producto y monetizacion.
- No implementes codigo extenso tu mismo si puedes delegarlo con un plan claro. Si un agente haiku se atasca, subelo a sonnet en su frontmatter.
- Tareas no triviales: plan corto, implementacion, tests, revision. Si un test falla, diagnostica la causa antes de reintentar. Verifica antes de afirmar: ejecuta el comando real y cita el resultado; si no pudiste verificar, dilo.
- Skills de git (`smart-commit`, `smart-push`, `smart-pr`, `smart-flow`, `daily-sync`): solo las invoca el usuario (`disable-model-invocation`).

### Orca: un worktree por tarea
Orca crea un git worktree aislado por tarea. Configuracion en `orca.yaml` (raiz).
- **Crear**: pulsar `+` junto al repo, nombrar la tarea y partir de `develop`. Poner a la rama el nombre `<tipo>/<descripcion-en-espanol>` (regla 2). Elegir Claude Code en el desplegable de agente.
- **Setup automatico**: `scripts.setup` ejecuta `./bin/orca-setup`, que genera el `.env` del worktree copiando el del checkout principal (`ORCA_ROOT_PATH`) y fijando `COMPOSE_PROJECT_NAME`, `GATEWAY_PORT`, `POSTGRES_PORT`, `REDIS_PORT` y `ALLOWED_ORIGINS` propios (puertos deterministas por ruta, saltando los ocupados). Despues: `./bin/dev && ./bin/migrate && ./bin/seed`. `frontend/node_modules` se comparte entre worktrees (`worktree.sharedDirectories`).
- **Archivar**: `scripts.archive` ejecuta `./bin/orca-archive`, que baja el stack Docker del worktree y borra sus volumenes.
- **Un worktree, una tarea, un PR.** Evitar que dos worktrees toquen los mismos ficheros.
- **Version**: el incremento SemVer (regla 8) genera conflicto si varios PRs paralelos editan `package.json` y `CHANGELOG.md`. Hacerlo al final, sobre `develop` actualizado, justo antes del PR.
- **Revision y entrega**: revisar el diff en Orca con comentarios en linea que vuelven al agente. Commit, push y PR solo cuando el usuario lo ordene (regla 3), incluso si Orca ofrece botones para ello.
- **Pestanas en el mismo worktree**: para un agente extra sobre el mismo codigo (revision, investigacion, segundo frente sin solapar ficheros) abrir una pestana nueva con `orca terminal create --worktree active --command claude`. Para una tarea con rama propia, un worktree nuevo: `orca worktree create --name <tarea> --agent claude --prompt "<brief>"` (cargar antes `orca skills get orca-cli`).
- Varios agentes en paralelo: cada uno en su worktree. Para comparar enfoques, el mismo prompt en varios worktrees y quedarse con el mejor.
