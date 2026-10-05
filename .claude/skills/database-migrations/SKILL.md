---
name: database-migrations
description: Protocolo de migraciones seguras y reversibles con Alembic y SQLAlchemy sobre PostgreSQL 16 en saas-ski-portal.
---

# Migraciones de Base de Datos (database-migrations)

Procedimiento para generar, validar y aplicar migraciones Alembic. Las migraciones viven en `backend/migrations/versions/` (config en `backend/alembic.ini`, entorno en `backend/migrations/env.py`). Alembic se ejecuta dentro del contenedor backend.

## 1. Principios

1. **Reversibilidad obligatoria**: toda migracion implementa `upgrade()` y `downgrade()` y se comprueba que revierte sin dejar el esquema inconsistente.
2. **Sin bloqueos destructivos**: para columnas `nullable=False` en tablas con datos: anadir como anulable, rellenar valores existentes y despues endurecer.
3. **Desatendida**: debe poder ejecutarse sin intervencion con `alembic upgrade head`.

## 2. Flujo de trabajo

Aplicar migraciones pendientes:

```bash
./bin/migrate
```

Generar una migracion nueva (tras editar `backend/models.py`):

```bash
docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic revision --autogenerate -m "descripcion_concisa"
```

Revisar el archivo generado en `backend/migrations/versions/`: sin borrados accidentales de indices o tablas, y `downgrade()` completo (no `pass`).

Probar reversibilidad:

```bash
docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic upgrade head
docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic downgrade -1
./bin/migrate
```

## 3. Cabezas multiples (heads)

```bash
docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic heads
docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic merge -m "fusionar_ramas_migracion" <revision_1> <revision_2>
```

## 4. Notas del proyecto

- Los datos semilla de modulos (`AppModule`) ya se insertan desde migraciones de datos (por ejemplo `2314c15d1a0f_seed_default_modules.py`); mantener ese patron para catalogos.
- Si el cambio altera el despliegue, recuerda el incremento SemVer exigido en `CLAUDE.md`.
