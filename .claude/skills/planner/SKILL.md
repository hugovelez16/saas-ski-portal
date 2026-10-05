---
name: planner
description: Diseno tecnico, descomposicion de requisitos funcionales, definicion de contratos de API REST/Pydantic y planificacion TDD paso a paso. Usar al analizar requerimientos, disenar interfaces o elaborar planes de implementacion.
---

# Checklists complementarios de planificacion

El rol completo lo define el agente `planner` (`.claude/agents/planner.md`). Esta skill solo aporta una plantilla de plan; no invoca a otros agentes (el encadenado lo hace la sesion principal).

## Reglas

- Cumplir las reglas de `CLAUDE.md`: sin emojis, ramas y commits en espanol, sin commits, pushes ni PRs por iniciativa propia.
- Comprobar la rama activa antes de proponer cambios (`git branch --show-current`).
- Los planes se guardan en `docs/superpowers/plans/` con casillas `- [ ]`; las especificaciones de partida estan en `docs/superpowers/specs/`.

## Plantilla de plan

1. **Componentes afectados**: backend, frontend, gateway, base de datos o CI/CD.
2. **Contratos**: modelos y migracion Alembic, esquemas Pydantic v2, endpoints (ruta, metodo, codigos de estado), tipos TypeScript.
3. **Pasos TDD** (cada uno pequeno y verificable): test que falla, implementacion minima, refactor.
4. **Verificacion** por paso, con comandos exactos: `ruff check backend/`, `cd backend && pytest tests/`, y desde `frontend/` `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build`.
5. **Version**: indicar si el cambio requiere incremento SemVer (`package.json`, `frontend/package.json`, `CHANGELOG.md`).
6. **Dudas abiertas**: devolverlas a quien invoco en lugar de asumirlas.

## Skills de apoyo

- `api-design`: patrones REST, nombres y codigos HTTP.
- `tdd-workflow`: flujo dirigido por pruebas.
- `writing-plans`: metodologia de planes tecnicos.
