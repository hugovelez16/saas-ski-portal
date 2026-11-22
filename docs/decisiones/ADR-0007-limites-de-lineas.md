# ADR-0007: Limites de lineas

Estado: Aceptada (2026-11-22). Pendiente de implementar: el test de CI y la
lista de excepciones no existen todavia.

## Contexto

Hay ficheros de 1553 (`backend/crud.py`), 686 (`backend/schemas.py`) y 685
(`backend/routers/auth.py`) lineas (medido el 2026-11-22), y paginas de
frontend de 552 a 727. Un
fichero largo obliga al agente a leerlo entero para tocar una parte y mezcla
responsabilidades. Un limite solo documentado no se cumple.

## Decision

- Maximo 300 lineas por fichero y 120 por caso de uso (P15).
- Un test en CI mide los ficheros del backend (`backend/src/` y routers) y
  falla si alguno supera el limite que le toca.
- Los ficheros que hoy ya lo superan entran en una lista de excepciones
  versionada, con su numero de lineas actual como techo. La lista solo puede
  encoger: el test falla si un fichero de la lista crece o si se anade uno
  nuevo.
- Al migrar un contexto (ADR-0008) sus ficheros salen de la lista al
  partirse por debajo del limite.
- Alcance inicial: backend. Las paginas de frontend quedan fuera hasta que una
  issue propia fije su limite.

## Consecuencias

- El tamano deja de ser una opinion de revision: lo decide CI.
- Un cambio que hace crecer una excepcion obliga a partir el fichero en el
  mismo PR.
- Pendiente de implementar: el test, la lista inicial de excepciones (generada
  con `wc -l` el dia de la issue) y su mencion en `CLAUDE.md`. Es una issue de
  seguimiento aparte.
- Riesgo: un limite por lineas puede fomentar partir por partir. Se acepta; la
  estructura de ADR-0006 da el criterio de corte (un caso de uso, un fichero).
