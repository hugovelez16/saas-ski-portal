---
name: branch-workspace
description: Crea y gestiona worktrees de Git aislados fuera del repositorio, con una rama nueva por tarea, compatibles con Orca y con el uso de Claude Code desde terminal o VS Code. Usar cuando se inicie una funcionalidad, correccion o tarea nueva, o cuando el usuario pida crear un workspace, un worktree o aislar una rama.
---

# Skill: Branch Workspace

## Objetivo

Una rama, un worktree, una tarea. Cada worktree es un directorio independiente con su propia rama: varias tareas (o agentes) avanzan en paralelo sin `git checkout` cruzados. El entorno de ejecucion (Docker, puertos, `.env`) lo prepara `workspace-dev`; el cierre lo hace `workspace-clean`.

El proyecto se trabaja desde dos entornos y esta skill debe valer en ambos:

- **Modo Orca**: Orca crea el worktree y ejecuta `scripts.setup` (`./bin/orca-setup`) por su cuenta.
- **Modo terminal** (Claude Code en terminal o VS Code, sin Orca): el worktree se crea a mano con `git worktree add` y se llama a `./bin/orca-setup` con las mismas variables que usa Orca.

El resultado es el mismo en los dos: un worktree con `.env` propio, puertos propios y `COMPOSE_PROJECT_NAME` propio.

---

## Convencion de ubicacion

Los worktrees viven FUERA del repositorio, en un directorio hermano con el mismo prefijo:

```
<padre>/saas-ski-portal/                  checkout principal (develop)
<padre>/saas-ski-portal.worktrees/<nombre>   un directorio por tarea
```

Motivos: nada que ignorar en git, ruff, pytest, tsc y eslint no recorren checkouts anidados, y el contexto de build de Docker no incluye otros worktrees. Es relativa al checkout principal, asi que vale igual en cualquier equipo.

```bash
MAIN_REPO_ROOT=$(git worktree list --porcelain | sed -n '1s/^worktree //p')
WT_BASE="${MAIN_REPO_ROOT}.worktrees"
```

`<nombre>` es la descripcion de la rama sin el tipo (`feature/reportes-diarios` da `reportes-diarios`). En Orca, apuntar su directorio de workspaces a `$WT_BASE` (ajuste de Orca) para que ambos modos compartan ubicacion; si Orca usa otra ruta, funciona igual, solo cambia donde estan los directorios.

---

## Reglas (CLAUDE.md)

1. Rama `<tipo>/<descripcion-en-espanol>` en kebab-case (`feature`, `fix`, `refactor`, `chore`, `test`, `docs`). Ejemplo: `feature/reportes-diarios`.
2. `main` y `develop` estan protegidas: nunca trabajar ni commitear en ellas. Los cambios llegan por Pull Request.
3. Prohibido `git commit`, `git push` y crear PR por iniciativa propia (regla 3). Esta skill no hace ninguno.
4. Cero emojis. Ficheros nuevos o editados solo con Edit y Write (regla 7).
5. Un worktree, una tarea, un PR. Dos worktrees no deben tocar los mismos ficheros.
6. El incremento de version (regla 8) se hace al final, sobre `develop` actualizado, justo antes del PR, para no generar conflictos en `package.json` y `CHANGELOG.md`.

---

## Flujo

### Fase 1: Diagnostico (solo lectura)

```bash
git branch --show-current
git worktree list
git status -s
git fetch origin develop
```

Comprobar que no hay merge ni rebase a medias, que la rama y el directorio no existen ya, y detectar el modo: si existe la variable `ORCA_WORKTREE_PATH` o el usuario dice que usa Orca, modo Orca; en otro caso, modo terminal.

### Fase 2A: Modo Orca

Orca crea el worktree desde su interfaz (`+` junto al repo, partir de `develop`, nombrar la rama segun la regla 1). Esta skill solo guia: indicar al usuario los pasos y, cuando el worktree exista, continuar en la Fase 3. No ejecutar `git worktree add` a mano en este modo.

### Fase 2B: Modo terminal

Siempre desde `origin/develop`:

```bash
git worktree add --no-track -b <tipo>/<descripcion> "$WT_BASE/<nombre>" origin/develop
```

`--no-track` es obligatorio: sin el, la rama nueva queda con upstream `origin/develop` y un `git push` sin argumentos apuntaria a una rama protegida. El upstream correcto se fija en el primer push, que solo se hace cuando el usuario lo ordena.

Si la rama ya existe: `git worktree add "$WT_BASE/<nombre>" <rama-existente>`.

Preparar el `.env` del worktree con el mismo script que Orca (copia el `.env` del principal sin leerlo ni mostrarlo, y fija proyecto Compose y puertos propios):

```bash
cd "$WT_BASE/<nombre>"
ORCA_ROOT_PATH="$MAIN_REPO_ROOT" ORCA_WORKTREE_PATH="$PWD" ./bin/orca-setup
```

Sin `ORCA_ROOT_PATH` el script toma el propio worktree como raiz y falla al no encontrar `.env`: pasarlo siempre.

Reflejar `worktree.sharedDirectories` de `orca.yaml` (Orca lo hace solo): compartir `frontend/node_modules` con el principal si existe y el worktree no tiene el suyo.

```bash
[ -d "$MAIN_REPO_ROOT/frontend/node_modules" ] && [ ! -e frontend/node_modules ] && ln -s "$MAIN_REPO_ROOT/frontend/node_modules" frontend/node_modules
```

### Fase 3: Entrar y preparar

1. Entrar con la herramienta `EnterWorktree` pasando `path` con la ruta absoluta del worktree (debe figurar en `git worktree list`). Si la herramienta aparece como diferida, cargar antes su esquema con `ToolSearch` (`select:EnterWorktree`). `ExitWorktree` con `action: "keep"` al terminar; el borrado lo hace `workspace-clean`. Si `ExitWorktree` devuelve "no-op", no hace falta salir.
2. En VS Code, abrir el worktree como carpeta o ventana aparte para que la terminal de Claude parta ya dentro de el.
3. Levantar el entorno con `workspace-dev`.
4. Confirmar al usuario ruta, rama y puertos asignados.

### Fase 3 bis: Entrar en un worktree existente y sincronizarlo con develop

No crear otro: entrar con `EnterWorktree` y diagnosticar antes de tocar nada:

```bash
git branch --show-current
git status -s
git fetch origin develop
git rev-list --left-right --count origin/develop...HEAD
```

La salida es `<detras> <delante>`. Si esta detras, el usuario decide como traer `develop`; por defecto **merge** (`git merge origin/develop`), porque el historial usa merges y la rama suele estar ya en el remoto (un rebase obligaria a `push --force`).

1. **Ficheros locales que develop ya incorpora**: comparar antes (`git diff origin/develop -- <ruta>`; para ficheros sin seguimiento, `git show origin/develop:<ruta>`). Si son identicos, son duplicados y bloquearian el merge.
2. **Guardar con stash etiquetado**, nunca `git stash` pelado (la pila se comparte entre worktrees): `git stash push -u -m "<etiqueta-unica>"`, capturar el SHA con `git stash list --format='%H %gs'` y recuperar con `git stash apply <sha>`, no `pop`. Los ficheros sin seguimiento viven en el tercer padre: `git checkout <sha>^3 -- <fichero>` y despues `git restore --staged <fichero>`. Borrar el stash solo con permiso.
3. **Fusionar** con `git merge origin/develop`. Conflictos a mano, sin `--ours` ni `--theirs` a ciegas. El merge queda **sin commitear** hasta que el usuario lo ordene (regla 3).
4. **Colision de version (regla 8)**: si `develop` ya usa o supero la version de la rama, subir la de la rama por encima en `package.json` (raiz), `frontend/package.json` y `CHANGELOG.md`. En el changelog, la seccion de la rama va la primera y las de `develop` conservan su orden debajo.
5. **Verificar**: `cd backend && pytest tests/`, `ruff check backend/` y, desde `frontend/`, `npx tsc --noEmit`, `npm run lint` y `npm test`. Si cambio `requirements.txt` o `package-lock.json`, el entorno Docker necesita reconstruirse (`workspace-dev`, solo si el usuario lo ordena).

### Fase 4: Trabajo en paralelo

- Cada agente trabaja con rutas y directorio de trabajo dentro de su worktree y no toca otros. Al delegar a subagentes, indicar siempre la ruta absoluta del worktree.
- Tareas independientes y de larga vida: un worktree por tarea (esta skill u Orca).
- Subtareas cortas dentro de una misma tarea: herramienta `Agent` con `isolation: "worktree"`. Esos worktrees temporales los crea Claude Code dentro de `.claude/worktrees/`, no siguen esta convencion y se descartan al terminar.
- Un agente extra sobre el mismo codigo sin rama propia: en modo Orca, pestana nueva con `orca terminal create --worktree active --command claude`; en modo terminal, otra terminal de VS Code abierta en la misma carpeta.
- Dos agentes nunca editan el mismo fichero a la vez; si hay solape, serializar o dividir por ficheros.

### Fase 5: Cierre

Cuando la rama este fusionada por PR, o la tarea se descarte, usar `workspace-clean`. No borrar worktrees a mano.

---

## Referencia rapida

| Accion | Comando |
| :--- | :--- |
| Listar worktrees | `git worktree list` |
| Base de worktrees | `"$(git worktree list --porcelain \| sed -n '1s/^worktree //p').worktrees"` |
| Crear con rama nueva | `git worktree add --no-track -b <rama> "$WT_BASE/<nombre>" origin/develop` |
| Crear con rama existente | `git worktree add "$WT_BASE/<nombre>" <rama-existente>` |
| Preparar `.env` y puertos | `ORCA_ROOT_PATH="$MAIN_REPO_ROOT" ORCA_WORKTREE_PATH="$PWD" ./bin/orca-setup` |
| Purgar referencias huerfanas | `git worktree prune` |
