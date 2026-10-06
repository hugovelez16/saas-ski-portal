---
name: postgres-patterns
description: Patrones de esquema, indexacion y gestion de sesiones en PostgreSQL 16 con SQLAlchemy 2.0 sincrono para saas-ski-portal.
---

# Patrones de PostgreSQL (postgres-patterns)

Guia de diseno de base de datos para PostgreSQL 16 y SQLAlchemy 2.0 (sesion sincrona, `psycopg2`-style URL `postgresql://`, ver `backend/database.py`).

## 1. Tipos de datos

| Caso de uso | Recomendado | Evitar | Nota |
|---|---|---|---|
| Claves primarias | `UUID(as_uuid=True)` con `default=uuid.uuid4` (convencion actual del proyecto) | Enteros magicos mezclados | Mantener la convencion de `models.py` |
| Importes y horas | `Numeric(10, 2)` | `Float` | Evita errores de redondeo en facturacion |
| Fechas de jornada | `Date` y `Time` | Cadenas | `WorkLog.start_date`, `start_time` |
| Marcas de tiempo | `DateTime` (idealmente `timezone=True` en columnas nuevas) | Cadenas | El codigo actual usa `datetime.utcnow` |
| Configuracion flexible | `JSONB` | `JSON` / `Text` | `tax_config`, `settings`, `rates_config`, `extra_data` |
| Estados y roles | `Enum` (`UserRole`, `CompanyRole`) | Enteros sin descripcion | |

## 2. Indexacion

- Indice B-Tree en columnas de filtro frecuente, sobre todo las claves de multiempresa (`company_id`, `user_id`) y fechas de `work_logs`.
- Compuestos: igualdad primero, rango despues (por ejemplo `(company_id, start_date)`).
- Unicos para identificadores naturales (`users.email`).
- Verificar con `EXPLAIN ANALYZE` en `psql` antes de anadir indices.

## 3. Sesiones y transacciones

- Una sesion por peticion con `Depends(get_db)` (`SessionLocal`, `autocommit=False`); el cierre lo gestiona el generador.
- `commit()` explicito al final de la operacion y `rollback()` ante error; transacciones cortas.
- No mantener la transaccion abierta durante llamadas externas (envio de email, HTTP): hacerlas antes o despues de persistir.
- El engine usa los valores por defecto de SQLAlchemy; si se ajusta el pool, hacerlo en `create_engine` (`pool_size`, `max_overflow`, `pool_pre_ping=True`).
