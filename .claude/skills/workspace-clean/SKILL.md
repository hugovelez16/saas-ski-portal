---
name: workspace-clean
description: Cierra un worktree aislado tras fusionar su PR o al descartarlo, tanto si lo creo Orca como si se creo a mano: audita lo que se perderia, pide confirmacion, apaga y purga sus contenedores y volumenes, elimina el worktree y limpia la rama local. Usar cuando el usuario pida limpiar, cerrar, apagar o eliminar un workspace o worktree.
disable-model-invocation: true
---

# Skill: Workspace Clean

## Objetivo

Cerrar un worktree liberando contenedores, volumenes, puertos y rama local sin perder trabajo. Es destructiva: cada paso irreversible exige confirmacion expresa del usuario en esta ejecucion.

## Reglas (CLAUDE.md)

- Cero emojis y todo en espanol.
- Nunca borrar ramas protegidas (`main`, `develop`) ni el checkout principal.
- Nunca ejecutar con el directorio de trabajo dentro del worktree a borrar: antes salir con `ExitWorktree` (`action: "keep"`) o hacer `cd` a la raiz del checkout principal.
- Prohibido `--force`, `rm -rf` y `git branch -D` salvo orden expresa del usuario despues de ver la auditoria de la Fase 1.
- Prohibido commit, push y PR por iniciativa propia (regla 3). Si la rama tiene trabajo sin integrar, avisar; no guardarlo por cuenta propia.
- Si el worktree lo gestiona Orca, es preferible archivarlo desde Orca: su `scripts.archive` (`./bin/orca-archive`) ya baja el stack y borra volumenes. Esta skill sirve para worktrees creados a mano y para limpiar lo que Orca no haya borrado. No ejecutar ambos sobre el mismo worktree sin comprobar antes que el otro no lo haya hecho ya.

---

## Fase 1: Identificar y auditar (solo lectura)

```bash
MAIN_REPO_ROOT=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
cd "$MAIN_REPO_ROOT"
git worktree list
WT="${MAIN_REPO_ROOT}.worktrees/<nombre>"     # o la ruta que muestre git worktree list (p. ej. la de Orca)
BRANCH=$(git -C "$WT" branch --show-current)
git -C "$WT" status -s
git fetch --prune origin
git -C "$WT" log origin/develop..HEAD --oneline
git branch --merged origin/develop | grep -w "$BRANCH" || echo "rama NO fusionada en develop"
git branch -vv | grep -w "$BRANCH"
```

Usar siempre la ruta que devuelve `git worktree list`: si Orca creo el worktree, no estara bajo `$MAIN_REPO_ROOT.worktrees`.

`git fetch --prune` marca como `gone` el upstream de las ramas cuyo remoto ya se borro (GitHub lo hace al fusionar si esta activado). Una rama `gone` con `git log origin/develop..HEAD` vacio esta integrada: ningun commit se perderia. Cuidado con los merges por squash: el contenido esta en `develop` pero los commits no, y `git branch --merged` no los detecta. En ese caso mostrar la PR fusionada como prueba.

Presentar al usuario:
- cambios sin commitear (se perderian al borrar el worktree);
- commits que no estan en `develop` (se perderian al borrar la rama local si no hay copia remota);
- si la rama figura fusionada en `develop`;
- que se va a destruir: contenedores y volumenes del proyecto Compose del worktree (incluida su base de datos), el directorio del worktree y la rama local.

Pedir confirmacion expresa ("Procedo con el cierre de <nombre>?"). Si hay cambios o commits sin integrar, informar de que hay que guardarlos primero (el usuario decide cuando usar `/smart-commit` y `/smart-push`), o descartar solo si lo dice con claridad.

## Fase 2: Apagar y purgar contenedores

Solo tras la confirmacion de la Fase 1. El `.env` del worktree fija el proyecto Compose, asi que basta ejecutar desde su raiz:

```bash
cd "$WT"
docker compose -f docker-compose.dev.yml down -v --remove-orphans
cd "$MAIN_REPO_ROOT"
```

Es lo mismo que hace `./bin/orca-archive`. Comprobar con `docker ps -a` que no quedan contenedores del proyecto del worktree (`COMPOSE_PROJECT_NAME` empieza por `ski_`).

Si el worktree no tiene `docker-compose.dev.yml` o `.env`, omitir este paso. Sin `.env` propio, Compose usaria el proyecto por defecto (`ski_dev`) y podria tocar el stack del checkout principal: en ese caso no ejecutar nada y avisar.

## Fase 3: Eliminar el worktree

```bash
git worktree remove "$WT"
git worktree prune
```

- No usar `--force` por defecto. Los ficheros ignorados (`.env`, `node_modules`, symlinks) no bloquean el borrado; los cambios sin commitear si.
- El enlace simbolico `frontend/node_modules` (compartido con el principal) se borra como enlace; no toca el directorio original. Comprobar con `ls -ld "$WT/frontend/node_modules"` antes si hay dudas, y nunca borrar con `rm -rf` sobre esa ruta.
- Si falla por cambios sin commitear: mostrarlos y repetir con `--force` solo si el usuario lo ordena expresamente.
- Si falla por permisos (Podman rootless crea ficheros con otro uid): `podman unshare rm -rf "<ruta-del-fichero-o-carpeta>"` y repetir; solo tras la confirmacion de la Fase 1.

## Fase 4: Rama local

Solo con aprobacion del usuario.

- Rama fusionada en `origin/develop`: `git branch -d "$BRANCH"`.
- `git branch -d` compara con el upstream y con el `develop` local, no con `origin/develop`: si el upstream esta `gone` o el `develop` local esta atrasado, falla con "not fully merged" aunque la rama este integrada. No saltar a `-D` por inercia. Primero demostrar la integracion (`git log origin/develop..<rama>` vacio, la rama en `git branch --merged origin/develop`, o la PR fusionada) y mostrarsela al usuario; con esa prueba y su confirmacion, `git branch -D "$BRANCH"` es seguro. Para evitar `-D`, actualizar antes `develop` en el checkout principal con `git pull --ff-only`.
- Rama no fusionada: mostrar de nuevo los commits que se perderian y usar `git branch -D "$BRANCH"` unicamente si el usuario lo ordena.
- Rama remota: normalmente la elimina GitHub al fusionar; limpiar referencias con `git fetch --prune`. No borrar ramas remotas sin orden.

## Fase 5: Resumen

```markdown
### Workspace Cerrado

- Worktree: `<nombre>` eliminado y registrado con `git worktree prune`
- Contenedores y volumenes: detenidos y eliminados (proyecto `<COMPOSE_PROJECT_NAME>`)
- Puertos liberados: <GATEWAY_PORT>, <POSTGRES_PORT>, <REDIS_PORT>
- Rama local: `<rama>` eliminada / conservada
```
