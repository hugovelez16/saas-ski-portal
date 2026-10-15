# 10 - Modulos y suscripciones (solo lectura)

Fuentes: `backend/routers/modules.py` (274 lineas), `backend/models.py:203-271`, `backend/crud.py:883-1030`, `backend/routers/utils.py:57-90`, `backend/routers/work_logs.py`, `backend/routers/companies.py`, migracion `backend/migrations/versions/923b0452b91d_add_module_system.py`.

## 1) Relacion modulo-empresa

- Una suscripcion (`ModuleSubscription`) apunta a un `AppModule` y a **una** entidad: empresa (`company_id`) o usuario (`user_id`). Ver `backend/models.py:244-254`.
- La validacion XOR (exactamente uno) solo existe en aplicacion: `backend/crud.py:933-936`. No hay CHECK ni UniqueConstraint en modelo ni migracion.
- `scope` (enum company/user, `backend/models.py:203-205`) es independiente de `company_id`/`user_id`; no se valida coherencia.
- `AppModule.target_scope` ("company"|"user"|"both", `backend/models.py:229-231`) no se comprueba al crear suscripciones (`backend/routers/modules.py:134-142` solo verifica que el modulo exista).

## 2) Por endpoint (`backend/routers/modules.py`)

| Endpoint | Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|---|
| GET /modules | Quien puede / include_inactive | Cualquier autenticado; solo platform admin ve inactivos (resto fuerza False) | modules.py:35-44 | Catalogo global, sin empresa |
| POST /modules | Quien puede | Solo platform admin | modules.py:47-60, 25-29 | Duplicado code_name -> 400 (modules.py:56-58) |
| PUT /modules/{id} | Quien puede | Solo platform admin | modules.py:63-76 | Permite `is_active=false` global (schemas.py:306-313) |
| GET /modules/subscriptions | Quien puede | Admin: todas. Manager con `active_role=="manager"` y `active_company_id`. Resto 403 | modules.py:95-104 | `active_role` viene del JWT |
| GET /modules/subscriptions | Pertenencia a empresa | Manager: `company_id` forzado a su empresa activa; parametro ignorado | modules.py:101-104 | Evita IDOR en lectura; membresia no se revalida |
| GET /modules/subscriptions | company.is_active | NO comprobado | modules.py:106-122 | Empresa inactiva sigue listando |
| GET /modules/subscriptions | Expiracion / estado | Devuelve todas, incluidas expiradas o canceladas | modules.py:113-119 | Sin filtro |
| POST /modules/subscriptions | Quien puede / pertenencia | Solo platform admin; no aplica pertenencia (crea para cualquier company_id/user_id) | modules.py:125-146 | No verifica que la empresa exista (FK -> error de BD) |
| POST /modules/subscriptions | Suscripcion duplicada empresa+modulo | PERMITIDA. Sin check previo ni UniqueConstraint | crud.py:932-952; migracion 923b0452b91d (sin unique) | Duplicados posibles |
| POST /modules/subscriptions | scope vs company_id/user_id | NO validado | crud.py:939-944; schemas.py:330-338 | scope "company" con user_id es aceptado |
| POST /modules/subscriptions | status invalido | ValueError capturado -> 400 | modules.py:139-142; crud.py:944 | OK |
| POST /modules/subscriptions | target_scope del modulo | NO aplicado | modules.py:134-142 | "company" no impide suscripcion de usuario |
| PUT /modules/subscriptions/{id} | Quien puede | Solo platform admin | modules.py:149-162 | OK |
| PUT /modules/subscriptions/{id} | status invalido / expiracion | ValueError sin capturar -> 500. expires_at en pasado admitido (sin job; solo filtro en consulta) | crud.py:961; modules.py:159 (sin try) | Bug: deberia ser 400 |
| DELETE /modules/subscriptions/{id} | Quien puede | Solo platform admin | modules.py:165-175 | OK |
| GET /modules/{id} | Quien puede | Solo platform admin | modules.py:265-274 | Rutas /me y /subscriptions declaradas antes: sin colision |
| GET /modules/me | Quien puede | Cualquier autenticado (worker incluido); rol no interviene | modules.py:181-186 | |
| GET /modules/me?company_id | Pertenencia a empresa | Verificada: CompanyMember con user_id, company_id e is_active=True | modules.py:194-206 | OK; falta is_active de la empresa |
| GET /modules/me | Empresa efectiva sin parametro | Se toma `active_company_id` del JWT; no se revalida membresia | modules.py:208; auth.py:334, 396 | Membresia verificada solo en login (auth.py:261) |
| GET /modules/me | Admin sin empresa | Catalogo activo completo | modules.py:217-220 | Bypass por diseno |
| GET /modules/me | Admin con empresa | Solo suscripciones de empresa (no personales) | modules.py:222-232 | Inconsistente con usuario normal |
| GET /modules/me | Estado y expiracion | status in (active, trial) y expires_at NULL o > utcnow | modules.py:214-215, 228-229, 237-238 | OK |
| GET /modules/me | Modulo inactivo global | Excluido en el bucle final | modules.py:258 | OK |
| GET /modules/me | Calculo final | Union personales + empresa, dedup por module.id | modules.py:234-262 | Sin rol ni company.is_active |

## 3) Calculo de /modules/me (resumen)

- Admin sin `company_id` ni contexto: catalogo activo completo (modules.py:217-220).
- Admin con empresa: solo suscripciones de empresa activas y no expiradas (modules.py:222-232).
- Usuario no admin: suscripciones con `user_id` = yo OR `company_id` = empresa efectiva, status en {active, trial}, no expiradas, modulo activo (modules.py:233-262).
- Rol (`active_role`) no se usa. `company.is_active` no se usa.

## 4) Casos

| Endpoint | Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|---|
| POST /modules/subscriptions | Suscripcion duplicada empresa+modulo | Permitida | crud.py:932-952 | Recomendable indice unico parcial o check previo |
| (global) PUT /modules/{id} | Modulo desactivado globalmente | Acceso denegado en user_has_module y /me; suscripciones intactas | crud.py:990-991; modules.py:258 | Reactivar restaura acceso sin tocar suscripciones |
| PUT y DELETE /modules/subscriptions/{id} | Suscripcion de otra empresa (IDOR) | No aplica a non-admin: solo platform admin escribe | modules.py:157, 170 | Lectura acotada a empresa activa (modules.py:101-104) |
| GET /modules/me?company_id | IDOR con empresa ajena | Bloqueado por membresia activa | modules.py:196-206 | OK |
| DELETE /modules/subscriptions/{id} | Borrar suscripcion en uso | Sin comprobacion; revoca acceso de inmediato | modules.py:172; crud.py:969-974 | Sin soft delete; FK sin ondelete (migracion 923b0452b91d) |
| (global) company.is_active=False | Acceso a modulos | Modulos siguen activos en /modules/me y user_has_module | modules.py:194-262; crud.py:977-1017 | Solo work_logs y companies lo consideran (seccion 5) |

## 5) Feature gating en otros routers

| Endpoint | Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|---|
| work_logs (supervisor) | Consulta modulos | SI: `user_has_module(..., "worker_daily_report")` | work_logs.py:161 | Dentro de bloque con membresia activa |
| work_logs (acceso a empresa) | company.is_active | Comprobado salvo platform admin | work_logs.py:45, 80, 253, 294 | OK |
| companies (lista de empresas) | Consulta modulos | SI: filtra por `worker_daily_report` y company.is_active | companies.py:117-127 | companies.py:124 |
| require_module (dependencia) | Uso en routers | NO aplicado en ningun endpoint; solo en docstring | utils.py:57-82; utils.py:67 | `export_pdf` no protegido en codigo actual |
| require_module vs user_has_module | Bypass admin | require_module y /me admin pasan; user_has_module NO tiene bypass | utils.py:72-74; crud.py:977-1017 | Inconsistencia; revisar |
| Reportes (routers) | Consulta modulos | NO hay referencias a module en otros routers | grep `module` en backend/routers | Reportes no gateados por modulo |

## Hallazgos resumidos

- Suscripcion duplicada: permitida (sin UniqueConstraint ni check).
- `scope` y `target_scope` no se validan contra `company_id`/`user_id`.
- `PUT /modules/subscriptions/{id}` con status invalido devuelve 500 (ValueError sin capturar).
- Empresa `is_active=False` no corta acceso a modulos en `/modules/me` ni en `user_has_module`.
- `require_module` esta definido pero no se usa en ningun endpoint.

## NO DEFINIDO

- Expiracion automatica: no hay job en el alcance leido; solo filtro en consulta. Verificar si existe cron fuera de `backend/routers`.
- Si `routers/auth.py:329` bloquea login de empresa inactiva (contexto no leido; fuera de alcance).
