---
name: docker-patterns
description: Patrones de orquestacion con Docker Compose y Podman rootless, healthchecks y contenedores seguros para poc-portal.
---

# Patrones de Contenedores y Docker (docker-patterns)

Esta skill documenta las directivas de diseno, seguridad y ejecucion de contenedores para el stack de POC Portal utilizando Podman y Docker Compose.

## 1. Directivas de Diseno de Contenedores

1. **Construccion Multietapa (Multi-stage Builds)**:
   - **Frontend**: Etapa 1 basada en Node 20 LTS para instalar dependencias y compilar activos estaticos (`npm run build`). Etapa 2 basada en Nginx Alpine para servir unicament los archivos generados en `dist/`.
   - **Backend**: Etapa 1 para compilar wheels o instalar dependencias en entorno virtual. Etapa 2 basada en `python:3.12-slim` copiando unicamente el runtime necesario.

2. **Ejecucion con Usuarios No Privilegiados**:
   - Nunca ejecutar los procesos de aplicacion como `root` dentro del contenedor.
   - Definir usuarios y grupos dedicados en el Dockerfile (`USER appuser`).

3. **Optimizacion de Capas y Cache**:
   - Copiar primero los ficheros de dependencias (`package.json`, `package-lock.json`, `pyproject.toml`) antes del codigo fuente para maximizar la reutilizacion de la cache de capas.

## 2. Orquestacion con Docker Compose / Podman Compose

1. **Healthchecks Reales**:
   - Todo servicio de base de datos debe declarar una sonda de salud valida:
     ```yaml
     healthcheck:
       test: ["CMD-SHELL", "pg_isready -U postgres -d poc_portal"]
       interval: 5s
       timeout: 3s
       retries: 5
     ```
   - Los servicios dependientes deben usar la condicion `condition: service_healthy`:
     ```yaml
     depends_on:
       postgres:
         condition: service_healthy
     ```

2. **Persistencia de Datos**:
   - Utilizar volumenes con nombre para los datos persistentes (`pgdata:/var/lib/postgresql/data`) y evitar rutas relativas del host para motores de base de datos en produccion.

3. **Compatibilidad Podman Rootless**:
   - Asegurar que `~/.config/containers/registries.conf` contenga `unqualified-search-registries = ["docker.io"]`.
   - Las herramientas CLI utilizan los wrappers compatibles en `~/.local/bin/docker` y `~/.local/bin/docker-compose`.

## 3. Comandos de Administracion Local

```bash
# Iniciar infraestructura en segundo plano
docker-compose up -d

# Comprobar estado de salud de todos los servicios
docker-compose ps

# Inspeccionar logs del backend o la base de datos
docker-compose logs -f backend
docker-compose logs -f postgres
```
