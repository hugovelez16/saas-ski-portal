# Auditoria

Prefijo: `R-AUD`. Tabla: `audit_logs`. Modelo: `AuditLog` (`backend/models.py`).
Helper: `backend/audit.py` (`AuditAction`, `record_audit`, `REASON_MAX_LENGTH`).
Puerto de dominio: `backend/src/domain/ports/audit_port.py`.

La [auditoria](../glosario.md) es el registro de quien hizo que, cuando y sobre
quien o que. Solo la consulta el administrador de plataforma (PA). Este fichero
sustituye a la seccion 10 de `logica-negocio-empresa.md`, que queda como
historico. Las reglas de suplantacion y de concesion del rol de PA viven en
`acceso.md` y aqui se enlazan: R-ACC-65, R-ACC-66 y R-ACC-67.

## Campos

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `id` | UUID | Si | Identificador |
| `action` | texto | Si | Nombre de la accion (R-AUD-10 a R-AUD-25) |
| `actor_user_id` | UUID | No | Quien ejecuta la accion: PA, manager o worker (R-AUD-03) |
| `company_id` | UUID | No | Empresa afectada; vacio si la accion no es de una empresa |
| `target_user_id` | UUID | No | Usuario sobre el que recae la accion |
| `old_value` | JSONB | No | Valor anterior |
| `new_value` | JSONB | No | Valor nuevo |
| `reason` | texto | No | Motivo, maximo 500 caracteres (R-AUD-02) |
| `extra_data` | JSONB | No | Datos adicionales de la accion; `{}` si no hay |
| `created_at` | fecha y hora | Si | Instante del evento, naive en UTC |
| `admin_user_id` | UUID | No | **Retirada (R-AUD-04).** Se elimina conservando su informacion en los eventos viejos |
| `impersonated_user_id` | UUID | No | **Retirada (R-AUD-04).** Se elimina conservando su informacion en los eventos viejos |

## Reglas

### Evento

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-AUD-01 | El evento se anade a la misma transaccion que el cambio auditado: se confirma o se descarta con el. El registro nunca hace commit por su cuenta | Cerrado | 10 | `backend/audit.py:record_audit` |
| R-AUD-02 | `reason` se recorta a 500 caracteres al registrar | Cerrado | 10 | `backend/audit.py:REASON_MAX_LENGTH` |
| R-AUD-03 | `actor_user_id` es quien ejecuta la accion, no siempre el PA: el manager que anade o desactiva un worker (P6) o edita tipos de turno e impuestos (S1), y el worker de una empresa autonoma que edita sus tarifas (P7, S7) | Cerrado | P6, P7, S1, S7 | `backend/audit.py:record_audit` ya recibe el actor; pendiente de implementar (issue de seguimiento): hoy esas escrituras solo las hace el PA |
| R-AUD-04 | Las columnas heredadas `admin_user_id` e `impersonated_user_id` se eliminan tras conservar su informacion en los eventos viejos; `record_audit` deja de escribir `admin_user_id` | Cerrado | 10, Repaso 2026-11-25 (ronda 2 7.2) | pendiente de implementar (issue de seguimiento): siguen en `backend/models.py:AuditLog` y `backend/audit.py:record_audit` |
| R-AUD-05 | Cada accion usa un nombre de `AuditAction`; el listado de nombres conocidos incluye tambien las acciones heredadas (R-AUD-22, R-AUD-26) | Cerrado | 10 | `backend/routers/audit_logs.py:KNOWN_ACTIONS` |

### Consulta

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-AUD-06 | Solo el PA consulta la auditoria; manager y worker reciben 403 | Cerrado | `revision-base.md` (matriz de permisos) | `backend/routers/audit_logs.py:read_audit_logs` (`require_platform_admin`) |
| R-AUD-07 | La consulta admite filtros por empresa, actor, usuario objetivo, accion y rango de fechas (`from`, `to`) | Cerrado | 10 | `backend/crud.py:get_audit_logs` |
| R-AUD-08 | La consulta se pagina (`limit` 1 a 200, por defecto 50, y `offset`) y ordena por fecha descendente | Cerrado | 10 | `backend/crud.py:get_audit_logs` |
| R-AUD-09 | Si `from` es posterior a `to`, la consulta responde 422 | Cerrado | 10 | `backend/routers/audit_logs.py:read_audit_logs` |

### Acciones vigentes

Contrastadas con `grep -n '= "' backend/audit.py` (16 acciones) y con
`LEGACY_ACTIONS` de `backend/routers/audit_logs.py`.

| ID | Regla: accion y cuando se registra | Estado | Codigo |
|---|---|---|---|
| R-AUD-10 | `company.created`: alta de empresa | Cerrado | `create_company` |
| R-AUD-11 | `company.updated`: cambio de `name` | Cerrado | `common.py:COMPANY_EVENT_ACTIONS` |
| R-AUD-12 | `company.suspended` y `company.reactivated`: cambio de `is_active`, con el actor | Cerrado | `common.py:company_event` |
| R-AUD-13 | `company.managed_changed`: cambio de `is_managed` (S7), solo PA | Cerrado | `common.py:COMPANY_EVENT_ACTIONS` |
| R-AUD-14 | `company.deleted`: borrado de empresa | Cerrado | `delete_company` |
| R-AUD-15 | `company.tax_config_changed` y `company.worklog_definitions_changed`: edicion de impuestos o tipos de turno, por el PA o por el manager (S1) | Cerrado | `common.py:COMPANY_EVENT_ACTIONS`; la edicion por el manager: pendiente de implementar (issue de seguimiento) |
| R-AUD-16 | `company.settings_changed`: cambio de ajustes de empresa (`settings`, editables por manager y PA) o de plataforma (solo PA) (R-EMP-07, R-EMP-08, R-EMP-45 a R-EMP-49) | Cerrado | `common.py:COMPANY_EVENT_ACTIONS`; separacion de ajustes: pendiente de implementar (issue de seguimiento) |
| R-AUD-17 | `member.added` y `member.reactivated`: alta, invitacion/aceptacion (R-MEM-24) y reactivacion de membresia; el manager tambien gestiona workers (P6) | Cerrado | `add_member`; invitaciones y ejecucion por el manager: pendiente de implementar (issue de seguimiento) |
| R-AUD-18 | `member.deactivated` y `member.removed`: desactivacion y borrado de membresia (con turnos se desactiva, sin turnos se borra); el manager tambien desactiva workers (P6) | Cerrado | `set_member_status`, `remove_member`; la ejecucion por el manager: pendiente de implementar (issue de seguimiento) |
| R-AUD-19 | `member.role_changed`: cambio de rol de una membresia, solo PA | Cerrado | `set_member_role` |
| R-AUD-20 | `member.rates_changed`: cambio de tarifa, bruto/neto o impuestos propios, con valor anterior y nuevo; tambien el worker en empresa autonoma (P7) | Cerrado | `set_member_rates`; el worker: pendiente de implementar (issue de seguimiento) |
| R-AUD-21 | `user.status_changed`: activacion o desactivacion de un usuario (ronda 2 7.3) | Cerrado | Definida en `AuditAction` y listada en `KNOWN_ACTIONS`, pero ningun caso de uso la emite: pendiente de implementar (issue de seguimiento) |
| R-AUD-22 | `2fa_reset`: el PA resetea el 2FA de un usuario; pasa al formato comun (`record_audit`) con `actor_user_id` y `target_user_id`, sin usar `impersonated_user_id` (ronda 2 7.2) | Cerrado | pendiente de implementar (issue de seguimiento): hoy `backend/routers/users.py` escribe sin `record_audit` |

Las rutas sin carpeta de la columna "Codigo" son casos de uso de
`backend/src/application/use_cases/company/`. Todas las filas tienen el origen
en la seccion 10 de `logica-negocio-empresa.md`, salvo lo que cita una decision
(P6, P7, S1, S7, Repaso 2026-11-25).

### Acciones nuevas por las decisiones de revision

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-AUD-23 | `impersonation.started`: el inicio de cada suplantacion se registra con el PA como actor y el usuario suplantado como objetivo (R-ACC-67) | Cerrado | P4, O22, Repaso 2026-11-25 | pendiente de implementar (issue de seguimiento): `backend/routers/auth.py:impersonate_user` no registra nada |
| R-AUD-24 | `impersonation.ended`: el fin de cada suplantacion se registra con el PA como actor y el usuario suplantado como objetivo (R-ACC-67) | Cerrado | P4, O22, Repaso 2026-11-25 | pendiente de implementar (issue de seguimiento): `backend/routers/auth.py:stop_impersonation` no registra nada |
| R-AUD-25 | `user.platform_admin_granted`: la concesion del rol de PA, por seed o comando de servidor, se registra en `audit_logs` (R-ACC-65) | Cerrado | P5, O22, Repaso 2026-11-25 | pendiente de implementar (issue de seguimiento): el seed no escribe en `audit_logs` |

### Acciones historicas de turnos

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-AUD-26 | `create_work_log`, `update_work_log`, `delete_work_log` y `create_work_log_bulk` son acciones solo historicas: los eventos existentes se conservan y se consultan, y dejan de escribirse al retirar "ver como" y pasar a suplantacion de solo lectura (R-ACC-53, R-ACC-66) | Retirada | P4, Repaso 2026-11-25 (ronda 2 7.1) | `backend/routers/audit_logs.py:LEGACY_ACTIONS`; `backend/routers/work_logs.py:record_impersonation_audit` sigue escribiendo: pendiente de implementar (issue de seguimiento) |
| R-AUD-27 | No se auditan los turnos en general (creacion, edicion ni borrado); basta el `calculation_snapshot` guardado en cada turno | Cerrado | O21, Repaso 2026-11-25 | no aplica |

### Retencion

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-AUD-28 | La auditoria se conserva siempre, sin purga automatica. El PA puede purgar a mano eligiendo una fecha: ve cuantos registros hay anteriores y confirma en un dialogo; la purga se audita (quien, hasta que fecha y cuantos) y ese apunte no se borra | Cerrado | O20, Repaso 2026-11-25 (ronda 2 7.4) | pendiente de implementar (issue de seguimiento) |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Falla el cambio auditado | No queda evento: la transaccion se descarta | R-AUD-01 |
| `reason` de 600 caracteres | Se guarda recortado a 500 | R-AUD-02 |
| Manager o worker pide `GET /audit-logs` | 403 | R-AUD-06 |
| `from` posterior a `to` | 422 | R-AUD-09 |
| `limit` 500 | 422 (maximo 200) | R-AUD-08 |
| Evento de la accion `create_work_log` anterior a P4 | Se consulta como cualquier otro | R-AUD-26 |
| PA suplantando a un worker | No hay escrituras que auditar; solo inicio y fin | R-AUD-23, R-AUD-24 |
| Evento sin empresa (`2fa_reset`, concesion de PA) | `company_id` vacio; el filtro por empresa no lo devuelve | R-AUD-07 |

## Relacion con otras entidades

- Acceso (`acceso.md`): R-ACC-53 (retirada), R-ACC-65, R-ACC-66 y R-ACC-67
  definen que se audita de la suplantacion y de la concesion del rol de PA.
- Empresa (`empresa.md`): `settings` solo guarda `default_is_gross` (R-EMP-45 a
  R-EMP-49); `company.settings_changed` se mantiene con ese alcance. Empresa
  gestionada o autonoma es `is_managed` (R-AUD-13).
- Membresia (`membresia.md`): altas, invitaciones, bajas y cambios de rol y tarifa
  de R-AUD-17 a R-AUD-20.
