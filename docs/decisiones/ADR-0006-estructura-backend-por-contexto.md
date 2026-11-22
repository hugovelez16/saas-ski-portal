# ADR-0006: Estructura del backend por contexto

Estado: Aceptada (2026-11-22). Parte pendiente de implementar: `backend/src/`
sigue organizado por capas con el contexto dentro de cada una.

## Contexto

Un cambio de turnos obliga a leer `backend/crud.py` (1553 lineas),
`backend/schemas.py` (686) y `backend/routers/work_logs.py` (383): unas 2600
lineas de tres ficheros que mezclan todos los contextos. Un agente de IA
trabaja mejor con un contexto pequeno y acotado. `backend/src/` ya cumple casi
todo; el problema esta fuera de el (medicion de `revision-base.md`, seccion 6,
2026-11-22).

## Decision

Estructura vertical por contexto (P14, O4), en lugar de contexto dentro de cada
capa:

- `backend/src/<contexto>/{domain,application,infrastructure}`. Contextos:
  `company`, `membership`, `work_log`, `access`, `module`, `audit`.
- Un `README.md` por contexto de 60 lineas como maximo: responsabilidad, reglas
  `R-*` que implementa, puertos que expone y consume, endpoints y comando de
  tests. Es lo unico que un agente lee antes de abrir codigo.
- Casos de uso: una clase con un `execute` por fichero, que recibe un comando
  tipado y el actor y lanza excepciones de dominio, nunca `HTTPException`.
- El caso de uso solo conoce interfaces de `domain/ports`; la implementacion
  SQLAlchemy vive en `infrastructure` y se inyecta en el router.
- El router valida la entrada, llama a un caso de uso y traduce excepciones.
  Sin logica en routers. Un test de imports prohibe importar `models`, `crud` o
  `sqlalchemy` desde `backend/routers/v2/`.
- Cada caso de uso declara su `Action` (ADR-0005).
- Orden de migracion: ADR-0008.

## Consecuencias

- Un agente lee el README del contexto y su carpeta, no el backend entero.
- Cada contexto migrado vacia su parte de `crud.py` y `schemas.py`.
- Pendiente de implementar: mover los ficheros actuales de `backend/src/` a
  carpetas por contexto, crear los README y el test de imports. Es una issue de
  seguimiento por contexto, no parte de este ADR.
- Coste: durante la migracion conviven dos formas de organizar el codigo
  (contextos ya migrados y `crud.py`). El orden de ADR-0008 lo acota.
- Los limites de tamano estan en ADR-0007.
