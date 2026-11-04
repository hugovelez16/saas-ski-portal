---
name: workspace-dev
description: Prepara y levanta el entorno de desarrollo de un worktree aislado (Docker Compose, puertos y .env propios, migraciones, sembrado y tests) tanto si el worktree lo creo Orca como si se creo a mano desde terminal. Usar cuando el usuario pida levantar el entorno dev, iniciar un workspace o preparar un worktree para ejecutar la aplicacion y los tests.
disable-model-invocation: true
---

# Skill: Workspace Dev

## Objetivo

Que cada worktree tenga su propio entorno y no pise a los demas:

1. `.env` propio, copiado del checkout principal sin leerlo ni mostrarlo (lo genera `./bin/orca-setup`).
2. `COMPOSE_PROJECT_NAME`, `GATEWAY_PORT`, `POSTGRES_PORT`, `REDIS_PORT` y `ALLOWED_ORIGINS` propios dentro de ese `.env`.
3. Contenedores, red y volumenes con nombre propio (`docker-compose.dev.yml` interpola `COMPOSE_PROJECT_NAME`).
4. Base de datos propia: el PostgreSQL del stack del worktree.

Vale para los dos modos de trabajo: worktree creado por Orca, o creado a mano con `branch-workspace` (modo terminal). En ambos el estado final es identico.

## Reglas (CLAUDE.md)

- Nunca imprimir ni copiar `.env`, claves RSA (`backend/keys/`) ni tokens (regla 9). Para comprobar una clave, `grep -c '^CLAVE=' .env` (solo cuenta) o leer unicamente `GATEWAY_PORT` con `grep -m1 '^GATEWAY_PORT=' .env`.
- Docker: siempre `docker compose -f docker-compose.dev.yml ...`. Todo montaje de volumen lleva sufijo `:z` (SELinux, Podman rootless). En esta maquina `docker` puede ser un enlace a `podman`.
- Esta skill solo arranca el entorno por orden del usuario. Despues no reiniciar ni reconstruir contenedores por cambios de codigo (hay recarga en caliente por los montajes `./backend` y `./frontend`); reconstruir solo si cambian `requirements.txt` o `package.json` y el usuario lo ordena.
- `./scripts/sync_db.sh` nunca se lanza por iniciativa propia.
- Prohibido commit, push y PR por iniciativa propia (regla 3). Cero emojis, todo en espanol. Ficheros con Edit y Write (regla 7).

---

## Fase 1: Identificar el worktree

Ejecutar desde la raiz del worktree:

```bash
git branch --show-current
git worktree list
MAIN_REPO_ROOT=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
pwd
```

Los scripts `./bin/*` calculan su raiz a partir de su propia ruta, asi que actuan siempre sobre el worktree desde el que se invocan.

## Fase 2: `.env` del worktree

```bash
test -f .env && echo "existe" || echo "no existe"
grep -c '^COMPOSE_PROJECT_NAME=' .env
```

- **`.env` existe y el conteo es 1**: el worktree ya esta preparado (Orca ejecuto `scripts.setup` o se llamo a `orca-setup` a mano). Reutilizarlo: los contenedores existentes dependen de esos puertos.
- **No existe `.env`, o el conteo es 0** (es una copia del principal y chocaria con su proyecto y puertos): generarlo con el mismo script que Orca, que fija proyecto Compose y puertos propios deterministas por ruta, saltando los ocupados:

```bash
ORCA_ROOT_PATH="$MAIN_REPO_ROOT" ORCA_WORKTREE_PATH="$PWD" ./bin/orca-setup
```

Si el principal no tiene `.env`, el script parte de `.env.example`: avisar al usuario de que hay que rellenar secretos a mano (no inventarlos).

Comprobar que las variables se resuelven por worktree y no con los valores por defecto (`ski_dev`, `8080`, `5432`):

```bash
docker compose -f docker-compose.dev.yml config | grep -E "container_name|published|^name:"
```

Si salen los valores por defecto, parar y avisar: el `.env` no es el del worktree.

## Fase 3: Dependencias y claves

- Frontend: `frontend/node_modules` se comparte con el principal (`worktree.sharedDirectories` de `orca.yaml`; `branch-workspace` lo enlaza en modo terminal). Si falta y se necesita fuera de Docker, `cd frontend && npm ci` solo por orden del usuario.
- `backend/keys/` (claves RSA) esta ignorada por git y NO viaja con el worktree. Comprobar con `ls backend/keys` que existen; si faltan, pedir al usuario que las copie desde el checkout principal o las genere. No mostrar su contenido.

## Fase 4: Contenedores

Comprobar primero que no hay stack previo de este worktree y que los puertos estan libres:

```bash
docker ps --format '{{.Names}} | {{.Status}} | {{.Ports}}'
```

Primer arranque (por orden del usuario):

```bash
./bin/dev && ./bin/migrate && ./bin/seed
```

`./bin/dev` hace `up -d --build`. Si `podman-compose` se queda bloqueado tras crear `backend` sin crear `frontend` ni `gateway`, no diagnosticar ni reiniciar: lanzar con limite de tiempo (`timeout 180 ./bin/dev`), verificar con `docker ps`, informar de los contenedores que faltan y proponer un segundo `./bin/dev`, que solo crea los que no existen.

`./bin/migrate` y `./bin/seed` usan `docker compose run --rm backend`. El sembrado crea administrador y empresa si `.env` define `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` (comprobar con `grep -c`, sin imprimir valores).

Verificacion de salud, solo lectura:

```bash
./bin/logs --tail 60 backend 2>&1 | grep -Ei "startup complete|uvicorn running|password authentication|error"
```

Si aparece `password authentication failed` con el `.env` correcto, la causa habitual es un volumen de PostgreSQL reutilizado de una ejecucion anterior con otra contrasena. No borrar volumenes ni cambiar credenciales sin que el usuario lo ordene: es destructivo (pierde los datos de desarrollo del worktree).

Servicios: `postgres` (PostgreSQL 16), `redis` (7), `backend` (FastAPI con recarga), `frontend` (Next.js) y `gateway` (Nginx: frontend en `/`, backend en `/api/`).

Parar sin borrar datos: `./bin/stop`. Borrar volumenes (`down -v`) solo lo hace `workspace-clean` o el usuario.

## Fase 5: Tests y comprobaciones

Backend:

```bash
ruff check backend/
cd backend && pytest tests/
```

Frontend, desde `frontend/`:

```bash
npm run lint
npx tsc --noEmit
npm test
npm run build
```

Si el backend necesita la base de datos del stack para sus tests, ejecutarlos dentro del contenedor del worktree (`docker compose -f docker-compose.dev.yml exec backend pytest tests/`) para que usen el PostgreSQL de este worktree y no el de otro. Citar siempre el resultado real; si algo no se pudo ejecutar, decirlo.

## Fase 6: Informe

```markdown
### Entorno de Desarrollo Iniciado

- Worktree / Rama: `<ruta>` / `<rama>`
- Proyecto Compose: `<COMPOSE_PROJECT_NAME>`
- Gateway: http://localhost:<GATEWAY_PORT> (API docs en /api/docs)
- PostgreSQL (host): `localhost:<POSTGRES_PORT>`, Redis: `localhost:<REDIS_PORT>`
- Contenedores: <estado de `docker ps`>
- Migraciones y sembrado: <hechos / pendientes>
```
