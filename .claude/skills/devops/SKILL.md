---
name: devops
description: Orquestacion de contenedores con Docker Compose y Podman rootless, configuracion de Nginx como gateway/proxy inverso y pipelines CI/CD (GitHub Actions, GHCR, Komodo). Usar al gestionar despliegues, Dockerfiles, compose y workflows de CI/CD.
---

# Rol: DevOps & Cloud Engineer (devops)

Version de rol para uso como skill. El detalle de stack, Dockerfiles, gateway, pipelines y healthchecks esta en el agente [`devops`](../../agents/devops.md); aqui solo se recogen las reglas de decision y los comandos.

## Directivas Obligatorias

1. Cumplir estrictamente con CLAUDE.md:
   - Prohibido realizar commits, pushes o abrir PRs por iniciativa propia.
   - Nombres de ramas y mensajes de commit en espanol (`feat: ...`, `chore: ...`).
   - Prohibicion total de emojis en Dockerfiles, manifiestos Compose, workflows y scripts Bash.
2. Comprobar la rama activa antes de modificar cualquier configuracion (`git branch --show-current`).
3. Compatibilidad cruzada: manifiestos y scripts deben funcionar igual en Podman rootless (Fedora/RHEL) y Docker estandar; volumenes con sufijo `:z`.
4. Usar siempre `docker compose -f docker-compose.dev.yml` en local (prod: `docker-compose.prod.yml`).

## Reglas de Decision

- **Version SemVer**: todo PR que cambie la aplicacion incrementa `package.json` (raiz), `frontend/package.json` y `CHANGELOG.md`. Los workflows `deploy-dev.yml` y `deploy-prod.yml` leen la version del `package.json` raiz para etiquetar imagenes en GHCR (`dev-vX.Y.Z` / `vX.Y.Z`); sin incremento se pierde trazabilidad y rollback en Komodo.
- **Ramas protegidas**: `main` y `develop` no admiten push directo; cambios via PR tras pasar `ci.yml`.
- **Despliegue**: push a `develop` (dev) o `main` (prod) construye y publica backend, frontend y gateway, y dispara el webhook de Komodo. Los secretos (`KOMODO_WEBHOOK*`, `KOMODO_SECRET*`) nunca se imprimen ni se copian a ficheros versionados.
- **Gateway**: `/` al frontend, `/api/` al backend; configuracion en `gateway/nginx.conf` (prod) y `gateway/nginx.dev.conf` (dev).

## Comandos de Verificacion

```bash
docker compose -f docker-compose.dev.yml config
docker compose -f docker-compose.dev.yml ps
docker compose -f docker-compose.dev.yml logs -f backend gateway
```

## Habilidades y Skills Asociadas

- `docker-patterns`: Patrones de contenedores seguros y rootless.
- `verification-loop`: Auditoria integral y recoleccion de evidencia.
- `daily-sync`: Sincronizacion segura del repositorio.
