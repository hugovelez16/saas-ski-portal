# Plan de implementacion de Empresa (por bloques PR-nn, un PR por bloque)

Fecha: 2026-10-18 (revision 3: E7 corregido, scripts de reparacion de datos y procedimiento de despliegue con migracion; revision 2: decisiones P-1 a P-17 y desbloqueo de X1, X3 y Q3). Rama de analisis: `docs/analisis-entidad-empresa`.
Fuentes: `cambios-empresa.md` (catalogo), `logica-negocio-empresa.md` (comportamiento objetivo), `CLAUDE.md` del proyecto.

Nomenclatura: los bloques de este plan se llaman `PR-00`, `PR-01`, ... para no confundirlos con los items del catalogo (`B1` del catalogo = billing en dos niveles, sigue bloqueado; `B2`..`B5` del catalogo = modulos y billing). Cuando se cita un item del catalogo se escribe "item B1 del catalogo".

Este documento es un plan, no codigo. Esta pensado para que `backend-dev`, `frontend-dev` y `tester` (haiku) lo ejecuten sin decidir. Las decisiones ya tomadas por el usuario estan en la seccion 4.1 (se citan como `[P-n]`); lo que sigue abierto esta en la seccion 4.2 y el plan asume la opcion recomendada, indicando que cambia si se elige otra. Lo que ejecuta el usuario (produccion, backups, `.env`) se marca como **ACCION DEL USUARIO**.

## 0. Convenciones y reglas de ejecucion

### 0.1 Reglas del proyecto que aplican a todo bloque
- Antes de editar: `git branch --show-current`. Una rama por bloque con nombre `<tipo>/<descripcion-en-espanol>` (se sugiere una en cada bloque). Partir de `develop`.
- Prohibido `git commit`, `git push` y crear PR salvo orden expresa del usuario en ese mensaje. El plan nunca los pide.
- Ficheros solo con Edit/Write. Bash solo para tests, linters, git de lectura y comandos de sistema.
- Sin emojis en codigo, comentarios, logs, commits ni PR. Mensajes de error y textos de UI en espanol.
- No leer ni imprimir `.env`, `backend/keys/` ni tokens reales. `./scripts/sync_db.sh` nunca por iniciativa propia. Ningun agente ejecuta comandos contra produccion: los comandos de produccion de este plan son siempre **ACCION DEL USUARIO**.
- No ampliar alcance: si un paso es ambiguo o choca con el codigo, el agente devuelve la duda y se detiene.

### 0.2 Ciclo de cada bloque
1. `tester`: escribe primero los tests del bloque y comprueba que FALLAN por el motivo correcto (un test que falle antes del arreglo). Cita la salida real.
2. `backend-dev` (y `frontend-dev` en paralelo si toca ficheros distintos): implementa. Si el bloque tiene migracion con riesgo de datos, implementa ANTES el script de reparacion (subtarea `PR-nn.R`, seccion 9) y despues la migracion.
3. `tester`: ejecuta los tests y cita el resultado real.
4. Verificacion completa del bloque (comandos de 0.3).
5. Reviewers (solo lectura): `code-reviewer` siempre; ademas los indicados en cada bloque (`database-reviewer` revisa tambien los scripts de reparacion); `reviewer` valida el cumplimiento de `CLAUDE.md` en el PR final. Si reportan fallos, se vuelve al desarrollador y se repite.
6. Paso final del PR: incremento SemVer (0.4) sobre `develop` actualizado.
7. Si el PR contiene una migracion (PR-02, PR-06, PR-09, PR-10, PR-11, PR-23 y los de v2 si migran): la descripcion del PR incluye el "Paso previo de despliegue" de la seccion 10 y la lista de scripts de reparacion que hay que ejecutar. El despliegue en produccion NO se hace hasta que el usuario complete ese procedimiento.

### 0.3 Comandos de verificacion
- Backend lint: `ruff check backend/` (desde la raiz).
- Backend tests: `cd backend && pytest tests/ -q` (un fichero: `pytest tests/routers/test_x.py -q`). El Python del host no tiene las dependencias (verificado: `ModuleNotFoundError: fastapi`), asi que se ejecuta en el contenedor [P-17]: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/ -q` (el volumen `./backend:/app:z` ya esta montado). Tras cambiar `backend/requirements.txt` o el `Dockerfile` hay que reconstruir: `docker compose -f docker-compose.dev.yml build backend`.
- Migraciones: `./bin/migrate` (equivale a `docker compose -f docker-compose.dev.yml run --rm backend python3 -m alembic upgrade head`). Reversibilidad de cada migracion nueva, en este orden: `... alembic upgrade head`, `... alembic downgrade -1`, `... alembic upgrade head`, `... alembic heads` (un solo head).
- Frontend (desde `frontend/`): `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build`.
- Un PR no se da por bueno si falla alguno de los comandos aplicables.

### 0.4 Paso de version (regla 8) al final de cada PR
Estado actual verificado: `package.json` raiz y `frontend/package.json` en `0.8.1`; el `CHANGELOG.md` tiene seccion `## [0.8.1] - 2026-10-08` con subseccion `### Tipo de Cambio SemVer`. La imagen de cada despliegue se etiqueta con la version de `package.json` (verificado en `.github/workflows/deploy-dev.yml` y `deploy-prod.yml`: `dev-vX.Y.Z` y `vX.Y.Z`).
- Se hace al final, con la rama actualizada con `develop` (el merge de `develop` lo ordena el usuario; los agentes no lo hacen por iniciativa propia). Mientras el proyecto esta en `0.y.z`, los cambios incompatibles suben MINOR.
- Editar (Edit) tres ficheros con el mismo numero: `package.json` (campo `version`), `frontend/package.json` (campo `version`) y `CHANGELOG.md` (seccion nueva encima de la `[0.8.1]`, formato `## [X.Y.Z] - AAAA-MM-DD`, subseccion `### Tipo de Cambio SemVer` con `- **MINOR**: ...` o `- **PATCH**: ...`, y `### Funcionalidades y Mejoras` / `### Corregido` / `### Seguridad` / `### Cambios Internos` segun corresponda, con los ficheros tocados).
- El numero exacto (siguiente PATCH o MINOR respecto a la version de `develop` en ese momento) lo calcula el agente leyendo `package.json` de `develop` actualizado. Cada bloque indica solo el tipo.

### 0.5 Reparto de agentes y paralelismo
- `tester` abre y cierra cada bloque. `backend-dev` y `frontend-dev` pueden trabajar en paralelo dentro de un bloque porque los ficheros son distintos y el contrato (request/response) esta fijado en este plan; la verificacion integrada (`npm run build` + `pytest`) se hace al final. `devops` en PR-00 (CI), PR-16 (Dockerfile) y PR-22 (gateway).
- Bloques entre si: ver seccion 3. Dos bloques que tocan `backend/routers/companies.py` o `backend/crud.py` no deben ir en worktrees paralelos sin avisar (regla "un worktree, una tarea, un PR").

### 0.6 Estilo de los contratos
- La API v1 serializa en `camelCase` (`CamelModel` en `backend/schemas.py`, `populate_by_name=True`: acepta `snake_case` y `camelCase` en la entrada). Los esquemas nuevos de v1 heredan de `CamelModel`. En los ejemplos de v1 se escribe el nombre Python (`snake_case`); el JSON real va en `camelCase`.
- La API v2 (PR-16 a PR-18) serializa en `snake_case` sin alias [X7, ver 4.2 Q-2]; el JSON de v2 coincide con los nombres de BD y dominio.
- Errores: `HTTPException`/`PolicyError` con `detail` en espanol, texto claro y sin datos internos (sin ids de usuario, sin flags como `is_manager`).
- Constantes numericas aceptadas [P-12]: nombre de empresa 1..120; nombre de impuesto 1..50; maximo 20 impuestos; valor de impuesto 0..1 (fraccion); fecha de turno entre 2000-01-01 y hoy + 730 dias; motivo de auditoria hasta 500; `label` de tipo de turno 1..60; `limit` de listados paginados de filas 1..2000 (el tope solo se aplica en PR-08, despues de PR-07).
- Principio de agregados [P-12]: toda suma o metrica (dashboards, informes, totales) la calcula el backend sobre el rango COMPLETO de fechas en endpoints de agregados; el frontend nunca suma filas de una pagina. Los listados de filas devuelven tambien el total de filas del rango (cabecera `X-Total-Count`, ver PR-07).

## 1. Alcance: incluido y excluido

### 1.1 Excluidos (bloqueados)
Solo dos: F6 (settings de membresia, O10) y el item B1 del catalogo (billing en dos niveles, O11). Cerrados por el usuario: X5 (se mantiene Python) y X4 (`crud.py` NO se divide; lo sustituira v2). Desbloqueados e incluidos: X1, X3, Q3, y con ellos X7. X6 (RLS) sigue fuera del plan por instruccion previa del coordinador.

### 1.2 Items incluidos que dependen de un bloqueado: tratamiento
| Item | Depende de | Tratamiento |
|---|---|---|
| P5 (`require_module` en billing avanzado e informes) | item B1 del catalogo / O11 | Solo se cubre parte diario (PR-14). Billing avanzado: no existe la division basico/avanzado, asi que no se protege `billing-summary` con modulo (romperia el billing basico, que debe funcionar sin modulo). Informes: verificado que no existe endpoint de informes (los PDF se generan en el frontend con `/work-logs`), no hay nada que proteger. Ambos quedan condicionados al item B1 del catalogo. |
| U6 (retirar `allow_tutorial` y `allow_coordination`) | F6/O10 | Tambien los escribe `frontend/src/components/admin/member-settings-dialog.tsx` en los `settings` del MIEMBRO (zona de O10). Ese dialogo y los `settings` de miembro NO se tocan. Solo se retiran del catalogo de `settings` de empresa y de `company-settings-dialog.tsx` (sin uso, verificado). |
| X2 (politica usable desde v1 y v2) | - | Politica en `backend/access_policy.py`, modulo puro sin imports de FastAPI ni SQLAlchemy. Lo usan v1 (PR-03) y v2 (PR-16 a PR-18). |
| E3 | F1 | Se hace dentro de PR-10. |
| T5 | F1 | Se hace en PR-12, despues de PR-10. |
| T10 (parte diario) y U13 | A2 (logs) | Independientes entre si: U13 se reparte entre PR-14 (parte diario) y PR-15 (pantalla de logs). |
| X1, X3, Q3, X7 | decision v1-primero o v2-absorbe (Q-1) | Planificados bajo la opcion recomendada (v1 primero, luego port a v2). Ver 4.2 para que cambia con la otra opcion. |

## 2. Hallazgos de la verificacion contra el codigo (discrepancias con el catalogo)

Verificado con Read/Grep/ejecucion los dias 2026-10-17 y 2026-10-18.

1. S2: los cuatro `get_current_user` estan en `backend/routers/companies.py` lineas 245, 270, 304 y 327 (handlers `update_member_status`, `read_company`, `read_company_rates`, `update_company_member`). Coincide. `get_current_user` solo debe quedar en `backend/routers/auth.py:169` (`/verify-2fa`).
2. Q2: hay SIETE ficheros `test_*.py` en la raiz de `backend/` (no ocho): `test_auth_dev_bypass.py`, `test_billing_summary.py`, `test_dashboard_summary.py`, `test_governance.py`, `test_modules.py`, `test_rates.py`, `test_work_logs_supervisor.py`. `backend/pytest.ini` ya tiene `testpaths = tests .`, pero la CI ejecuta `pytest tests/` (no los recoge). Los tests existentes llaman a los handlers directamente con usuarios a los que se les pegan atributos (`is_platform_admin`, `active_role`, `active_company_id`); la mayoria usan `SessionLocal()` contra la BD real y `test_dashboard_summary.py` hace `commit` (peligroso contra la BD de desarrollo).
3. `backend/src/` NO se usa en produccion: ningun router ni `crud.py` lo importa; solo lo importan los tests de `backend/tests/`. El `Dockerfile` no pone `src` en `PYTHONPATH` y los modulos de `src/` se importan como raiz (`from domain.entities...`). Consecuencia: hasta PR-15 todo el trabajo es sobre v1; PR-16 anade `PYTHONPATH` al `Dockerfile`.
4. `backend/src/` (v2) esta mas incompleto de lo que dice el catalogo: (a) `backend/src/infrastructure/persistence/sqlalchemy/repositories/company_repository.py:11` importa `domain.ports.repositories.company_repository_port`, que NO EXISTE (solo hay `user_repository_port.py` y `work_log_repository_port.py`): el repositorio de empresa no se puede importar; (b) la entidad `Company` (`domain/entities/company.py`) no tiene `is_active`, `is_managed` ni `updated_at`, el mapper y `save()` del repositorio no los persisten, y aun tiene `fiscal_id`; (c) `CompanyMember` (`domain/entities/company_member.py`) no tiene `settings` ni `updated_at`; (d) no hay capa de presentacion v2 ni casos de uso de empresa (solo `application/use_cases/work_logs/`); (e) `domain/value_objects/tax_configuration.py` tiene tres tasas fijas (`irpf_rate`, `social_security_rate`, `extra_rate`), no claves libres.
5. `POST /users/` (`routers/users.py:15-23`) esta ademas roto: llama a `auth.get_user_by_email`, que no existe en `auth.py` (esta en `crud.py`); devuelve `response_model=schemas.UserCreate` (que incluye `password`).
6. `crud.update_work_log` (`crud.py:550`) usa `models.WorkLog.group_id`, columna que no existe: `apply_to_group` con `group_id` lanza `AttributeError` (500). Ademas `WorkLogResponse.group_id` siempre sale `None` porque el grupo vive en `extra_data["group_id"]`. T4 lo corrige (PR-08).
7. El frontend NO decodifica el token: obtiene `activeRole`, `activeCompanyId` e `isPlatformAdmin` de `GET /users/me` (`AuthContext.tsx`).
8. `?companyId=` esta en 12 sitios del frontend: `(app)/layout.tsx:52,82,100`, `company-switcher.tsx:28,51`, `manager/calendar/page.tsx:41`, `manager/settings/page.tsx:14`, `manager/dashboard/page.tsx:16,35`, `manager/billing/BillingPageClient.tsx:20`, `manager/users/[userId]/page.tsx:365,420`, `manager/users/page.tsx:67,84,285`, `manager/daily-reports/page.tsx:65`, `manager/shifts/page.tsx:38`, `list/page.tsx:46`, `reports/print/page.tsx:21`, `AuthContext.tsx:218,220`, `dashboard-today-card.tsx:111`.
9. Gateway: el login real es `POST /api/token` (no `/api/auth/`). Rutas de autenticacion: `/token`, `/verify-2fa`, `/refresh-token`, `/logout`, `/auth/*`. Dos ficheros: `gateway/nginx.conf` y `gateway/nginx.dev.conf`. Prefijo v2: NO hace falta cambiar el gateway ni `next.config.ts` (verificado): `location /api/` hace `proxy_pass http://backend_upstream/` (quita `/api/`) y el rewrite de Next `/api/:path*` -> `${BACKEND_INTERNAL_URL}/:path*`; una ruta `/v2/...` montada en FastAPI (con `root_path="/api"`) se sirve como `/api/v2/...`. El cliente axios usa `baseURL=/api`, por lo que el frontend llamara `/v2/...`.
10. T11: `RedisManager.get/set/delete/delete_pattern` (`backend/redis_config.py`) ya capturan excepciones y devuelven `None`/`False`; el dashboard no devuelve 500 por Redis caido. T11 se reduce a un test de regresion y al tratamiento de inactivos. Con Redis caido cada llamada espera hasta 2 s (`socket_timeout=2.0`): PR-03 anade un backoff en `RedisManager`.
11. Pantallas que hoy obtienen sumas o totales a partir de filas con `limit` alto (no valen con tope 2000; ver PR-07): `components/manager/company-dashboard.tsx:126` (`limit: 10000`, estadisticas y desgloses calculados en el navegador, lineas 152-302; `:139` hoy, `limit: 1000`), `app/(app)/reports/page.tsx:259` (`limit: 1000 // Ensure we get enough`), `app/(app)/reports/print/page.tsx:39` (`limit: 1000`), `components/work-log/report-generation-dialog.tsx:102` (`limit: 1000 // Ensure we get enough records`), `app/(app)/admin/users/[userId]/page.tsx:396` (`limit: 1000`, sin rango de fechas), `app/(app)/manager/calendar/page.tsx:56` (`limit: 1000`, sin rango de fechas), `app/(app)/manager/daily-reports/page.tsx:151` y `app/(app)/admin/daily-reports/DailyReportPageClient.tsx:40` (`limit: 2000`, un solo dia).
12. `crud.create_user` (auto-union a la empresa "Personal") lo usa solo `POST /users` (PA) tras eliminar el registro publico: ver M8 en PR-05.
13. Frontend: `lib/api/settings.ts:getUserRates` llama a `GET /companies/{id}/members/me`, que NO existe en el backend (cae al `catch`), y `lib/api/users.ts` llama a `GET /users/{id}/sessions`, tampoco existe. Fuera de alcance.
14. Modulos existentes (migraciones): `worker_daily_report`, `billing`, `reports`. Registro de sidebar en `(app)/layout.tsx:21-45`.
15. La ultima migracion (head) es `8f10a2b3c4d5` (cadena lineal verificada). Cada migracion nueva usa como `down_revision` el head vigente en `develop` en ese momento.
16. `AuditLog` hoy exige `impersonated_user_id` y `admin_user_id` NOT NULL (`models.py:193-200`): A1 necesita migracion.
17. `dev_seed.py` crea la membresia del PA con `CompanyRole.admin` y `seed.py` con `CompanyRole.manager`; el rol `admin` de empresa esta reservado y no debe asignarse.
18. `lib/api/settings.ts:updateUserRates` y 5 pantallas llaman a `PUT /companies/{id}/members/{uid}` (ver PR-05).
19. Despliegue (ver seccion 10): `deploy-prod.yml` se dispara con cada push a `main` (y `workflow_dispatch`), publica `backend`/`frontend`/`gateway` con tags `latest` y `vX.Y.Z` y llama al webhook de Komodo; `docker-compose.prod.yml` tiene un servicio one-shot `migrate` (`python3 -m alembic upgrade head`, imagen `backend:${IMAGE_TAG:-latest}`) y el `backend` depende de `migrate` con `service_completed_successfully`; hay un servicio `pgbackups` (`prodrigestivill/postgres-backup-local`, `@daily` por defecto, retencion 7 dias / 4 semanas / 3 meses en `${BACKUP_DIR:-/mnt/nas_backups/clases-vesotel}`); `backend/migrations/env.py` ejecuta las migraciones dentro de `context.begin_transaction()` (DDL transaccional de PostgreSQL). No existe hoy ningun script de reparacion de datos ni directorio `backend/scripts/`.

## 3. Orden de ejecucion y dependencias

| Bloque | Titulo | Items | Depende de | Paralelo con | Tipo version |
|---|---|---|---|---|---|
| PR-00 | Entorno de pruebas del backend | Q2 | - | - | sin version (excepcion regla 8) [P-13] |
| PR-01 | Seguridad inmediata de autenticacion | S2, S3, S7, S8, I1 | PR-00 | PR-02 | PATCH |
| PR-02 | Auditoria: modelo, migracion y helper (migra) | A1 (base) | PR-00 | PR-01 | MINOR |
| PR-03 | Politica central de permisos, cache de acceso y modo "ver como" | P1, P4, X2, S5, T9, I2, I4, items B2/B4 del catalogo, P-3 | PR-00, PR-01 | - | PATCH |
| PR-04 | Token minimo, emision de contexto y "ver como" del PA | S1, S4, S6 (+FE) | PR-03 | - | PATCH |
| PR-05 | Membresias solo plataforma y endpoints de miembro (migra: retira `users.default_company_id`, sin script) | P2 (membresia), P6, P3, M1-M4 (M2/M3 obsoletos), M6, M9 (+FE) | PR-02, PR-04 | PR-07 | MINOR |
| PR-06 | Gestion de empresa solo plataforma (migra, con script de reparacion) | P2 (empresa), P3, E1, E2, E4-E8 (+FE) | PR-02, PR-05 | PR-07 | MINOR |
| PR-07 | Agregados de turnos y migracion de pantallas (antes del tope de `limit`) | P-12 | PR-03, PR-04 | PR-05, PR-06 | MINOR |
| PR-08 | Reglas de turnos (incluye el tope de `limit`) | T1-T4, T6, M5, P3 (turnos) (+FE) | PR-04, PR-07 | - | PATCH |
| PR-09 | `work_logs.company_id` NOT NULL (migra, con script de reparacion) | T8 | PR-08, PR-05 + script ejecutado en produccion | cualquiera | PATCH |
| PR-10 | Impuestos con claves libres (migra, con script de reparacion) | F1, E3 (+FE) | PR-06, PR-08 | - | MINOR |
| PR-11 | Contratos de `settings`, tipos de turno y tarifas (migra, con script de reparacion) | F2-F5, F7, U6 (+FE) | PR-10 | - | MINOR |
| PR-12 | Recalculo y avisos de turnos, dashboard | T5, T7, T11 (+FE) | PR-08, PR-10 | PR-13 | MINOR |
| PR-13 | Vista reducida y completa de empresa (v1) | P7, P8 (+FE) | PR-06, PR-11 | PR-12 | MINOR |
| PR-14 | Parte diario y modulos | T10, items B2-B5 del catalogo, P5 parcial (+FE) | PR-03, PR-08 | PR-15 | MINOR |
| PR-15 | Consulta de logs de auditoria | A2 (+FE) | PR-02, PR-05, PR-06 | PR-14 | MINOR |
| PR-16 | API v2: cimientos y alineacion del dominio | X1 (1/3), Q3 (arnes) | PR-11, PR-13 | PR-14, PR-15 | MINOR |
| PR-17 | API v2: empresa y vistas | X1 (2/3), X3, X7, Q3 | PR-16, PR-13 | - | MINOR |
| PR-18 | API v2: membresias, tarifas e impuestos | X1 (3/3), X3, Q3 | PR-17 | - | MINOR |
| PR-19 | Frontend transversal | U1, U4, U7, U8, U10, banner "ver como" | PR-04, PR-06, PR-13 | PR-16-18 | MINOR |
| PR-20 | Frontend: migracion de empresa a v2, endpoint a endpoint | X1/X7 (cliente) | PR-17, PR-18, PR-19 | - | MINOR |
| PR-21 | Retirada de los endpoints de empresa de v1 | X1 (cierre) | PR-20 | - | MINOR |
| PR-22 | Rate limit en el gateway | I3 | - | cualquiera | PATCH |
| PR-23 | Cierre: borrar `fiscal_id` (migra, con script de exportacion) | E2 final | PR-06, PR-11 + script ejecutado en produccion | - | PATCH |

A3 (trigger `updated_at`) queda fuera del plan [P-16].

Bloques con migracion y por tanto con "paso previo de despliegue" (seccion 10): PR-02, PR-05, PR-06, PR-09, PR-10, PR-11, PR-23. PR-16 a PR-18 (v2) no planifican migraciones; si alguno acaba incluyendo una, aplica la misma regla. Bloques con script de reparacion de datos (seccion 9): PR-06, PR-09, PR-10, PR-11, PR-23. PR-02 no necesita script (solo anade columnas y relaja NOT NULL; no puede chocar con datos). PR-05 tampoco (solo borra una columna que el codigo ya no usa).

Cadena critica: PR-00 -> PR-01 -> PR-03 -> PR-04 -> PR-05 -> PR-06 -> PR-10 -> PR-11 -> PR-13 -> PR-16 -> PR-17 -> PR-18 -> PR-20 -> PR-21. Paralelizables: PR-02 con PR-01; PR-07 con PR-05/PR-06 (cuidado con `crud.py`); PR-09 en cualquier momento tras PR-08; PR-12 con PR-13; PR-14 con PR-15 y con PR-16; PR-19 con PR-16..PR-18; PR-22 en cualquier momento.

Restriccion transversal cumplida: todo cambio del backend que rompe un flujo que la UI ofrece hoy (anadir miembro, estado de membresia, rol, `reset-password-email`, editores de configuracion de empresa, crear turno de worker en gestionada, sumas en el navegador) sale en el mismo PR que su adaptacion en el frontend (PR-05, PR-06, PR-07, PR-08).

## 4. Decisiones y preguntas

### 4.1 Decisiones tomadas por el usuario
| Id | Decision | Donde se aplica |
|---|---|---|
| P-1 | P6 y P7 en v1 con despliegue coordinado backend+frontend | PR-05, PR-13 |
| P-2 | Vista reducida incluye `worklog_definitions` y `tax_config` en solo lectura | PR-13, PR-17 |
| P-3 | El manager pierde "entrar como worker". El PA conserva "ver como" worker/manager de una empresa, sin suplantar a ningun usuario y SOLO LECTURA | PR-03, PR-04, PR-19 |
| P-4 | El PA NO se bloquea: `switch-scope` emite `cid` de empresa suspendida para el PA; worker y manager siguen bloqueados | PR-04 |
| P-5 | Anti-enumeracion: 403 igual para inexistente/ajena/sin membresia; 404 solo PA | PR-03 |
| P-6 | `PUT /companies` sin cambios -> 422 | PR-06 |
| P-7 | Seed y dev_seed mantienen la membresia del PA con rol `manager` | PR-01 |
| P-8 | Tests con SQLite en memoria + marcador `postgres` en CI | PR-00 |
| P-9 | Bypass solo con `ENVIRONMENT=development` Y `DEV_LOGIN_BYPASS`; arranque abortado si no. Revision humana del `.env` de produccion | PR-01 |
| P-10 | `price_type` por defecto `net`; solo afecta a la vista del dashboard. El calculo de impuestos lo decide `is_gross` por tarifa: `is_gross=True` descuenta los impuestos de `tax_config` al calcular el snapshot; `False` es tarifa neta sin deduccion; default `False` | PR-10, PR-11 |
| P-11 | `tax_config: {}` valido | PR-10 |
| P-12 | Valores de 0.6 aceptados, con cambio: el tope de `limit` (2000) aplica SOLO al listado paginado de filas; toda suma o metrica la calcula el backend en endpoints de agregados sobre el rango completo; los listados devuelven el total de filas. Bloque nuevo de agregados ANTES de aplicar el tope | PR-07, PR-08 |
| P-13 | B0 (ahora PR-00) sin subida de version | PR-00 |
| P-14 | El parte diario oculta importes al worker con DOS esquemas de respuesta (campos ausentes, no null) | PR-14 |
| P-15 | 409 en suscripciones duplicadas activas/trial de la misma empresa+modulo | PR-14 |
| P-16 | A3 (trigger `updated_at`) fuera | - |
| P-17 | `pytest` en contenedor con `docker compose -f docker-compose.dev.yml` | todos |
| X1/X3/Q3 | Desbloqueadas. Python se mantiene (X5), `crud.py` no se divide (X4). v2 solo cubre el area empresa (empresa, membresias, tarifas, impuestos y lo necesario); prefijo `/api/v2/`; v1 se mantiene y sus endpoints de empresa se retiran solo cuando el frontend use v2 en todos ellos; el frontend migra endpoint a endpoint cuando v2 tiene paridad probada | PR-16 a PR-21 |
| E7 | Corregido: una empresa sin manager NO es un problema ni una precondicion (`logica-negocio-empresa.md` 4.3: el PA anade un manager o cambia el rol de un worker; no hay guardia de ultimo manager). La consulta E7 es solo informativa para documentar el procedimiento de recuperacion | PR-06, seccion 7 |
| Reparacion | Antes de cada migracion con riesgo de datos hay un script de reparacion idempotente en `backend/scripts/` con `--dry-run` por defecto y `--apply`; la migracion sigue abortando con `RuntimeError` si quedan datos sin arreglar. Reglas en la seccion 9 | PR-06, PR-09, PR-10, PR-11, PR-23 |
| Despliegue | Procedimiento de despliegue de PR con migracion (backup, script, rollback) como paso previo obligatorio. Seccion 10 | PR-02, PR-06, PR-09, PR-10, PR-11, PR-23 |
| Catalogo | Siguen bloqueados solo F6 y el item B1 del catalogo | seccion 1 |
| Datos de produccion | Tras analizar la copia del backup (seccion 7.1): `worklog_definitions.unit` admite `hours`, `days` y `fixed`; la migracion de PR-10 elimina los `extra` de `tax_overrides` a 0 que la empresa no define (aborta si alguno es distinto de 0 o no numerico); `cost_markup` sale del contrato (con copia del valor en el backup); ensayo previo con copia anonimizada (10.2, b bis); migraciones compatibles con el codigo anterior (10.1, 10.3) | PR-10, PR-11, PR-23, seccion 10 |
| Ventana de despliegue | Se ACEPTA que, durante los segundos en que corre `migrate`, el contenedor de la release anterior siga sirviendo con el esquema ya cambiado y alguna peticion falle. Sin releases previas ni divisiones: PR-10, PR-11 y PR-23 van cada uno en un solo PR (PR-23 borra `fiscal_id` en su migracion), y PR-05 (borra `default_company_id`) igual. PR-10 y PR-11 se despliegan fuera de horas de uso. v1 y v2 viven en la misma imagen (`/api/` y `/api/v2/`): el riesgo es solo el contenedor de la release anterior, independiente de v1/v2 | PR-05, PR-10, PR-11, PR-23, 10.3 |
| default_company_id | Se elimina (Q-10 resuelta): ultima empresa en `localStorage` del navegador (clave unica `lastCompanyId`, sin datos personales; lectura con `try/catch`), enviada como `company_id` en el login y validada por el backend; fallback por `sort_order`; PA neutro; nada en servidor | PR-04, PR-05 (PR-05.D) |

### 4.2 Preguntas abiertas (el plan asume la recomendada)
| Id | Pregunta | Recomendada | Si se elige la otra |
|---|---|---|---|
| Q-1 | Orden v1/v2 para los bloques de empresa PR-05, PR-06, PR-10, PR-11 y PR-13. Opcion A: se implementan primero en v1 y luego se portan a v2 con pruebas de paridad. Opcion B: v2 los absorbe (se construyen directamente en v2 y v1 solo recibe los arreglos de seguridad y la politica central PR-00..PR-04, PR-07..PR-09). | Opcion A. Motivos: (1) cierran ya los fallos de seguridad (hoy un manager puede anadir miembros, cambiar roles y editar la configuracion de la empresa); (2) la politica (`access_policy.py`), los contratos (`contracts.py`) y la auditoria (`audit.py`) son modulos compartidos, asi que el port a v2 es fino; (3) el v1 terminado es la referencia de las pruebas de paridad (Q3); (4) P-1 ya fija P6 y P7 en v1. | PR-05, PR-06, PR-10, PR-11 y PR-13 desaparecen de v1 y sus pasos pasan a PR-17/PR-18 (se anaden ahi sus tests, scripts de reparacion y migraciones); PR-20 pasa a ser la primera vez que el frontend ve esas reglas; PR-03 y PR-04 siguen igual; las ocultaciones de UI (U2, U3, U5, U11) se mueven a PR-20. No hay arnes de paridad (Q3) entre v1 y v2 para esas reglas: se sustituye por tests directos de v2. |
| Q-2 | X7: v2 serializa en `snake_case` (sin alias `camelCase`); el cliente v2 del frontend se tipa en `snake_case`. v1 sigue en `camelCase`. | Si | v2 hereda de `CamelModel` y el cliente v2 reutiliza los tipos actuales; desaparece el adaptador de PR-20. |
| Q-3 | Total de filas en los listados (P-12): cabecera `X-Total-Count` en `GET /work-logs` (compatible: el cuerpo sigue siendo una lista) o cambiar el cuerpo a un objeto `{items, total}`. | Cabecera `X-Total-Count` | `GET /work-logs` devuelve `{items, total}`; hay que migrar todos los llamadores a la vez en PR-07. |
| Q-4 | `is_gross = False` (tarifa neta, P-10): el codigo actual no descuenta nada del neto, pero sigue calculando un bruto informativo dividiendo entre `1 - suma_de_tasas` (`crud.py:219-222`). Mantener ese bruto informativo o dejar `gross_amount` igual al neto. | Mantener el calculo actual (sin cambio de comportamiento) | `gross_amount = net_amount` para tarifas netas; hay que migrar el significado de `gross_amount` historico en informes. |
| Q-5 | "Ver como" del PA (P-3): el PA no suplanta a nadie, asi que, por ejemplo, "ver como worker" muestra la interfaz y los permisos del worker pero los datos "propios" (turnos propios) son los del PA (normalmente vacios). Aceptar esa limitacion. | Aceptar (la alternativa, mostrar datos de la empresa completa como worker, rompe el aislamiento de "solo propios") | - |
| Q-6 | Ruta y formato de los ficheros que escriben los scripts de reparacion (backups de nombres recortados, de `fiscal_id`, de `settings`/`worklog_definitions`, y listas de decision manual). Deben quedar fuera del repo versionado y no contener secretos. | JSON, un fichero por ejecucion y tema, `<tema>_<AAAAMMDDTHHMMSSZ>.json`, permisos `0600`, en `${BACKUP_DIR}/repairs/` (el mismo directorio de backups que ya monta `pgbackups`; dentro del contenedor `/backups/repairs`). Los scripts se niegan a escribir dentro del arbol del repo. | Otra ruta: basta cambiar el valor de `--backup-dir`; si el formato debe ser otro (p. ej. CSV para las listas manuales), cambia solo `repair_common.write_backup`. |
| Q-7 | Settings/`worklog_definitions` con claves DESCONOCIDAS (ni mapeadas ni retiradas): la migracion de PR-11 aborta si existen. Para desbloquearla, el script ofrece `--apply --drop-unknown CLAVE[,CLAVE]` (hace backup del valor y la elimina) o el usuario decide anadir la clave al modelo. Aceptar. | Si, eliminar solo con `--drop-unknown` explicito y backup previo | La migracion elimina las desconocidas sin pedir confirmacion (peor: perdida silenciosa). |
| Q-8 | `fiscal_id` real (PR-23): la migracion aborta si hay valores reales y la variable `FISCAL_ID_EXPORTED=1` no esta presente; el usuario la fija tras exportar con el script. Aceptar ese seguro. | Si | Sin seguro: la migracion borra la columna y la unica salvaguarda es el backup de la BD (seccion 10). |
| Q-9 | En el fallo de `migrate` (seccion 10, c): se afirma que la version anterior sigue desplegada porque `backend` depende de `migrate`. No he podido verificar como actualiza Komodo el stack (puede recrear `frontend` y `gateway` aunque `backend` no arranque). Confirmar el comportamiento real de Komodo o aceptar el riesgo de frontend nuevo con backend antiguo durante el fallo. | Confirmar en Komodo (ACCION DEL USUARIO) y, mientras tanto, ejecutar siempre los scripts de reparacion ANTES de fusionar a `main` (seccion 10, paso b) para que `migrate` no falle | - |
| Q-10 | **RESUELTA.** M3 (PR-05): en produccion 2 usuarios tienen `default_company_id` sin membresia activa (seccion 7.1). Decision del usuario: se ELIMINA `default_company_id` (columna, API y UI). La ultima empresa activa se guarda en el `localStorage` del navegador, el frontend la envia como `company_id` en el login y el backend valida la membresia; si no es valida, usa la primera membresia activa por `company_members.sort_order`; sin ninguna, token sin empresa; el PA mantiene contexto neutro. No se guarda en servidor. Implementacion: login en PR-04 y retirada de la columna en PR-05.D. | Resuelta | - |

## 5. Bloques

Plantilla: Objetivo, Rama, Items, Depende de, Reviewers, Precondiciones de datos, Subtareas (agente, ficheros, firmas, contrato, tests, verificacion), Paso de version.

---

### PR-00 - Entorno de pruebas del backend (Q2)

- Rama: `chore/entorno-pruebas-backend`. Items: Q2. Depende de: nada. Reviewers: `code-reviewer`. Version: ninguna [P-13].
- Objetivo: que `cd backend && pytest tests/` ejecute TODA la suite, sin tocar jamas la BD de desarrollo, con fixtures reutilizables por los bloques siguientes [P-8].

**PR-00.1 [backend-dev] Infraestructura de tests**
- Crear `backend/tests/conftest.py`:
  - Al principio del fichero, ANTES de cualquier import de `database`: `os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite://")`; `os.environ.setdefault("ENCRYPTION_KEY", "dGVzdF9rZXlfZm9yX2NpX3ZhbGlkYXRpb25fcHVycG9zZXM=")`; `os.environ["ENVIRONMENT"] = "test"`; `os.environ.pop("DEV_LOGIN_BYPASS", None)`; `os.environ.pop("NODE_ENV", None)`. Nunca usar el `DATABASE_URL` real del entorno.
  - Registrar el hook `@compiles(JSONB, "sqlite")` que devuelve `"JSON"` (copiar el de `test_governance.py:18-20`).
  - Crear `engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)` si no hay `TEST_DATABASE_URL`; si lo hay, `create_engine(TEST_DATABASE_URL)`. Crear `TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)`. Despues de importar `database`, reasignar `database.engine = engine` y `database.SessionLocal = TestingSession` (asi los tests antiguos que hacen `from database import SessionLocal` usan la BD de test sin editarlos).
  - Fixture autouse `_schema`: antes de cada test `Base.metadata.create_all(engine)`; despues `Base.metadata.drop_all(engine)`. Solo con SQLite. Con `TEST_DATABASE_URL` (PostgreSQL migrado por Alembic) NO crear ni borrar tablas: cada test usa transaccion con rollback (fixture `db` abre `connection.begin()` y hace `rollback()` al final).
  - Fixture `db()` -> `Session` de `TestingSession`.
  - Fixture autouse `fake_redis`: asigna `redis_config.redis_manager._client = FakeRedisClient()` (clase en `backend/tests/fakes.py`) y la restaura al terminar.
  - Fixture `client(db)` -> `fastapi.testclient.TestClient(main.app)` SIN usar `with` (para no ejecutar el `lifespan`), con `main.app.dependency_overrides[database.get_db] = lambda: db` (generador que hace `yield db`). Limpiar overrides al terminar.
  - Registrar el marcador `postgres` en `pytest.ini`; un hook `pytest_collection_modifyitems` marca como `skip` los tests `@pytest.mark.postgres` si no hay `TEST_DATABASE_URL`.
- Crear `backend/tests/fakes.py`: `class FakeRedisClient` con `store: dict`, `ttl: dict`, `raise_errors: bool = False`; metodos `get(key)`, `set(key, value, ex=None, nx=False)` (devuelve `True`/`None` como redis-py), `delete(*keys) -> int`, `scan_iter(match=None, count=None)` (glob con `fnmatch`), `incr(key)`, `expire(key, seconds)`, `ping()`. Si `raise_errors` es `True`, todos lanzan `redis.ConnectionError`.
- Crear `backend/tests/factories.py` con estas funciones (firmas exactas):
  - `make_user(db, *, email: str | None = None, role: str = "user", is_active: bool = True, password: str = "pw12345678") -> models.User` (email aleatorio `u_<hex6>@test.com`; `hashed_password = auth.get_password_hash(password)`; `db.add`, `db.commit`, `db.refresh`).
  - `make_company(db, *, name: str | None = None, is_active: bool = True, is_managed: bool = False, tax_config: dict | None = None, worklog_definitions: dict | None = None, settings: dict | None = None) -> models.Company` (defaults: `tax_config={"social_security": 0.0648}`, `worklog_definitions={"particular": {"unit": "hours", "label": "Particular", "fields": []}}`, `settings={}`).
  - `make_member(db, user, company, *, role: str = "worker", is_active: bool = True, rates_config: dict | None = None) -> models.CompanyMember` (default `rates_config={"particular": {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}}`; `role` se convierte con `models.CompanyRole(role)`).
  - `make_work_log(db, user, company, *, type: str = "particular", start_date: date | None = None, end_date: date | None = None, start_time: time | None = time(9, 0), end_time: time | None = time(11, 0), net_amount: float = 40.0, extra_data: dict | None = None) -> models.WorkLog` (`start_date` default `date(2026, 1, 10)`).
  - `make_token(user, company=None, *, scope: str = "full", claims: dict | None = None, expires_minutes: int = 30) -> str`: `auth.create_access_token(data={"sub": str(user.id), "cid": str(company.id) if company else None, "scope": scope, **(claims or {})}, expires_delta=timedelta(minutes=expires_minutes))`.
  - `as_user(client, user, company=None, *, scope: str = "full", claims: dict | None = None) -> TestClient`: `client.cookies.clear()`, `client.cookies.set("access_token", make_token(...))`, devuelve `client`.
- Mover con `git mv` a `backend/tests/routers/` (crear con `__init__.py`): `test_auth_dev_bypass.py`, `test_billing_summary.py`, `test_dashboard_summary.py`, `test_governance.py`, `test_modules.py`, `test_work_logs_supervisor.py`. Ediciones permitidas en ellos: (a) quitar el `os.environ["DATABASE_URL"] = "sqlite:///:memory:"` y el `@compiles(JSONB...)`/`create_all` duplicados de `test_governance.py`; (b) marcar con `@pytest.mark.postgres` todo `test_billing_summary.py` (usa la funcion SQL `get_billing_summary`, solo PostgreSQL). Si un test falla por motivos de la migracion de entorno, corregir solo el test; si falla por un fallo real del codigo de produccion, NO tocar produccion: anotarlo y reportarlo.
- `git mv backend/test_rates.py backend/tools/print_company_rates.py` (crear `backend/tools/`; no es un test: consulta la BD al importarse). No borrar.
- Editar `backend/pytest.ini`: `testpaths = tests`; mantener `pythonpath = src .` y `asyncio_mode = auto`; anadir `markers = postgres: requiere PostgreSQL (TEST_DATABASE_URL)`.
- Editar `backend/requirements.txt`: anadir `httpx>=0.27,<1` (lo exige `TestClient`; la CI ya lo instala aparte).
- Editar `CLAUDE.md` (seccion Comandos, linea de Backend): anadir "Los tests nunca usan `DATABASE_URL`; usan SQLite en memoria o `TEST_DATABASE_URL`".
- Verificacion: `docker compose -f docker-compose.dev.yml build backend` y `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/ -q`; `ruff check backend/`; `ls backend/test_*.py` no debe listar nada. Citar el resumen de pytest (passed/skipped/failed).

**PR-00.2 [devops] CI**
- Editar `.github/workflows/ci.yml`: en el paso de Pytest anadir `TEST_DATABASE_URL: postgresql://ski_test_user:ski_test_password@localhost:5432/ski_test_db` junto a las variables existentes; el paso `pip install` ya incluye `httpx`. El paso de migraciones (`alembic upgrade head`) se mantiene antes de pytest.
- Verificacion: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` (si PyYAML no esta instalado, indicarlo); `pytest tests/` sigue siendo el comando.

**PR-00.3 [tester]** Escribir `backend/tests/test_infra.py`: (1) `test_database_url_is_never_the_real_one`: `str(database.engine.url).startswith("sqlite")` cuando no hay `TEST_DATABASE_URL`; (2) `test_factories_create_rows` (usuario, empresa, membresia, turno); (3) `test_client_uses_db_override`: `GET /health` devuelve 200; (4) `test_fake_redis_is_installed`: `redis_manager.set("k","v")` y `get("k") == "v"`.
- Reviewers: `code-reviewer`. Sin paso de version.

---

### PR-01 - Seguridad inmediata de autenticacion (S2, S3, S7, S8, I1)

- Rama: `fix/seguridad-autenticacion-basica`. Depende de: PR-00. Reviewers: `code-reviewer`, `security-reviewer`. Version: PATCH.
- Precondiciones de datos (solo lectura): usuarios con `is_active IS NULL` (S3, seccion 7).

**PR-01.0 [tester] Tests que fallan primero** - `backend/tests/routers/test_auth_security.py` (usa `client`, `as_user`, factories):
1. `test_2fa_pending_token_rejected_on_company_endpoints` (parametrizado): con `as_user(client, user, scope="2fa_pending")` y una empresa/membresia reales, `PUT /companies/{cid}/members/{uid}/status?status=active`, `GET /companies/{cid}`, `GET /companies/{cid}/rates-v2`, `PUT /companies/{cid}/members/{uid}` (body `{}`) responden 403 con `detail == "2FA Verification Required"`.
2. `test_2fa_pending_token_reaches_verify_2fa`: usuario sin 2FA activado y token `2fa_pending`: `POST /verify-2fa` con `{"code": "000000"}` responde 400 (`2FA not enabled for this user`), no 401/403 por scope.
3. `test_login_rejects_inactive_user`: usuario `is_active=False`, `POST /token` (form `username`, `password`) -> 403 `Cuenta desactivada. Contacta con el administrador`.
4. `test_login_active_user_ok`: 200.
5. `test_valid_token_of_inactive_user_rejected`: `GET /users/me` con token valido de usuario `is_active=False` -> 401.
6. `test_refresh_rejects_inactive_user`: crear `auth.create_refresh_token({"sub": ...})` + `auth.create_session(db, user.id, token)`; `client.cookies.set("refresh_token", token)`; `POST /refresh-token` -> 401.
7. `test_public_registration_removed`: `POST /users/` y `POST /users` sin cookie, con body valido (`{"email": "new@test.com", "password": "x"}`): nunca 200/201 y `db.query(User).filter_by(email="new@test.com").count() == 0`.
8. `test_create_user_requires_platform_admin`: `POST /users` como manager -> 403.
9. `test_dev_mode_requires_environment_and_flag` (monkeypatch env): `ENVIRONMENT=development` + `DEV_LOGIN_BYPASS=true` -> True; solo `ENVIRONMENT=development` -> False; solo `DEV_LOGIN_BYPASS=true` -> False; `NODE_ENV=development` solo -> False.
10. `test_assert_dev_bypass_safe`: `ENVIRONMENT=production` + `DEV_LOGIN_BYPASS=true` -> `RuntimeError`; `ENVIRONMENT=development` -> no lanza; sin bypass -> no lanza.
11. `test_lifespan_does_not_seed`: `import inspect, main; assert "seed_initial_data" not in inspect.getsource(main.lifespan)`.
12. `test_seed_skips_when_platform_admin_exists`: con `INITIAL_ADMIN_EMAIL`/`INITIAL_ADMIN_PASSWORD` definidos (monkeypatch) y un PA existente con otro email, `seed.seed_initial_data(db)` devuelve `False` y no crea usuario ni empresa.
13. `test_seed_creates_when_no_platform_admin`: BD sin PA -> devuelve `True`, crea PA, empresa y membresia con rol `CompanyRole.manager`.
14. `test_dev_seed_membership_role_is_manager`: `dev_seed.ensure_dev_admin_user(db)` crea membresia con rol `manager` (hoy `admin`).

**PR-01.1 [backend-dev] S2**
- `backend/routers/companies.py`: cambiar `Depends(auth.get_current_user)` por `Depends(auth.get_verified_user)` en `update_member_status` (linea 245), `read_company` (270), `read_company_rates` (304), `update_company_member` (327).
- Verificar con `grep -rn "get_current_user" backend --include=*.py`: solo debe quedar `backend/auth.py` (definicion) y `backend/routers/auth.py` (`/verify-2fa`).

**PR-01.2 [backend-dev] S3**
- `backend/auth.py`: en `get_current_user` y `get_verified_user`, tras `user = crud.get_user(...)` y `user is None`, anadir `if user.is_active is False: raise HTTPException(status_code=401, detail="Cuenta desactivada", headers={"WWW-Authenticate": "Bearer"})` (`is False` para tratar `NULL` como activo).
- `backend/routers/auth.py`: en `login_for_access_token`, en la rama no-dev, despues de verificar la contrasena: `if user.is_active is False: raise HTTPException(403, "Cuenta desactivada. Contacta con el administrador")`. En `refresh_access_token`, tras cargar el usuario: si `user.is_active is False`: `auth.revoke_session(db, refresh_token)` y `HTTPException(401, "Cuenta desactivada")`.

**PR-01.3 [backend-dev] S7**
- `backend/routers/users.py`: borrar el handler `create_user` (lineas 15-23, `POST /users/`). Quitar imports sin uso (`ruff check` lo indica).
- Comprobar que ningun `response_model` contiene `password`: `grep -n "response_model=schemas.UserCreate" backend/routers/*.py` sin resultados.

**PR-01.4 [backend-dev] S8 [P-9]**
- `backend/dev_seed.py`: `is_dev_mode()` devuelve `env == "development" and bypass` (eliminar `NODE_ENV` y el bypass suelto). Anadir `def assert_dev_bypass_safe() -> None`: si `DEV_LOGIN_BYPASS` es verdadero (`true/1/yes`) y `ENVIRONMENT.lower() != "development"`: `raise RuntimeError("DEV_LOGIN_BYPASS esta activo fuera de ENVIRONMENT=development. Aborting startup.")`.
- `backend/main.py`: en `lifespan`, tras la comprobacion de `ENCRYPTION_KEY`, llamar `dev_seed.assert_dev_bypass_safe()`.
- Actualizar `backend/tests/routers/test_auth_dev_bypass.py` al nuevo contrato.
- **ACCION DEL USUARIO** (anotar en el PR): revisar el `.env` de produccion (no definir `DEV_LOGIN_BYPASS` verdadero ni `ENVIRONMENT`/`NODE_ENV` igual a `development`). `docker-compose.prod.yml` carga `.env` por `env_file` (verificado). Los agentes NO leen `.env`.

**PR-01.5 [backend-dev] I1**
- `backend/main.py`: eliminar el bloque "Sembrado inicial de datos si procede" (lineas 102-108). La inicializacion de desarrollo (`dev_seed.ensure_dev_admin_user`) se mantiene, solo con `is_dev_mode()`.
- `backend/seed.py` (`seed_initial_data`): sustituir la comprobacion `existing_user` por: `if db.query(models.User).filter(models.User.role == models.UserRole.admin).first(): print("[Seed] Ya existe un administrador de plataforma. Omitiendo sembrado."); return False`. Mantener la membresia con `CompanyRole.manager` [P-7]. El `fiscal_id` NO se toca aqui (PR-06).
- `backend/dev_seed.py`: cambiar `role=models.CompanyRole.admin` (linea 96) por `models.CompanyRole.manager` [P-7].
- `bin/seed` no cambia.

**PR-01.6 [tester]** Ejecutar PR-01.0 y confirmar que pasan. Verificacion: `ruff check backend/` y `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/ -q`.

**PR-01.V Version**: PATCH. CHANGELOG `### Seguridad`: tokens `2fa_pending` rechazados en endpoints de empresa, usuarios desactivados sin acceso, registro publico eliminado, bypass de desarrollo restringido, sembrado fuera del arranque.

---

### PR-02 - Auditoria: modelo, migracion y helper (A1, parte base)

- Rama: `feat/auditoria-base-empresa`. Depende de: PR-00. Reviewers: `code-reviewer`, `database-reviewer`. Version: MINOR.
- Objetivo: poder registrar los eventos de empresa/membresia con quien, cuando, accion, empresa, valor anterior, nuevo y motivo. Los eventos concretos se emiten en PR-05/PR-06 (cada uno donde nace el cambio).
- Migracion: SI (anade columnas y relaja NOT NULL; no puede chocar con datos existentes, por eso no necesita script de reparacion). **Paso previo de despliegue obligatorio: seccion 10** (el backup de la BD aplica; el paso b de scripts no aplica).

**PR-02.0 [tester]** `backend/tests/test_audit.py`: (1) `test_record_audit_adds_row_without_commit`: llamar al helper, `db.rollback()` y comprobar que no quedo fila; llamar de nuevo y `db.commit()` y comprobar la fila; (2) `test_record_audit_serializes_uuid_and_dates`: `old_value={"company_id": uuid4()}` se guarda como string; (3) `test_existing_2fa_reset_sets_actor`: `POST /users/{id}/reset-2fa` como PA crea fila con `actor_user_id == admin.id` y `admin_user_id == admin.id`; (4) `test_impersonation_audit_sets_actor`: `record_impersonation_audit` rellena `actor_user_id`.

**PR-02.1 [backend-dev] Modelo** (`backend/models.py`, clase `AuditLog`, hoy lineas 193-200):
- `impersonated_user_id` y `admin_user_id` con `nullable=True`.
- Anadir: `actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)`; `company_id = Column(UUID(as_uuid=True), nullable=True, index=True)` (SIN `ForeignKey`: debe sobrevivir al borrado de la empresa, E4); `target_user_id = Column(UUID(as_uuid=True), nullable=True)`; `old_value = Column(JSONB, nullable=True)`; `new_value = Column(JSONB, nullable=True)`; `reason = Column(Text, nullable=True)`.

**PR-02.2 [backend-dev] Migracion** `backend/migrations/versions/b7e1a0d10001_extend_audit_logs.py`, `down_revision` = head vigente (hoy `8f10a2b3c4d5`):
- `upgrade()`: anadir las 6 columnas; `op.alter_column("audit_logs", "impersonated_user_id", nullable=True)` y `admin_user_id`; `UPDATE audit_logs SET actor_user_id = admin_user_id` (backfill); indices `ix_audit_logs_company_created (company_id, created_at)` y `ix_audit_logs_action (action)`.
- `downgrade()` (no destructiva): `UPDATE audit_logs SET admin_user_id = COALESCE(admin_user_id, actor_user_id), impersonated_user_id = COALESCE(impersonated_user_id, target_user_id, actor_user_id)`; borrar indices; `alter_column(... nullable=False)` en los dos; borrar las 6 columnas. Documentar en el docstring que si hubiese filas con `actor_user_id` nulo el downgrade fallara.
- Verificar con la secuencia de 0.3.

**PR-02.3 [backend-dev] Helper** `backend/audit.py` (nuevo):
```python
class AuditAction:  # constantes str, sin Enum para serializar facil
    COMPANY_CREATED = "company.created"; COMPANY_UPDATED = "company.updated"
    COMPANY_SUSPENDED = "company.suspended"; COMPANY_REACTIVATED = "company.reactivated"
    COMPANY_MANAGED_CHANGED = "company.managed_changed"; COMPANY_DELETED = "company.deleted"
    COMPANY_TAX_CONFIG_CHANGED = "company.tax_config_changed"
    COMPANY_SETTINGS_CHANGED = "company.settings_changed"
    COMPANY_DEFINITIONS_CHANGED = "company.worklog_definitions_changed"
    MEMBER_ADDED = "member.added"; MEMBER_DEACTIVATED = "member.deactivated"
    MEMBER_REACTIVATED = "member.reactivated"; MEMBER_REMOVED = "member.removed"
    MEMBER_ROLE_CHANGED = "member.role_changed"; MEMBER_RATES_CHANGED = "member.rates_changed"
    USER_STATUS_CHANGED = "user.status_changed"

def record_audit(db: Session, *, action: str, actor_id, company_id=None, target_user_id=None,
                 old_value: dict | None = None, new_value: dict | None = None,
                 reason: str | None = None, extra: dict | None = None) -> models.AuditLog:
    """Anade la entrada a la sesion SIN commit: se confirma con la transaccion del cambio."""
```
Implementacion: convertir `old_value`, `new_value` y `extra` con `json.loads(json.dumps(x, default=str))`; rellenar `actor_user_id=actor_id` y `admin_user_id=actor_id` (compatibilidad); `db.add(...)`; devolver la fila. Truncar `reason` a 500 caracteres.
- Actualizar los dos escritores existentes: `routers/users.py` (entrada `2fa_reset`, linea 251) y `routers/work_logs.py` (`record_impersonation_audit`, linea 21) para fijar tambien `actor_user_id` (el admin).
- Verificacion: tests PR-02.0; `ruff check backend/`; secuencia de migracion.

**PR-02.V Version**: MINOR.

---

### PR-03 - Politica central de permisos, cache de acceso y modo "ver como"

- Rama: `refactor/politica-central-permisos`. Items: P1, P4, X2, S5, T9, I2, I4, items B2 y B4 del catalogo, P-3 (parte de politica). Depende de: PR-00, PR-01. Reviewers: `code-reviewer`, `security-reviewer`. Version: PATCH.
- Precondiciones de datos: membresias con rol `admin` (seccion 7).
- Objetivo: UN solo sitio decide quien puede que sobre una empresa; rol y estados leidos de BD (con cache); empresa suspendida bloquea todo salvo al PA; el PA puede "ver como" worker o manager en solo lectura. No cambia aun la matriz de roles (PR-05/PR-06).
- Cambios de comportamiento visibles: (a) listar turnos, billing y dashboard de una empresa suspendida -> 403 para no-PA; (b) `GET /modules/me` ignora modulos de empresa suspendida; (c) para no-PA, empresa inexistente/ajena/sin membresia -> 403 `No tienes acceso a esta empresa` en vez de 404 [P-5]; (d) los 403 dejan de incluir `is_manager`, `is_self`, ids; (e) el rol sale de la membresia, no del token (el manager pierde "entrar como worker" [P-3]); (f) un token con claim `view_as` solo puede leer.
- Nota: el tope de `limit` en `GET /work-logs` NO se aplica aqui (PR-08, despues de PR-07) [P-12]; solo `skip >= 0` y `limit >= 1`.

**PR-03.0 [tester] Tests que fallan primero** - `backend/tests/policy/test_access_policy.py` (unitarios puros, sin BD) y `backend/tests/routers/test_company_access.py` (HTTP):
- Unitarios de `access_policy.authorize_company`: PA + empresa inexistente -> `PolicyError(404)`; PA + empresa suspendida -> `"platform_admin"`; no-PA + empresa inexistente -> 403 `MSG_NO_ACCESS`; no-PA sin membresia -> 403 `MSG_NO_ACCESS` (mismo texto que inexistente); membresia inactiva -> 403 `MSG_NO_ACCESS`; membresia activa y empresa suspendida -> 403 `MSG_SUSPENDED`; worker con `min_role="manager"` -> 403 `MSG_FORBIDDEN`; manager con `token_company_id` distinto -> 403 `MSG_SWITCH_COMPANY`; manager con token correcto -> `"manager"`; rol `admin` de membresia se normaliza a `"manager"`.
- Unitarios "ver como": PA con `view_as="worker"` y `min_role="manager"` -> 403 `MSG_FORBIDDEN`; con `view_as="worker"` y `min_role="worker"` -> `"worker"`; con `view_as="manager"` y `min_role="manager"` y `token_company_id` correcto -> `"manager"`; con `view_as="manager"` y `min_role="platform_admin"` -> 403; PA con `view_as` y empresa inexistente -> 404; `assert_view_as_read_only("worker", "POST", "/work-logs")` -> `PolicyError(403)`; `("worker", "GET", ...)` ok; `POST /auth/switch-scope`, `/logout`, `/refresh-token` permitidos.
- HTTP "ver como": PA con `make_token(pa, company, claims={"view_as": "worker"})`: `GET /companies/{cid}` 200, `GET /companies/{cid}/members` 403, `POST /work-logs` 403 con `detail` que contiene `solo lectura`, `PUT /companies/{cid}` 403, `GET /users` (lista, solo PA) 403, `POST /auth/switch-scope` no se bloquea por el modo; con `view_as="manager"`: `GET /companies/{cid}/members` 200, `GET /companies/{cid}/dashboard-summary` 200, `GET /work-logs/billing-summary` 200, y cualquier `POST/PUT/DELETE` 403; claim `view_as` en el token de un no-PA se ignora (el manager sigue siendo manager normal y puede escribir); `view_as` sin `cid` se ignora; `GET /users/me` con `view_as="worker"` devuelve `viewAs == "worker"`, `isReadOnlyView == true`, `activeRole == "worker"`, `isPlatformAdmin == true`; PA con `cid` y sin `view_as`: `activeRole` es `null`.
- HTTP (Q1: aislamiento entre empresas): manager de A no puede `GET /companies/{B}/members`, `GET /companies/{B}/dashboard-summary`, `GET /work-logs/billing-summary?company_id=B...`, `GET /companies/{B}/rates-v2` (403); manager de A con token con `cid=B` no gestiona A (403); worker de A no lista turnos de B; `GET /companies/{uuid-inexistente}` -> 403 para manager y 404 para PA; id mal formado en path -> 422.
- HTTP (suspendida): con empresa `is_active=False`: worker `GET /work-logs?company_id=...` -> 403; manager `GET /work-logs/billing-summary` -> 403; manager `GET /companies/{id}/dashboard-summary` -> 403; PA los tres -> 200; `GET /modules/me` de un worker con suscripcion de la empresa suspendida NO devuelve ese modulo.
- HTTP (efecto inmediato, S5): PA cambia a un manager a `worker` con `PUT /companies/{cid}/members/{uid}` (`{"role": "worker"}`): la siguiente peticion del mismo token del manager a `GET /companies/{cid}/members` -> 403 sin esperar al TTL; membresia desactivada -> 403 inmediato; empresa suspendida (`PUT /companies/{cid}` `{"isActive": false}`) -> 403 inmediato.
- HTTP (Redis caido): `fake_redis.raise_errors = True`: un manager legitimo sigue recibiendo 200 (se lee de BD).
- Unitario backoff: `RedisManager.get` tras una excepcion no vuelve a intentar durante 30 s (`time.monotonic` parcheado).
- PA desde BD (P4): usuario con `users.role=admin` en BD y token con `is_admin: false` en claims se trata como PA; usuario `role=user` con token `is_admin: true` NO es PA.
- Rol desde BD: token con claim `role: "manager"` de un usuario cuya membresia es `worker` -> 403 en endpoints de manager. Token con claim `role: "worker"` de un manager -> sigue siendo manager (el claim se ignora) [P-3].
- Token caducado (`make_token(user, expires_minutes=-1)`) -> `GET /users/me` 401.
- Limites: `GET /work-logs?skip=-1` -> 422; `?limit=0` -> 422; `?limit=5000` -> 200 (todavia sin tope).
- Reescribir contra `client`/`as_user` los tests ya existentes en `tests/routers/` que llaman a handlers directamente (`test_governance.py`, `test_work_logs_supervisor.py`, `test_modules.py`, `test_dashboard_summary.py`): conservar cada escenario (mismo nombre y mismo resultado esperado) y cambiar solo la forma de invocar. Donde el resultado cambie por los puntos (a)-(e), actualizarlo con un comentario `# PR-03: ...`. Los de `test_billing_summary.py` (marcador `postgres`) idem.

**PR-03.1 [backend-dev] Modulo puro** `backend/access_policy.py` (nuevo; PROHIBIDO importar `fastapi` o `sqlalchemy`):
```python
ROLE_PLATFORM_ADMIN = "platform_admin"; ROLE_MANAGER = "manager"; ROLE_WORKER = "worker"
VIEW_AS_ROLES = frozenset({"worker", "manager"})
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
VIEW_AS_WRITE_ALLOWLIST = frozenset({"/auth/switch-scope", "/logout", "/refresh-token"})
MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_FORBIDDEN = "No tienes permisos para esta accion"
MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_SWITCH_COMPANY = "Cambia a esta empresa para gestionarla"
MSG_MANAGED_READONLY = "En empresas gestionadas solo el equipo gestor puede modificar turnos y tarifas"
MSG_VIEW_AS_READONLY = "Modo 'ver como' de solo lectura: sal del modo para modificar datos"

class PolicyError(Exception):
    def __init__(self, status_code: int, detail: str): ...   # atributos status_code, detail

def normalize_member_role(role: str | None) -> str | None   # "admin"|"manager" -> "manager"; "worker" -> "worker"; otro -> None
def assert_view_as_read_only(view_as: str | None, method: str, path: str) -> None
    # si view_as y method no en SAFE_METHODS y path no en VIEW_AS_WRITE_ALLOWLIST -> PolicyError(403, MSG_VIEW_AS_READONLY)

@dataclass(frozen=True)
class CompanyFacts:
    company_id: str; exists: bool; is_active: bool; is_managed: bool
    membership_active: bool; membership_role: str | None     # ya normalizado

def authorize_company(*, is_platform_admin: bool, view_as: str | None = None, token_company_id: str | None,
                      facts: CompanyFacts, min_role: str) -> str
```
`min_role` in `{"worker","manager","platform_admin"}`. Orden exacto (desvio razonado respecto a `logica-negocio-empresa.md` 3.2: se comprueba la membresia ANTES que la suspension para no revelar empresas suspendidas a quien no es miembro, I4):
1. PA: si `not exists` -> `PolicyError(404, "Empresa no encontrada")`. Si `view_as` (rol de vista): `min_role == "platform_admin"` -> 403 `MSG_FORBIDDEN`; rango de `view_as` menor que `min_role` -> 403 `MSG_FORBIDDEN`; `min_role == "manager"` y `token_company_id != company_id` -> 403 `MSG_SWITCH_COMPANY`; devolver `view_as`. Sin `view_as`: devolver `ROLE_PLATFORM_ADMIN` (aunque la empresa este suspendida [P-4]).
2. No PA: `not exists or not membership_active` -> `PolicyError(403, MSG_NO_ACCESS)`.
3. `not is_active` -> `PolicyError(403, MSG_SUSPENDED)`.
4. `min_role == "platform_admin"` -> `PolicyError(403, MSG_FORBIDDEN)`.
5. Rango (`worker`=1, `manager`=2): si el rol de la membresia es menor que `min_role` -> `PolicyError(403, MSG_FORBIDDEN)`.
6. Si `min_role == "manager"` y `token_company_id != company_id` -> `PolicyError(403, MSG_SWITCH_COMPANY)`.
7. Devolver el rol de la membresia.
Mas funciones puras: `require_platform_admin(is_platform_admin: bool) -> None` (403 `MSG_FORBIDDEN`); `can_write_work_log(*, role: str, is_managed: bool, is_owner: bool) -> None` (PA/manager: ok; worker: si `is_managed` -> 403 `MSG_MANAGED_READONLY`; si no es propietario -> 403 `MSG_FORBIDDEN`); `can_edit_member_rates(*, role: str, is_managed: bool, is_self: bool) -> None` (PA/manager: ok; worker: si no `is_self` -> 403 `MSG_FORBIDDEN`; si `is_managed` -> 403 `MSG_MANAGED_READONLY`); `can_edit_member_settings(*, role: str, is_self: bool) -> None` (PA/manager ok; worker solo `is_self`).
- Modelo de "rol real" frente a "rol de vista" [P-3]: el PA siempre es PA en BD (`users.role`); el rol de vista es un claim opcional `view_as` (`"worker"` o `"manager"`) que SOLO se respeta si el usuario es PA, el token tiene `cid` y el valor esta en `VIEW_AS_ROLES`; en cualquier otro caso se ignora. Mientras hay `view_as`, el PA actua con los permisos de ese rol (jerarquia worker < manager < PA) y todo metodo no seguro se rechaza con `MSG_VIEW_AS_READONLY`. No hay suplantacion: la identidad (`sub`) sigue siendo la del PA.

**PR-03.2 [backend-dev] Cache de acceso** `backend/access_cache.py` (nuevo):
```python
ACCESS_CACHE_TTL_SECONDS = 60
def get_access(user_id: str, company_id: str) -> dict | None
def set_access(user_id: str, company_id: str, facts: dict) -> None   # {"company_active": bool, "is_managed": bool, "membership_active": bool, "membership_role": str|None}
def invalidate_membership(user_id, company_id) -> None   # borra "access:{user_id}:{company_id}"
def invalidate_company(company_id) -> None               # redis_manager.delete_pattern(f"access:*:{company_id}")
```
Clave `access:{user_id}:{company_id}`; valor JSON; usa `redis_manager.get/set/delete/delete_pattern`; nunca decide sola: si no hay dato o falla, el llamador lee de BD. No cachear empresas inexistentes.
- `backend/redis_config.py`: anadir backoff: atributo `_down_until: float = 0.0`; en cada `except` de `get/set/delete/delete_pattern`: `self._down_until = time.monotonic() + 30`; al inicio de esos metodos: `if time.monotonic() < self._down_until: return <valor por defecto>`. Importar `time`.

**PR-03.3 [backend-dev] Dependencias** `backend/routers/deps.py` (nuevo):
```python
@dataclass
class AccessContext:
    db: Session; user: models.User; role: str; is_platform_admin: bool; is_managed: bool; company_id: str | None; is_read_only_view: bool
    @property
    def company(self) -> models.Company | None   # carga perezosa de BD

def acting_platform_admin(user) -> bool           # user.is_platform_admin (BD) and not user.view_as
def load_company_facts(db, user, company_id) -> CompanyFacts     # cache -> BD; company_id invalido => exists False
def authorize(db, user, company_id, *, min_role: str = "worker", module: str | None = None) -> AccessContext
def require_company(min_role: str = "worker", module: str | None = None)   # fabrica; usa el path param `company_id: UUID`
def require_platform_admin(user=Depends(auth.get_verified_user)) -> models.User   # 403 si no es PA o si hay view_as
def manages_user(db, actor, target_user_id) -> bool    # sustituye a check_manager_access
def require_active_member(db, user_id, company_id) -> models.CompanyMember   # PolicyError(422, "El usuario no tiene una membresia activa en esta empresa"); se usa en PR-08
def require_module(code_name: str)   # mismo contrato que routers/utils.require_module
```
- `user.is_platform_admin` (real, de BD) se usa solo para informar (`/users/me`); toda decision de permisos usa `acting_platform_admin(user)`.
- `authorize`: construye los argumentos desde `user` (`user.active_company_id` como `token_company_id`, `user.view_as`), llama a `access_policy.authorize_company`, y si `module` esta definido y el rol efectivo no es PA: `crud.user_has_module(db, user_id, company_id, module)` -> si no, `PolicyError(403, f"Tu cuenta no tiene acceso al modulo '{module}'. Contacta con el administrador.")`.
- `manages_user(db, actor, target)`: PA actuando -> True; si no, `actor.active_company_id` no nulo, `authorize(... min_role="manager")` no lanza y el objetivo tiene membresia activa en esa empresa -> True; en otro caso False.
- Registrar en `backend/main.py` (tras crear `app`): `@app.exception_handler(PolicyError)` que devuelve `JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})`.

**PR-03.4 [backend-dev] auth.py** (`get_current_user` y `get_verified_user`; esta ultima pasa a recibir tambien `request: Request`):
- Fijar `user.is_platform_admin = (user.role == models.UserRole.admin)` (ignorar el claim `is_admin`), `user.active_company_id = payload.get("cid")`.
- `user.view_as = payload.get("view_as")` solo si `user.is_platform_admin`, hay `cid` y el valor esta en `VIEW_AS_ROLES`; si no, `None`. Tras fijarlo, `access_policy.assert_view_as_read_only(user.view_as, request.method, request.scope["path"])`.
- `user.active_role`: si PA con `view_as` -> `view_as`; PA sin `view_as` -> `None`; no PA con `cid` -> rol normalizado de la membresia activa (consulta con cache `access_cache`) o `None`. El claim `role` del token se IGNORA siempre.
- Conservar `token_scope` y `admin_user_id`.

**PR-03.5 [backend-dev] Handlers**: sustituir los `if not is_platform_admin and ...` por llamadas a `deps`. Mapeo exacto (mismos permisos que hoy salvo lo indicado; "PA" significa `acting_platform_admin`):
| Endpoint | Politica |
|---|---|
| `GET /companies` | sin cambio de matriz; PA = `acting_platform_admin`; `skip` `ge=0`, `limit` `Query(100, ge=1, le=2000)` (listado de empresas, no de turnos) |
| `POST /companies` | `Depends(deps.require_platform_admin)` |
| `PUT /companies/{company_id}` | `require_company("manager")`; si no es PA y el payload trae `is_active`/`is_managed` -> 403 `MSG_FORBIDDEN` (se conserva) |
| `GET /companies/detailed` | PA: todas; no PA: empresas activas donde es manager con token coherente, o worker con modulo `worker_daily_report` (como hoy); sin ninguna -> 403 `MSG_FORBIDDEN` |
| `GET /companies/{company_id}/members`, `PUT .../members/order`, `GET .../rates-v2`, `GET .../dashboard-summary` | `require_company("manager")` |
| `POST .../members/add`, `PUT .../members/{user_id}/status` | `require_company("manager")` (pasan a PA en PR-05) |
| `GET /companies/{company_id}` | `require_company("worker")` |
| `PUT .../members/{user_id}` | `require_company("worker")`; dentro: si no es manager/PA y `user_id != current_user.id` -> 403 `MSG_FORBIDDEN`; resto de la logica se mantiene hasta PR-05 |
| `GET /users/{user_id}`, `GET /users/{user_id}/companies`, `POST /users/{user_id}/reset-password-email` | PA, o `deps.manages_user(...)` (el ultimo pasa a PA en PR-05) |
| `POST /work-logs`, `POST /work-logs/bulk` | `authorize(db, user, work_log.company_id, min_role="worker")` (bulk: `"manager"`); crear para otro usuario exige rol manager/PA |
| `GET /work-logs` | PA sin restriccion. No PA con `company_id` (parametro o `cid`): `authorize(... "worker")`; manager/PA ven todos y pueden filtrar `user_id`; worker con modulo `worker_daily_report` mantiene la vista de empresa (cambia en PR-14); worker sin modulo solo propios; pedir `user_id` ajeno sin ser manager de esa empresa -> 403. Sin empresa: solo propios y de empresas activas |
| `GET /work-logs/billing-summary` | `authorize(db, user, company_id, min_role="manager")` |
| `DELETE /work-logs/{work_log_id}`, `PUT /work-logs/{work_log_id}` | `work_log_id: UUID`; cargar el turno (404 si no existe); `authorize(db, user, log.company_id, "worker")`; la regla propietario/gestionada de hoy se expresa con `access_policy.can_write_work_log`; si `log.company_id` es `None`: solo PA o propietario |
| `modules.list_subscriptions` | no PA: `authorize(db, user, active_cid, "manager")` (sin `cid` -> 403) |
| `modules.get_my_modules` | `company_id` explicito: `authorize(... "worker")`; si la empresa efectiva esta suspendida: no PA -> solo suscripciones personales; PA -> como PA sin contexto |
| `users`: lista, alta, estado, `PUT /users/{id}`, `reset-2fa`, impersonacion | `require_platform_admin` (rechaza `view_as`) |
- Todos los parametros de path `company_id`, `user_id`, `work_log_id` pasan a tipo `UUID` (422 si es invalido). Adaptar `str(...)` donde `crud` espere cadenas.
- `crud.user_has_module(db, user_id, company_id, code_name)`: ignorar la suscripcion de empresa si `Company.is_active` es falso (item B2 del catalogo); si `company_id` es nulo, igual que hoy.
- `crud.py`: tras cada `commit` de `update_company` (si cambian `is_active`/`is_managed`), `update_company_member`, `update_company_member_status`, `join_company` llamar a `access_cache.invalidate_company(...)` o `invalidate_membership(...)`.
- Eliminar `backend/routers/utils.py` (sustituido por `deps`); `grep -rn "routers.utils\|is_manager_of_company\|check_manager_access" backend` sin resultados.
- I2: sustituir los `print` de depuracion por `logging.getLogger(__name__)` sin datos sensibles (solo ids opacos en WARNING): `routers/companies.py:70,340-343,348`, `crud.py:778,841,848`, `routers/users.py:220`, `routers/auth.py:598`. Los 403 de `update_company_member` pasan a `MSG_FORBIDDEN`.
- Item B4 del catalogo: borrar `crud.get_subscriptions` (sin uso, verificado con grep antes de borrar).
- `GET /users/me` (`routers/users.py:read_users_me`): anadir a `schemas.UserResponse` los campos `view_as: str | None = None` y `is_read_only_view: bool = False`; rellenarlos desde `user.view_as`.
- Verificacion: `ruff check backend/`; pytest completo.

**PR-03.V Version**: PATCH. `### Seguridad`/`### Corregido`: politica central, empresa suspendida bloquea turnos/billing/dashboard/modulos, cache de acceso con invalidacion, modo "ver como" de solo lectura, respuestas 403 sin datos internos.

---

### PR-04 - Token minimo, emision de contexto y "ver como" del PA (S1, S4, S6)

- Rama: `fix/token-minimo-y-cambio-de-empresa`. Depende de: PR-03. Reviewers: `code-reviewer`, `security-reviewer`. Version: PATCH.
- Objetivo: el JWT solo lleva `sub`, `cid`, `scope`, `exp` (mas los tecnicos `iat`, `type`, `jti`; `admin_user_id` solo en tokens `impersonated`; `view_as` solo en tokens de PA en modo "ver como"); `cid` nunca apunta a una empresa suspendida o sin membresia activa para worker/manager; `switch-scope` no acepta rol del cliente.

**PR-04.0 [tester]** `backend/tests/routers/test_token_scope.py`:
1. `test_access_token_claims_are_minimal`: login de un manager; decodificar con `auth.jwt.decode(token, auth.PUBLIC_KEY, algorithms=["RS256"])`; el conjunto de claves es exactamente `{"sub","cid","scope","exp","iat","type","jti"}` (sin `role` ni `is_admin` ni `view_as`). Un PA sin empresa: no hay clave `cid`.
2. `test_switch_scope_ignores_client_role`: worker hace `POST /auth/switch-scope` `{"companyId": A, "companyRole": "manager"}` -> 200, y `GET /users/me` da `activeRole == "worker"`; un manager con `companyRole: "worker"` sigue como `manager` [P-3].
3. `test_switch_scope_requires_active_membership`: sin membresia o membresia inactiva -> 403 `No tienes acceso a esta empresa`; empresa suspendida (worker/manager) -> 403 `Empresa inactiva o suspendida`; empresa inexistente -> 403 `No tienes acceso a esta empresa`.
4. `test_switch_scope_platform_admin`: PA sin `companyId` -> token sin `cid`; PA a empresa activa -> `cid` presente, `activeRole` es `null` y no hay `view_as`; PA a empresa SUSPENDIDA -> 200 con `cid` [P-4]; PA a empresa inexistente -> 404.
5. `test_switch_scope_view_as`: PA con `{"companyId": A, "viewAs": "worker"}` -> token con claim `view_as == "worker"` y `cid`; `GET /users/me` da `activeRole == "worker"`, `viewAs == "worker"`, `isReadOnlyView == true`; `viewAs` invalido (`"admin"`) -> 422; `viewAs` sin `companyId` -> 422; no-PA con `viewAs` -> 403 `Solo el administrador de la plataforma puede usar 'ver como'`; volver a `POST /auth/switch-scope` con `{"companyId": A}` quita el modo; con el token `view_as`, `POST /work-logs` -> 403 solo lectura; `POST /refresh-token` no conserva `view_as`.
6. `test_login_company_selection` (la ultima empresa activa la elige el cliente; el servidor no la guarda, ver PR-05.D): login no PA con `company_id` (campo opcional del formulario) de una membresia activa de empresa activa -> `cid` = esa; con `company_id` de empresa sin membresia, con membresia inactiva, inexistente o suspendida -> se ignora y `cid` = la primera membresia activa de empresa activa por `company_members.sort_order` ascendente (desempate `joined_at`); sin `company_id` -> igual fallback; fallback que salta empresas suspendidas; usuario solo con empresas suspendidas -> token sin `cid`; sin membresias -> token sin `cid` y `GET /users/me` 200; PA con o sin `company_id` -> token sin `cid` (contexto neutro). El `company_id` del cliente es solo una sugerencia: si no es membresia activa del usuario (por ejemplo, otro usuario entra en el mismo navegador y el `localStorage` conserva la empresa del anterior) el backend lo ignora y aplica el fallback.
6b. `test_verify_2fa_company_selection` (usuario con `is_2fa_enabled`; el token provisional solo lleva `sub` y `scope`, no `company_id`): `POST /auth/verify-2fa` con `{"code": <valido>, "companyId": <membresia activa>}` -> `cid` = esa; `companyId` sin membresia / inactiva / inexistente / suspendida -> se ignora y `cid` = primera por `sort_order`; sin `companyId` -> igual fallback; usuario sin membresias -> token sin `cid`; PA con `companyId` -> token sin `cid`; `companyId` mal formado (no UUID) -> 422; codigo invalido o token que no es `2fa_pending` -> 400/403 como hoy; el login con 2FA no envia `cid` en ningun caso.
7. `test_refresh_applies_same_rules`: igual que 6 para `POST /refresh-token`.
8. `test_cid_never_without_role`: para toda la matriz anterior, `GET /users/me` devuelve `activeCompanyId` nulo o `activeRole` no nulo para worker/manager.
9. `test_impersonation_token`: `POST /admin/impersonate/{id}` como PA -> token con `scope == "impersonated"`, `admin_user_id` presente y `exp` a unos 10 min; el rol sale de BD.
10. Actualizar `tests/routers/test_auth_dev_bypass.py` (`payload.get("is_admin")` ya no existe): comprobar `GET /users/me` con `isPlatformAdmin == True`.

**PR-04.1 [backend-dev]**
- `backend/auth.py`: nueva firma `generate_user_tokens(db, user, company_id: str | None = None, scope: str | None = None, force_none: bool = False, view_as: str | None = None) -> tuple[str, str]` (sin parametro `role`). Datos del token: `{"sub": str(user.id), "scope": scope or "full"}`; `cid` solo si no es `None`; `view_as` solo si el usuario es PA, hay `cid` y `view_as in VIEW_AS_ROLES`. Anadir `resolve_active_company(db, user, requested_company_id: str | None, *, force_none: bool = False) -> str | None`:
  - PA: devuelve `requested_company_id` si no es `force_none`, si no `None` (la existencia la valida `switch-scope`; NO se filtra por empresa suspendida [P-4]).
  - No PA: orden de candidatos: `requested_company_id` y, despues, las membresias activas por `company_members.sort_order` ascendente (desempate `joined_at`); devuelve el primero cuya membresia este activa Y cuya empresa este activa; si ninguno, `None`. No se lee `user.default_company_id` (el campo se retira en PR-05.D). La validacion de membresia ocurre siempre en el servidor: el `company_id` que envia el cliente (leido de su `localStorage`) es solo una sugerencia y nunca concede acceso.
- `get_current_user`/`get_verified_user` ya ignoran `role` e `is_admin` desde PR-03; aqui se elimina de `schemas.TokenData` los campos `company_role` y `is_platform_admin` si ya nadie los usa (`ruff` y `grep` lo confirman); `members/add` sigue usando `TokenData` para `email` hasta PR-05.
- `backend/schemas.py`: nuevo `class SwitchScopeRequest(CamelModel): company_id: UUID | None = None; view_as: Literal["worker", "manager"] | None = None` (campos extra como `companyRole` se ignoran).
- `backend/routers/auth.py` `switch_scope`: body `SwitchScopeRequest`. No PA: `view_as` presente -> 403 `Solo el administrador de la plataforma puede usar 'ver como'`; sin `company_id` -> 400 `company_id is required`; empresa inexistente o sin membresia activa -> 403 `MSG_NO_ACCESS`; empresa suspendida -> 403 `MSG_SUSPENDED`. PA: sin `company_id` (y sin `view_as`) -> `generate_user_tokens(..., force_none=True)`; `view_as` sin `company_id` -> 422; con `company_id`: inexistente -> 404 `Empresa no encontrada`; suspendida -> permitido [P-4]. `login_for_access_token` (hoy `auth.py:254` usa `default_company_id` como `cid` por defecto) (`POST /auth/token`, `OAuth2PasswordRequestForm`) acepta un campo de formulario opcional `company_id` y llama a `resolve_active_company(db, user, company_id)`; si el usuario es PA fuerza `force_none=True` (contexto neutro, el `company_id` se ignora). Con 2FA activo, el login devuelve el token provisional (`{"sub", "scope": "2fa_pending"}`, 5 minutos, `routers/auth.py` ~110-128) y NO conserva `company_id`: el cliente lo reenvia en el segundo paso. `POST /auth/verify-2fa`: `schemas.Verify2FA(CamelModel)` pasa de `{code}` a `{code: str; company_id: UUID | None = None}` (JSON `{code, companyId?}`); tras validar el TOTP y poner en lista negra el token provisional, `verify_2fa` llama a `auth.generate_user_tokens(db, current_user, company_id=...)` con la misma regla del login (`resolve_active_company`: membresia activa de empresa activa, si no primera por `sort_order`, sin membresias token sin `cid`, PA con `force_none=True`). Los demas llamadores de `generate_user_tokens` (`login_for_access_token`, `verify_2fa`, `refresh_access_token`, `dev_bypass_login`, `impersonate_user`) usan la nueva firma. `impersonate_user` sigue anadiendo `scope`, `admin_user_id` y `exp` de 10 min.

**PR-04.2 [frontend-dev]** (paralelo; contrato: `POST /auth/switch-scope` body `{companyId: string | null, viewAs?: 'manager' | 'worker'}`; `GET /users/me` devuelve ademas `viewAs` e `isReadOnlyView`):
- `frontend/src/lib/types.ts` (`UserProfile`): anadir `viewAs?: 'manager' | 'worker' | null` e `isReadOnlyView?: boolean`.
- `frontend/src/context/AuthContext.tsx`: `switchScope(companyId: string | null, viewAs?: 'manager' | 'worker')` (quitar el parametro `role`); `api.post('/auth/switch-scope', { companyId, viewAs })`; tras `fetchUser()` decidir destino con el usuario devuelto: sin `companyId` -> `/admin/companies`; `userData.activeRole === 'manager'` -> `/manager/dashboard?companyId=...`; si no -> `/dashboard?companyId=...` (el `?companyId=` desaparece en PR-19). Para un PA con `companyId` y sin `viewAs` -> `/admin/companies/{companyId}`. Actualizar `AuthContextType.switchScope`.
- `frontend/src/components/auth/scope-selection-dialog.tsx` (lineas 83-134): para worker/manager, un unico boton "Entrar" que llama `switchScope(company.id)` y muestra el rol de la membresia como texto (eliminar `canBeManager` y el boton de rol). Para el PA, tres botones por empresa: "Gestionar" (`switchScope(id)`), "Ver como manager" (`switchScope(id, 'manager')`) y "Ver como worker" (`switchScope(id, 'worker')`), con el texto "Solo lectura" en los dos ultimos.
- `frontend/src/components/company-switcher.tsx`: adaptar la llamada a `switchScope`.
- Ultima empresa activa en el navegador: nuevo `frontend/src/lib/last-company.ts` con `getLastCompanyId(key)` / `setLastCompanyId(key, companyId)` sobre `localStorage`, siempre dentro de `try/catch` (puede lanzar o estar vacio en ventana privada o con datos bloqueados; entonces se omite sin error). UNA clave unica `lastCompanyId` cuyo valor es el id de la empresa; la clave no lleva email ni `userId` (no se guardan datos personales en claves). Si otro usuario entra en ese navegador, el backend valida la membresia al emitir el token y, si el valor no es membresia activa de ese usuario, lo ignora y aplica el fallback por `sort_order`, por lo que no hay riesgo de acceso. `AuthContext.login` lee la clave y envia `company_id` en el formulario de `POST /auth/token`; si la respuesta es `requires_2fa`, el paso de verificacion reenvia el mismo valor como `companyId` en el cuerpo de `POST /auth/verify-2fa` (`lib/api` / `AuthContext.verify2FA` (`frontend/src/context/AuthContext.tsx`, firma actual `verify2FA(code)`; se amplia con `companyId` opcional y el login lo pasa desde `login/page.tsx`)); tras `fetchUser()` y en cada `switchScope` con `companyId` exitoso guarda `user.activeCompanyId`. Un PA no envia ni guarda empresa. Tests vitest en `AuthContext.test.tsx`: el login envia `company_id` guardado; sin valor no envia; un `localStorage` que lanza no rompe el login; `switchScope` guarda la clave; con `requires_2fa` el paso 2FA envia `companyId` guardado y, sin valor, no lo envia.
- Tests vitest en `frontend/src/__tests__/context/AuthContext.test.tsx`: `switchScope(id)` envia `{companyId}` sin `companyRole`; `switchScope(id, 'worker')` envia `viewAs`. Nuevo `__tests__/components/scope-selection-dialog.test.tsx`: el PA ve los tres botones, un manager ve uno.
- Verificacion: `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build`.

**PR-04.V Version**: PATCH.

---

### PR-05 - Membresias solo plataforma y endpoints de miembro

- Rama: `feat/membresias-solo-plataforma`. Items: P2 (membresia), P6, P3 (parte miembros), M1, M2 y M3 (ambos obsoletos: se retira `default_company_id`, PR-05.D), M4, M6, M9, A1 (eventos de membresia), U2 (parte miembros). Depende de: PR-02, PR-04. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR (cambio incompatible en 0.y.z) [P-1].
- Precondiciones de datos: P1/S1 (membresias `admin`) (seccion 7). M3 ya no es precondicion: `default_company_id` se elimina (Q-10 cerrada, PR-05.D) y los 2 usuarios de produccion con valor obsoleto caen en el fallback del login de PR-04. Si la consulta de membresias `admin` devuelve filas, avisar al usuario: se tratan como `manager` en la politica pero no se migran.
- Migracion: SI, solo la de PR-05.D (`b7e1a0d10007`, borra `users.default_company_id`; `down_revision` = head vigente). Procedimiento de la seccion 10 (sin script de reparacion: no hay datos que reparar). Un solo PR con codigo y migracion: durante la ventana de `migrate` el contenedor de la release anterior puede fallar alguna peticion (aceptado, seccion 10.3).

**PR-05.0 [tester]** `backend/tests/routers/test_members.py` (cada caso falla antes del arreglo):
- Matriz (Q1): manager recibe 403 en `POST /companies/{id}/members/add`, `PUT .../members/{uid}/status`, `PUT .../members/{uid}/role`, `DELETE .../members/{uid}`, `POST /users/{uid}/reset-password-email`; worker 403 en todos; PA 200.
- `members/add`: usuario nuevo en la empresa -> membresia `worker` activa y evento `member.added`; membresia inactiva con rol `manager` -> al reactivar vuelve como `worker` (M6) y evento `member.reactivated` con `old_value {"is_active": false, "role": "manager"}` y `new_value {"is_active": true, "role": "worker"}`; membresia ya activa -> 200 sin cambios ni evento; email inexistente -> 404; email mal formado -> 422.
- `status`: valores validos `active`/`inactive` (y los heredados `approved`, `true`, `1`/`rejected`, `false`, `0`); otro valor -> 422; desactivar no reasigna nada (no existe `default_company_id`; el siguiente login cae en el fallback por `sort_order`); reactivar fuerza rol `worker` (M6).
- `role`: PA cambia `worker` a `manager` -> 200 y evento `member.role_changed`; valor `admin` -> 422; membresia inexistente -> 404; el cambio es efectivo en la siguiente peticion del afectado (cache invalidada).
- `DELETE members/{uid}`: sin turnos -> 200 `{"deleted": true, "deactivated": false, "reason": null}`, fila borrada, evento `member.removed`; con turnos -> 200 `{"deleted": false, "deactivated": true, "reason": "has_work_logs"}`, membresia `is_active=False` y turnos conservados, evento `member.deactivated`.
- `rates`: manager edita tarifas de otro y propias en gestionada y autonoma (200); worker edita las suyas en autonoma (200) y en gestionada 403 `MSG_MANAGED_READONLY`; worker edita las de otro 403; evento `member.rates_changed` con `old_value`/`new_value` = `rates_config` anterior/nuevo; `base_rate` negativo -> 422.
- `settings`: worker edita sus propios `settings` en gestionada y autonoma (200); ajenos 403; manager y PA 200.
- Modo "ver como": el PA en `view_as` recibe 403 en todos los endpoints de esta lista (solo lectura).
- `PUT /companies/{cid}/members/{uid}` (ruta antigua) ya no existe: 405 o 404.
- M3 (obsoleto): `PUT /users/me` y `PUT /users/{id}` con `defaultCompanyId` ya no lo guardan (campo desconocido ignorado, 200); `GET /users/me` no devuelve `defaultCompanyId`; `models.User` no tiene la columna (test `postgres` de la migracion: `upgrade` la borra y `downgrade` la recrea nula).
- M4: `PUT /users/me` con cualquier campo editable que no sea el nombre NO borra `first_name`/`last_name`; con `{"firstName": null}` los nombres se conservan.
- M9: PA `PUT /users/{su-id}/status?is_active=false` -> 403 `No puedes desactivar tu propia cuenta`; PA se degrada a si mismo (`PUT /users/{su-id}` `{"role": "user"}`) -> 403; con helper que simule un unico PA activo y un actor distinto, desactivar o degradar a ese PA -> 409 `La plataforma no puede quedarse sin administradores`; con dos PA, desactivar al otro -> 200; `role` invalido (`"superuser"`) -> 422.
- `GET /companies/{cid}/members?status=active|inactive` filtra; otro valor -> 422.
- Trazas: los eventos tienen `actor_user_id` = PA, `company_id`, `target_user_id`.

**PR-05.1 [backend-dev] Esquemas** (`backend/schemas.py`, todos `CamelModel`):
```python
class AddMemberRequest(CamelModel):  email: EmailStr
class MemberRoleUpdate(CamelModel):  role: Literal["worker", "manager"]
class MemberRatesUpdate(CamelModel): rates_config: dict[str, dict[str, Any]]   # PR-11 lo sustituye por RatesConfig; validador: cada base_rate presente debe ser numero >= 0
class MemberSettingsUpdate(CamelModel): settings: dict[str, Any]
class MemberDeleteResponse(CamelModel): deleted: bool; deactivated: bool; reason: str | None = None
```
Eliminar `CompanyMemberUpdate` y reemplazar `schemas.TokenData` en `members/add` por `AddMemberRequest`.

**PR-05.2 [backend-dev] Endpoints** (`backend/routers/companies.py`; todos con `company_id: UUID`, `user_id: UUID`):
| Metodo y ruta | Politica | Respuesta |
|---|---|---|
| `POST /companies/{company_id}/members/add` | `Depends(deps.require_platform_admin)`; la empresa debe existir (404 `Empresa no encontrada`) | `CompanyMemberResponse` (200) |
| `PUT /companies/{company_id}/members/{user_id}/status?status=` | PA | `CompanyMemberResponse` |
| `PUT /companies/{company_id}/members/{user_id}/role` body `MemberRoleUpdate` | PA | `CompanyMemberResponse` |
| `DELETE /companies/{company_id}/members/{user_id}` | PA | `MemberDeleteResponse` |
| `PUT /companies/{company_id}/members/{user_id}/rates` body `MemberRatesUpdate` | `require_company("worker")` + `access_policy.can_edit_member_rates(role, is_managed, is_self)`; PA/manager cualquier miembro | `CompanyMemberResponse` |
| `PUT /companies/{company_id}/members/{user_id}/settings` body `MemberSettingsUpdate` | `require_company("worker")` + `can_edit_member_settings` | `CompanyMemberResponse` |
| `PUT /companies/{company_id}/members/order` | `require_company("manager")` (sin cambio) | sin cambio |
| `GET /companies/{company_id}/members?status=` | `require_company("manager")`; `status` `Literal["active","inactive"] | None`; el handler traduce a `bool` | lista |
- Eliminar el handler `update_company_member` (`PUT /companies/{company_id}/members/{user_id}`) y `crud.update_company_member`; su logica se reparte en `crud.set_member_rates`, `crud.set_member_settings`, `crud.set_member_role`. Rol y `is_active` ya no viajan en payloads de tarifas/ajustes.
- `crud.py` (firmas): `add_member(db, company_id, user_id, *, actor_id) -> CompanyMember` (crea `worker`, o reactiva forzando `worker`; `record_audit` `member.added`/`member.reactivated` ANTES del `commit`); `set_member_status(db, company_id, user_id, is_active: bool, *, actor_id) -> CompanyMember | None` (si pasa a activo fuerza `worker`; si pasa a inactivo no reasigna nada); `set_member_role(db, company_id, user_id, role: str, *, actor_id)`; `set_member_rates(db, company_id, user_id, rates_config: dict, *, actor_id)`; `set_member_settings(db, company_id, user_id, settings: dict)`; `remove_member(db, company_id, user_id, *, actor_id) -> dict`; se eliminan las dos copias actuales de la reasignacion de `default_company_id` (`crud.py:731-742` y `:784-797`); todas invalidan `_invalidate_company_rates` y `access_cache.invalidate_membership`.
- Eventos (`audit.AuditAction`): `member.added`, `member.reactivated`, `member.deactivated`, `member.removed`, `member.role_changed`, `member.rates_changed`, con `company_id` y `target_user_id`.
- `routers/users.py`: `reset_password_via_email` -> `Depends(deps.require_platform_admin)`. `PUT /users/me` (M4): `data = user.model_dump(exclude_unset=True)`; descartar `first_name`/`last_name` si son `None`. M3 queda obsoleto: ya no hay `default_company_id` que validar (PR-05.D). M9: antes de `toggle_user_status` y `update_user`, `crud.ensure_platform_admin_invariants(db, actor, target, *, new_role: str | None, new_is_active: bool | None)`: el actor no puede desactivarse (403 `No puedes desactivar tu propia cuenta`) ni degradarse (403 `No puedes cambiar tu propio rol de plataforma`); si el cambio dejase 0 PA activos -> 409 `La plataforma no puede quedarse sin administradores` (`crud.count_active_platform_admins(db) -> int`); `role` solo `admin|user` (422 en otro caso).
- M8 (Confirmar): `crud.create_user`: quitar el bloque de auto-union a la empresa "Personal" (lineas 64-77) SOLO si la comprobacion de datos M8 (seccion 7, informativa) muestra que no existe esa empresa; si existe con usuarios, dejar el bloque y anotar el motivo en el PR. El ejecutor pregunta al usuario el resultado antes de decidir.

**PR-05.3 [frontend-dev]** (paralelo; contrato fijado arriba):
- Crear `frontend/src/hooks/use-permissions.ts`:
```ts
export function usePermissions(company?: CompanyResponse | null): {
  isPlatformAdmin: boolean;
  isReadOnlyView: boolean;             // user.isReadOnlyView: el PA en "ver como"
  role: 'platform_admin' | 'manager' | 'worker' | null;
  isManaged: boolean;
  canCreateWorkLog: boolean;
  canEditWorkLog: (log: { userId: string }) => boolean;
  canManageMembers: boolean;            // solo PA
  canEditCompany: boolean;              // solo PA
  canEditRates: (targetUserId: string) => boolean;   // PA|manager, o el propio en autonoma
}
```
  Fuente: `useAuth()` (`user.role === 'admin' || user.isPlatformAdmin`, `user.activeRole`, `user.id`, `user.isReadOnlyView`) y la empresa activa de `useQuery(['myCompanies'], getMyCompanies)` cuando no se pasa `company`. Si `isReadOnlyView` es `true`, TODOS los `can*` devuelven `false`.
- `frontend/src/lib/api/companies.ts`: eliminar `updateCompanyMember`; anadir `updateMemberRole(companyId, userId, role: 'worker'|'manager')` (`PUT .../role`), `updateMemberRates(companyId, userId, ratesConfig)` (`PUT .../rates`, body `{ratesConfig}`), `updateMemberSettings(companyId, userId, settings)` (`PUT .../settings`, body `{settings}`), `removeCompanyMember(companyId, userId)` (`DELETE`). `lib/api/settings.ts:updateUserRates` pasa a llamar a `updateMemberRates` (y `updateMemberSettings` si `existingSettings`).
- Migrar los llamadores de `updateCompanyMember` (verificados): `admin/companies/[companyId]/page.tsx:65` (rol -> `updateMemberRole`), `admin/users/[userId]/page.tsx:133,403` (tarifas -> `updateMemberRates`), `manager/users/[userId]/page.tsx:133` (tarifas), `components/admin/user-rates-edit-dialog.tsx:114` (tarifas), `components/admin/member-settings-dialog.tsx:56` (ajustes -> `updateMemberSettings`). No cambiar el contenido de `member-settings-dialog.tsx` (zona O10).
- U2 (miembros): ocultar a no-PA, usando `usePermissions`: en `manager/users/page.tsx` el interruptor de estado de membresia (`updateMemberStatus`, linea 90) y cualquier selector de rol; `AddMemberDialog` y el boton de reset de contrasena (`components/admin/user-edit-dialog.tsx:178`) solo para PA. El manager conserva reordenar (`updateCompanyMembersOrder`) y editar tarifas de su equipo.
- Tests vitest: `__tests__/lib/api/companies.test.ts` (nuevas funciones: ruta, metodo y body); `__tests__/hooks/use-permissions.test.tsx` (PA, manager, worker en autonoma, worker en gestionada, PA en solo lectura: todos los `can*` en `false`).
- Verificacion: lint, `tsc`, `npm test`, `npm run build`.

**PR-05.D [backend-dev + frontend-dev] Retirada de `users.default_company_id`** (Q-10 cerrada; el login ya no lo usa desde PR-04). Primero el codigo deja de leer y escribir la columna y despues la migracion la borra, en el mismo PR (ventana aceptada, seccion 10.3):
- Backend v1: `models.py:55,67` (columna y relacion); `crud.py:74` (alta de usuario: ya no fija la empresa Personal como default; el auto-join M8 se decide aparte); `crud.py:731-742` y `:784-797` (reasignacion al desactivar o borrar membresia); `routers/users.py:144`; `seed.py:76` y `dev_seed.py:60,78` (dejan de rellenarlo); `schemas.py:106,119,125` (se quita de los esquemas de usuario y de `/users/me`; `PUT /users/me` ya no lo acepta); `auth.py:254` (ya resuelto en PR-04). E4 (`DELETE /companies/{id}`, PR-06): el recuento de dependencias deja de incluir "usuarios con `default_company_id`" (PR-06 se escribe sin esa comprobacion; si PR-06 ya estuviera hecho, se quita aqui).
- Backend v2: `backend/src/domain/entities/user.py:26`, `mappers/user_mapper.py:25,41` y `repositories/company_repository.py:43` (`count_dependencies`, clave `default_company_users`) dejan de usarlo; PR-16 parte de esa base.
- Frontend: `manager/settings/page.tsx:14`, `reports/page.tsx:78,89`, `work-log-form.tsx:33-72`, `user-dialog.tsx:85-94,253`, `work-logs-table.tsx:22`, `lib/types.ts:19`; `notifications-section.tsx:14` (se elimina el aviso "no hay empresa por defecto") y `profile/page.tsx:53,112,142,201,289,348` (se elimina el selector de empresa por defecto). Los usos de empresa preferida pasan a la empresa activa del token (`user.activeCompanyId`). Tests vitest: el perfil no muestra selector de empresa por defecto; `notifications-section` no muestra el aviso; `tsc` sin referencias a `defaultCompanyId` (`grep -rn "defaultCompanyId\|default_company_id" backend frontend/src` solo debe devolver la migracion baseline y la nueva).
- Migracion `backend/migrations/versions/b7e1a0d10007_drop_users_default_company_id.py` (`down_revision` = head vigente): `upgrade`: `op.drop_column("users", "default_company_id")` (borra tambien su FK); `downgrade`: la recrea nullable con FK a `companies.id` y SIN datos (el rollback correcto con datos es restaurar el backup; en produccion los 2 valores existentes son obsoletos).
- Tests de comportamiento: los de PR-04.0 punto 6 (login con empresa valida, invalida, sin membresias, PA y fallback por `sort_order`); seeds: `seed.py`/`dev_seed.py` crean usuarios sin la columna y el login de cada uno elige una empresa.

**PR-05.4 [tester]** Ejecutar todo (backend en contenedor, `ruff check backend/`, comandos de frontend).

**PR-05.V Version**: MINOR. CHANGELOG: endpoints nuevos (`role`, `rates`, `settings`, `DELETE`), ruta antigua eliminada, membresias solo PA, `default_company_id` eliminado (`### Cambios Internos`: migracion `b7e1a0d10007`).

**PR-05 - Seguimientos anotados tras la revision (fuera de alcance de PR-05, decididos con el usuario)**:
- M1 (seguridad): `MemberSettingsUpdate.settings` es `dict[str, Any]` sin lista blanca. En `crud.get_user_companies` el `settings` efectivo es `company.settings` actualizado con `member.settings`, asi que un worker puede escribir en su membresia claves de nivel empresa. Se cierra en PR-11 (ver PR-11.1).
- M2 (seguridad): `MemberRatesUpdate` solo valida `base_rate >= 0`, sin limite de tamano ni profundidad ni validacion de los demas campos numericos. Lo sustituye `RatesConfig` en PR-11, con el limite de tamano (ver PR-11.1).
- Pruebas con Postgres real: (a) carrera M9: `crud.count_active_platform_admins` toma `FOR UPDATE`, pero los tests usan SQLite, que lo ignora; falta un test `postgres` con `TEST_DATABASE_URL` que lance dos desactivaciones en paralelo y compruebe que no quedan 0 PA; (b) carrera en `crud.remove_member`: el bloqueo de la membresia no impide que un turno nuevo entre entre la comprobacion de `WorkLog` y el borrado (`work_logs` no tiene FK a `company_members`); decidir si se cierra con un bloqueo en la creacion de turnos (PR-08) o se acepta; (c) test `postgres` de la migracion `b7e1a0d10007` con Alembic (`upgrade`/`downgrade`): hoy se probo a mano y el repo no tiene ningun test `postgres` que ejecute Alembic. Propuesta: crear ese arnes (Alembic sobre `TEST_DATABASE_URL`) en el primer bloque posterior que migre (PR-06) y reutilizarlo en los siguientes.
- Carrera de `crud.remove_member` (decision de PR-08, aceptada por el usuario: se hace en PR-06 junto al arnes `postgres`): NO se cierra en PR-08. Cerrarla exige `SELECT ... FOR UPDATE` sobre la membresia en `crud.create_work_log` y `create_work_log_bulk` (en bulk, en orden determinista de `user_id` para evitar interbloqueos) y un test `postgres` con dos transacciones en paralelo; SQLite ignora el bloqueo y no hay hoy arnes de concurrencia. Efecto de la carrera: un turno nuevo creado en la ventana de milisegundos entre la comprobacion de `WorkLog` y el borrado de la membresia deja un turno de un usuario sin membresia (caso ya tolerado por T1/M5: los turnos antiguos no se tocan). Propuesta: hacerlo junto al arnes `postgres` de PR-06.
- Limpieza menor: `NotificationsSection` queda como componente vacio y `dashboard/page.tsx` lo sigue importando; eliminarlo junto a su uso en el siguiente bloque que toque el dashboard (PR-12).
- Trazabilidad A1: `POST /users` (`routers/users.py`, `create_user_admin`) une al usuario a la empresa con `crud.join_company`, que no emite `member.added`. Hacer que `join_company` registre `member.added` con `actor_id` (o que `create_user_admin` use `add_member`). Propuesta: PR-06 (siguiente bloque que toca membresias y usuarios), con un test que compruebe el evento.
- Tarifas y ajustes en dos peticiones: `frontend/src/lib/api/settings.ts:updateUserRates` hace `PUT rates` y luego `PUT settings` reenviando `existingSettings`. El reenvio ya no hace falta (el endpoint de tarifas no toca `settings`), puede pisar un cambio concurrente de ajustes y un fallo del segundo `PUT` deja el estado a medias. Separar las dos operaciones en los llamadores y dejar `updateUserRates` solo con tarifas. Propuesta: PR-11 (contratos de `settings` y tarifas, PR-11.2).
- M8 resuelto: sin empresas "Personal" en produccion (confirmado por el usuario); el auto-join de `crud.create_user` se retiro en PR-05.

---

### PR-06 - Gestion de empresa solo plataforma

- Rama: `feat/gestion-empresa-solo-plataforma`. Items: P2 (empresa), P3 (empresa), E1, E2 (retirar referencias), E4, E5, E6, E7 (solo documentacion), E8, A1 (eventos de empresa), U2/U3/U5/U9/U11 (parte). Depende de: PR-02, PR-05. Reviewers: `code-reviewer`, `security-reviewer`, `database-reviewer` (migracion E1 y script de reparacion). Version: MINOR.
- Precondiciones de datos: E1 (nombres vacios, solo espacios, con espacios sobrantes o de mas de 120 caracteres): se arreglan con `backend/scripts/repair_company_names.py` (subtarea PR-06.R, seccion 9) y la migracion aborta con `RuntimeError` si quedan. E2 (empresas con `fiscal_id` real): solo informativa en este bloque (la columna se conserva hasta PR-23). **E7 (empresas sin manager) NO es una precondicion ni un bloqueo**: una empresa sin manager no es un problema (`logica-negocio-empresa.md` 4.3: el PA anade un manager o cambia el rol de un worker; no hay guardia de ultimo manager). Su consulta (seccion 7) es solo informativa para documentar el procedimiento de recuperacion.
- Migracion: SI (`b7e1a0d10002`, longitud de `companies.name`). **Paso previo de despliegue obligatorio: seccion 10**, incluido el script `repair_company_names.py` en `--dry-run` y despues `--apply`.

**PR-06.0 [tester]** `backend/tests/routers/test_company_admin.py`:
- Matriz: `GET /companies` -> 403 para manager y worker, 200 PA; `POST /companies` y `PUT /companies/{id}` -> 403 para manager (incluido cambiar `name`, `taxConfig`, `worklogDefinitions`, `settings`); 200 PA; PA en `view_as` -> 403.
- E1: `POST /companies` con `name` `null`, `""`, `"   "`, > 120 caracteres -> 422; `" Nueva  "` se guarda como `"Nueva"`; `PUT` con `name: null` -> 422 (no 500).
- E4: `DELETE /companies/{id}` como PA de empresa sin nada asociado -> 204 y evento `company.deleted` con `old_value` {name,is_active,is_managed}; con miembros/turnos/suscripciones -> 409 con `detail` que enumera los motivos (`"No se puede borrar la empresa: tiene 2 miembros, 10 turnos"`), sin cascadas, empresa intacta; manager -> 403.
- E5: `PUT /companies/{id}` `{"isActive": false, "reason": "Impago"}` -> evento `company.suspended` con `actor_user_id`, `reason`; reactivar -> `company.reactivated`.
- E6: cambio `isManaged` solo PA, evento `company.managed_changed` con `old_value {"is_managed": false}` / `new_value {"is_managed": true}`, y no se recalcula ningun turno existente.
- Otros eventos: `taxConfig` -> `company.tax_config_changed`; `settings` -> `company.settings_changed`; `worklogDefinitions` -> `company.worklog_definitions_changed`; `name` -> `company.updated`; alta -> `company.created`.
- E8 [P-6]: `PUT` con `{}` -> 422 `No hay cambios que guardar`; con valores iguales a los actuales -> 422 igual; no se crea ninguna fila de auditoria.
- P3: `crud.update_company(db, company_id, data, actor=<no PA>)` lanza `PolicyError(403)`; `crud.get_company_for_actor(db, id, actor=<manager de otra empresa>)` -> `None`.
- E2: ninguna respuesta de empresa (`GET /companies`, `/companies/{id}`, `/users/me/companies`, `/companies/detailed`) contiene `fiscalId`; `POST` con `fiscalId` se ignora.
- Cache: tras `PUT isActive false`, un manager con token vigente recibe 403 en su siguiente peticion.
- `GET /users/me/companies` para PA incluye `isActive` e `isManaged` (hoy los omite).
- E7: una empresa SIN ningun manager es un estado valido: `GET /companies/{id}` como PA funciona, el PA puede anadir un manager (`members/add` + `role`) y no existe ninguna comprobacion de "ultimo manager" (desactivar o degradar al unico manager responde 200).

**PR-06.R [backend-dev] Script de reparacion de nombres de empresa** (antes de la migracion; detalle y reglas en la seccion 9):
- Crear `backend/scripts/__init__.py`, `backend/scripts/repair_common.py` (comun a todos los scripts, definido en la seccion 9) y `backend/scripts/repair_company_names.py`.
- Reglas fijadas por el usuario: nombre nulo o vacio (o solo espacios) -> `"Empresa " + str(id)[:8]`; espacios sobrantes al inicio/fin -> `strip()` (el mismo arreglo que hara la migracion; es determinista); nombre de mas de 120 caracteres (tras el `strip`) -> se recorta a los 120 primeros y el nombre ORIGINAL completo se guarda en un fichero de backup (`name_backup`, JSON) antes de escribir. Nada queda para decision manual en este script (todas las reglas son deterministas); el codigo de salida es `0` si no hay nada pendiente.
- Firma: `def run(db: Session, *, apply: bool, backup_dir: Path | None) -> RepairReport` y `def main(argv: list[str] | None = None) -> int`. Idempotente: una segunda ejecucion con `--apply` no cambia nada.
- Tests (`backend/tests/scripts/test_repair_company_names.py`, SQLite; la columna `name` es NOT NULL en el modelo, asi que el caso "nulo" se prueba con la cadena vacia y con una cadena de solo espacios): (1) `--dry-run` (por defecto) no escribe en BD ni en disco y lista los cambios; (2) `--apply` rellena `"Empresa " + id[:8]` en vacio y solo espacios; (3) `--apply` recorta a 120 y el fichero de backup contiene `{company_id, original_name}` del nombre original completo, fuera del repo; (4) `--apply` sin `--backup-dir` y con recortes pendientes -> error y no escribe nada; (5) segunda ejecucion sin cambios (idempotente); (6) se niega a usar un `--backup-dir` dentro del arbol del repo; (7) nombres validos no se tocan.
- Verificacion: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/scripts/test_repair_company_names.py -q`; ejecucion manual en desarrollo: `docker compose -f docker-compose.dev.yml run --rm backend python3 -m scripts.repair_company_names --dry-run`.

**PR-06.1 [backend-dev]**
- `backend/schemas.py`: `CompanyBase.name`/`CompanyUpdate.name` con validador comun `normalize_company_name(v: str | None) -> str`: `strip()`, longitud 1..120 (`COMPANY_NAME_MAX = 120`), rechaza `None` y cadena vacia (422). Quitar `fiscal_id` de `CompanyBase`, `CompanyUpdate` y respuestas. Anadir a `CompanyUpdate`: `reason: str | None = Field(None, max_length=500)` (solo para auditoria; no se persiste en la empresa).
- Migracion `backend/migrations/versions/b7e1a0d10002_company_name_length.py` (`down_revision` = `b7e1a0d10001` o el head vigente), SOLO comprueba y altera (no repara; la reparacion es del script): `upgrade`: `SELECT id FROM companies WHERE name IS NULL OR length(btrim(name)) = 0 OR name <> btrim(name) OR length(name) > 120`; si hay filas, `RuntimeError("Hay N empresas con nombre no valido (ids: ...). Ejecuta backend/scripts/repair_company_names.py --apply antes de migrar (ver docs/empresa/plan-implementacion-empresa.md, seccion 9)")` y NO se hace ningun cambio; si no, `alter_column("companies", "name", type_=sa.String(120), existing_nullable=False)`. `downgrade`: `alter_column` a `sa.String()`. Modelo: `name = Column(String(120), nullable=False)`. Secuencia de reversibilidad de 0.3.
- Test de la migracion (marcador `postgres`, `backend/tests/test_migration_company_name.py`): con un nombre de 130 caracteres `upgrade` lanza `RuntimeError` con el mensaje y no cambia la BD; tras ejecutar el script (`run(db, apply=True, ...)`) `upgrade` pasa.
- `backend/routers/companies.py`:
  - `GET /companies`: `Depends(deps.require_platform_admin)`; `skip/limit` con tope.
  - `POST /companies`: `require_platform_admin`; `crud.create_company(db, company, *, actor_id)` registra `company.created`.
  - `PUT /companies/{company_id}`: `require_platform_admin`; `crud.update_company(db, company_id, data, *, actor: models.User, reason: str | None = None)`. Si `exclude_unset` queda vacio, o ningun campo cambia respecto al estado actual -> 422 `No hay cambios que guardar`. Por cada campo que cambie, un evento: `name` -> `company.updated`; `is_active` -> `company.suspended`/`company.reactivated` (con `reason`); `is_managed` -> `company.managed_changed`; `tax_config`, `settings`, `worklog_definitions` -> sus acciones; `old_value`/`new_value` con solo ese campo. Tras el commit: `access_cache.invalidate_company`.
  - `DELETE /companies/{company_id}` -> 204; `require_platform_admin`; `crud.delete_company(db, company_id, *, actor_id)`: cuenta miembros, turnos, y suscripciones (`module_subscriptions.company_id`) (`default_company_id` se retira en PR-05.D, que va antes); si alguno > 0: `PolicyError(409, "No se puede borrar la empresa: tiene N miembros, N turnos, N suscripciones")` (solo los conceptos con N > 0). Si 0: `record_audit(company.deleted)`, borrar, `commit`, `invalidate_company`.
  - `GET /companies/{company_id}` y `GET /companies/detailed`: sin cambio de matriz (la vista reducida es PR-13); quitar `fiscal_id`.
- `backend/crud.py` (P3): `get_company_for_actor(db, company_id, actor) -> models.Company | None` (PA actuando: cualquier empresa; no PA: solo con membresia activa); `update_company` exige `actor` PA (`PolicyError(403)` si no). `get_user_companies` (linea 673) y `routers/users.py:77`: quitar `fiscal_id`; en el diccionario del PA anadir `is_active`/`is_managed`.
- E2 (resto de referencias de backend, inventario verificado): `models.py:84` (la columna se mantiene, comentario `# Obsoleto: se borra en PR-23`), `schemas.py:167,185`, `crud.py:673`, `routers/users.py:77`, `seed.py:53`, `dev_seed.py:37`, `backend/src/domain/entities/company.py:14`, `backend/src/infrastructure/persistence/sqlalchemy/mappers/company_mapper.py:15,27`, `backend/src/infrastructure/persistence/sqlalchemy/repositories/company_repository.py:84`, `backend/tests/infrastructure/test_sqlalchemy_mappers.py:45,56`.
- E7 (solo docs): en `docs/empresa/analisis-entidad-empresa.md` seccion 10.1 (linea 335, "Ciclo de vida"): corregir la afirmacion sobre empresa sin manager (no es un riesgo ni un estado invalido) y anadir el procedimiento: "el PA anade un manager con `POST /companies/{id}/members/add` y lo asciende con `PUT /companies/{id}/members/{uid}/role` (`manager`), o cambia el rol de un worker existente con ese mismo endpoint; no hay guardia de ultimo manager". Leer la seccion antes de editar y mantener el estilo. No se anade ninguna comprobacion de "empresa con al menos un manager" en codigo.

**PR-06.2 [frontend-dev]** (paralelo):
- U9 / E2 (quitar `fiscalId`): `components/admin/company-dialog.tsx` (lineas 36, 50, 119), `app/(app)/admin/companies/CompaniesPageClient.tsx` (60: filtro; 236 y 281: "Sin CIF/NIF"), `app/(app)/admin/modules/page.tsx:259`, `app/(app)/admin/modules/[moduleId]/page.tsx:402`, `lib/types.ts:32`, `lib/api/companies.ts:6` y `__tests__/lib/api/companies.test.ts`. Permitir editar `name`.
- U11 (manager deja de ver editores): `components/admin/company-configuration-tab.tsx`: las tarjetas "Reglas de Negocio", "Experiencia del Trabajador" y "Definiciones Tecnicas" (lineas 51-106) solo se renderizan si `isPlatformAdmin`; el manager solo ve la tarjeta de "Modulos Activos" sin el enlace "Gestionar Modulos". Retirar la condicion `user?.activeRole === 'manager'` de la linea 83. `app/(app)/manager/settings/page.tsx`: si el usuario no es PA, mostrar solo la tarjeta de modulos y el texto "La configuracion de la empresa la gestiona el administrador de la plataforma".
- U3: `getCompanies` solo para PA. Llamadores verificados: `admin/modules/page.tsx:45`, `admin/modules/[moduleId]/page.tsx:67`, `components/admin/user-dialog.tsx:72` (areas de PA: sin cambio) y `app/(app)/profile/page.tsx:43` (importa `getCompanies` de `lib/api/settings` sin necesitarlo: quitar el import). Cualquier otro uso por no-PA -> `getMyCompanies`.
- U5: confirmacion con el `Dialog` existente antes de suspender, reactivar y cambiar `isManaged` en `CompaniesPageClient.tsx` (switches en 205-210 y 310-315); la de suspender pide un motivo opcional que se envia como `reason`.
- U2 (empresa): `app/(app)/admin/companies/[companyId]/page.tsx` y `CompaniesPageClient.tsx` solo montan acciones de edicion si `usePermissions().canEditCompany`.
- Tests vitest: `CompaniesPageClient` (confirmacion antes de `updateCompany`), `company-configuration-tab` (manager no ve editores; PA si).

**PR-06.V Version**: MINOR. CHANGELOG `### Cambios Internos`: nuevo `backend/scripts/repair_company_names.py` (obligatorio ejecutarlo en `--dry-run` y `--apply` antes de desplegar; seccion 10 del plan).

---

### PR-07 - Agregados de turnos y migracion de pantallas (antes del tope de `limit`) [P-12]

- Rama: `feat/agregados-de-turnos`. Items: P-12. Depende de: PR-03, PR-04. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR.
- Objetivo: que ninguna pantalla sume ni muestre totales a partir de filas de una pagina. Se anade (a) el total de filas en los listados, (b) un endpoint de agregados sobre el rango completo y (c) se migran las pantallas de la seccion 2, punto 11. El tope de `limit` NO se aplica en este bloque (PR-08).
- Precondiciones de datos: ninguna. Migracion: NO.

**PR-07.0 [tester]** `backend/tests/routers/test_work_log_aggregates.py`:
- Crear 2500 turnos de una empresa (insercion masiva con `db.bulk_save_objects`) repartidos en 30 dias, 3 tipos y 4 usuarios. `GET /work-logs/summary` devuelve `totals.logsCount == 2500` y sumas (`totalHours`, `totalNet`, `totalGross`) iguales a las calculadas en el test con SQL directo; `byType`, `byDay` y `byUser` suman lo mismo que `totals`; `uniqueDays` correcto.
- `GET /work-logs?limit=100&skip=0` devuelve 100 filas y la cabecera `X-Total-Count == "2500"`; con `skip=2400` devuelve 100; el total no depende de `limit`/`skip`; con filtros (`user_id`, rango) el total refleja el filtro [Q-3].
- Autorizacion: manager de la empresa ve `byUser` completo y puede filtrar `user_id`; worker solo recibe sus propios datos (`byUser` solo contiene su `userId`; `user_id` ajeno -> 403); manager de otra empresa -> 403; empresa suspendida -> 403 no-PA, 200 PA; PA en `view_as` worker -> trata como worker; sin `company_id` ni `user_id`: agregados propios de empresas activas.
- Validacion: sin `start_date`/`end_date` -> 422; `start_date > end_date` -> 422; fechas fuera de [2000-01-01, hoy+730] -> 422; rango vacio -> totales a 0 y listas vacias.
- Cache: dos llamadas iguales (la segunda desde Redis) devuelven lo mismo; crear un turno invalida la cache (`crud.invalidate_dashboard_summary`), con Redis caido sigue funcionando.
- Que `GET /companies/{id}/dashboard-summary` ya existente (con cache) sigue igual.

**PR-07.1 [backend-dev]**
- `backend/schemas.py` (`CamelModel`):
```python
class WorkLogTotals(CamelModel):  logs_count: int; total_hours: float; total_net: float; total_gross: float; unique_days: int; active_users: int
class WorkLogTypeTotals(CamelModel):  type: str; logs_count: int; hours: float; net: float; gross: float
class WorkLogDayTotals(CamelModel):   date: date; logs_count: int; hours: float; net: float; gross: float
class WorkLogUserTotals(CamelModel):  user_id: UUID; first_name: str | None; last_name: str | None; email: str | None; logs_count: int; hours: float; net: float; gross: float; unique_days: int
class WorkLogSummaryResponse(CamelModel):  start_date: date; end_date: date; totals: WorkLogTotals; by_type: list[WorkLogTypeTotals]; by_day: list[WorkLogDayTotals]; by_user: list[WorkLogUserTotals]
```
  `hours` es la suma de `duration` (igual que `dashboard-summary`: la unidad la da el tipo).
- `backend/routers/work_logs.py`: nuevo `GET /work-logs/summary` (declararlo ANTES de `/{work_log_id}`), query `company_id: UUID | None`, `user_id: UUID | None`, `start_date: date`, `end_date: date` (obligatorias). Visibilidad identica a `GET /work-logs` (PR-03.5): con `company_id` o `cid`: `authorize(... "worker")`; manager/PA -> todos los usuarios y filtro `user_id` libre; worker -> `user_id` forzado al propio (y `byUser` solo con el propio); `user_id` ajeno sin ser manager -> 403. `GET /work-logs`: anadir cabecera de respuesta `X-Total-Count` (parametro `response: Response`); `main.py`: `CORSMiddleware(..., expose_headers=["X-Total-Count"])`.
- `backend/crud.py`: `count_work_logs(db, *, user_id, company_id, start_date, end_date, only_active_companies) -> int` (mismos filtros que `get_work_logs`); `get_work_log_summary(db, *, company_id, user_id, start_date, end_date) -> dict` con agregacion SQL (`func.sum`, `func.count`, `func.count(distinct(...))`, `group_by`), nunca iterando filas en Python; `end_date`/`start_date` con la misma semantica de solape que `get_work_logs` (`end_date >= start`, `start_date <= end`). Cache Redis de 300 s con clave `dashboard_summary:{company_id}:wls:{user_id or '-'}:{start}:{end}` (asi `invalidate_dashboard_summary` la borra); sin cache si no hay `company_id`.

**PR-07.2 [frontend-dev]** (paralelo; contrato fijado arriba)
- `frontend/src/lib/api/work-logs.ts`: anadir `getWorkLogsPage(params): Promise<{ items: WorkLog[]; total: number }>` (lee `response.headers['x-total-count']`), `getAllWorkLogs(params, opts?: { pageSize?: number; maxRows?: number }): Promise<WorkLog[]>` (pagina de 500 en 500 hasta `total`; `maxRows` por defecto 20000; para detalle de filas de exportaciones y calendario, NUNCA para sumar) y `getWorkLogSummary(params: { companyId?: string; userId?: string; startDate: string; endDate: string }): Promise<WorkLogSummary>`. Tipos `WorkLogSummary`, `WorkLogTotals`, etc. en `lib/types.ts`. Mantener `getWorkLogs` (sin cambios) para llamadores que no necesitan total.
- `components/manager/company-dashboard.tsx` (126 y 139): eliminar `periodLogs` con `limit: 10000`; las estadisticas, desgloses por tipo/dia/trabajador (lineas 152-302) salen de `getCompanyDashboardSummary` (ya importado, linea 24); `todayLogs` (`limit: 1000`, un dia) -> `getAllWorkLogs` de un dia; la exportacion (linea 315) -> `getAllWorkLogs` del rango. El hijo que recibe `workLogs={periodLogs}` (linea 410): inspeccionar y alimentarlo con los agregados; si realmente necesita filas, `getWorkLogsPage` con paginacion de servidor.
- `app/(app)/reports/page.tsx:259` (`fetchLogs`) y `app/(app)/reports/print/page.tsx:39`: totales y `statsMap` por usuario/dia desde `getWorkLogSummary`; las filas de detalle del PDF/CSV desde `getAllWorkLogs`; quitar los `limit: 1000 // Ensure we get enough`. `components/work-log/report-generation-dialog.tsx:102`: igual (CSV con `getAllWorkLogs`).
- `app/(app)/admin/users/[userId]/page.tsx:396`: tabla paginada en servidor con `getWorkLogsPage` (tamano 50) y total en la cabecera de la tabla; sin `limit: 1000`.
- `app/(app)/manager/calendar/page.tsx:56`: consulta acotada al rango visible del calendario (mes/semana) con `getAllWorkLogs({ companyId, startDate, endDate })`; la clave de la consulta incluye el rango.
- `manager/daily-reports/page.tsx:151` y `admin/daily-reports/DailyReportPageClient.tsx:40` (`limit: 2000`, un dia): sin cambio aqui (caben en el tope y PR-14 los sustituye por el endpoint de parte diario).
- Tests vitest: `__tests__/lib/api/work-logs.test.ts` (`getWorkLogsPage` lee la cabecera; `getAllWorkLogs` pagina y respeta `maxRows`; `getWorkLogSummary` ruta y params); `__tests__/components/manager-dashboard.test.tsx` actualizado (sin llamadas con `limit: 10000`; las cifras vienen del resumen).
- Verificacion: lint, `tsc`, `npm test`, `npm run build`; `grep -rn "limit: 10000\|limit: 1000\|Ensure we get enough" frontend/src` solo debe dejar usos de `limit` de paginas de listado.

**PR-07.V Version**: MINOR.

---

### PR-08 - Reglas de turnos (T1, T2, T3, T4, T6, M5, P3 turnos)

- Rama: `fix/reglas-de-turnos`. Items: T1, T2, T3, T4, T6, M5, P3 (turnos), U2 (turnos), U12. Depende de: PR-04, PR-07. Reviewers: `code-reviewer`, `security-reviewer`. Version: PATCH.
- Precondiciones de datos: T1/M5 (turnos de usuarios sin membresia activa en la empresa del turno: no se tocan, pero se informan), seccion 7 (informativa). Migracion: NO.

**PR-08.0 [tester]** `backend/tests/routers/test_work_log_rules.py`:
- T1: crear turno propio, de otro (manager) y en lote (`/bulk`), y como PA, para un usuario sin membresia o con membresia inactiva -> 422 `El usuario no tiene una membresia activa en esta empresa`; en `/bulk` basta un usuario invalido para rechazar todo y no crear ningun turno.
- T2: worker en empresa gestionada crea turno propio -> 403 `MSG_MANAGED_READONLY`; en autonoma -> ok; manager y PA en gestionada -> ok. Worker no puede editar ni borrar en gestionada (403). PA en `view_as` -> 403 solo lectura.
- T3: `PUT /work-logs/{id}` con `userId` o `companyId` distintos a los del turno -> 422 `No se puede cambiar la empresa ni el usuario de un turno`; con los mismos valores o sin ellos -> 200.
- T4: `POST /work-logs/bulk` ignora un `groupId` enviado por el cliente y genera uno propio (`extraData.group_id` comun a todos los turnos del lote); `POST /work-logs` individual ignora `groupId`; `PUT ...?apply_to_group=true` por un manager actualiza solo los turnos del mismo grupo Y de la misma empresa (un turno de otra empresa con el mismo `group_id` queda intacto); `apply_to_group` por un worker -> 403; ya no hay 500 (`AttributeError`); `WorkLogResponse.groupId` viene relleno desde `extra_data`.
- T6: `startDate > endDate` -> 422; fecha `2062-01-01` -> 422; fecha `1999-12-31` -> 422; `duration` negativa -> 422; `netAmount` negativo -> 422; `workLogId` mal formado en `DELETE`/`PUT` -> 422; `GET /work-logs?limit=2001` -> 422 [P-12]; `?limit=2000` -> 200 y la cabecera `X-Total-Count` sigue reflejando el total real (no el tope); `?limit=0` -> 422.
- M5: con membresia inactiva, `crud.create_work_log` no calcula con esa tarifa (rechaza 422 por T1); editar un turno antiguo de un miembro inactivo cambiando solo la descripcion -> 200.
- P3: `crud.delete_work_log(db, id, company_id=otra)` -> `None` y el turno sigue existiendo; `crud.update_work_log(..., company_id=otra)` -> `None`.
- Sin `companyId` en el body -> 422 `company_id es obligatorio`.

**PR-08.1 [backend-dev]**
- `backend/schemas.py`: constantes `MIN_WORKLOG_DATE = date(2000, 1, 1)`, `MAX_WORKLOG_FUTURE_DAYS = 730`. En `WorkLogBase`: validador `model_validator(mode="after")` `start_date <= end_date` y rango de ambas fechas; `duration`, `net_amount`, `gross_amount`, `amount` con `ge=0`. `WorkLogCreate`/`WorkLogBulkCreate`: `company_id: UUID` obligatorio; `group_id` deja de aceptarse como entrada (`Field(None, alias="groupId", exclude=True)` e ignorarlo en `crud`). Nuevo `class WorkLogUpdate(CamelModel)` con los campos de `WorkLogBase` opcionales mas `user_id: UUID | None` y `company_id: UUID | None`; `PUT /work-logs/{id}` pasa a recibir `WorkLogUpdate`. `WorkLogResponse`: validador `after` que, si `group_id is None` y `extra_data.get("group_id")`, lo rellena con `UUID(...)`.
- `backend/routers/work_logs.py`: en `create_work_log`: `authorize` (PR-03) -> `can_write_work_log(role, is_managed, is_owner)` (T2) -> `deps.require_active_member(db, work_log.user_id, work_log.company_id)` (T1; tambien PA). `create_work_log_bulk`: comprobar a todos los `user_ids` antes de crear nada. `update_work_log`: si el payload trae `user_id`/`company_id` distintos -> `PolicyError(422, "No se puede cambiar la empresa ni el usuario de un turno")` (T3). `read_work_logs`: `limit: int = Query(100, ge=1, le=2000)`, `skip: int = Query(0, ge=0)` [P-12; las pantallas ya no dependen de limites mayores gracias a PR-07].
- `backend/crud.py`:
  - `get_company_member(db, user_id, company_id, *, only_active: bool = False)`. `create_work_log` y `create_work_log_bulk` lo llaman con `only_active=True` y lanzan `ValueError` si no hay membresia (defensa en profundidad). Quitar el `group_id` entrante: en `create_work_log` ninguno; en `create_work_log_bulk` siempre `uuid.uuid4()` generado.
  - `delete_work_log(db, work_log_id, *, company_id)` y `update_work_log(db, work_log_id, work_log, *, company_id, apply_to_group=False)`: filtran por `WorkLog.company_id == company_id` (P3). Corregir la busqueda del grupo (linea ~547-553): `db.query(models.WorkLog).filter(models.WorkLog.company_id == db_work_log.company_id, models.WorkLog.extra_data["group_id"].as_string() == str(group_id))` (sin `models.WorkLog.group_id`, que no existe).
  - `_update_single_work_log`: quitar `user_id`/`company_id` de `new_data` antes de aplicar.

**PR-08.2 [frontend-dev]** (paralelo)
- U2 (turnos): usando `usePermissions`, ocultar/deshabilitar "Nuevo turno", edicion y borrado cuando `!canCreateWorkLog` / `!canEditWorkLog(log)` en: `app/(app)/list/page.tsx`, `app/(app)/calendar/page.tsx`, `components/work-log/work-log-form.tsx`, `components/work-log/details-dialog.tsx`, `components/work-log/work-logs-table.tsx`. Worker en empresa gestionada: texto "En esta empresa los turnos los registra el equipo gestor".
- U12: las validaciones de fecha del frontend se conservan como aviso previo; si el backend responde 422, mostrar `error.response.data.detail` en el toast de `components/work-log/user-dialog.tsx` (el interceptor global llega en PR-19).
- Tests vitest: `__tests__/components/work-log-permissions.test.tsx` (worker gestionada no ve "Nuevo turno"; worker autonoma si; manager siempre; PA en solo lectura nunca).

**PR-08.V Version**: PATCH.

---

### PR-09 - `work_logs.company_id` NOT NULL (T8)

- Rama: `chore/company-id-obligatorio-en-turnos`. Depende de: PR-08, PR-05 (el script ya no usa `default_company_id`) y de que el script de reparacion se haya ejecutado en produccion (seccion 10). Reviewers: `code-reviewer`, `database-reviewer` (migracion y script). Version: PATCH.
- Migracion: SI (`b7e1a0d10003`). **Paso previo de despliegue obligatorio: seccion 10**, con `repair_work_log_company.py` en `--dry-run` y despues `--apply`. La migracion NO inventa datos: solo comprueba y altera.
- Precondicion de datos (ACCION DEL USUARIO, solo lectura): consulta T8 de la seccion 7 y, mejor, el propio `--dry-run` del script, que lista que se asignaria y que quedaria para decision manual.

**PR-09.R [backend-dev] Script `backend/scripts/repair_work_log_company.py`** (reglas fijadas por el usuario; usa `repair_common.py`, seccion 9):
- Para cada turno con `company_id IS NULL`, en este orden:
  1. Si el usuario del turno tiene EXACTAMENTE UNA membresia (activa o no) -> se asigna esa empresa.
  2. (Sin regla de `default_company_id`: esa columna se retira en PR-05.D, anterior a este bloque, y no se sustituye por otra heuristica.)
  3. En cualquier otro caso (varias membresias, o ninguna membresia) -> el turno se LISTA para decision manual. NO se inventa dato: no se usa la empresa con mas turnos ni la empresa "Personal".
- `--dry-run` (por defecto) lista asignaciones propuestas y la lista manual; `--apply` escribe solo las asignaciones deterministas y guarda en `--backup-dir` dos ficheros: `work_log_company_assigned_<ts>.json` (id del turno, usuario, empresa asignada y regla aplicada, para poder deshacer) y `work_log_company_manual_<ts>.json` (id, usuario, fecha de inicio, tipo, y sus membresias; es la lista para decidir a mano). Codigo de salida: `0` si no quedan turnos sin empresa, `2` si quedan para decision manual.
- Idempotente: tras `--apply`, una segunda ejecucion no asigna nada nuevo y solo repite la lista manual.
- La decision manual la toma el usuario (ACCION DEL USUARIO): para cada turno listado fija el `company_id` con una sentencia SQL revisada (el plan no genera esa sentencia ni elige empresa) y vuelve a ejecutar el script hasta salida `0`.
- Tests (`backend/tests/scripts/test_repair_work_log_company.py`, SQLite): (1) usuario con una sola membresia (incluso inactiva) -> se asigna; (2) usuario con dos membresias -> lista manual, sin asignar nada; (4) usuario con dos membresias -> lista manual (aunque una empresa tenga muchos mas turnos o se llame "Personal"); (5) usuario sin membresias -> lista manual; (6) `--dry-run` no escribe en BD ni en disco; (7) `--apply` escribe los dos ficheros fuera del repo y solo toca las asignaciones deterministas; (8) idempotencia; (9) codigo de salida `2` con pendientes y `0` sin ellos.
- Verificacion: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/scripts/test_repair_work_log_company.py -q`.

**PR-09.0 [tester]** `backend/tests/test_migration_work_logs_company.py` (marcador `postgres`): con la BD en la revision anterior insertar un turno sin empresa; `upgrade` aborta con `RuntimeError` (mensaje con numero de turnos y referencia al script) y la BD queda en la revision anterior; tras ejecutar el script o asignar la empresa a mano, `upgrade` pasa; `models.WorkLog.__table__.c.company_id.nullable is False`; `downgrade` vuelve a `nullable=True`.

**PR-09.1 [backend-dev]**: migracion `backend/migrations/versions/b7e1a0d10003_work_logs_company_id_not_null.py` (`down_revision` = head vigente): `upgrade`: `SELECT count(*) FROM work_logs WHERE company_id IS NULL`; si es > 0 -> `RuntimeError("Hay N turnos sin empresa. Ejecuta backend/scripts/repair_work_log_company.py (--dry-run, revisar, --apply) y resuelve a mano los listados antes de migrar (ver docs/empresa/plan-implementacion-empresa.md, seccion 9)")` y no cambia nada; si no, `op.alter_column("work_logs", "company_id", nullable=False)`. `downgrade`: `nullable=True`. Modelo: `models.WorkLog.company_id` con `nullable=False`. (La migracion ya NO contiene el `UPDATE` de reasignacion automatica del borrador anterior: toda reasignacion es del script.)
- Verificacion: secuencia de reversibilidad (0.3), pytest completo.

**PR-09.V Version**: PATCH. CHANGELOG `### Cambios Internos`: `backend/scripts/repair_work_log_company.py`.

---

### PR-10 - Impuestos con claves libres (F1, E3)

- Rama: `feat/impuestos-claves-libres`. Depende de: PR-06, PR-08. Reviewers: `code-reviewer`, `database-reviewer` (migracion de datos y script). Version: MINOR.
- Migracion: SI (`b7e1a0d10004`). **Paso previo de despliegue obligatorio: seccion 10**, con `repair_tax_values.py` en `--dry-run` y despues `--apply`.
- Precondiciones de datos (ACCION DEL USUARIO): consulta F1 de la seccion 7 y el `--dry-run` del script. Si aparecen claves distintas de `social_security`, `irpf_base` (empresa) o `ss`, `irpf`, `extra` (override), se detiene y consulta: el renombrado y la limpieza de la migracion solo cubren esas. En produccion (seccion 7.1) hay 14 overrides `extra`, todos con valor 0, sin efecto en importes: la migracion los elimina.
- Semantica de `is_gross` [P-10], que este bloque deja explicita en codigo, docstring y tests: `is_gross=True` -> el importe de la tarifa es bruto y se descuentan del bruto TODOS los impuestos efectivos (`resolve_taxes`) para obtener el neto del snapshot; `is_gross=False` (default) -> la tarifa es neta: `net_amount` es el importe de la tarifa (mas extras) y NO se deduce ningun impuesto; el bruto que se devuelve en ese caso es informativo (calculo actual, sin cambios, Q-4). `price_type` de `settings` no interviene en el calculo: solo decide la vista del dashboard.

**PR-10.R [backend-dev] Script `backend/scripts/repair_tax_values.py`** (reglas fijadas por el usuario; usa `repair_common.py`):
- Recorre `companies.tax_config` y, en cada `company_members.rates_config[tipo].tax_overrides`, cada valor de impuesto.
- Valor numerico (int/float, no bool) dentro de [0, 1] -> correcto, no se toca. Cadena numerica que parsea a un numero dentro de [0, 1] (`"0.15"`) -> unica correccion automatica permitida (no hay ambiguedad de escala): se convierte a `float` con `--apply`. Cualquier otro caso -> NO se corrige: se LISTA para decision manual. En concreto: numero fuera de [0, 1] (p. ej. `15`: no se sabe si significa 15 %), numero negativo, cadena no numerica o numerica fuera de rango, `null` en `tax_config` (en `tax_overrides` `null` es valido: significa "sin override"), booleano, `NaN`/infinito.
- Tambien lista para decision manual lo que rompera las validaciones de `TaxConfig` aunque el valor sea valido: nombre de impuesto vacio o de mas de 50 caracteres, mas de 20 entradas, nombres duplicados tras `strip` (p. ej. `"IRPF"` y `"IRPF "`).
- Informa de las claves de override que la migracion renombrara (`ss`, `irpf`) y de las claves `extra` de override: cuantas hay, cuantas valen 0 (la migracion las eliminara si la empresa no define `extra` en su `tax_config`) y cuales valen distinto de 0 o no son numericas (decision manual: bloquean, la migracion aborta y las lista). Informa tambien de las claves de override desconocidas (ni `ss`/`irpf`/`extra` ni presentes en el `tax_config` de la empresa): informativo, no bloquea.
- `--dry-run` por defecto; `--apply` convierte solo las cadenas numericas en rango y guarda en `--backup-dir` `tax_values_before_<ts>.json` (valor anterior de cada campo tocado) y `tax_values_manual_<ts>.json` (lista de decision manual: `company_id`, ruta del valor, valor actual). Salida `0` si no hay pendientes manuales, `2` si los hay. Idempotente.
- Decision manual (ACCION DEL USUARIO): el usuario corrige cada valor listado (p. ej. con la pantalla de edicion de empresa o una sentencia revisada) y repite hasta salida `0`.
- Tests (`backend/tests/scripts/test_repair_tax_values.py`, SQLite): (1) `0.15` y `0` correctos no se tocan; (2) `"0.15"` se convierte con `--apply`; (3) `15`, `-0.1`, `"abc"`, `"15"`, `true`, `NaN`, `null` en `tax_config` se listan y NO se modifican; (4) `null` en `tax_overrides` se acepta; (5) nombre vacio, nombre de 51 caracteres, 21 entradas y duplicados se listan; (6) `--dry-run` no escribe; (7) `--apply` escribe los dos ficheros fuera del repo; (8) idempotencia; (9) salida `2`/`0`; (10) las claves `ss`/`irpf` aparecen como "renombrara"; (11) `extra` con valor 0 y ausente del `tax_config` aparece como "se eliminara" y `--dry-run` informa del total y de cuantos valen 0; (12) `extra` distinto de 0 o no numerico se lista como decision manual (salida `2`) y no se modifica; (13) `extra` a 0 pero definido en el `tax_config` de la empresa NO se elimina.
- Verificacion: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/scripts/test_repair_tax_values.py -q`.

**PR-10.0 [tester]** `backend/tests/domain/test_tax_config.py` y `backend/tests/routers/test_tax_calculation.py`:
- `TaxConfig`: acepta `{}`; acepta `{"IRPF": 0.15, "Seguridad Social": 0.0648}`; **acepta valor 0**; rechaza nombre vacio o solo espacios, nombre > 50, valor `-0.1`, `1.1`, `"0.1"` (cadena), `True`, `None`, `NaN`; rechaza > 20 entradas; claves duplicadas tras `strip` rechazadas.
- Calculo (`crud.calculate_dynamic_work_log`): con `is_gross=True` resta TODAS las entradas (tres impuestos libres suman) y `net = gross * (1 - suma)`; con `is_gross=False` el neto es base + extras sin deduccion aunque la empresa tenga impuestos; sin `is_gross` en la tarifa se comporta como `False`; override del miembro con la misma clave manda sobre la empresa; override con clave que la empresa no tiene se suma (solo con `is_gross=True`); `tax_overrides: null` no rompe; `tax_overrides: {"IRPF": null}` equivale a "sin override"; importe manual no aplica impuestos; el `snapshot` incluye `"tax_applied": {nombre: tasa}` y `"version"` nuevo.
- E3 / API [P-11]: `POST /companies` sin `taxConfig` -> 422; con `taxConfig: null` -> 422; con `taxConfig: {}` -> 201; con valor invalido -> 422; `PUT /companies/{id}` `{"taxConfig": {"IRPF": "x"}}` -> 422.
- `rates`: `PUT .../rates` con `taxOverrides` fuera de 0..1 -> 422.
- Migracion (marcador `postgres`): un `rates_config` con `tax_overrides {"ss": 0.06, "irpf": 0.15, "extra": 0.01}` pasa a `{"social_security": ..., "irpf_base": ...}` (el `extra` en 0 se elimina porque la empresa no lo define) y `downgrade` revierte el renombrado (no recrea el `extra` eliminado: valia 0 y no tenia efecto); un `extra` en 0 que la empresa SI define en `tax_config` se conserva; un `extra` distinto de 0 o no numerico aborta con `RuntimeError` y lo lista, SIN cambiar nada; un valor fuera de 0..1 o no numerico (incluida una cadena numerica no convertida) en `tax_config` o `tax_overrides` aborta con `RuntimeError` SIN cambiar nada; tras ejecutar el script (cadenas en rango) pasa; los valores de decision manual siguen abortando hasta que se corrijan.

**PR-10.1 [backend-dev]**
- Crear `backend/contracts.py` (se ampliara en PR-11):
```python
TAX_NAME_MAX = 50; TAX_MAX_ENTRIES = 20
class TaxConfig(RootModel[dict[str, float]]):   # valida nombre (strip, 1..50, sin duplicados), valor numero real no bool, 0 <= v <= 1, finito, <= 20 entradas
    def as_dict(self) -> dict[str, float]
def resolve_taxes(company_tax_config: dict | None, tax_overrides: dict | None) -> dict[str, float]
    # efectivo = {**company_tax_config, **{k: v for k, v in (tax_overrides or {}).items() if v is not None}}
```
- `schemas.py`: `CompanyBase.tax_config: TaxConfig` obligatorio (sin default; `{}` valido); `CompanyUpdate.tax_config: TaxConfig | None`. Quitar el default `{"social_security": 0.0, "irpf_base": 0.0}` (linea 168). `models.py:87`: `tax_config = Column(JSONB, nullable=True)` sin `default=`.
- `crud.calculate_dynamic_work_log` (lineas 145-156 y 209-277): sustituir `irpf`/`ss`/`extra` fijos por `taxes = resolve_taxes(company_tax_config, user_rate.get("tax_overrides") or {})`; `total_tax_rate = sum(taxes.values())`; la deduccion solo se aplica si `is_gross`; en `display_lines` una linea `{"type": "tax", "code": nombre, "label": f"{nombre} ({round(tasa*100,2)}%)", "value": -round(gross_total*tasa, 2)}` por cada entrada con tasa > 0; anadir `"tax_applied": taxes` al snapshot y subir `"version"` a `"2.3-free-taxes"`. `src/` se alinea en PR-18 (paridad); anotar la divergencia temporal en el PR.
- Migracion de datos `backend/migrations/versions/b7e1a0d10004_unify_tax_override_keys.py`: PRIMERO valida (sin escribir): recorre `companies.tax_config` y `company_members.rates_config[*].tax_overrides` y, si algun valor no es numerico dentro de [0, 1] (salvo `null` en `tax_overrides`) o algun nombre incumple `TaxConfig`, lanza `RuntimeError("Hay N valores de impuestos no validos (empresa/miembro, ruta, valor): ... Ejecuta backend/scripts/repair_tax_values.py y corrige a mano los listados antes de migrar (ver docs/empresa/plan-implementacion-empresa.md, seccion 9)")` y no cambia nada. Despues, para cada tipo con `tax_overrides` objeto, renombra `ss`->`social_security`, `irpf`->`irpf_base` y ELIMINA la clave `extra` cuando vale 0 y la empresa no la define en `tax_config` (produccion: 14 overrides, todos a 0, sin efecto en importes); si algun `extra` vale distinto de 0 o no es numerico, la validacion previa aborta y lo lista (decision manual). Compatibilidad con el codigo anterior: el renombrado es un cambio de datos que el backend antiguo no lee durante la ventana de `migrate` (ver seccion 10.3). NO convierte cadenas ni corrige valores: eso es del script. `downgrade`: renombrado inverso. Idempotente.
- Eventos `company.tax_config_changed` ya se emiten desde PR-06.

**PR-10.2 [frontend-dev]** (paralelo)
- Crear `frontend/src/components/admin/tax-overrides-fields.tsx`: recibe `companyTaxConfig: Record<string, number>`, `value: Record<string, number | null>`, `onChange`; un campo porcentual por cada clave de la empresa mas las claves extra del override; vacio = `null`. Sustituir los campos fijos `ss`/`irpf`/`extra` en: `app/(app)/profile/page.tsx` (lineas ~169-172, 272, 577-584), `app/(app)/admin/users/[userId]/page.tsx` (58, 88-153, 299-340), `app/(app)/manager/users/[userId]/page.tsx` (52, 86-153), `components/admin/user-rates-edit-dialog.tsx`, y la lectura de `app/(app)/admin/companies/[companyId]/page.tsx:414-422`. Tipos en `lib/types.ts`: `Company.taxConfig: Record<string, number>`; `DynamicRateEntry.tax_overrides: Record<string, number | null>`.
- Tarifa: el control `is_gross` de los formularios de tarifas queda rotulado "Tarifa bruta (se descuentan los impuestos)" / "Tarifa neta (sin deduccion)"; sin impuestos precargados.
- `components/admin/tax-config-builder.tsx`: editor de pares nombre/valor libres (anadir, quitar, renombrar), valores 0..100 en pantalla y 0..1 en el payload, **0 permitido**, sin valores por defecto, validacion de nombre no vacio y NaN.
- `components/admin/company-dialog.tsx`: el alta exige `taxConfig` (puede quedar vacio con la confirmacion "sin retenciones").
- Tests vitest: `__tests__/components/tax-config-builder.test.tsx` y `__tests__/components/tax-overrides-fields.test.tsx`.
- Verificacion: lint, `tsc`, tests, build.

**PR-10.V Version**: MINOR. CHANGELOG `### Cambios Internos`: `backend/scripts/repair_tax_values.py`.

---

### PR-11 - Contratos de `settings`, tipos de turno y tarifas (F2, F3, F4, F5, F7, U6)

- Rama: `feat/contratos-settings-y-tipos-de-turno`. Depende de: PR-10. Reviewers: `code-reviewer`, `database-reviewer` (migracion y script). Version: MINOR.
- Migracion: SI (`b7e1a0d10005`). El `downgrade` NO es completo (no recrea las claves retiradas ni los `settings` antiguos): para este bloque el rollback correcto tras aplicar la migracion es RESTAURAR EL BACKUP (seccion 10, paso d). **Paso previo de despliegue obligatorio: seccion 10**, con `repair_settings_definitions.py` en `--dry-run` y despues `--apply`.
- Precondiciones de datos (ACCION DEL USUARIO): consulta F1/F3/F4 de la seccion 7 y el `--dry-run` del script.

**PR-11.R [backend-dev] Script `backend/scripts/repair_settings_definitions.py`** (usa `repair_common.py`):
- Clasifica cada clave de `companies.settings` en: (a) MAPEADA por la migracion (`features`->`modules`, `billing.price_type`->`business_logic.price_type`, `input_mode`->`worker_experience.input_mode`), (b) RETIRADA que la migracion eliminara (`allow_tutorial`, `allow_coordination`, `is_managed`, `business_logic.cost_markup` y `billing.cost_markup_percent`; el valor de `cost_markup` se guarda en el backup JSON antes de borrarlo y el `--dry-run` lo informa por empresa: en produccion solo MasSki tiene `billing.cost_markup_percent = 32.0`, un porcentaje y no una fraccion; Querkus y Surf in Comporta tienen `business_logic.cost_markup = 0`), (c) valida del modelo `CompanySettings`, (d) DESCONOCIDA (ni mapeada, ni retirada, ni del modelo).
- Clasifica cada tipo de `companies.worklog_definitions`: con `unit` valido (`hours`/`days`/`fixed`; `fixed` es el tipo de turno que se cobra por unidad sea cual sea la duracion y ya existe en constructor de tipos, facturacion, listados y analitica); sin `unit` pero con `is_range` (la migracion fija `days` si `is_range` es verdadero y `hours` si es falso; produccion: 1 tipo, Querkus.campamentos, pasa a `days`); `unit: "hours"` con `is_range: true` (contradiccion; no existe en produccion: decision manual si aparece); `unit` con cualquier otro valor (NO soportado por el contrato: decision manual); sin `unit` ni `is_range` (la migracion fija `hours`, informativo); `label` vacio o de mas de 60 caracteres (decision manual).
- El script INFORMA de todo lo anterior y en especial de las claves RETIRADAS y DESCONOCIDAS que la migracion eliminaria. Las desconocidas bloquean la migracion (aborta) hasta que el usuario decida: anadirlas al modelo (cambio de codigo) o eliminarlas con `--apply --drop-unknown CLAVE[,CLAVE]` [Q-7].
- `--dry-run` (por defecto): solo informa. `--apply`: NO modifica datos por si mismo, salvo `--drop-unknown`; lo que hace es escribir en `--backup-dir` el fichero `settings_definitions_before_<ts>.json` con el valor ORIGINAL de `settings` y `worklog_definitions` de TODAS las empresas (copia previa, necesaria porque el `downgrade` es incompleto) y, con `--drop-unknown`, eliminar esas claves tras guardarlas en el mismo fichero. Salida `0` si no hay desconocidas ni tipos de decision manual, `2` si las hay. Idempotente.
- Tests (`backend/tests/scripts/test_repair_settings_definitions.py`, SQLite): (1) clasifica correctamente mapeadas, retiradas, validas y desconocidas; (2) `unit: "fixed"` se acepta (no es decision manual); `unit: "weekly"` (valor ajeno al contrato), `unit: "hours"` con `is_range: true` y `label` de 61 caracteres -> decision manual; (2b) `cost_markup` y `billing.cost_markup_percent` se clasifican como retiradas y su valor queda en el backup con permisos `0600`; (3) `is_range` sin `unit` -> informativo; (4) `--dry-run` no escribe; (5) `--apply` sin `--drop-unknown` no cambia la BD y escribe el backup completo fuera del repo; (6) `--apply --drop-unknown foo` elimina solo `foo` y lo guarda en el backup; (7) `--drop-unknown` de una clave mapeada o valida se rechaza; (8) idempotencia; (9) salida `2`/`0`.
- Verificacion: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/scripts/test_repair_settings_definitions.py -q`.

**PR-11.0 [tester]** `backend/tests/domain/test_contracts.py`, `backend/tests/routers/test_company_contracts.py`:
- `CompanySettings`: defaults (`business_logic.price_type == "net"` [P-10], sin campo `cost_markup`, `worker_experience.input_mode == "manual_single"`, `allow_manual_amount False`, `ui_customization.labels == {}`, `modules == {}`); `extra="forbid"` rechaza `allow_tutorial`, `allow_coordination`, `is_managed`, `cost_markup` (en `business_logic`), `billing.cost_markup_percent`, claves desconocidas y tipos incorrectos; `allowed_rates` sigue aceptada; lectura tolerante `CompanySettings.from_db(raw)` ignora claves desconocidas (con `logging.warning`) y rellena defaults.
- `WorklogDefinition`: `unit` en `hours|days|fixed` obligatorio (`fixed` valido; otro valor o sin `unit` -> 422 aunque tenga `is_range`); `label` 1..60; `fields` lista.
- `RateEntry`: `base_rate >= 0`, `is_gross` bool con default `False` [P-10], `tax_overrides` como en PR-10, `extras` con `value >= 0` y `per_unit` bool; `PUT .../rates` con un tipo sin definicion en la empresa -> 422 `Tipo de turno desconocido`.
- API: `PUT /companies/{id}` con `settings` invalidos -> 422; `GET /companies/{id}` (PA) devuelve `settings` con defaults aplicados.
- Migracion (marcador `postgres`): `features`->`modules`, `billing.price_type`->`business_logic.price_type`, `input_mode`->`worker_experience.input_mode`; elimina `allow_tutorial`, `allow_coordination`, `settings.is_managed`, `business_logic.cost_markup` y `billing.cost_markup_percent`; `is_range: true`->`unit: "days"`, `false`/ausente->`unit: "hours"` y borra `is_range` (solo si el tipo no tiene `unit`; un `unit: "fixed"` se conserva); clave de `settings` desconocida, `unit` distinto de `hours`/`days`/`fixed` tras el mapeo, `unit: "hours"` con `is_range: true` o `label` invalido -> `RuntimeError` con `company_id` y SIN cambiar nada; tras `--drop-unknown` de esa clave pasa.
- Defaults mutables (F5): dos `Company()` creadas sin `settings` no comparten el mismo dict.
- `tests/application/test_create_work_log_use_case.py:93`: actualizar al contrato (sin `is_range`).

**PR-11.1 [backend-dev]**
- Ampliar `backend/contracts.py`:
```python
class BusinessLogic(BaseModel):    model_config = ConfigDict(extra="forbid"); price_type: Literal["net","gross"] = "net"   # sin cost_markup: se elimina del contrato (el backend no lo usa en ningun calculo; podria volver con los informes avanzados de coste, B1/O11, bloqueado)
class WorkerExperience(BaseModel): model_config = ConfigDict(extra="forbid"); input_mode: Literal["manual_single","timer","bulk"] = "manual_single"; allow_manual_amount: bool = False
class UiLabels(BaseModel):         model_config = ConfigDict(extra="forbid"); worklog: str | None = Field(None, max_length=60); client: str | None = Field(None, max_length=60)
class UiCustomization(BaseModel):  model_config = ConfigDict(extra="forbid"); labels: UiLabels = UiLabels()
class CompanySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_logic: BusinessLogic = BusinessLogic(); worker_experience: WorkerExperience = WorkerExperience()
    ui_customization: UiCustomization = UiCustomization(); modules: dict[str, bool] = {}; allowed_rates: list[str] | None = None
    @classmethod
    def from_db(cls, raw: dict | None) -> "CompanySettings"    # descarta claves desconocidas con warning
    def ui_view(self) -> dict    # parte de interfaz para la vista reducida (PR-13): worker_experience, ui_customization, modules, business_logic.price_type
class WorklogDefinition(BaseModel): model_config = ConfigDict(extra="allow"); unit: Literal["hours","days","fixed"]; label: str = Field(min_length=1, max_length=60); fields: list[dict[str, Any]] = []
class WorklogDefinitions(RootModel[dict[str, WorklogDefinition]])   # claves 1..50 caracteres
class ExtraEntry(BaseModel): value: float = Field(ge=0); per_unit: bool = False
class RateEntry(BaseModel): model_config = ConfigDict(extra="allow"); base_rate: float = Field(0, ge=0); is_gross: bool = False; tax_overrides: dict[str, float | None] = {}; extras: dict[str, ExtraEntry] = {}
class RatesConfig(RootModel[dict[str, RateEntry]])
```
Cada valor de `tax_overrides` valida 0..1 con el mismo validador que `TaxConfig`. Documentar en el docstring de cada clave de `CompanySettings` para que sirve, tipo y default. `price_type` solo afecta a la vista del dashboard (documentarlo en el docstring, P-10).
- `schemas.py`: `CompanyBase.settings: CompanySettings | None`, `worklog_definitions: WorklogDefinitions`, `CompanyUpdate` igual con `None`; `MemberRatesUpdate.rates_config: RatesConfig` (sustituye al placeholder de PR-05) y el router de `rates` valida que cada tipo exista en `worklog_definitions` de la empresa (422).
- Seguimiento de PR-05 (M1, M2): (a) `MemberSettingsUpdate.settings` valida contra una lista blanca de claves de usuario (notificaciones y preferencias de interfaz); cualquier otra clave, y en particular las que existan en `CompanySettings`, -> 422; limite de tamano del JSON. (b) `RatesConfig` (sustituye al placeholder `dict[str, dict]`) limita el numero de claves y el tamano total, y valida finito y `>= 0` en todos los campos numericos conocidos. Tests en `test_company_contracts.py`: worker con `settings` de nivel empresa -> 422; `rates_config` por encima del limite -> 422; valor negativo, `NaN` o no numerico en cualquier campo de tarifa -> 422.
- `crud.py`: `get_worklog_unit` (lineas 104-108): eliminar el respaldo `is_range`; si falta `unit` lanza `ValueError`. `backend/src/application/use_cases/work_logs/create_work_log_use_case.py:63-65`: igual. Las respuestas de empresa devuelven `settings` con defaults (`CompanySettings.from_db(...).model_dump()`).
- F5: en `models.py` convertir todos los `default={...}`/`default={}` JSONB mutables en callables: `Company.worklog_definitions`/`settings` -> `default=dict`; `CompanyMember.rates_config`/`settings` -> `default=dict`; `WorkLog.extra_data` -> `default=dict`; `AuditLog.extra_data` -> `default=dict`.
- F3/F4 migracion `backend/migrations/versions/b7e1a0d10005_normalize_settings_and_definitions.py`: PRIMERO valida sin escribir y lanza `RuntimeError("Hay N empresas con settings o tipos de turno que la migracion no puede normalizar: ... Ejecuta backend/scripts/repair_settings_definitions.py y resuelve los listados antes de migrar (ver docs/empresa/plan-implementacion-empresa.md, seccion 9)")` si encuentra claves de `settings` desconocidas, `unit` no soportado (distinto de `hours`/`days`/`fixed`), `hours` con `is_range: true` o `label` invalido. Despues aplica el mapeo exacto de los tests (mapeadas, retiradas, `is_range`). `downgrade` solo restaura `is_range` a partir de `unit == "days"` y no recrea las claves retiradas ni los `settings` antiguos (documentarlo en el docstring: el rollback correcto es restaurar el backup).
- F7: el catalogo (`CompanySettings`) no contiene las claves retiradas; la edicion de `settings` ya es solo PA (PR-06).

**PR-11.2 [frontend-dev]** (paralelo)
- F2 / U6: `frontend/src/hooks/use-company-settings.ts`: eliminar `DEFAULT_SETTINGS` y la logica de migracion de claves antiguas; `useCompanySettings(company)` devuelve `company?.settings ?? {}` tipado como `CompanySettings` (el backend entrega los defaults). `lib/types.ts`: quitar `features`, `billing` e `input_mode` deprecados de `CompanySettings`. `app/(app)/manager/daily-reports/page.tsx:93`: quedarse solo con `settings.modules`. `components/manager/company-dashboard.tsx:172-173`: usar solo `business_logic.price_type` (`net` = un unico precio). `components/admin/business-logic-builder.tsx` y `worker-ux-builder.tsx`: sin fallbacks a claves antiguas ni valores por defecto propios. `cost_markup`: quitar el campo del constructor del panel (`business-logic-builder.tsx`), del hook (`use-company-settings.ts`) y de los tipos (`lib/types.ts`, tambien `billing.cost_markup_percent`).
- U6: quitar `settings.is_managed` y `(currentCompany as any)?.is_managed`: `app/(app)/admin/companies/CompaniesPageClient.tsx:137,262` (usar solo `company.isManaged`) y `app/(app)/profile/page.tsx:94-95` (la correccion de fondo es U7 en PR-19; aqui solo se retira `settings?.is_managed`). Borrar `components/admin/company-settings-dialog.tsx` (verificado: ningun import fuera del propio fichero; volver a ejecutar `grep -rn "company-settings-dialog\|CompanySettingsDialog" frontend/src` antes de borrar). NO tocar `member-settings-dialog.tsx` (O10).
- F4: `components/admin/worklog-definition-builder.tsx` (lineas 39-41, 51): escribir solo `unit` (`hours|days|fixed`), sin `is_range`; `list/page.tsx:495` y `profile/page.tsx:521`: usar `definition.unit === 'days'` sin respaldo `is_range`.
- Tests vitest: `__tests__/hooks/use-company-settings.test.ts` (devuelve lo que llega, sin defaults), `__tests__/components/worklog-definition-builder.test.tsx` (no emite `is_range`).

**PR-11.V Version**: MINOR. CHANGELOG `### Cambios Internos`: `backend/scripts/repair_settings_definitions.py`; `### Funcionalidades y Mejoras`: nota de que el rollback de esta version requiere restaurar el backup.

---

### PR-12 - Recalculo y avisos de turnos, dashboard (T5, T7, T11)

- Rama: `feat/recalculo-y-avisos-de-turnos`. Depende de: PR-08, PR-10. Reviewers: `code-reviewer`. Version: MINOR. Migracion: NO.

**PR-12.0 [tester]** `backend/tests/routers/test_work_log_recalc.py`, `test_work_log_overlap.py`, `test_dashboard_inactive.py`:
- T5: editar solo `description` -> `net_amount`, `gross_amount`, `duration` y `calculation_snapshot` NO cambian aunque se haya cambiado la tarifa del miembro despues; cambiar `endTime` (mismo tipo) -> recalcula con la tarifa y definicion del `calculation_snapshot` del turno (no con la vigente) y con los impuestos de `snapshot["tax_applied"]`; turno antiguo sin `tax_applied` usa `resolve_taxes(company.tax_config, snapshot.rate_applied.tax_overrides)`; cambiar el `type` recalcula con la tarifa vigente del miembro (exige membresia activa, si no 422); `amount`/`netAmount` manual explicito manda siempre; sin tarifa y sin importe manual -> 400 con mensaje claro; `?recalculate_with_current_rates=true` recalcula con la tarifa vigente (manager/PA; worker 403).
- T7: crear un turno que solapa con otro del mismo usuario y empresa -> 200/201 con `warnings: [{"code": "overlap", "message": "...", "conflictingLogIds": [id]}]`; sin solape -> `warnings == []`; turnos contiguos (fin == inicio) no solapan; turnos que cruzan medianoche se comparan como intervalos datetime; tipo `days` solapa por rango de fechas; editar un turno no se solapa consigo mismo; el mismo usuario en OTRA empresa no genera aviso; `/bulk` devuelve avisos con `userId` por cada solape.
- T11: `GET /companies/{id}/dashboard-summary` con `fake_redis.raise_errors=True` -> 200 y misma forma que con cache; los totales (`periodMetrics`) incluyen turnos de miembros inactivos; `workersSummary` incluye a los inactivos con `isActive == false`; un miembro inactivo sin turnos hoy no aparece en `todayActiveMembers`.

**PR-12.1 [backend-dev]**
- T5 en `crud._update_single_work_log`: detectar si cambian `type`, `duration`/`start_time`/`end_time`, `start_date`/`end_date`, `amount`/`net_amount`; si NO cambia ninguno -> no recalcular. Si cambia el `type`: `type_def`/`type_rate` vigentes (miembro activo, si no `ValueError` -> 422). Si cambia otro campo del mismo `type`: `type_def = snapshot["definition"]`, `type_rate = snapshot["rate_applied"]`, `company_tax_config = snapshot.get("tax_applied") or company.tax_config`. Recalcular con la tarifa vigente solo con parametro explicito `PUT /work-logs/{id}?recalculate_with_current_rates=true` (manager/PA; default `false`).
- T7: nuevo `backend/work_log_rules.py` (puro): `find_overlaps(candidate: dict, existing: list[dict]) -> list[str]` (ids). Intervalo: `start = datetime.combine(start_date, start_time or time.min)`, `end = datetime.combine(end_date, end_time or time.max)`; solapan si `a.start < b.end and b.start < a.end`. `WorkLogResponse` anade `warnings: list[WorkLogWarning] = []` con `class WorkLogWarning(CamelModel): code: str; message: str; conflicting_log_ids: list[UUID] = []; user_id: UUID | None = None`. En `POST /work-logs`, `POST /work-logs/bulk` y `PUT /work-logs/{id}`: consultar turnos del mismo `user_id` y `company_id` (excluyendo el propio). Mensaje: "Este turno se solapa con otro del mismo trabajador". Solo avisa; nunca rechaza.
- T11: en `routers/companies.py:get_company_dashboard_summary` envolver cache en `try/except` y devolver siempre `schemas.DashboardSummaryResponse(**data)`; en `crud.get_dashboard_summary` `workers_summary` incluye todos los miembros (activos e inactivos) con `is_active`; `today_active_members` solo de usuarios con turnos hoy.

**PR-12.2 [frontend-dev]** (paralelo)
- `lib/types.ts`: `WorkLog.warnings?: { code: string; message: string; conflictingLogIds: string[]; userId?: string }[]`. Crear `lib/work-log-warnings.ts`: `export function notifyWorkLogWarnings(toast: (o: { title: string; description?: string }) => void, log: { warnings?: WorkLog['warnings'] }): void` que, si hay avisos, llama `toast({ title: "Aviso", description: avisos.map(w => w.message).join(" ") })`. Llamarla tras el exito en `components/work-log/user-dialog.tsx:179,182` y `components/work-log/manager-add-log-dialog.tsx:195` (bulk).
- `components/manager/dashboard/dashboard-team-table.tsx`: insignia "Inactivo" para `isActive === false`.
- Tests vitest: `__tests__/lib/work-log-warnings.test.ts`.

**PR-12.V Version**: MINOR.

---

### PR-13 - Vista reducida y completa de empresa en v1 (P7, P8, U11 resto) [P-1, P-2]

- Rama: `feat/vistas-reducida-y-completa-de-empresa`. Depende de: PR-06, PR-11. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR. Migracion: NO.

**PR-13.0 [tester]** `backend/tests/routers/test_company_views.py`:
- `GET /users/me/companies` (worker, manager): cada empresa trae `id`, `name`, `isManaged`, `role`, `isActiveMember`, `ratesConfig` (propia), `worklogDefinitions`, `taxConfig` [P-2] y `settings` solo con claves de interfaz (`ui_view()`); NO trae `isActive`, ni `settings.business_logic.costMarkup`, ni `allowedRates`, ni `fiscalId`. PA (actuando): todas con la vista completa (`isActive`, `isManaged`, `settings` completo). PA en `view_as`: vista reducida.
- `GET /companies/{id}`: PA vista completa; manager y worker vista reducida; empresa suspendida -> 403 para no-PA.
- `GET /users/{id}/companies` (P8): manager solo ve las empresas que comparte con el objetivo (interseccion con sus membresias activas); worker -> 403; PA todas (incluidas inactivas).
- La vista reducida no incluye campos que no deba (comprobar el conjunto exacto de claves).

**PR-13.1 [backend-dev]**
- `schemas.py`: `CompanyReducedResponse(CamelModel)` con `id: UUID`, `name: str`, `is_managed: bool`, `role: str | None`, `is_active_member: bool`, `rates_config: dict | None`, `worklog_definitions: dict`, `tax_config: dict[str, float]`, `settings: dict` (resultado de `CompanySettings.ui_view()`); `CompanyFullResponse` (la actual `CompanyResponse` sin `fiscal_id`).
- Endpoints: `GET /users/me/companies` y `GET /companies/{id}` usan `response_model=None` y serializan con el esquema correcto por rol (completo para PA actuando; reducido para el resto). `crud.get_user_companies` devuelve el diccionario completo y un helper `to_reduced_company(d: dict) -> dict` construye la vista reducida.
- P8: `GET /users/{user_id}/companies`: PA todas; manager: empresas con membresia activa del solicitante donde el objetivo tambien es miembro (`include_inactive` solo PA); worker 403.

**PR-13.2 [frontend-dev]** (paralelo)
- `lib/types.ts`: `CompanyResponse` separa campos solo-PA (`isActive`, `settings` completo) como opcionales; ajustar los usos con `tsc`.
- U11 resto: las pantallas del manager (`manager/billing`, `manager/users`, `manager/shifts`, `manager/calendar`, `manager/dashboard`) no deben depender de campos solo-PA; ejecutar `npx tsc --noEmit` y corregir.
- Tests vitest: `__tests__/lib/api/companies.test.ts` (forma reducida).

**PR-13.V Version**: MINOR.

---

### PR-14 - Parte diario y modulos (T10, items B2-B5 del catalogo, P5 parcial)

- Rama: `feat/parte-diario-y-modulos`. Depende de: PR-03, PR-08. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR. Migracion: NO.
- Alcance de P5: solo el parte diario (modulo `worker_daily_report`). Billing avanzado e informes: ver seccion 1.2.
- Precondiciones de datos (informativas): suscripciones duplicadas o con `scope` incoherente (item B3 del catalogo, seccion 7). No hay migracion; si existen duplicados, el 409 solo actua sobre altas nuevas.

**PR-14.0 [tester]** `backend/tests/routers/test_daily_report.py`, `test_subscriptions.py`:
- T10: `GET /companies/{cid}/daily-report?date=2026-01-10`: worker con el modulo -> 200 con miembros activos y turnos del dia de TODA la empresa; en el JSON de cada turno NO existen las claves `netAmount` ni `grossAmount` (ausentes, no `null`) [P-14]; manager con modulo -> las claves existen con importes; PA actuando -> las claves existen; PA en `view_as` worker -> sin las claves; manager/worker sin modulo -> 403 `Tu cuenta no tiene acceso al modulo 'worker_daily_report'. Contacta con el administrador.`; empresa suspendida -> 403 no-PA; fecha mal formada -> 422; sin `date` usa hoy; turno que cruza medianoche aparece el dia siguiente tambien; miembros inactivos con turno ese dia aparecen con `isActive == false`.
- `GET /work-logs` de un worker con modulo devuelve SOLO sus turnos; `GET /companies/detailed` para worker -> 403 (solo manager/PA).
- Items B3 del catalogo: `POST /modules/subscriptions` con `scope: "otra"` -> 422; `status: "otro"` -> 422; `scope: "company"` sin `companyId` -> 422; `scope: "user"` sin `userId` -> 422; modulo con `target_scope: "company"` y suscripcion de usuario -> 422; duplicado activo/trial misma empresa+modulo -> 409 [P-15]; `PUT /modules/subscriptions/{id}` con `status` invalido -> 422; `AppModuleCreate.target_scope` fuera de `company|user|both` -> 422.
- Item B4 del catalogo: `crud.get_subscriptions` no existe.

**PR-14.1 [backend-dev]**
- `schemas.py`: `class DailyReportMember(CamelModel): user_id: UUID; first_name: str | None; last_name: str | None; role: str; is_active: bool; sort_order: int`; DOS esquemas de turno [P-14]: `class DailyReportLogWorker(CamelModel): id: UUID; user_id: UUID; type: str; start_date: date; end_date: date; start_time: time | None; end_time: time | None; duration: float | None; description: str | None` y `class DailyReportLogFull(DailyReportLogWorker): net_amount: float | None; gross_amount: float | None`; DOS respuestas: `DailyReportWorkerResponse` y `DailyReportFullResponse`, cada una con `company_id: UUID; date: date; members: list[DailyReportMember]; work_types: dict[str, dict[str, str]]` y `logs` del tipo correspondiente.
- `routers/companies.py`: `GET /companies/{company_id}/daily-report?date=` con `require_company("worker", module="worker_daily_report")`. El handler elige el esquema segun `ctx.role`: `manager` o `platform_admin` -> `DailyReportFullResponse`; `worker` (incluye el PA en `view_as` worker) -> `DailyReportWorkerResponse`. Declararlo con `response_model=None` y `responses={200: {"model": DailyReportFullResponse | DailyReportWorkerResponse}}` y devolver `JSONResponse(content=obj.model_dump(mode="json", by_alias=True))`, para que FastAPI no vuelva a filtrar por un `response_model` comun y no filtre ni anada campos. `work_types` = `{codigo: {"label", "unit"}}`. Registrar la ruta ANTES de `/{company_id}`.
- `GET /work-logs`: eliminar la rama "worker con modulo ve la empresa" (PR-03.5): worker solo propios. `GET /companies/detailed`: eliminar la rama worker con modulo.
- Suscripciones (`schemas.py`, `crud.create_subscription`/`update_subscription`, `routers/modules.py`): `scope: Literal["company","user"]`, `status: Literal["active","trial","cancelled","expired"]`, `target_scope: Literal["company","user","both"]`; coherencia `scope`/`company_id`/`user_id`; compatibilidad con `module.target_scope`; duplicado (misma empresa+modulo con estado `active|trial`) -> `HTTPException(409, "La empresa ya tiene este modulo activo")`; usuario analogo.
- Item B4 del catalogo: borrar `crud.get_subscriptions` si PR-03 no lo hizo.

**PR-14.2 [frontend-dev]** (paralelo)
- `lib/api/companies.ts`: `getDailyReport(companyId: string, date: string): Promise<DailyReportResponse>` (`GET /companies/${companyId}/daily-report`, `params: { date }`); tipos en `lib/types.ts` con los importes opcionales (`netAmount?`, `grossAmount?`).
- `app/(app)/manager/daily-reports/page.tsx`: sustituir `getCompaniesDetailed` + `getWorkLogs` (lineas 106-155, incluido `limit: 2000`) por `getDailyReport`; `companyUsers` sale de `members`; las definiciones de `workTypes`. `app/(app)/admin/daily-reports/DailyReportPageClient.tsx:40`: igual (sustituir el `limit: 2000`). Crear/editar/borrar siguen usando los endpoints de turnos.
- Tests vitest: `__tests__/lib/api/companies.test.ts` (`getDailyReport`).

**PR-14.V Version**: MINOR.

---

### PR-15 - Consulta de logs de auditoria (A2, U13 logs)

- Rama: `feat/consulta-logs-auditoria`. Depende de: PR-02, PR-05, PR-06. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR. Migracion: NO.

**PR-15.0 [tester]** `backend/tests/routers/test_audit_logs.py`: solo PA (manager y worker 403, sin token 401, PA en `view_as` 403); filtros `company_id`, `actor_user_id`, `target_user_id`, `action` (igualdad exacta), `from`/`to` (fechas ISO, `from > to` -> 422); orden `created_at` descendente; paginacion `limit` 1..200 (default 50) y `offset`, con `total` del conjunto filtrado; incluye eventos antiguos (`2fa_reset`) con `actorUserId`; `GET /audit-logs/actions` devuelve el catalogo de acciones.

**PR-15.1 [backend-dev]**
- Router nuevo `backend/routers/audit_logs.py` (registrar en `main.py`): `GET /audit-logs` (`Depends(deps.require_platform_admin)`) con query `company_id: UUID | None`, `actor_user_id: UUID | None`, `target_user_id: UUID | None`, `action: str | None`, `from_date: datetime | None` (alias `from`), `to_date: datetime | None` (alias `to`), `limit: int = Query(50, ge=1, le=200)`, `offset: int = Query(0, ge=0)`. Respuesta `AuditLogPage(CamelModel)`: `total: int`, `items: list[AuditLogItem]`; `AuditLogItem`: `id`, `action`, `created_at`, `actor_user_id`, `actor_email: str | None`, `company_id`, `target_user_id`, `old_value`, `new_value`, `reason`, `extra_data`. `GET /audit-logs/actions` -> `list[str]` (constantes de `audit.AuditAction` mas `2fa_reset`, `create_work_log`, `create_work_log_bulk`, `update_work_log`, `delete_work_log`).
- `crud.get_audit_logs(db, *, filters..., limit, offset) -> tuple[int, list[AuditLog]]` con los indices de PR-02.

**PR-15.2 [frontend-dev]** (paralelo)
- Pagina `frontend/src/app/(app)/admin/audit-logs/page.tsx` (solo PA; si no, redirigir a `/dashboard`), `frontend/src/lib/api/audit-logs.ts` (`getAuditLogs(params)`, `getAuditActions()`), tabla con filtros (empresa, usuario, accion, rango de fechas), paginacion y desplegable con `oldValue`/`newValue` en JSON. Enlace "Auditoria" en el sidebar del PA (`(app)/layout.tsx`).
- Tests vitest: `__tests__/lib/api/audit-logs.test.ts` y render de la pagina con datos simulados.

**PR-15.V Version**: MINOR.

---

### PR-16 - API v2: cimientos y alineacion del dominio (X1 parte 1, arnes de Q3)

- Rama: `feat/api-v2-cimientos`. Items: X1 (1/3), Q3 (arnes), X2 (uso desde v2). Depende de: PR-11, PR-13. Reviewers: `code-reviewer`, `security-reviewer`, `database-reviewer` (repositorios). Version: MINOR. Migracion: NO (si el port a v2 requiriese una, aplica la seccion 10).
- Alcance de v2 [decision del usuario]: SOLO el area empresa (empresa, membresias, tarifas, impuestos y lo necesario). Todo lo demas (turnos, auth, usuarios, modulos, auditoria, dashboards, parte diario) sigue en v1. Prefijo `/api/v2/`.
- Decision pendiente que condiciona este bloque: Q-1 (se asume opcion A: v1 primero, v2 es el port con paridad).
- Gateway: sin cambios (hallazgo 9). Verificacion manual con el stack arriba: `curl -s http://localhost:${GATEWAY_PORT:-8080}/api/v2/ping`.

**PR-16.0 [tester]**
- `backend/tests/domain/test_company_entity.py`: `Company` tiene `is_active` (default `True`), `is_managed` (default `False`), `updated_at` y NO tiene `fiscal_id`; `CompanyMember` tiene `settings` y `updated_at`.
- `backend/tests/infrastructure/test_company_repository.py` (SQLite): el modulo `infrastructure.persistence.sqlalchemy.repositories.company_repository` se puede importar (hoy falla); `get_by_id`, `get_by_name`, `list_companies(skip, limit)`, `count_companies`, `save` (persiste `is_active`, `is_managed`, `settings`, `tax_config`, `worklog_definitions`), `delete`, `count_dependencies`; repositorio de miembros: `get_membership`, `list_members_by_company(company_id, is_active=None)`, `list_companies_by_user`, `save` (persiste `settings`, `rates_config`, `role`, `is_active`, `sort_order`), `delete`, `count_work_logs(user_id, company_id)`.
- `backend/tests/infrastructure/test_sqlalchemy_mappers.py`: actualizar al dominio alineado (sin `fiscal_id`, con los campos nuevos).
- `backend/tests/routers/v2/test_v2_mount.py`: `GET /v2/ping` -> 200 `{"status": "ok", "version": "v2"}`; `GET /health` (v1) sigue 200; una `DomainException` lanzada en un endpoint de prueba de v2 se traduce a su codigo (`EntityNotFoundException` -> 404, `ConflictException` -> 409, `ValidationDomainException` -> 422, `UnauthorizedDomainActionException` -> 403).
- `backend/tests/parity/test_harness.py`: `to_snake` convierte claves `camelCase` anidadas a `snake_case`; `assert_parity` ignora las claves de una lista; `call_both` ejecuta la misma peticion en v1 y v2.

**PR-16.1 [devops] Dockerfile**: editar `backend/Dockerfile`: anadir `PYTHONPATH=/app:/app/src` al bloque `ENV`. Verificacion: `docker compose -f docker-compose.dev.yml build backend` y `docker compose -f docker-compose.dev.yml run --rm backend python3 -c "import domain.entities.company, models; print('OK')"`. Confirmar que `docker-compose.dev.yml` y `docker-compose.prod.yml` no sobreescriben `PYTHONPATH` (verificado el 2026-10-18: no aparece).

**PR-16.2 [backend-dev] Dominio y persistencia (alinear `src/` con la BD)**
- `backend/src/domain/entities/company.py`: `Company(id, name, tax_config, worklog_definitions, settings, is_active: bool = True, is_managed: bool = False, created_at, updated_at)`; sin `fiscal_id` (retirado en PR-06). `backend/src/domain/entities/company_member.py`: anadir `settings: Dict[str, Any] = field(default_factory=dict)` y `updated_at: Optional[datetime] = None`.
- `backend/src/domain/exceptions/domain_exceptions.py` (hoy: `DomainException`, `EntityNotFoundException`, `InvalidRateConfigurationException`, `UnauthorizedDomainActionException`, `InactiveMembershipException`, `ModuleAccessDeniedException`): anadir `ConflictException(DomainException)` y `ValidationDomainException(DomainException)`.
- Crear `backend/src/domain/ports/repositories/company_repository_port.py` (hoy NO existe, y `company_repository.py:11` lo importa): 
```python
class CompanyRepositoryPort(ABC):      # todos async
    get_by_id(company_id: str) -> Optional[Company]; get_by_name(name: str) -> Optional[Company]
    list_companies(*, skip: int = 0, limit: int = 100) -> List[Company]; count_companies() -> int
    save(company: Company) -> Company; delete(company_id: str) -> None
    count_dependencies(company_id: str) -> Dict[str, int]    # claves: members, work_logs, subscriptions
class CompanyMemberRepositoryPort(ABC):
    get_membership(user_id: str, company_id: str) -> Optional[CompanyMember]
    list_members_by_company(company_id: str, is_active: Optional[bool] = None) -> List[CompanyMember]
    list_companies_by_user(user_id: str) -> List[CompanyMember]
    save(member: CompanyMember) -> CompanyMember; delete(user_id: str, company_id: str) -> None
    count_work_logs(user_id: str, company_id: str) -> int
```
  Crear `backend/src/domain/ports/audit_port.py`: `AuditLogPort.record(*, action, actor_id, company_id=None, target_user_id=None, old_value=None, new_value=None, reason=None) -> None`. Anadir a `UserRepositoryPort` `count_active_platform_admins() -> int`.
- `backend/src/infrastructure/persistence/sqlalchemy/mappers/company_mapper.py` y `.../repositories/company_repository.py`: mapear y persistir `is_active`, `is_managed`, `updated_at`, `settings` (empresa y miembro); implementar los metodos nuevos de los puertos; `list_members_by_company` ordena por `sort_order`, `joined_at`. `SqlAlchemyAuditLog` en `.../repositories/audit_repository.py` envuelve `audit.record_audit` (el commit lo hace el repositorio de la transaccion).
- Reglas compartidas: el dominio y los casos de uso de v2 usan `access_policy.py` (X2), `contracts.py` (PR-10/PR-11) y `audit.AuditAction` TAL CUAL; no duplican reglas.

**PR-16.3 [backend-dev] Capa HTTP de v2**
- Crear `backend/routers/v2/__init__.py` con `router = APIRouter(prefix="/v2")` e incluir en el los sub-routers que lleguen en PR-17/PR-18; `GET /v2/ping`. Crear `backend/routers/v2/deps.py` (fabricas de repositorios y casos de uso a partir de `Depends(get_db)`) y `backend/routers/v2/schemas.py` con `class V2Model(BaseModel): model_config = ConfigDict(from_attributes=True)` (sin alias) [Q-2]. Los routers de v2 reutilizan `deps.require_company`, `deps.require_platform_admin` y `access_policy`.
- `backend/main.py`: `app.include_router(v2.router)` y manejadores de excepcion para `DomainException` (tabla del test). El manejador de `PolicyError` ya existe (PR-03).
- Directorio de casos de uso: `backend/src/application/use_cases/company/__init__.py` (vacio por ahora).

**PR-16.4 [backend-dev] Arnes de paridad (Q3)**
- `backend/tests/parity/helpers.py`: `to_snake(obj)`, `assert_parity(v1, v2, *, ignore: set[str] = frozenset())`, `call_both(client, method, v1_path, v2_path, *, v1_body=None, v2_body=None)`; fixture `parity_world(db)` que crea una escenario comun (PA, manager, worker, empresa autonoma y gestionada, suspendida). Documentar en el docstring que las diferencias intencionadas (renombrados de X3) se declaran en una tabla `KNOWN_DIFFERENCES` del propio test.
- Verificacion: tests de PR-16.0; `ruff check backend/`; pytest completo en contenedor.

**PR-16.V Version**: MINOR. Actualizar tambien `CLAUDE.md` (seccion Stack): "API v2 del area empresa en `/api/v2/` (`backend/routers/v2/`, `backend/src/`)".

---

### PR-17 - API v2: empresa y vistas (X1 parte 2, X3, X7, Q3)

- Rama: `feat/api-v2-empresa`. Depende de: PR-16, PR-13. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR. Migracion: NO.
- Regla: v2 reproduce el comportamiento final de v1 (PR-03, PR-06, PR-13) con casos de uso en `backend/src/application/use_cases/company/`; v1 no se modifica.

**Endpoints (JSON en `snake_case`; politica identica a v1 salvo renombrados):**
| v2 | Sustituye en v1 | Politica | Respuesta |
|---|---|---|---|
| `GET /v2/companies?include=members&skip&limit` | `GET /companies` y `GET /companies/detailed` (X3) | PA actuando (los demas usan `/v2/me/companies`) | `{ "items": [CompanyFull (con `members` si `include=members`)], "total": int }` |
| `POST /v2/companies` | `POST /companies` | PA | `CompanyFull` (201) |
| `GET /v2/companies/{company_id}` | `GET /companies/{id}` | `require_company("worker")` | `CompanyFull` si PA actuando; `CompanyReduced` en otro caso |
| `PUT /v2/companies/{company_id}` | `PUT /companies/{id}` | PA | `CompanyFull` |
| `DELETE /v2/companies/{company_id}` | `DELETE /companies/{id}` | PA | 204 |
| `GET /v2/me/companies` | `GET /users/me/companies` | usuario autenticado | lista `CompanyReduced` o `CompanyFull` (PA actuando) |
| `GET /v2/users/{user_id}/companies` | `GET /users/{id}/companies` | PA, o manager (interseccion, P8) | lista |
- Esquemas (`backend/routers/v2/schemas.py`, `snake_case`): `CompanyFull` (`id, name, is_active, is_managed, tax_config, worklog_definitions, settings, created_at, updated_at`), `CompanyReduced` (los campos de `CompanyReducedResponse` de PR-13 en `snake_case`), `CompanyCreateV2`, `CompanyUpdateV2` (con `reason`). Validan con `contracts.py` (`TaxConfig`, `WorklogDefinitions`, `CompanySettings`), por lo que heredan `unit` en `hours|days|fixed` y la ausencia de `cost_markup`.
- Casos de uso (`backend/src/application/use_cases/company/`): `create_company.py`, `update_company.py` (calcula el conjunto de cambios, 422 si vacio, emite los eventos de auditoria del catalogo por campo a traves de `AuditLogPort`), `delete_company.py` (409 con motivos), `get_company.py`, `list_companies.py`, `list_my_companies.py`, `list_user_companies.py`. Cada uno recibe puertos por constructor y es asincrono.
- X3: `?include=members` unifica "listado" y "detalle con miembros"; el solape de `/members` con `/companies/detailed` desaparece porque los miembros viven solo en `/v2/companies/{id}/members` (PR-18) y en `include=members`.
- La cache de acceso (`access_cache`) se invalida igual que en v1 (se llama desde el adaptador de repositorio tras `save`/`delete`).

**PR-17.0 [tester]** (cada caso falla antes de implementar)
- `backend/tests/routers/v2/test_v2_companies.py`: matriz de permisos (manager/worker 403 en alta, edicion, borrado y listado global; PA en `view_as` 403 en escritura); validaciones E1, E3 (`tax_config` obligatorio, `{}` valido), E8 (422 sin cambios), E4 (409 con motivos, 204 vacio); eventos de auditoria por campo con `actor_user_id`, `reason`, `old_value`, `new_value`; vista reducida exacta (conjunto de claves) y completa; anti-enumeracion (403 igual para inexistente/ajena; 404 PA); `include=members`; paginacion con `total`; `snake_case` en toda la respuesta (ninguna clave `camelCase`); una empresa sin manager es un estado valido (E7).
- `backend/tests/parity/test_company_parity.py`: para cada par v1/v2 de la tabla, mismos escenarios del `parity_world` -> mismo codigo de estado y mismos valores tras `to_snake`, salvo `KNOWN_DIFFERENCES` (forma `{items,total}`, `include=members`, 204).

**PR-17.1 [backend-dev]**: implementar casos de uso, `backend/routers/v2/companies.py` y registro en `backend/routers/v2/__init__.py`.
**Verificacion**: `ruff check backend/`; pytest en contenedor; `curl` manual contra `/api/v2/me/companies` con una sesion de desarrollo.

**PR-17.V Version**: MINOR.

---

### PR-18 - API v2: membresias, tarifas e impuestos (X1 parte 3, X3, Q3)

- Rama: `feat/api-v2-membresias-tarifas`. Depende de: PR-17. Reviewers: `code-reviewer`, `security-reviewer`, `database-reviewer`. Version: MINOR. Migracion: NO.

**Endpoints (`snake_case`; politica identica a v1 final):**
| v2 | Sustituye en v1 | Politica | Cuerpo / respuesta |
|---|---|---|---|
| `GET /v2/companies/{company_id}/members?is_active=bool` | `GET .../members` y el campo `members` de `detailed` | `require_company("manager")` | lista `MemberOut` (`user_id, company_id, role, is_active, sort_order, rates_config, settings, joined_at, updated_at, user`) |
| `POST /v2/companies/{company_id}/members` body `{email}` | `POST .../members/add` | PA | `MemberOut` (201 nueva, 200 existente) |
| `DELETE /v2/companies/{company_id}/members/{user_id}` | idem | PA | `{deleted, deactivated, reason}` |
| `PUT /v2/companies/{company_id}/members/{user_id}/status` body `{is_active: bool}` | `PUT .../status?status=` | PA | `MemberOut` |
| `PUT .../members/{user_id}/role` body `{role}` | idem | PA | `MemberOut` |
| `PUT .../members/{user_id}/rates` body `{rates_config}` | idem | `can_edit_member_rates` | `MemberOut` |
| `PUT .../members/{user_id}/settings` body `{settings}` | idem | `can_edit_member_settings` | `MemberOut` |
| `PUT /v2/companies/{company_id}/members/order` body `{user_ids}` | idem | `require_company("manager")` | `{"message": ...}` |
| `GET /v2/companies/{company_id}/rates` | `GET .../rates-v2` (X3: sin sufijo) | `require_company("manager")` | lista `MemberOut` |
- Casos de uso en `backend/src/application/use_cases/company/`: `add_member.py`, `remove_member.py`, `set_member_status.py`, `set_member_role.py`, `set_member_rates.py`, `set_member_settings.py`, `reorder_members.py`, `list_members.py`, `list_rates.py`. Mismas reglas M1-M6, M9 y eventos de auditoria que v1 (PR-05). No hay guardia de ultimo manager (E7).
- Impuestos y calculo: alinear el motor de `src/` con `crud.calculate_dynamic_work_log` (PR-10): `backend/src/domain/value_objects/tax_configuration.py` pasa de tres tasas fijas a `taxes: Dict[str, Decimal]` construido con una funcion equivalente a `contracts.resolve_taxes`; adaptar `backend/src/domain/services/work_log_calculation_service.py`, `value_objects/calculation_snapshot.py` y `value_objects/rate_definition.py` (`is_gross` con la semantica de P-10, `tax_applied` en el snapshot) y `application/use_cases/work_logs/create_work_log_use_case.py`; actualizar `backend/tests/domain/test_work_log_calculation_service.py` y `tests/application/test_create_work_log_use_case.py`.

**PR-18.0 [tester]**
- `backend/tests/routers/v2/test_v2_members.py`: los mismos casos que `test_members.py` de PR-05 (matriz, add/reactivacion como worker, status, role, delete con y sin turnos, rates con las reglas de gestionada, settings, `order`, filtro `is_active`, M2 en todos los caminos), contra v2 y en `snake_case`.
- `backend/tests/parity/test_members_parity.py`: paridad v1/v2 con `parity_world` para cada fila de la tabla (`KNOWN_DIFFERENCES`: `status` por cuerpo en vez de query; `members/add` -> `POST members`).
- `backend/tests/parity/test_calculation_parity.py` (Q3, nucleo): una rejilla de al menos 60 entradas (unidad `hours`/`days`; `is_gross` verdadero/falso; 0, 1 y 3 impuestos; override igual, distinto y solo en el miembro; extras fijos y por unidad; cruce de medianoche; importe manual) y comprobar que `crud.calculate_dynamic_work_log` y el motor de `src/` devuelven el mismo `net_amount`, `gross_amount` y `duration` (tolerancia 0.01) y el mismo `tax_applied`.

**PR-18.1 [backend-dev]**: implementar casos de uso, `backend/routers/v2/members.py`, registro en `backend/routers/v2/__init__.py` y el alineado del motor de calculo.
**Verificacion**: `ruff check backend/`; pytest completo en contenedor (incluye `tests/parity/`).

**PR-18.V Version**: MINOR.

---

### PR-19 - Frontend transversal (U1, U4, U7, U8, U10, banner "ver como")

- Rama: `feat/frontend-errores-y-empresa-activa`. Depende de: PR-04, PR-06, PR-13. Reviewers: `code-reviewer`. Version: MINOR. Migracion: NO.

**PR-19.0 [tester]** (vitest) `__tests__/lib/api.interceptor.test.ts`: 401, 403, 404, 409, 422 y 5xx producen un toast con el `detail` del backend (cadena); `detail` lista de FastAPI 422 (`[{msg, loc}]`) se une legiblemente; peticion con `meta: { silent: true }` no notifica; 401 no notifica si ya se esta cerrando sesion. `__tests__/components/view-as-banner.test.tsx`: con `user.isReadOnlyView` el banner "Viendo como manager (solo lectura)" / "worker" aparece y el boton "Salir del modo" llama a `switchScope(user.activeCompanyId)`; sin el modo no se renderiza.

**PR-19.1 [frontend-dev]**
- U1: `frontend/src/lib/api.ts`: `api.interceptors.response.use(...)` que, en error, llama a un notificador registrado (`setErrorNotifier(fn)`; `providers.tsx` lo registra con `useToast`). Mapeo: 401 -> sin toast (lo gestiona `AuthContext`); 403, 404, 409, 422, 5xx -> `toast({ variant: "destructive", title, description: detail })` con titulos "Sin permiso", "No encontrado", "Conflicto", "Datos no validos", "Error del servidor". Quitar los mensajes fijos de las mutaciones donde el `detail` aporte mas (revisar los 51 `variant: "destructive"` existentes).
- Banner "ver como" [P-3]: componente `components/view-as-banner.tsx` montado en `(app)/layout.tsx` sobre el contenido: texto "Viendo como <manager|worker> (solo lectura)" y boton "Salir del modo". Con `isReadOnlyView`, `usePermissions` ya devuelve `false` en todos los `can*` (PR-05): comprobar que ningun boton de escritura queda activo en `list`, `calendar`, `manager/*` y `admin/*`; los errores 403 de "solo lectura" los muestra el interceptor.
- U4: empresa suspendida: en `company-switcher.tsx` y `scope-selection-dialog.tsx` no ofrecer empresas con `isActive === false` a worker/manager (el PA si las ve); mensaje especifico "Tu empresa esta suspendida. Contacta con el administrador" cuando `GET /users/me/companies` devuelva vacio o una peticion responda 403 con `Empresa inactiva o suspendida`; un 403 al listar turnos no se pinta como lista vacia (`list/page.tsx`, `work-logs-table.tsx`: estado de error propio).
- U7: `app/(app)/profile/page.tsx` (lineas 94-97): las tarifas son editables solo si se confirma que la empresa es autonoma (`currentCompany?.isManaged === false`); si `currentCompany` es `undefined` -> solo lectura. Usar `usePermissions().canEditRates(user.id)`.
- U8: eliminar `?companyId=` de la URL (sitios listados en la seccion 2, punto 8). La empresa activa sale solo de `useAuth().user.activeCompanyId` (token) y se cambia con `switchScope`. Cambios: `(app)/layout.tsx` (quitar `currentCompanyId`/`querySuffix`/`?companyId=` en los hrefs de los modulos), `company-switcher.tsx` (usar `switchScope(company.id)`), `AuthContext.switchScope` (redirigir sin parametro), y cada pagina que lea `searchParams.get("companyId")` pasa a `user?.activeCompanyId`. `reports/print/page.tsx:21` conserva su parametro solo si es un enlace imprimible fuera de la sesion (consultar antes de quitar). Cambiar de empresa en una pestana la cambia en todas (cookie compartida): documentarlo en el changelog.
- U10: toasts del alta de empresa en espanol (`company-dialog.tsx`); sacar de `app/(app)/**` el correo de contacto fijo a `lib/config.ts` (`CONTACT_EMAIL`, leido de `NEXT_PUBLIC_CONTACT_EMAIL`; el valor se pide al usuario, no se inventa); tipar `updateCompany(companyId: string, data: CompanyUpdatePayload)` y `tax_config` (sin `any`); `components/admin/json-editor.tsx`: validar `NaN`/valores no finitos antes de guardar.
- Tests vitest para cada punto con logica.
- Verificacion: lint, `tsc`, `npm test`, `npm run build`; `grep -rn "companyId=" frontend/src/app frontend/src/components` no debe dejar usos de URL.

**PR-19.V Version**: MINOR.

---

### PR-20 - Frontend: migracion de empresa a v2, endpoint a endpoint (X1/X7, lado cliente)

- Rama: `feat/frontend-empresa-v2`. Items: X1 (cliente), X7. Depende de: PR-17, PR-18, PR-19. Reviewers: `code-reviewer`. Version: MINOR. Migracion: NO.
- Regla: una llamada de empresa pasa a `/v2/` solo cuando su fila de la tabla de PR-17/PR-18 tiene paridad probada (los tests de `tests/parity/` en verde en `develop`). El orden de migracion es el de la lista de abajo; cada paso es una subtarea independiente dentro del PR (o PRs mas pequenos si el usuario lo prefiere).

**PR-20.0 [tester]** (vitest) `__tests__/lib/api/v2/companies.test.ts` y `members.test.ts`: cada funcion del cliente v2 llama la ruta, el metodo y el cuerpo en `snake_case` indicados en las tablas de PR-17/PR-18 y devuelve el tipo declarado; `listCompanies({ include: 'members' })` envia `include=members`.

**PR-20.1 [frontend-dev]**
- Crear `frontend/src/lib/api/v2/types.ts` (tipos `snake_case`: `CompanyFull`, `CompanyReduced`, `MemberOut`, `Page<T>`) y `frontend/src/lib/api/v2/companies.ts` y `members.ts` con las funciones: `listCompanies`, `getCompany`, `createCompany`, `updateCompany`, `deleteCompany`, `listMyCompanies`, `listUserCompanies`, `listMembers`, `addMember`, `removeMember`, `setMemberStatus`, `setMemberRole`, `setMemberRates`, `setMemberSettings`, `reorderMembers`, `listRates`. Todas con `baseURL=/api` (las rutas empiezan por `/v2/...`).
- Estrategia: las pantallas siguen consumiendo los tipos actuales (`camelCase`) mediante un adaptador temporal `lib/api/v2/adapters.ts` (`fromV2Company`, `fromV2Member`) que se elimina cuando la pantalla migra a los tipos `snake_case` [Q-2]. Migrar en este orden, ejecutando `npm test` y `npm run build` tras cada paso: (1) `getMyCompanies` -> `listMyCompanies` (layout, selector, listados de worker/manager); (2) `getCompany` -> `getCompany` v2; (3) `getCompanies`/`getCompaniesDetailed` -> `listCompanies` (con `include=members` donde se usaban miembros); (4) `createCompany`, `updateCompany`, `deleteCompany` (pantallas de PA); (5) `getCompanyMembers`, `addCompanyMember`, `removeCompanyMember`, `updateMemberStatus`, `updateMemberRole`, `updateCompanyMembersOrder`; (6) `getCompanyRates` -> `listRates`, `updateMemberRates`, `updateMemberSettings`; (7) `getUserCompanies` -> `listUserCompanies`. NO migran: dashboard, parte diario, turnos, auditoria, modulos, usuarios, auth (siguen en v1).
- Al terminar: `grep -rn "api\.\(get\|post\|put\|delete\)(.*['\"\`]/companies\|/users/me/companies\|rates-v2\|companies/detailed" frontend/src` solo debe dejar `dashboard-summary` y `daily-report`.

**PR-20.V Version**: MINOR.

---

### PR-21 - Retirada de los endpoints de empresa de v1 (cierre de X1)

- Rama: `chore/retirar-empresa-v1`. Depende de: PR-20 y de que el frontend desplegado ya use v2 en todos ellos. Reviewers: `code-reviewer`, `security-reviewer`. Version: MINOR (cambio incompatible en 0.y.z). Migracion: NO.
- Condicion previa (la comprueba el agente y la cita en el PR): `grep` del paso final de PR-20 limpio; los tests de `tests/parity/` en verde.

**PR-21.0 [tester]**: mover los casos de `tests/routers/test_members.py`, `test_company_admin.py`, `test_company_views.py` a `tests/routers/v2/` si no estan ya cubiertos; borrar `tests/parity/` de empresa (la paridad ya no tiene dos lados) conservando `test_calculation_parity.py` mientras `crud.calculate_dynamic_work_log` y el motor de `src/` convivan; los endpoints retirados responden 404.

**PR-21.1 [backend-dev]**: eliminar de `backend/routers/companies.py` y `backend/routers/users.py`: `GET/POST /companies`, `PUT/DELETE /companies/{id}`, `GET /companies/detailed`, `GET /companies/{id}`, `GET /companies/{id}/members`, `PUT .../members/order`, `POST .../members/add`, `PUT .../members/{uid}/status|role|rates|settings`, `DELETE .../members/{uid}`, `GET .../rates-v2`, `GET /users/me/companies`, `GET /users/{id}/companies`. Se MANTIENEN en v1: `GET /companies/{id}/dashboard-summary`, `GET /companies/{id}/daily-report`, turnos, auth, usuarios, modulos, auditoria. Eliminar de `crud.py` las funciones de empresa y membresia que queden sin uso (confirmar con `grep`; `crud.py` NO se divide, X4) y los esquemas de v1 sin uso. `ruff check backend/` y pytest en contenedor.

**PR-21.V Version**: MINOR.

---

### PR-22 - Rate limit en el gateway (I3)

- Rama: `chore/rate-limit-gateway`. Agente: `devops`. Reviewers: `code-reviewer`. Version: PATCH. Independiente. Migracion: NO.

**PR-22.1 [devops]**: editar `gateway/nginx.conf` y `gateway/nginx.dev.conf`:
- En el bloque `http {}`: `limit_req_zone $binary_remote_addr zone=auth_zone:10m rate=10r/m;` y `limit_req_zone $binary_remote_addr zone=api_zone:10m rate=20r/s;` y `limit_req_status 429;`.
- Una `location ~ ^/api/(token|verify-2fa|refresh-token|logout|auth/)` (antes de `location /api/`) con `limit_req zone=auth_zone burst=10 nodelay;` y el MISMO `proxy_pass http://backend_upstream/;` y cabeceras de `location /api/`. `location /api/` (que sirve tambien `/api/v2/...`) con `limit_req zone=api_zone burst=40 nodelay;`.
- Las cabeceras `add_header` del `server` no se redefinen en las nuevas `location` (el comentario del fichero lo exige).
- Verificacion: `docker compose -f docker-compose.dev.yml run --rm gateway nginx -t` (o `docker run --rm -v $PWD/gateway/nginx.conf:/etc/nginx/nginx.conf:ro,z nginx:alpine nginx -t`); con el stack en marcha (`./bin/dev`): 15 peticiones rapidas a `http://localhost:${GATEWAY_PORT:-8080}/api/token` (POST con credenciales falsas) devuelven 401 las primeras y 429 las ultimas; una peticion normal a `/api/health` y a `/api/v2/ping` no se limita.

**PR-22.V Version**: PATCH.

---

### PR-23 - Cierre: borrar `fiscal_id` (E2 final)

- Rama: `chore/limpieza-fiscal-id`. Depende de: PR-06, PR-11 y de que el script de exportacion se haya ejecutado en produccion (seccion 10). Reviewers: `code-reviewer`, `database-reviewer` (migracion y script). Version: PATCH.
- Migracion: SI (`b7e1a0d10006`). El `downgrade` NO restaura los datos (recrea la columna vacia): si hay que volver atras tras aplicar la migracion, el rollback correcto es RESTAURAR EL BACKUP (seccion 10, paso d). **Paso previo de despliegue obligatorio: seccion 10**, con `repair_fiscal_id.py` (exportacion).
- Precondicion (ACCION DEL USUARIO): consulta E2 de la seccion 7 y el `--dry-run` del script. En produccion no hay `fiscal_id` reales (7.1): la exportacion no es necesaria, pero script y salvaguarda `FISCAL_ID_EXPORTED` se conservan.
- Compatibilidad (seccion 10.3): borrar la columna rompe al backend de la release anterior, que la selecciona. Decision del usuario: un solo PR (codigo y migracion); durante los segundos de `migrate` puede fallar alguna peticion del contenedor anterior y se acepta.

**PR-23.R [backend-dev] Script `backend/scripts/repair_fiscal_id.py`** (exportador; usa `repair_common.py`):
- Lista las empresas con `fiscal_id` REAL: no nulo, no vacio tras `strip` y distinto del valor de semilla `B00000000` (que `seed.py:53`/`dev_seed.py:37` ponian por defecto; se informa aparte como "valor de semilla, descartable").
- `--dry-run` (por defecto): lista cuantas empresas tienen valor real y cuantas solo de semilla; no escribe. `--apply` (exige `--backup-dir`): escribe `fiscal_id_export_<ts>.json` con `[{company_id, company_name, fiscal_id}]` de TODAS las empresas con valor real (y las de semilla marcadas con `"seed_value": true`) fuera del repo (formato y ruta: Q-6; el fichero contiene datos fiscales de empresas, no secretos de acceso; permisos `0600`) y NO modifica la BD. Idempotente (cada ejecucion genera un fichero nuevo con el mismo contenido). Salida `0` siempre que no haya errores; informa del numero de registros exportados.
- Tests (`backend/tests/scripts/test_repair_fiscal_id.py`, SQLite): (1) `--dry-run` no escribe; (2) `--apply` exporta solo los valores reales y marca los de semilla; (3) nulos y cadenas vacias se ignoran; (4) el fichero queda fuera del repo con permisos `0600` y contiene los campos esperados; (5) la BD no cambia; (6) `--apply` sin `--backup-dir` falla.
- Verificacion: `docker compose -f docker-compose.dev.yml run --rm backend pytest tests/scripts/test_repair_fiscal_id.py -q`.

**PR-23.1 [backend-dev]**: migracion `backend/migrations/versions/b7e1a0d10006_drop_companies_fiscal_id.py`: `upgrade`: si existen empresas con `fiscal_id` real (misma definicion que el script) y la variable de entorno `FISCAL_ID_EXPORTED` no es `1` -> `RuntimeError("Hay N empresas con fiscal_id real. Exporta con backend/scripts/repair_fiscal_id.py --apply y define FISCAL_ID_EXPORTED=1 para confirmar (ver docs/empresa/plan-implementacion-empresa.md, secciones 9 y 10)")` sin cambiar nada [Q-8]; si no, `op.drop_column("companies", "fiscal_id")`. `downgrade`: `op.add_column("companies", sa.Column("fiscal_id", sa.String(), nullable=True))` (sin datos). Quitar `fiscal_id` de `models.Company`, esquemas y frontend va en este mismo PR. `grep -rn "fiscal_id\|fiscalId" backend frontend/src` solo debe devolver la migracion baseline, esta migracion y el script.
- Test `backend/tests/test_migration_fiscal_id.py` (marcador `postgres`): con un valor real y sin `FISCAL_ID_EXPORTED=1` `upgrade` lanza `RuntimeError` y la columna sigue; con `FISCAL_ID_EXPORTED=1` pasa; solo con valores de semilla pasa sin la variable; `downgrade` recrea la columna vacia; `Company` no tiene la columna.
- A3 (trigger de `updated_at`) queda FUERA [P-16].

**PR-23.V Version**: PATCH. CHANGELOG `### Cambios Internos`: `backend/scripts/repair_fiscal_id.py` y variable `FISCAL_ID_EXPORTED`.

## 6. Mapa de pruebas Q1 (caso -> bloque donde se prueba)

| Caso de Q1 | Bloque |
|---|---|
| Aislamiento entre empresas (dashboard, billing, turnos, miembros, modulos) | PR-03 |
| Escalada por `switch-scope` | PR-04 |
| Worker crea turno en gestionada y en autonoma | PR-08 |
| PA sobre empresa suspendida | PR-03 |
| PA "ver como": solo lectura | PR-03, PR-04, PR-05 |
| Manager cambia `is_active` o `is_managed` (403) | PR-06 |
| Manager desactiva miembros (403) | PR-05 |
| `is_managed` de true a false (sin recalculo) | PR-06 |
| Tokens `2fa_pending`, `impersonated` y caducado | PR-01 (2fa_pending), PR-04 (impersonated), PR-03 (caducado) |
| Usuario o membresia desactivados con token vigente | PR-01 (usuario), PR-03 (membresia) |
| Totales sobre el rango completo (> 2000 filas) | PR-07 |

## 7. Comprobaciones de datos previas (solo lectura) y su script de reparacion

Las ejecuta quien tenga acceso a la BD (los agentes no lanzan `./scripts/sync_db.sh` ni leen `.env`): **ACCION DEL USUARIO**. Todas son `SELECT`. La columna "Script" enlaza cada consulta con el script de la seccion 9 que la resuelve (el `--dry-run` del script hace la misma comprobacion con mas detalle, asi que la consulta es opcional cuando hay script) y con el bloque; "Bloquea?" indica si la migracion aborta si hay datos.

| Para | Consulta | Script | Bloque | Bloquea? |
|---|---|---|---|---|
| S3 | `SELECT count(*) FROM users WHERE is_active IS NULL;` | - (el codigo trata `NULL` como activo) | PR-01 | No. RESUELTA en produccion: 0 filas |
| Cuantos PA | `SELECT count(*) FROM users WHERE role = 'admin' AND is_active;` | - | PR-05 (M9) | No. RESUELTA en produccion: 1 PA activo |
| T8 | `SELECT user_id, count(*) FROM work_logs WHERE company_id IS NULL GROUP BY user_id;` | `repair_work_log_company.py` | PR-09 | Si (aborta si quedan turnos sin empresa). RESUELTA en produccion: 0 turnos sin empresa, PR-09 pasa sin reparar |
| T1, M5 | `SELECT w.company_id, w.user_id, m.is_active, count(*) FROM work_logs w LEFT JOIN company_members m ON m.user_id = w.user_id AND m.company_id = w.company_id WHERE w.company_id IS NOT NULL AND (m.user_id IS NULL OR m.is_active = false) GROUP BY 1,2,3;` | - (los turnos antiguos no se tocan) | PR-08 | No (informativa). RESUELTA en produccion: 0 filas |
| P1, S1 | `SELECT company_id, user_id FROM company_members WHERE role = 'admin';` | - | PR-03, PR-05 | No (informativa). RESUELTA en produccion: 0 membresias con rol `admin` |
| E7 | `SELECT c.id, c.name FROM companies c WHERE NOT EXISTS (SELECT 1 FROM company_members m WHERE m.company_id = c.id AND m.role = 'manager' AND m.is_active);` | - | PR-06 (solo documentacion del procedimiento de recuperacion) | **No. No es precondicion**: una empresa sin manager es un estado valido. Informativa en produccion: 7 de 8 empresas sin manager activo |
| M3 | `SELECT u.id FROM users u WHERE u.default_company_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM company_members m WHERE m.user_id = u.id AND m.company_id = u.default_company_id AND m.is_active);` | - (la validacion actua solo al escribir) | PR-05 | OBSOLETA (Q-10 resuelta: `default_company_id` se elimina, PR-05.D). No es precondicion ni hace falta reparar los 2 usuarios con valor obsoleto de produccion; la consulta se conserva solo como informativa hasta aplicar PR-05.D |
| M8 | `SELECT c.id, (SELECT count(*) FROM company_members m WHERE m.company_id = c.id) AS miembros FROM companies c WHERE c.name = 'Personal';` | - | PR-05 (decide si se quita el auto-join) | No (informativa). RESUELTA en produccion: 0 empresas "Personal" |
| E1 | `SELECT id, name, length(name) FROM companies WHERE name IS NULL OR length(btrim(name)) = 0 OR name <> btrim(name) OR length(name) > 120;` | `repair_company_names.py` | PR-06 | Si (aborta si quedan nombres no validos). RESUELTA en produccion: nombres validos, PR-06 pasa |
| F1 (impuestos) | `SELECT id, name, tax_config FROM companies;` y `SELECT DISTINCT k FROM company_members m, jsonb_each(m.rates_config) e(t, v), jsonb_object_keys(CASE WHEN jsonb_typeof(v->'tax_overrides') = 'object' THEN v->'tax_overrides' ELSE '{}'::jsonb END) k;` | `repair_tax_values.py` | PR-10 | Si (aborta con valores fuera de [0,1] o no numericos, o con un `extra` distinto de 0 / no numerico). RESUELTA en produccion: todo en 0..1 y los 14 `extra` valen 0 (los elimina la migracion) |
| F3 (settings) | `SELECT id, name, settings FROM companies;` | `repair_settings_definitions.py` | PR-11 | Si (aborta con claves desconocidas). Produccion: las claves legacy detectadas estan todas cubiertas (mapeadas, retiradas, `allowed_rates` conservada o `cost_markup` eliminada con copia previa) |
| F4 (tipos de turno) | `SELECT DISTINCT d.value->>'unit' AS unit, d.value ? 'is_range' AS tiene_is_range FROM companies c, jsonb_each(c.worklog_definitions) d;` | `repair_settings_definitions.py` | PR-11 | Si (aborta con `unit` fuera de `hours`/`days`/`fixed` o `label` invalido). RESUELTA en produccion: `unit` days/hours/fixed y 1 tipo sin `unit` con `is_range` (se fija `days`) |
| Item B3 del catalogo | `SELECT company_id, module_id, count(*) FROM module_subscriptions WHERE company_id IS NOT NULL GROUP BY 1,2 HAVING count(*) > 1;` y `SELECT id FROM module_subscriptions WHERE (scope = 'company' AND company_id IS NULL) OR (scope = 'user' AND user_id IS NULL);` | - | PR-14 | No (informativa). RESUELTA en produccion: sin suscripciones duplicadas |
| E2 | `SELECT count(*) FROM companies WHERE fiscal_id IS NOT NULL AND btrim(fiscal_id) <> '' AND fiscal_id <> 'B00000000';` | `repair_fiscal_id.py` (exporta) | PR-23 | Si, salvo `FISCAL_ID_EXPORTED=1`. RESUELTA en produccion: sin valores reales (no hace falta exportar; se conserva la salvaguarda) |

Comprobacion manual adicional (P-9, **ACCION DEL USUARIO**): que el `.env` de produccion no define `DEV_LOGIN_BYPASS` verdadero ni `ENVIRONMENT`/`NODE_ENV` igual a `development`.

### 7.1 Resultados de produccion

Fuente: copia del backup de produccion de 2026-10-18 00:00, restaurada y anonimizada en local (seccion 10.2, paso e). Solo consultas agregadas. Las filas de la tabla de arriba marcadas como RESUELTA/ABIERTA salen de aqui.

- Totales: 7 `users`, 8 `companies`, 93 `work_logs`, 13 `company_members`.
- Revision de Alembic: produccion esta en `737f741df8a7`; el head del repo es `8f10a2b3c4d5` (`is_active` e `is_managed` en `companies`), que produccion aun no tiene. Los ensayos de migracion con la copia empiezan con `alembic upgrade head`.
- Sin turnos con `company_id` nulo (PR-09 pasa sin reparar). Sin turnos de miembros inactivos ni sin membresia (T1, M5). Sin membresias con rol `admin`. Sin empresas "Personal" (M8). Nombres de empresa validos (PR-06 pasa). Sin `users.is_active` nulo (S3). Sin suscripciones duplicadas (B3).
- `fiscal_id` sin valores reales: PR-23 no necesita exportacion, pero conserva la salvaguarda `FISCAL_ID_EXPORTED`.
- 1 PA activo. 7 de 8 empresas sin manager activo (E7): informativo, no bloquea.
- 2 usuarios con `default_company_id` sin membresia activa (M3): RESUELTO. Q-10 cerrada: la columna se elimina y esos usuarios caen en el fallback por `sort_order` del login (PR-04); no hace falta script ni reparacion.
- Impuestos: `tax_config` usa `irpf_base` (6 empresas) y `social_security` (7), todos en 0..1. `tax_overrides` usa `extra` (14), `irpf` (14) y `ss` (10). Los 14 `extra` valen 0 y no estan en el `tax_config` de su empresa: la migracion de PR-10 los elimina.
- `settings` con claves legacy (empresas que las tienen): `billing` (3), `features` (3), `input_mode` en la raiz (3), `allow_coordination` (1), `allow_tutorial` (1), `allowed_rates` (1, se conserva en el contrato), `modules` (5), `business_logic` (2), `worker_experience` (1). Mapeo: `features.*` -> `modules.*` (`coordination`, `night_shifts`, `pickup_point`, `supplements`, `tutorials`, `worker_daily_report`) e `input_mode` de la raiz -> `worker_experience.input_mode`.
- `cost_markup`: solo MasSki tiene `billing.cost_markup_percent = 32.0` (porcentaje, no fraccion); Querkus y Surf in Comporta tienen `business_logic.cost_markup = 0`. Se elimina del contrato (PR-11); el script guarda el valor en el backup antes de borrarlo.
- `worklog_definitions`: `unit` con valores `days`, `hours` y `fixed`. 1 tipo (Querkus.campamentos) sin `unit` y con `is_range` verdadero -> `days`. 2 tipos `fixed` (Querkus.dias_sueltos, Xanadu.entreno_fijo), validos en el contrato. El caso `unit: hours` con `is_range: true` no existe en produccion; si aparece, decision manual.

## 8. Hechos fuera del alcance anotados (no se ejecutan)

- `auth.verify_reset_token` y `consume_reset_token` llaman a `redis_manager.get_client()`, que no existe; el error se traga en un `try/except` y la proteccion contra reutilizacion solo funciona en memoria del proceso (`_consumed_reset_jtis`). Reportar al usuario aparte.
- `GET /companies/{id}/members/me` y `GET /users/{id}/sessions` que consume el frontend no existen en el backend (hallazgo 13).
- Hallazgos de la revision de seguridad de PR-04, pendientes de decision de diseno (no se ejecutan en PR-04):
  - `POST /refresh-token` solo conoce `sub` (el refresh token no lleva empresa): tras `switch-scope` a la empresa B, el siguiente refresh devuelve la primera membresia por `sort_order` y un PA pierde su `cid`. El plan (PR-04.0, caso 7) lo acepta. Alternativa: guardar la empresa activa en la sesion (`sessions`) o en el refresh token y revalidarla al refrescar.
  - Refrescar una sesion impersonada emite un token `full` de 30 min para el usuario objetivo y alarga la impersonacion. Alternativa: negar el refresh a sesiones impersonadas (el access `impersonated` caduca a los 10 min y el PA vuelve con `stop-impersonation`).
  - `POST /admin/impersonate/{id}` permite impersonar a un usuario inactivo o a otro PA. Alternativa: rechazar ambos casos.
  - `auth.resolve_active_company` devuelve para un PA el `company_id` pedido sin validar su existencia (la valida `switch-scope`). Si otro llamador futuro pasa un `company_id` a un PA, debe validarlo antes.
- Hallazgos de la revision de PR-07, pendientes (no se ejecutan en PR-07):
  - `GET /work-logs/summary` no limita la duracion del rango (hasta unos 26 anos entre 2000-01-01 y hoy+730) y el caso sin empresa no se cachea. Proponer en PR-08, junto al tope de `limit`, un maximo de unos 400 dias con 422.
  - `crud.get_dashboard_summary` y `GET /work-logs/summary` suman solo `duration`; antes el dashboard del frontend calculaba las horas con `end_time - start_time` cuando `duration` era NULL. Comprobado en produccion el 2026-10-20 (solo lectura): 93 turnos y 0 con `duration` NULL, por lo que no hay cambio de cifras; si en el futuro aparecen turnos sin `duration`, rellenarla o calcularla en la agregacion.
  - `byDay` y `uniqueDays` agrupan por `start_date`: un turno multidia que empieza antes del rango pedido aparece en `byDay` con una fecha fuera del rango (los totales siguen cuadrando).
  - La cache de `GET /work-logs/summary` (300 s) solo se invalida al escribir turnos: un cambio de nombre o email de usuario o de membresia puede tardar hasta 300 s en verse en `byUser`.
  - Un worker con el modulo `worker_daily_report` recibe tambien el resumen de toda la empresa con importes (ya veia esas filas en `GET /work-logs`); lo resuelve PR-14.
- Si se elige la opcion B de Q-1, ver la columna "Si se elige la otra" de la tabla 4.2.

## 9. Mecanismo de reparacion de datos previo a las migraciones con riesgo

Objetivo: que ninguna migracion choque con datos reales de produccion y que la correccion de datos sea visible, revisable y reversible, nunca implicita dentro de la migracion.

### 9.1 Reglas generales (aplican a todos los scripts)
- Ubicacion: `backend/scripts/` (hoy no existe; lo crea PR-06.R con `__init__.py`). Un script por tema: `repair_company_names.py` (PR-06), `repair_work_log_company.py` (PR-09), `repair_tax_values.py` (PR-10), `repair_settings_definitions.py` (PR-11), `repair_fiscal_id.py` (PR-23). Todos viajan en la imagen del backend (`COPY . .` del `Dockerfile`) y se ejecutan con `python3 -m scripts.<nombre>` desde `/app`.
- Comun, `backend/scripts/repair_common.py` (lo crea PR-06.R; los demas bloques lo reutilizan):
```python
@dataclass
class RepairReport:
    topic: str
    changes: list[dict]          # lo que --apply escribe (o escribiria)
    manual: list[dict]           # casos de decision manual: NO se tocan
    informational: list[dict]    # avisos que no bloquean
    backup_files: list[Path]     # ficheros escritos (vacio en --dry-run)
    def exit_code(self) -> int   # 0 si manual vacio; 2 si hay decision manual pendiente

def parse_args(argv: list[str] | None) -> argparse.Namespace
    # --dry-run (defecto, accion store_true con default True) / --apply (excluyentes), --backup-dir PATH (o env REPAIR_BACKUP_DIR)
def ensure_backup_dir(path: Path | None, *, required: bool) -> Path | None
    # rechaza (SystemExit con mensaje) un directorio dentro del arbol del repo (resolve() bajo la raiz de backend/..); lo crea con permisos 0700
def write_backup(directory: Path, topic: str, payload: object) -> Path
    # escribe <topic>_<AAAAMMDDTHHMMSSZ>.json (UTF-8, indent=2), permisos 0600; nunca incluye secretos ni hashes de contrasena
def print_report(report: RepairReport) -> None   # texto en espanol: resumen, cambios, pendientes manuales
```
- Modo: `--dry-run` es el DEFECTO y no escribe nada (ni en BD ni en disco); `--apply` escribe. Cada script expone `run(db: Session, *, apply: bool, backup_dir: Path | None) -> RepairReport` (probable en tests) y `main(argv=None) -> int` (devuelve el codigo de salida: `0` limpio, `2` pendientes de decision manual, `1` error).
- Idempotentes: ejecutar dos veces `--apply` deja la BD igual que una; sin efectos acumulativos.
- Transaccionales: cada `--apply` hace UN `commit` al final; si algo falla, `rollback` y no queda cambio parcial en BD. (Los ficheros de backup se escriben ANTES del commit.)
- Las migraciones NO reparan: solo comprueban y abortan con `RuntimeError` y mensaje claro (cuantos registros, ids o rutas, y que script ejecutar) si quedan datos sin arreglar, sin cambiar nada. Como el DDL es transaccional (hallazgo 19), un aborto deja la BD intacta.
- Ficheros de backup/listas: fuera del repo versionado, sin secretos [Q-6]. Ruta propuesta: `${BACKUP_DIR}/repairs/` (el mismo directorio que ya monta `pgbackups`; en el contenedor `/backups/repairs`). Los scripts se niegan a escribir dentro del repo.
- Conexion: los scripts usan `database.SessionLocal` (mismas variables que la app). Ningun agente los ejecuta contra produccion: en produccion los ejecuta el usuario (**ACCION DEL USUARIO**). Los agentes solo los prueban con SQLite en los tests y en la BD de desarrollo local.
- Tests de cada script: en `backend/tests/scripts/` con SQLite (fixtures de PR-00); las migraciones correspondientes se prueban con marcador `postgres` (abortan con datos sin reparar y pasan tras el script). Todo script tiene al menos: `--dry-run` no escribe, `--apply` escribe lo esperado, idempotencia, negativa a escribir dentro del repo y codigo de salida.
- Reviewers: `database-reviewer` revisa cada script junto a su migracion.

### 9.2 Reglas por script (fijadas por el usuario)
| Script | Bloque | Regla |
|---|---|---|
| `repair_company_names.py` | PR-06 | Nombre nulo, vacio o solo espacios -> `"Empresa " + id[:8]`. Espacios sobrantes -> `strip`. Nombre de mas de 120 -> se recorta a 120 y el original completo se guarda en el fichero de backup. Sin decision manual |
| `repair_work_log_company.py` | PR-09 | Turno sin `company_id`: una sola membresia del usuario -> esa empresa; varias o ninguna -> se LISTA para decision manual (sin regla de `default_company_id`, que se elimina). No se usa la empresa con mas turnos ni la "Personal" |
| `repair_tax_values.py` | PR-10 | Impuestos fuera de [0, 1] o no numericos NO se corrigen (no se sabe si `15` es 15 %): se listan. Unica correccion automatica: cadena numerica dentro de [0, 1] -> numero. Un override `extra` distinto de 0 o no numerico se lista como decision manual; los `extra` a 0 solo se informan (los elimina la migracion) |
| `repair_settings_definitions.py` | PR-11 | Informa de las claves de `settings` retiradas (incluida `cost_markup`, cuyo valor guarda en el backup antes de borrarlo) y de las desconocidas que la migracion eliminaria, y de tipos de turno no soportados (`fixed` es valido). Guarda copia previa de `settings` y `worklog_definitions` (el `downgrade` es incompleto). Las desconocidas solo se eliminan con `--drop-unknown` explicito |
| `repair_fiscal_id.py` | PR-23 | `fiscal_id` real -> se exporta a un fichero de backup fuera del repo antes de borrar la columna. No modifica la BD |

## 10. Procedimiento de despliegue de un PR con migracion

Aplica a todo PR que contenga una migracion Alembic: PR-02, PR-05, PR-06, PR-09, PR-10, PR-11, PR-23 y los de v2 (PR-16 a PR-18) si llegasen a migrar. Es un paso previo OBLIGATORIO: la descripcion del PR lo enlaza y el despliegue en produccion no se hace hasta completarlo. Todo comando de produccion lo ejecuta el usuario (**ACCION DEL USUARIO**); los agentes no tocan produccion, ni `sync_db.sh`, ni `.env`.

### 10.1 Hechos verificados que sustentan el procedimiento
- `.github/workflows/deploy-prod.yml` se dispara con cada push a `main` (y `workflow_dispatch`), construye `backend`, `frontend` y `gateway`, los publica en GHCR con tags `latest` y `vX.Y.Z` (la version de `package.json`) y llama al webhook de Komodo. Hay un flujo analogo en `deploy-dev.yml` para `develop` con tags `dev-latest` y `dev-vX.Y.Z`. Fusionar a `main` despliega: por eso el paso b (scripts) se hace ANTES de fusionar a `main`.
- `docker-compose.prod.yml`: servicio one-shot `migrate` (imagen `backend:${IMAGE_TAG:-latest}`, `python3 -m alembic upgrade head`, `restart: "no"`); `backend` depende de `migrate` con `service_completed_successfully` (no arranca si la migracion falla); servicio `pgbackups` (`prodrigestivill/postgres-backup-local`, `SCHEDULE=@daily` por defecto, retencion 7 dias / 4 semanas / 3 meses, destino `${BACKUP_DIR:-/mnt/nas_backups/clases-vesotel}`).
- Verificado en `docker-compose.prod.yml`: el servicio `migrate` ejecuta `python3 -m alembic upgrade head` con la imagen del backend, con `restart: "no"`; `backend` depende de `migrate` con `service_completed_successfully`; `frontend` y `gateway` NO dependen de `migrate`.
- Consecuencia de lo anterior: mientras `migrate` corre, el backend antiguo sigue sirviendo con el esquema ya cambiado. Criterio obligatorio para toda migracion: debe ser compatible con el codigo anterior (anadir antes de quitar; no renombrar ni borrar columnas, tablas ni claves que el codigo antiguo lee en la misma version que las deja de usar). Revision por PR en 10.3.
- `backend/migrations/env.py` ejecuta las migraciones con `context.begin_transaction()` y PostgreSQL tiene DDL transaccional: si una migracion falla, se revierte todo lo que habia pendiente en esa ejecucion (`alembic upgrade head` corre las pendientes en una sola transaccion). No lo cubre: los cambios de datos hechos por los scripts de reparacion (son transacciones aparte) ni nada ejecutado fuera de Alembic.

### 10.2 Pasos
**a) Backup de la BD de produccion antes de desplegar (ACCION DEL USUARIO).**
1. Comprobar que existe el backup diario reciente de `pgbackups` en `${BACKUP_DIR}` (retencion 7 dias/4 semanas/3 meses). El diario NO basta si el PR migra datos: hacer ademas un backup manual inmediatamente antes, por ejemplo (ajustar nombres de contenedor, usuario y base a los reales de produccion; el `pg_dump` en formato custom permite `pg_restore` selectivo):
   `docker exec <proyecto>-postgres pg_dump -U <usuario> -Fc <base> > "${BACKUP_DIR}/pre_<PR-nn>_$(date +%Y%m%dT%H%M%SZ).dump"`.
2. Verificar que el fichero existe, tiene un tamano razonable y se puede listar: `pg_restore --list <fichero> | head`. Anotar la ruta y la version de imagen desplegada ahora (tag SemVer anterior, para el rollback del paso d).

**b) Reparar datos con el script, ANTES de fusionar a `main` (ACCION DEL USUARIO).**
1. Los scripts viajan en la imagen que publica el despliegue de `develop` (`backend:dev-vX.Y.Z`, creada al fusionar el PR a `develop`). Ejecutarlos desde esa imagen contra la BD de produccion, montando el directorio de backups para guardar los ficheros fuera del repo:
   `docker run --rm --network <red-de-la-bd-de-produccion> --env-file <.env de produccion> -v ${BACKUP_DIR}:/backups:z ghcr.io/<repo>/backend:dev-vX.Y.Z python3 -m scripts.<script> --dry-run`
   (los comandos exactos de red y variables dependen de la instalacion de produccion; usa el mismo `env_file` que el servicio `backend`. Los agentes no preparan ni ven ese `.env`).
2. Revisar la salida del `--dry-run` (cambios propuestos y lista de decision manual). Resolver a mano los casos de decision manual (el plan no los resuelve ni elige por ti).
3. Si procede, repetir con `--apply --backup-dir /backups/repairs`. `--backup-dir` debe apuntar a un volumen persistente fuera del repo y de la imagen (el `-v ${BACKUP_DIR}:/backups:z` del paso 1): dentro de un contenedor `run --rm` cualquier otra ruta se pierde al terminar y con ella el nombre original de los recortes. Repetir `--dry-run` hasta que el codigo de salida sea `0` (nada pendiente) y volver a ejecutarlo justo antes de fusionar a `main`, porque entre el `--apply` y la migracion el codigo antiguo puede haber guardado un nombre no valido.
4. Alternativa si no se puede ejecutar desde la imagen de `develop`: fusionar a `main` con la migracion abortando de forma segura (paso c) y ejecutar el script con la imagen `vX.Y.Z` ya publicada; el riesgo es el descrito en Q-9 (frontend y gateway nuevos con backend antiguo durante el fallo). Por eso NO es la ruta recomendada.
5. Ensayo previo: ver el paso b bis (copia anonimizada en un Postgres 16 desechable). Alternativa, restaurar el backup en la BD local con `./scripts/sync_db.sh` (solo administradores, nunca por iniciativa de un agente).

**b bis) Ensayo previo con una copia anonimizada del backup de produccion (ACCION DEL USUARIO).** Recomendado antes de cada PR con migracion; los agentes solo ven los resultados agregados.
1. Postgres 16 desechable: `docker run --rm -d --name pg-ensayo -p 127.0.0.1:55432:5432 -e POSTGRES_PASSWORD=<temporal> postgres:16` (solo 127.0.0.1, sin volumenes: se destruye al parar). Nada de `-v`.
2. Restaurar por stdin con `psql` (el volcado es de `pg_dump` 18 y el servidor es 16): `psql -h 127.0.0.1 -p 55432 -U postgres -d <base> < <volcado.sql>` (descomprimiendo antes por stdin si el backup esta comprimido). El unico error esperado es `unrecognized configuration parameter "transaction_timeout"`; cualquier otro error invalida el ensayo.
3. Anonimizar ANTES de cualquier otra consulta: `users.email`, `users.hashed_password`, `users.first_name`, `users.last_name`, `users.otp_secret`, y `user_sessions.refresh_token`, `user_sessions.ip_address`, `user_sessions.device_name`. Solo se ejecutan consultas agregadas (conteos, claves distintas); no se vuelcan filas con datos personales a la conversacion ni a ficheros versionados.
4. La copia esta en la revision de Alembic de produccion (`737f741df8a7`, anterior al head del repo `8f10a2b3c4d5`): el ensayo empieza con `alembic upgrade head` y despues se ejecutan los scripts de reparacion (`--dry-run`) y la migracion del PR.
5. Al terminar: `docker stop pg-ensayo` (con `--rm` desaparece) y borrar el volcado descomprimido si se creo.

**c) Si la migracion falla, no cambia nada y se queda la version anterior desplegada.**
- La migracion aborta con `RuntimeError` (o por error de BD) dentro de una transaccion: PostgreSQL revierte el DDL y la BD queda en la revision anterior. El servicio `migrate` termina con error, asi que `backend` (que depende de `migrate` con `service_completed_successfully`) no arranca y no se sirve la version nueva del backend. Pasos del usuario: leer el log de `migrate` (el mensaje indica que script ejecutar), corregir los datos (paso b) y relanzar el despliegue (`workflow_dispatch` de `deploy-prod.yml` o redeploy en Komodo).
- A comprobar en Komodo (Q-9, **ACCION DEL USUARIO**): que el contenedor `backend` anterior sigue en pie mientras `migrate` falla y si `frontend` y `gateway` se recrean con la version nueva. Mientras no se confirme, el procedimiento es ejecutar siempre el paso b antes de fusionar a `main`.

**d) Si falla despues de aplicarse la migracion (ACCION DEL USUARIO).**
- Caso general (el `downgrade` es completo: PR-02, PR-06, PR-09, PR-10 y migraciones de v2 si las hubiera): ejecutar `alembic downgrade -1` con la imagen NUEVA (es la que contiene los ficheros de migracion): `docker compose -f docker-compose.prod.yml run --rm migrate python3 -m alembic downgrade -1`, y despues volver a la imagen anterior fijando `IMAGE_TAG` al tag SemVer anterior (`vX.Y.Z` anotado en el paso a) y redesplegando desde Komodo. El orden importa: primero el `downgrade` (necesita la imagen nueva), luego el rollback de imagen.
- PR-11 y PR-23: el `downgrade` NO es completo (PR-11 no recrea las claves de `settings` retiradas ni los `settings` antiguos; PR-23 recrea `fiscal_id` vacia). El rollback correcto es RESTAURAR EL BACKUP del paso a: parar `backend` y `frontend`, `pg_restore --clean --if-exists -d <base> <fichero.dump>` con el volcado `pre_<PR-nn>_...dump`, fijar `IMAGE_TAG` al tag anterior y redesplegar. Se pierden los datos escritos entre el backup y la restauracion: por eso el backup manual se hace justo antes de fusionar. Los ficheros de `repairs/` (copia previa de `settings`/`worklog_definitions`, export de `fiscal_id`) permiten recuperar solo esos datos si se prefiere una restauracion parcial.
- Tras cualquier rollback, dejar anotado en el PR que fallo y que dato lo provoco, y no reintentar el despliegue hasta corregir el script o los datos.

### 10.3 Resumen por PR
| PR | Migracion | Script previo (paso b) | `downgrade` | Rollback correcto tras aplicar |
|---|---|---|---|---|
| PR-02 | `b7e1a0d10001` auditoria | no aplica | completo | `alembic downgrade -1` + imagen anterior |
| PR-05 | `b7e1a0d10007` borrar `users.default_company_id` (PR-05.D; el nombre no sigue el orden de la cadena: `down_revision` = head vigente) | no aplica | incompleto (recrea la columna nula, sin datos) | restaurar el backup |
| PR-06 | `b7e1a0d10002` longitud de nombre | `repair_company_names.py` | completo | `alembic downgrade -1` + imagen anterior |
| PR-09 | `b7e1a0d10003` `company_id` NOT NULL | `repair_work_log_company.py` | completo | `alembic downgrade -1` + imagen anterior |
| PR-10 | `b7e1a0d10004` claves de impuestos | `repair_tax_values.py` | completo en renombrado inverso; no recrea los `extra` en 0 eliminados (sin efecto) | `alembic downgrade -1` + imagen anterior |
| PR-11 | `b7e1a0d10005` settings y tipos de turno | `repair_settings_definitions.py` | incompleto | restaurar el backup |
| PR-23 | `b7e1a0d10006` borrar `fiscal_id` | `repair_fiscal_id.py` | incompleto (sin datos) | restaurar el backup |
| PR-16 a PR-18 | ninguna prevista | segun el caso | segun el caso | aplicar esta seccion si alguna migra |

Ventana de despliegue (decision del usuario): durante los segundos en que corre `migrate`, el contenedor de la release anterior sigue sirviendo con el esquema ya cambiado y alguna peticion puede fallar. Se ACEPTA ese riesgo. v1 y v2 viven en la misma imagen (prefijos `/api/` y `/api/v2/`): el riesgo es solo el del contenedor de la release anterior durante la ventana y es independiente de v1/v2. No se dividen bloques en dos releases ni se anaden releases previas de compatibilidad. Revision por PR del criterio de 10.1 (anadir antes de quitar):
- PR-05: `DROP COLUMN users.default_company_id`: el contenedor anterior selecciona esa columna en consultas de `users` (incluido el login) y fallarian durante la ventana. Aceptado, un solo PR con codigo y migracion; despliegue fuera de horas de uso.
- PR-02: solo anade columnas a `audit_logs`; compatible.
- PR-06: acota la longitud de `companies.name`; compatible porque los nombres de produccion ya son validos (7.1); el codigo antiguo solo fallaria (`DataError`, 500) si creara o editara una empresa con un nombre de mas de 120 caracteres durante la ventana de `migrate`. La migracion recrea la vista `"Work Logs"` y toma `ACCESS EXCLUSIVE` sobre `companies` con `lock_timeout` de 5 s: si no obtiene el bloqueo, aborta sin cambios y se relanza.
- PR-09: `company_id` NOT NULL es compatible solo si el codigo en produccion ya nunca inserta turnos sin empresa. PR-09 exige PR-08 ya desplegado antes; el orden de bloques (seccion 3) lo garantiza.
- PR-10: renombrar `ss`/`irpf` y eliminar `extra` NO es compatible del todo: el backend antiguo lee `ss`/`irpf` en `tax_overrides` y durante la ventana calcularia sin esos overrides. Riesgo acotado: la ventana dura lo que tarda `migrate` y el efecto solo existe con `is_gross=True`. Aceptado por el usuario: un solo PR, sin release previa que lea ambas claves; se despliega fuera de horas de uso.
- PR-11: borrar claves de `settings` y `is_range` tiene el mismo caracter (el codigo antiguo lee `features`, `input_mode`, `is_range`). Mismo tratamiento que PR-10 (un solo PR, fuera de horas de uso) y, ademas, rollback por restauracion de backup.
- PR-23: `DROP COLUMN fiscal_id` NO es compatible: el modelo antiguo seleccionaria una columna inexistente en cada consulta de `companies`. Decision del usuario: un solo PR cuya migracion borra `fiscal_id`; puede fallar alguna peticion del contenedor anterior durante la ventana (aceptado).

## 11. Procedimiento de ejecucion de bloques (Orca)

Cada bloque PR-nn se ejecuta en su propio worktree de Orca con un agente Claude independiente. La sesion principal prepara y revisa; el usuario decide y entrega. Este procedimiento vale para cualquier sesion nueva sin depender de la conversacion donde se definio.

### 11.1 Reparto de responsabilidades

- Usuario: ordena lanzar cada bloque, responde las dudas de diseno que el agente le devuelva, y ejecuta commit, push, PR y merge (regla 3 de `CLAUDE.md`). Tambien ejecuta las acciones de produccion por PR: backup y `--apply` del script de reparacion antes de PR-06, PR-09, PR-10, PR-11 y PR-23 (seccion 10).
- Sesion principal (Claude): comprueba dependencias, crea el worktree, lanza el agente con el prompt, revisa el resultado (`git diff`, `ruff`, `pytest`) cuando el usuario lo pide y cierra los worktrees.
- Agente del bloque: implementa su bloque del plan, delega lo delegable, pasa los reviewers y para a preguntar ante cualquier ambiguedad. No hace commit, push ni PR.
- No hay vigilancia automatica de los agentes (se probo un monitor y no compensa). El usuario los observa en Orca y avisa a la sesion principal con "revisa PR-nn".

### 11.2 Antes de lanzar un bloque

1. Comprobar en la seccion 3 que sus dependencias estan mergeadas en `develop` (`gh pr list --state all` y `git log origin/develop`). Un bloque con "Paralelo con: -" no se lanza en paralelo con otro que toque `auth.py`, `models.py` u otros ficheros comunes.
2. Comprobar la memoria y las notas del proyecto por si el bloque esta aparcado o tiene una decision pendiente (por ejemplo PR-22, aparcado por los proxies delante del gateway).
3. Si el bloque migra: backup y script de reparacion en produccion antes de desplegarlo (seccion 10). El agente solo escribe codigo, script y tests.
4. Elegir la rama `<tipo>/<descripcion-en-espanol>` (regla 2) y los reviewers: `code-reviewer` siempre; ademas `security-reviewer` (auth, endpoints, secretos) o `database-reviewer` (modelos, migraciones) segun el bloque.

### 11.3 Crear el worktree y lanzar el agente

Orca parte por defecto de `main`, que va por detras de `develop` y no tiene el plan. Hay que corregirlo y quitar el prefijo de usuario que Orca anade a la rama. Desde el checkout principal:

```bash
orca worktree create --name <tipo>-<descripcion> --no-parent --base-branch origin/develop --setup run --json
cd <padre>/saas-ski-portal.worktrees/saas-ski-portal/<tipo>-<descripcion>
git reset --hard origin/develop        # solo si el worktree esta vacio
git branch -m "$(git branch --show-current)" <tipo>/<descripcion>
git log --oneline -1                   # debe ser el ultimo commit de develop
orca agent launch --agent claude --worktree path:<ruta-del-worktree> --prompt "$(cat <fichero-del-prompt>)" --json
```

Notas: el prompt se guarda en un fichero y se pasa con `cat` para no escapar comillas. Los worktrees quedan en `<padre>/saas-ski-portal.worktrees/saas-ski-portal/<nombre>` (ruta anidada por la configuracion de Orca). El agente corre con `bypass permissions`, por lo que el prompt debe prohibir explicitamente commit, push, lectura de `.env` y cualquier accion fuera del worktree.

### 11.4 Plantilla del prompt de un bloque

El prompt es un fichero de texto con estas secciones, sustituyendo lo marcado:

- Rol: "Eres el agente de implementacion del bloque PR-nn (<titulo>) del plan docs/empresa/plan-implementacion-empresa.md. Trabaja SOLO dentro de este worktree."
- Pasos iniciales: leer `CLAUDE.md` entero; leer la tabla de la seccion 3 y la seccion del bloque (PR-nn.0 a PR-nn.V) y lo que cite de las secciones 4, 7, 9 y 10; no ampliar el alcance (listar los items del bloque y advertir que el siguiente bloque es otro); comprobar con `git branch --show-current` que la rama es la esperada.
- Reglas de git y estilo: prohibido `git commit`, `git push` y crear PR; sin emojis; ficheros solo con Edit y Write; nunca leer ni imprimir `.env` ni `backend/keys/`; Docker siempre con `docker compose -f docker-compose.dev.yml`; orden de trabajo del bloque (tests que fallan primero, luego implementacion, luego verificacion con `ruff check backend/` y `pytest tests/ -q`).
- Delegacion: ver 11.5, incluyendo que partes del bloque NO se pueden delegar fuera.
- Revision y cierre: lanzar `code-reviewer` y el reviewer especifico del bloque (solo lectura, en paralelo) y corregir hasta aprobar; probar `upgrade` y `downgrade` si hay migracion; subir la version al final (11.6); informar con ficheros cambiados, salida real de las pruebas, hallazgos de los reviewers y delegacion usada; ante cualquier duda o choque con el codigo, parar y preguntar.

### 11.5 Regla de delegacion

- El agente delega las tareas acotadas y mecanicas (buscar usos en el codigo, editar una lista cerrada de ficheros, renombrados, escribir tests de un caso ya definido) en subagentes. Prefiere agentes externos de Orca (codex, cursor, grok) y, si no, subagentes de Claude (`backend-dev`, `frontend-dev`, `tester`, `devops`).
- Antes de usar un agente externo comprueba su cuota. El CLI de Orca no da el porcentaje de uso: si no puede medirlo, se lo pregunta al usuario y no lo da por bueno. Con poca cuota, sin cuota o sin poder comprobarla, usa subagentes de Claude.
- Los agentes externos no leen `CLAUDE.md`: el prompt les ordena leerlo y repite las prohibiciones (sin commit, push ni PR; sin leer `.env`; solo Edit y Write). Un agente por worktree y sin solapar ficheros. El resultado se verifica con `git diff` y pruebas antes de darlo por bueno.
- Nunca se delega fuera la logica de auth, tokens, politica de permisos, aislamiento multiempresa, migraciones, modelos ni seguridad (`CLAUDE.md`). En esos bloques solo se delegan fuera busquedas y listas cerradas de ficheros, con revision. En la practica, los bloques de auth, permisos y migraciones los implementan subagentes de Claude.

### 11.6 Version y conflictos entre bloques paralelos

El incremento SemVer (regla 8) edita `package.json`, `frontend/package.json` y `CHANGELOG.md`, que comparten todos los bloques. Cada agente lo hace al final, sobre `develop` actualizado (`git fetch origin develop`; si develop ya trae cambios de version, sube por encima). El primer bloque que se mergea gana y el otro rebasa o fusiona `develop` y ajusta la version. Los bloques sin version (docs, tooling interno) no tocan esos ficheros.

### 11.7 Revision, entrega y cierre

1. Cuando el agente termina o para a preguntar, el usuario avisa con "revisa PR-nn". La sesion principal lee el terminal del agente, ejecuta `git diff`, `ruff` y `pytest` y da un veredicto corto.
2. Si hay fallos, se devuelven al agente del worktree (en su terminal) hasta que pasen.
3. El usuario ordena `/smart-flow` (commit atomico en espanol, push y PR a `develop`) y el merge cuando pasan los tres checks de CI (Backend QA, Frontend QA, GitGuardian). GitHub no permite aprobar el propio PR; `develop` no exige review.
4. Tras el merge: actualizar `develop` en el checkout principal, cerrar el worktree con la skill `workspace-clean` (baja el stack Docker y borra volumenes) y lanzar el siguiente bloque cuyas dependencias queden cumplidas.

### 11.8 Bloques lanzables en paralelo

Solo se lanzan a la vez bloques que la columna "Paralelo con" de la seccion 3 permite y que no comparten ficheros: PR-01 con PR-02, PR-05 con PR-07, PR-12 con PR-13, PR-14 con PR-15, y PR-22 con cualquiera si no esta aparcado. El resto es secuencial (por ejemplo PR-04 espera a PR-03, porque ambos tocan la capa de autenticacion).
