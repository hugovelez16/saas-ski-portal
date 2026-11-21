---
name: issue-triage
description: Revisa el backlog de saas-ski-portal, completa las issues incompletas y propone pasarlas a "Listo para agente". Usar cuando el usuario pregunte que hay pendiente, pida revisar el backlog, hacer triaje o elegir la siguiente issue.
disable-model-invocation: true
---

# issue-triage

Mantiene el backlog util: las issues en "Listo para agente" tienen que estarlo
de verdad. La referencia es `docs/flujo/issues.md`.

## Reglas

- Propones; el usuario decide. Solo cambias el estado o cierras issues con su
  confirmacion, o si lo ha pedido en ese mismo mensaje.
- Si cierras una issue (duplicada, obsoleta o descartada), deja siempre un
  comentario con el motivo.
- No cambies el alcance de una issue sin preguntar.

## Flujo

### 1. Resumen

```bash
gh issue list --repo hugovelez16/saas-ski-portal --state open --limit 200 \
  --json number,title,labels,updatedAt
num=$(gh project list --owner hugovelez16 --format json \
  --jq '.projects[] | select(.title == "saas-ski-portal") | .number')
gh project item-list "$num" --owner hugovelez16 --format json --limit 200
git worktree list
```

Presenta una tabla por `Estado` y, dentro de cada estado, por prioridad:

| # | Titulo | Estado | Prioridad | Areas | Migracion |

Senala:

- issues sin `tipo/*` o sin `prioridad/*`;
- issues en "En curso" sin actividad en 7 dias, o sin worktree;
- worktrees sin issue asociada (trabajo que se perderia);
- issues en "En revision" cuyo PR ya esta cerrado;
- posibles duplicados.

### 2. Triaje

Para cada issue en Backlog que el usuario quiera preparar:

1. Comprueba los 4 criterios de "listo" de `docs/flujo/issues.md`.
2. Si falta informacion que puedes sacar del repo (rutas, secciones de
   dominio, comandos de verificacion), completala con
   `gh issue edit <n> --repo hugovelez16/saas-ski-portal --body-file <fichero>`.
   Respeta las secciones de la plantilla.
3. Si falta una decision del usuario, comenta en la issue con
   `gh issue comment` y apuntalo en la tabla final.
4. Propon el estado de destino. Con el OK del usuario:
   `scripts/project-estado.sh <n> "Listo para agente"`.

### 3. Siguiente trabajo

Si el usuario pregunta que hacer a continuacion:

- Propon issues en "Listo para agente", ordenadas por prioridad.
- Indica cuales se pueden lanzar en paralelo: no comparten ficheros y como
  mucho una lleva migracion.
- Cada una se lanza con `/issue-start <n>`.
