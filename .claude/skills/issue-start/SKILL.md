---
name: issue-start
description: Lanza una issue en "Listo para agente" - crea con Orca su worktree y su rama desde origin/develop y arranca un agente Claude con /issue-work <n>. Se ejecuta desde el checkout principal. Usar con "/issue-start <n>".
disable-model-invocation: true
---

# issue-start

Una issue equivale a un worktree, una rama y un agente. Comandos en
`docs/flujo/orca.md`.

## Entrada

`<n>`: numero de la issue.

## Flujo

### 1. Puerta de entrada (solo lectura)

```bash
git -C /home/usuario/00_datos/saas-ski-portal branch --show-current
gh issue view <n> --repo hugovelez16/saas-ski-portal --json number,title,labels,state,body
```

Para si se cumple cualquiera de estas condiciones, e informa sin cambiar
nada:

- El checkout principal no esta en `develop`.
- La issue esta cerrada.
- No esta en "Listo para agente". Compruebalo en el Project con
  `gh project item-list`.
- Tiene la label `bloqueada`.
- Le falta alguna seccion obligatoria de `tarea-agente`.
- Ya hay 2 issues en "En curso" en el Project: informa de cuales son.
- Lleva la label `migracion` y otra issue en "En curso" tambien.

Si la issue comparte "Ficheros probables" (salvo `CHANGELOG.md`) con alguna
en "En curso", avisa en el informe antes de lanzar.

### 2. Nombre de la rama

`<tipo>/<n>-<descripcion>`:

- `<tipo>` sale de la label `tipo/*`.
- `<descripcion>` sale del titulo: en espanol, en minusculas, con guiones, sin
  tildes ni caracteres especiales y con 5 palabras como maximo.
- Ejemplo: `feat/12-reportes-de-soporte`.

Nombre del worktree: `<n>-<descripcion>`.

### 3. Worktree y agente

Modelo: `sonnet` por defecto, `opus` si la issue tiene la label
`modelo/opus`. Esfuerzo siempre `medium`.

```bash
ORCA="${ORCA_CLI_COMMAND:-orca-ide}"
git fetch origin
$ORCA worktree create \
  --repo path:/home/usuario/00_datos/saas-ski-portal \
  --name <n>-<descripcion> --no-parent \
  --base-branch origin/develop --branch <tipo>/<n>-<descripcion> \
  --issue <n> --agent claude --model <sonnet|opus> --effort medium \
  --setup run --prompt "/issue-work <n>" --json
```

- `--setup run` ejecuta `./bin/orca-setup` (ver `docs/flujo/orca.md`).
- Si el comando falla, lee `$ORCA worktree create --help` y corrige los flags.
  No reintentes a ciegas. Si habla de `--retry-launch`, sigue sus
  instrucciones.
- Si queda un directorio en `.orca-preparing/` de un intento fallido, avisa;
  no lo borres sin confirmacion.

### 4. Comprobar que el agente recibio el prompt

`launch.prompt.outcome: "handed-to-terminal"` no garantiza que Claude haya
recibido el prompt, y `launch.outcome.handle` puede apuntar a una terminal ya
terminada.

1. Localiza la terminal viva del worktree (fila con `status` `running`):

   ```bash
   $ORCA terminal list --worktree path:<ruta del JSON> --json
   ```

2. Lee lo que muestra:

   ```bash
   $ORCA terminal read --terminal <handle> --screen --json
   ```

3. Si `/issue-work <n>` aparece, el agente arranco: sigue a "5. Estado".
4. Si no aparece, reenvialo:

   ```bash
   $ORCA terminal send --terminal <handle> --text "/issue-work <n>" \
     --enter --wait-submit 20 --json
   ```

   La respuesta tiene que incluir `turn_started`. Si no, vuelve a leer la
   pantalla. No reenvies a ciegas.
5. Si sigue sin arrancar, no des la issue por lanzada: no ejecutes "5.
   Estado" e informa con el handle y la ultima pantalla leida.

### 5. Estado

```bash
scripts/project-estado.sh <n> "En curso"
gh issue comment <n> --repo hugovelez16/saas-ski-portal \
  --body "En curso. Rama <tipo>/<n>-<descripcion>, worktree <ruta del JSON>."
```

### 6. Informe

Devuelve la rama, la ruta del worktree, el modelo, el handle de la terminal,
el estado del agente (arrancado al primer intento, tras reenviar el prompt o
no arrancado) y los avisos de ficheros compartidos.

## Sin Orca

Si `orca-ide` no esta disponible, usa el bloque "Sin Orca" de
`docs/flujo/orca.md` y di al usuario que abra `claude "/issue-work <n>"` en el
worktree.
