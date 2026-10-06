---
name: database-reviewer
description: Checklist de revision de base de datos de saas-ski-portal (SQLAlchemy 2.0 sincrono, Alembic, PostgreSQL 16). Usar al disenar esquemas, crear migraciones o revisar el rendimiento de base de datos.
---

# Database Reviewer (checklist)

El detalle del stack y las responsabilidades esta en el agente `database-reviewer` (`.claude/agents/database-reviewer.md`). Esta skill es solo la lista de comprobacion.

## Antes de aprobar un cambio de modelo

- `backend/models.py` y migracion nueva en `backend/migrations/versions/` van juntos, con `downgrade()` completo.
- Columnas nuevas `nullable=False` en tablas con datos: anadir anulable, rellenar, endurecer (ver `database-migrations`).
- Claves foraneas con `ondelete` definido e indice en la columna FK usada en filtros (`company_id`, `user_id`).
- Importes en `Numeric`, configuracion flexible en `JSONB`.
- Consultas en `crud.py`/routers sin N+1 (`selectinload`/`joinedload`) y filtradas por empresa.

## Verificacion

```bash
./bin/migrate
docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic heads
docker compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "\di"
```
