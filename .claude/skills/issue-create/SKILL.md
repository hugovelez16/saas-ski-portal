---
name: issue-create
description: Registra una issue en GitHub (hugovelez16/saas-ski-portal) con la plantilla que toque (tarea-agente, bug o idea), despues de buscar duplicados, con labels tipo/area/prioridad, y la anade al Project en Backlog. Usar cuando el usuario pida crear una issue, apuntar algo o dejar una tarea pendiente, o cuando un agente encuentre algo fuera del alcance de su issue.
---

# issue-create

Convierte una peticion o un hallazgo en una issue que otro agente, sin acceso a
esta conversacion, pueda trabajar. La referencia de plantillas, labels y
estados es `docs/flujo/issues.md`.

## Reglas

- Todo en espanol y sin emojis (CLAUDE.md regla 6).
- No inventes. Cada ruta y cada regla citada se ha comprobado. Lo que no se
  sabe va en el cuerpo como "Pregunta abierta", y la issue se queda en Backlog.
- Una issue tiene un objetivo y produce un PR. Si no cabe, dividela. Si
  incluye una migracion Alembic, lleva la label `migracion`.
- **Confirmacion:**
  - En una sesion interactiva, muestra el borrador (titulo, labels y cuerpo) y
    espera el OK.
  - Si te invoca un agente desde `issue-work`, por un hallazgo fuera de su
    alcance, creala directamente en Backlog.

## Flujo

### 1. Duplicados

```bash
gh issue list --repo hugovelez16/saas-ski-portal --state all --search "<palabras clave>" --json number,title,state
```

- Si existe una equivalente abierta, anade la informacion con
  `gh issue comment <n> --body-file <fichero>` y devuelve su numero.
- Si existe cerrada, citala en el cuerpo.

### 2. Plantilla

| Caso | Plantilla | Cuerpo |
|---|---|---|
| Trabajo concreto que puede hacer un agente | `tarea-agente.yml` | Secciones `### Objetivo`, `### Contexto a leer`, `### Reglas afectadas`, `### Criterios de aceptacion`, `### Fuera de alcance`, `### Ficheros probables` |
| Algo roto | `bug.yml` | `### Pasos`, `### Esperado`, `### Obtenido`, `### Entorno` |
| Idea sin refinar o futura | `idea.yml` | `### Problema`, `### Propuesta`, `### Prioridad sugerida` |

En "Contexto a leer" van rutas exactas con seccion, por ejemplo
`docs/dominio/membresia.md`, nunca "docs/". El indice
de documentacion esta en `docs/README.md`.

### 3. Titulo y labels

- Titulo: `<tipo>(<ambito>): <descripcion en espanol>`.
- Labels: un `tipo/*`, al menos un `area/*` y un `prioridad/*`. `modelo/opus`
  solo si exige criterio (dominio, auth, aislamiento multiempresa,
  arquitectura).

### 4. Registro

Escribe el cuerpo en un fichero del scratchpad y crea la issue:

```bash
gh issue create --repo hugovelez16/saas-ski-portal \
  --title "<titulo>" --body-file <fichero> \
  --label "tipo/<x>" --label "area/<y>" --label "prioridad/<z>"
scripts/project-estado.sh <n> "Backlog"
```

### 5. Informe

Devuelve el numero, el titulo y la URL. Si le falta algo para estar "Listo
para agente" (`docs/flujo/issues.md`), enumeralo.
