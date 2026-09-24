---
name: postgres-patterns
description: Patrones de optimizacion de consultas, diseno de esquemas relacionales, indexacion y gestion de concurrencia en PostgreSQL 16 para poc-portal.
---

# Patrones de PostgreSQL (postgres-patterns)

Esta skill proporciona la guia tecnica y patrones de diseno de base de datos para PostgreSQL 16 y SQLAlchemy 2.0 asincrono dentro del proyecto POC Portal.

## 1. Guia de Tipos de Datos Recomendados

| Caso de Uso | Tipo Recomendado | Tipo a Evitar | Justificacion |
|---|---|---|---|
| Claves Primarias | `Integer` / `BigInteger` (Identity) | `UUID` aleatorio v4 sin ordenar | Menor tamano de indice, mejor localidad de cache en B-Tree |
| Texto Corto / Slugs | `String(length)` con constraint | `Text` sin limite o `Char(n)` con padding | Valida el tamano maximo en esquema |
| Marcas de Tiempo | `DateTime(timezone=True)` | `DateTime(timezone=False)` | Previene ambiguedades de zona horaria |
| Estados de Ticket | `Enum` o `String(50)` indexado | `Integer` magico sin descripcion | Claridad de negocio y autodocumentacion |
| Datos Estructurados | `JSONB` | `JSON` plano / `Text` | Permite consultas con operadores de inclusion `@>` e indices GIN |

## 2. Estrategias de Indexacion

1. **Indices de B-Tree Simples**:
   - Aplicar en columnas utilizadas en filtros de igualdad o busquedas frecuentes:
     ```sql
     CREATE INDEX ix_tickets_status ON tickets (status);
     CREATE INDEX ix_tickets_created_by ON tickets (created_by);
     ```

2. **Indices Compuestos**:
   - Orden estricto: columnas de igualdad primero, seguidas de columnas de rango o fecha:
     ```sql
     CREATE INDEX ix_tickets_status_created_at ON tickets (status, created_at DESC);
     ```

3. **Indices Unicos**:
   - Obligatorios para identificadores naturales de recursos:
     ```sql
     CREATE UNIQUE INDEX uq_tickets_slug ON tickets (slug);
     CREATE UNIQUE INDEX uq_ci_callbacks_idempotency_key ON ci_callbacks (idempotency_key);
     ```

## 3. Gestion de Conexiones y Concurrencia

1. **Estrategia de Pooling**:
   - **Desarrollo y Produccion**: Utilizar un pool asincrono gestionado con limites de conexion razonables (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`).
   - **Pruebas Automatizadas (Pytest)**: Configurar obligatoriamente `poolclass=NullPool` para abrir y cerrar conexiones de forma aislada por cada sesion de test, evitando errores de operaciones concurrentes en el mismo socket de `asyncpg`.

2. **Aislamiento de Transacciones**:
   - Siempre delimitar transacciones mediante bloques de contexto:
     ```python
     async with session_factory() as session:
         async with session.begin():
             # Operaciones atomicas
             ...
     ```
   - Evitar mantener transacciones abiertas durante llamadas HTTP externas (por ejemplo, llamadas a la API de Forgejo). Realizar primero las llamadas de red y abrir la transaccion unicamente para la persistencia.
