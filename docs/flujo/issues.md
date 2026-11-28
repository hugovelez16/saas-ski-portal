# Issues y Project

Toda tarea o idea vive como issue en `hugovelez16/saas-ski-portal`. Nada se
queda apuntado fuera (ni en documentos sueltos ni en worktrees sin commit).

## Plantillas (`.github/ISSUE_TEMPLATE/`)

| Plantilla | Uso |
|---|---|
| `tarea-agente.yml` | Trabajo que puede hacer un agente. Campos obligatorios: Objetivo, Contexto a leer, Reglas afectadas, Criterios de aceptacion, Fuera de alcance y Ficheros probables |
| `bug.yml` | Error: pasos, que se esperaba, que se obtuvo y entorno (local, dev o prod, con version) |
| `idea.yml` | Idea sin refinar: problema, propuesta y prioridad sugerida. Pasa por triaje antes de ir a un agente |

## Labels

| Familia | Valores |
|---|---|
| `tipo/*` | `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`, `ci` |
| `area/*` | `backend`, `frontend`, `infra`, `dominio`, `flujo`, `legal`, `diseno` |
| `prioridad/*` | `alta`, `media`, `baja` |
| `modelo/*` | `opus` |
| otras | `bloqueada`, `migracion` |

- Sin label `modelo/*`, `/issue-start` lanza el agente con Sonnet. Pon
  `modelo/opus` solo en issues que exigen criterio: dominio, auth, aislamiento
  multiempresa o arquitectura con decisiones abiertas.
- `migracion`: la issue incluye una migracion Alembic. El PR necesita
  `database-reviewer` y, si borra o altera columnas, el paso previo de
  despliegue (backup y script de reparacion).

## Project "saas-ski-portal"

El campo `Estado` tiene estos valores:

| Estado | Significa | Quien mueve la issue aqui |
|---|---|---|
| Backlog | Apuntada, sin refinar | `/issue-create` |
| Listo para agente | Cumple el criterio de abajo | `/issue-triage` |
| En curso | Tiene worktree y agente | `/issue-start` |
| En revision | PR abierto | `/issue-work` |
| Hecho | PR fusionado | `/issue-work` despues del merge; si no, a mano |

Para cambiar el estado: `scripts/project-estado.sh <n> "<Estado>"`. Necesita el
scope `project` en el token de `gh` (`gh auth refresh -s project`).

Usa siempre el campo `Estado`. El campo `Status` que GitHub crea por defecto
se ignora. La vista Board del Project se agrupa por `Estado`.

## Cuando una issue esta lista para un agente

Tiene que cumplir las cuatro condiciones:

1. "Contexto a leer" tiene rutas exactas, y la seccion cuando el fichero es
   largo.
2. "Reglas afectadas" tiene IDs (`R-EMP-04`) o la seccion del documento de
   dominio (`docs/dominio/`), o "ninguna (solo docs)".
3. Los criterios de aceptacion se pueden verificar con un comando o un test.
4. "Fuera de alcance" esta relleno.
