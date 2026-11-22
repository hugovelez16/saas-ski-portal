# ADR-0008: Convivencia de API v1 y v2

Estado: Aceptada (2026-11-22). En curso: hoy v2 solo cubre el area empresa y
los endpoints de empresa existen tambien en v1.

## Contexto

La API v2 (`/api/v2/`, `backend/routers/v2/`, `backend/src/`) nacio solo para el
area empresa (X1, X3, Q3 de la tabla 4.1 del plan de empresa, historico) y
sustituia a "`crud.py` no se divide". Con la migracion por contextos (O4) hay
que fijar como conviven las dos versiones para que v1 no se quede para siempre.

## Decision

- `/api/v2/` usa `snake_case` (O4).
- Cada contexto migrado a v2 borra su v1 en la misma serie de PR, incluidos su
  parte de `crud.py` y `schemas.py` (P13). No se mantiene v1 hasta migrar todo.
- Ningun endpoint nuevo nace en v1.
- El frontend migra endpoint a endpoint cuando v2 tiene paridad probada, y el
  PR que cierra el contexto retira el v1 correspondiente (patron de PR-16 a
  PR-21 del plan de empresa).
- Orden de contextos: Turnos, luego Usuarios y Membresias, luego Modulos y
  billing (O4).
- v1 y v2 viven en la misma imagen y detras del mismo gateway (`/api/` sirve
  las dos).
- Python se mantiene como lenguaje del backend (X5 del plan de empresa).

Estructura interna de cada contexto: ADR-0006.

## Consecuencias

- La deuda de v1 tiene fecha de fin por contexto, no por voluntad.
- Cada serie de PR de un contexto incluye backend, frontend y borrado de v1; un
  contexto a medias no se deja entre releases largas.
- Pendiente de implementar: Turnos, Usuarios y Membresias, y Modulos y billing
  siguen en v1. La API de empresa (v2) todavia convive con su v1 hasta que el
  frontend deje de usarla.
