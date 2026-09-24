---
name: database-migrations
description: Protocolo de migraciones seguras y reversibles con Alembic async y SQLAlchemy en poc-portal.
---

# Migraciones de Base de Datos (database-migrations)

Esta skill define el procedimiento para generar, validar y aplicar migraciones de base de datos seguras con Alembic sobre PostgreSQL 16.

## 1. Principios de Migracion

1. **Reversibilidad Obligatoria**:
   - Toda migracion debe implementar tanto la funcion `upgrade()` como la funcion `downgrade()`.
   - Una migracion no se considera valida hasta que se compruebe que puede revertirse sin dejar el esquema en estado inconsistente.

2. **Cero Bloqueos Destructivos**:
   - Para anadir columnas no nulas (`nullable=False`) en tablas existentes:
     1. Anadir la columna como anulable (`nullable=True`).
     2. Poblar los valores por defecto en los registros existentes.
     3. Modificar la columna para requerir `nullable=False`.

3. **Autonomia por Entorno**:
   - Las migraciones deben poder ejecutarse de forma desatendida en el despliegue del contenedor backend o en el pipeline de CI/CD.

## 2. Flujo de Trabajo con Alembic

1. **Generacion de una Nueva Migracion**:
   ```bash
   cd /home/usuario/00_datos/poc-portal/backend
   .venv/bin/alembic revision --autogenerate -m "descripcion_concisa_en_espanol"
   ```

2. **Inspeccion Manual del Archivo Generado**:
   - Ubicado en `backend/alembic/versions/<revision_id>_<descripcion>.py`.
   - Verificar que no se hayan generado eliminaciones accidentales de indices o tablas.
   - Completar la funcion `downgrade()` si contiene operaciones `pass` o no reversibles.

3. **Ciclo de Prueba de Reversibilidad**:
   ```bash
   # Aplicar la migracion
   .venv/bin/alembic upgrade head

   # Probar la reversion
   .venv/bin/alembic downgrade -1

   # Reaplicar hasta la cabeza
   .venv/bin/alembic upgrade head
   ```

## 3. Resolucion de Divergencias de Cabeza (Heads)

Si multiples desarrollos generan cabezas paralelas (`multiple heads`):
```bash
# Identificar cabezas conflictivas
.venv/bin/alembic heads

# Fusionar cabezas en una nueva revision de merge
.venv/bin/alembic merge -m "fusionar_ramas_migracion" <revision_1> <revision_2>
```
