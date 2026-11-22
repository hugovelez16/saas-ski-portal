# ADR-0010: Migraciones con paso previo de despliegue

Estado: Aceptada (2026-11-22). Procedimiento vigente; el detalle operativo
sigue en las secciones 9 y 10 de
[../empresa/plan-implementacion-empresa.md](../empresa/plan-implementacion-empresa.md).

## Contexto

Algunas migraciones chocan con datos reales de produccion (nombres vacios,
turnos sin empresa, impuestos fuera de rango). Corregir datos dentro de la
migracion los esconde y no se puede revisar. Ademas, en produccion el servicio
`migrate` corre antes que `backend`, pero el contenedor de la release anterior
sigue sirviendo mientras tanto (`docker-compose.prod.yml`).

## Decision

- Antes de una migracion con riesgo de datos hay un script de reparacion
  idempotente en `backend/scripts/`, con `--dry-run` por defecto y `--apply`
  explicito. Es transaccional (un solo commit) y devuelve 0 si esta limpio, 2 si
  quedan decisiones manuales y 1 si falla.
- La migracion no repara: comprueba y aborta con `RuntimeError` si quedan datos
  sin arreglar, indicando cuantos y que script ejecutar. El DDL transaccional
  de PostgreSQL deja la BD intacta.
- Los ficheros de backup del script van fuera del repo y sin secretos; el script
  se niega a escribir dentro de el.
- Procedimiento de despliegue de un PR con migracion: backup de la BD, script,
  ensayo con copia anonimizada y despliegue. Todo comando de produccion lo
  ejecuta el usuario, nunca un agente.
- Ventana aceptada: durante los segundos en que corre `migrate`, el contenedor
  anterior sirve con el esquema ya cambiado y alguna peticion puede fallar. Por
  eso toda migracion debe ser compatible con el codigo anterior (anadir antes de
  quitar). Las que no lo pueden ser se despliegan fuera de horas de uso.
- Un PR con paso previo no se fusiona solo: `issue-work` no hace merge y deja la
  decision al usuario (`CLAUDE.md`, regla 3).

## Consecuencias

- La correccion de datos es visible, revisable y reversible.
- Cada migracion de riesgo cuesta un script, sus tests (SQLite, y marcador
  `postgres` para la migracion) y la revision de `database-reviewer`.
- Se acepta una ventana de errores de segundos en lugar de montar releases
  previas o divisiones en dos PR.
- Los ids P-/E7 de la tabla 4.1 que regulan datos concretos (por ejemplo,
  `repair_work_log_company.py`) siguen en el plan como historico.
