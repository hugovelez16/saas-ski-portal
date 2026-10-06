---
name: docker-patterns
description: Patrones de orquestacion con Docker Compose y Podman rootless, healthchecks y contenedores seguros para saas-ski-portal.
---

# Patrones de Contenedores y Docker (docker-patterns)

Esta skill documenta las directivas de diseno, seguridad y ejecucion de contenedores para el stack de saas-ski-portal utilizando Podman y Docker Compose. Para pipelines y despliegue ver el agente `devops`.

## 1. Directivas de Diseno de Contenedores

1. **Construccion Multietapa (Multi-stage Builds)**:
   - **Frontend** (`frontend/Dockerfile`): etapas `deps` (`npm ci --legacy-peer-deps`), `builder` (`npm run build`, con `NEXT_PUBLIC_API_URL` como build-arg) y `runner` (salida `standalone` de Next.js, `node server.js`). En desarrollo se usa el target `deps` con `npm run dev`.
   - **Backend** (`backend/Dockerfile`): imagen unica `python:3.12-slim`; `requirements.txt` se copia antes del codigo para aprovechar la cache de capas.

2. **Ejecucion con Usuarios No Privilegiados**:
   - Nunca ejecutar los procesos de aplicacion como `root` dentro del contenedor (backend: `saas_user`; frontend: `nextjs`).

3. **Optimizacion de Capas y Cache**:
   - Copiar primero los ficheros de dependencias (`package.json`, `package-lock.json`, `requirements.txt`) antes del codigo fuente.

## 2. Orquestacion con Docker Compose / Podman Compose

1. **Healthchecks Reales** (patron de `docker-compose.dev.yml`):
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres}"]
     interval: 5s
     timeout: 3s
     retries: 5
   ```
   Los servicios dependientes usan `condition: service_healthy`:
   ```yaml
   depends_on:
     postgres:
       condition: service_healthy
     redis:
       condition: service_healthy
   ```

2. **Persistencia de Datos y Redes**:
   - Volumen con nombre para Postgres (`postgres_data:/var/lib/postgresql/data:z`).
   - Red `internal_db` con `internal: true` (postgres y redis no salen a Internet) y red `internal_app` para backend, frontend y gateway.

3. **Compatibilidad Podman Rootless / SELinux**:
   - Todo montaje de volumen lleva sufijo `:z` (por ejemplo `./backend:/app:z`, `./gateway/nginx.dev.conf:/etc/nginx/nginx.conf:ro,z`).
   - Asegurar que `~/.config/containers/registries.conf` contenga `unqualified-search-registries = ["docker.io"]`.

4. **Parametrizacion por Worktree**:
   - Con varios worktrees en el mismo host, definir en `.env` `COMPOSE_PROJECT_NAME`, `GATEWAY_PORT`, `POSTGRES_PORT`, `REDIS_PORT` y `ALLOWED_ORIGINS` para evitar colisiones de nombres y puertos.

## 3. Comandos de Administracion Local

```bash
# Iniciar infraestructura en segundo plano (o bin/dev)
docker compose -f docker-compose.dev.yml up -d

# Comprobar estado de salud de todos los servicios
docker compose -f docker-compose.dev.yml ps

# Inspeccionar logs (o bin/logs)
docker compose -f docker-compose.dev.yml logs -f backend
docker compose -f docker-compose.dev.yml logs -f postgres
```
