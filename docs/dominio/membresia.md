# Membresia

Prefijo: `R-MEM`. Tabla: `company_members`. Modelo: `CompanyMember` (`backend/models.py`).
Entidad de dominio: `backend/src/domain/entities/company_member.py`.

La [membresia](../glosario.md) es la relacion de un usuario con una empresa: lleva
su rol en ella, su estado y sus tarifas. Es el eje del modelo. Este fichero
sustituye a las secciones 2.3 y 5 de `logica-negocio-empresa.md`, que quedan como
historico; donde contradigan a [revision-base.md](../producto/revision-base.md)
manda este (por ejemplo, la tabla 5 decia que solo el PA anade y desactiva
miembros: ya no vale para workers, O25).

Las reglas de acceso se enlazan, no se repiten (`acceso.md`): R-ACC-18 a R-ACC-23
(comprobaciones), R-ACC-27 a R-ACC-32 (roles), R-ACC-34 a R-ACC-36 (empresa
activa), R-ACC-64 y R-ACC-65 (quien anade y quien concede), R-ACC-69 (usuarios
demo manager y worker de cada empresa de prueba), R-ACC-75 a R-ACC-77 (alta
publica B2C: una empresa con el usuario como unico worker, sin manager; es un
caso de alta de membresia, no un tipo de miembro) y R-ACC-79 (rol y estado se
leen de BD en cada peticion, sin cache). La "empresa personal" esta retirada (P2).

## Campos

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `user_id` | UUID | Si | Usuario. Clave primaria junto con `company_id` |
| `company_id` | UUID | Si | Empresa (aislamiento) |
| `role` | enum | Si | `manager` o `worker`; por defecto `worker` (R-MEM-05) |
| `is_active` | booleano | Si | Si es false, el usuario no accede a esa empresa. Por defecto true |
| `sort_order` | entero | No | Orden de presentacion; por defecto 1000 (R-MEM-18) |
| `rates_config` | JSONB | No | Tarifas del miembro; su contenido es de `R-TAR` |
| `settings` | JSONB | No | **Retirada (R-MEM-22).** Se elimina |
| `joined_at`, `updated_at` | fecha y hora | No | Alta y ultima modificacion |

## Reglas

### Modelo y alta

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-01 | Hay una sola membresia por par `(user_id, company_id)` | Cerrado | 2.1, 5 | `backend/models.py:CompanyMember` (clave primaria compuesta) |
| R-MEM-02 | La membresia lleva rol, `is_active`, `sort_order` y `rates_config`. Un usuario puede tener membresias en varias empresas | Cerrado | 2.1 | `backend/models.py:CompanyMember` |
| R-MEM-03 | El PA anade a una empresa usuarios como worker; para que sea manager, cambia luego su rol (R-MEM-14) | Cerrado | P6, matriz de permisos | `backend/routers/v2/members.py:add_member` (`require_platform_admin`) |
| R-MEM-04 | El manager anade workers a su empresa activa; no da de alta managers (403) | Cerrado | P6, R-ACC-64 | pendiente de implementar (issue de seguimiento): hoy `add_member` solo admite al PA |
| R-MEM-05 | Se anade un usuario existente por su email; si no existe responde 404. La membresia nace activa, como worker y con `sort_order` 1000 | Cerrado | 5 | `backend/src/application/use_cases/company/add_member.py` (`AddMemberUseCase`), `backend/models.py:CompanyMember` (`sort_order`) |
| R-MEM-06 | Anadir a quien ya es miembro activo no cambia nada (200). Si su membresia esta inactiva, se reactiva segun R-MEM-11 y R-MEM-12 | Cerrado | 5 | `backend/src/application/use_cases/company/add_member.py`; fuerza `worker` al reactivar: pendiente de implementar (issue de seguimiento) |
| R-MEM-07 | No hay invitaciones por email a usuarios sin cuenta: el PA crea el usuario (R-ACC-11) y luego lo anade | Cerrado (aplazado) | 5 | no aplica |

### Baja

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-08 | Desactivar una membresia conserva sus turnos y corta el acceso a la empresa en la siguiente peticion (R-ACC-18, R-ACC-79). No hay `default_company_id` que reasignar: el siguiente login cae en el fallback de R-ACC-34 | Cerrado | 5 | `backend/src/application/use_cases/company/set_member_status.py`; la cache de acceso se quita: objetivo |
| R-MEM-09 | Eliminar una membresia solo es posible si no tiene turnos ni nada asociado, sin cascadas. Si los tiene, queda inactiva y conserva los turnos | Cerrado | 5 | `backend/src/application/use_cases/company/remove_member.py` (`count_work_logs`; hoy solo comprueba turnos) |
| R-MEM-10 | Desactivar o eliminar: el PA cualquier membresia; el manager solo las de workers de su empresa activa (403 si el destino es manager) | Cerrado | P6, R-ACC-64 | pendiente de implementar (issue de seguimiento): hoy los endpoints exigen PA (`require_platform_admin`) |
| R-MEM-11 | Un worker desactivado lo reactivan el manager de su empresa y el PA. Un manager desactivado lo reactiva solo el PA | Cerrado (worker), Confirmar (manager) | Decision 2026-11-22 (sustituye a "solo PA" de O8); manager: inferencia de R-ACC-64 | pendiente de implementar (issue de seguimiento): hoy solo el PA |
| R-MEM-12 | Reactivar una membresia no cambia su rol: conserva el que tenia | Cerrado | Decision 2026-11-22 (O8) | pendiente de implementar (issue de seguimiento): `set_member_status.py` y `add_member.py` fuerzan `worker` |
| R-MEM-13 | Los turnos de una membresia inactiva se conservan y cuentan en los totales, marcados como inactivos (O6). No se crean turnos nuevos a su nombre (regla de `R-TUR`, #68) | Cerrado | 5, O6 | `backend/src/application/use_cases/work_logs/create_work_log_use_case.py` |

### Roles

R-ACC-27 (solo `manager` y `worker`; el admin de empresa y `owner` estan retirados, O13) y
R-ACC-29 (solo el PA cambia el rol) viven en `acceso.md`.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-14 | Una membresia nueva es `worker`. El rol se cambia por un endpoint propio que identifica al usuario por su id; no viaja en los payloads de tarifas | Cerrado | 5, P6 | `backend/routers/v2/members.py:set_member_role` |
| R-MEM-15 | El cambio de rol solo admite `manager` y `worker`; otro valor responde 422. Pasar al rol que ya tiene no cambia nada ni genera evento | Cerrado | 5, P3 | `backend/src/application/use_cases/company/set_member_role.py` (`ASSIGNABLE_ROLES`). El enum `CompanyRole` aun contiene `admin`: pendiente de implementar (issue de seguimiento) |
| R-MEM-16 | Nadie concede un rol igual o superior al suyo: el worker no concede nada, el manager no cambia roles (R-ACC-64) y el rol de PA no se concede desde la aplicacion (R-ACC-65) | Cerrado | P5, P6, matriz de permisos | `backend/routers/v2/members.py:set_member_role` (`require_platform_admin`); hoy lo evita el decorador de cada endpoint |

### Estados

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-17 | Son tres estados independientes y cada uno corta el acceso por si solo: `User.is_active` (no autentica, R-ACC-10 y R-ACC-16), `CompanyMember.is_active` (no accede a esa empresa, R-ACC-18) y `Company.is_active` (nadie accede salvo el PA, R-ACC-19). Cambiar uno no modifica los otros | Cerrado | 2.3 | `backend/crud.py:update_user_status` solo toca el usuario |

### Orden y lista

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-18 | `sort_order` es solo de presentacion: no da permisos ni prioridad. Su unico efecto fuera de la lista es el fallback de empresa activa (R-ACC-34) | Cerrado | 5 | `backend/auth.py:resolve_active_company` |
| R-MEM-19 | El PA y el manager reordenan los miembros de la empresa; el worker recibe 403. `sort_order` pasa a ser la posicion en la lista enviada y los ids que no son miembros se ignoran | Cerrado | 5, matriz de permisos | `backend/routers/v2/members.py:reorder_members`, `backend/src/application/use_cases/company/reorder_members.py` |
| R-MEM-20 | El PA y el manager ven la lista de miembros, con filtro opcional por `is_active`; el worker recibe 403 | Cerrado | 5, matriz de permisos | `backend/routers/v2/members.py:list_members` |

### Auditoria

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-21 | Alta, reactivacion, desactivacion, eliminacion y cambio de rol se registran en `audit_logs` en la misma transaccion (R-AUD-01, R-AUD-17 a R-AUD-19). Sin cambio real no hay evento | Cerrado | 10 | `backend/src/application/use_cases/company/` (`audit_log.record`) |

### Retirada

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MEM-22 | `CompanyMember.settings` se elimina, con su endpoint, caso de uso, validador y permiso `can_edit_member_settings`, sin migracion de datos. Ninguna regla la usa. Sustituye a O10 (aparcado) | Retirada | P8, S9, O10 | pendiente de implementar (issue de seguimiento): siguen `backend/models.py:CompanyMember.settings`, `backend/routers/v2/members.py:set_member_settings`, `backend/src/application/use_cases/company/set_member_settings.py` y `backend/access_policy.py:can_edit_member_settings` |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Manager anade a un usuario como manager | 403 | R-MEM-04 |
| Manager desactiva a otro manager | 403 | R-MEM-10 |
| Manager reactiva a un worker desactivado | 2xx; sigue siendo worker | R-MEM-11, R-MEM-12 |
| Manager reactiva a un manager desactivado | 403 | R-MEM-11 |
| PA reactiva a un manager desactivado | 2xx; sigue siendo manager | R-MEM-12 |
| Email sin usuario | 404 | R-MEM-05 |
| Anadir a quien ya es miembro activo | 200, sin cambios | R-MEM-06 |
| Eliminar a un miembro con turnos | No se borra; queda inactivo y conserva los turnos | R-MEM-09 |
| Eliminar a un miembro sin turnos | Se borra la membresia | R-MEM-09 |
| Miembro desactivado con token vigente | 403 en la siguiente peticion a esa empresa | R-MEM-08 |
| Usuario desactivado con membresias activas | No se autentica; sus membresias no cambian | R-MEM-17 |
| Manager cambia el rol de una membresia | 403 | R-MEM-16 |
| PA cambia el rol a `admin` | 422 | R-MEM-15 |
| Worker pide la lista de miembros o la reordena | 403 | R-MEM-19, R-MEM-20 |

## Relacion con otras entidades

- Acceso (`R-ACC`): rol y `is_active` deciden R-ACC-18, R-ACC-23 y R-ACC-79.
- Empresa (`R-EMP`): `default_is_gross` se copia al miembro nuevo (R-EMP-46); borrar la empresa exige que no haya miembros.
- Turno (`R-TUR`, #68): crear turnos exige membresia activa del usuario del turno.
- Tarifa (`R-TAR`, #69): el contenido de `rates_config` y quien lo edita.
- Auditoria (`R-AUD`): R-AUD-17 a R-AUD-19.
