# Empresa

Prefijo: `R-EMP`. Tabla: `companies`. Modelo: `Company` (`backend/models.py`).
Entidad de dominio: `backend/src/domain/entities/company.py`. Contratos JSON:
`backend/contracts.py`.

La [empresa](../glosario.md) es la escuela cliente y el tenant: la unidad de
aislamiento de datos. Puede ser **gestionada** (`is_managed = true`) o **autonoma**
(`is_managed = false`) y puede estar suspendida.

Describe el comportamiento objetivo tras la revision de base (#114,
2026-11-22, [revision-base.md](../producto/revision-base.md)); donde contradice
a la seccion 4 de `logica-negocio-empresa.md` (eliminado, ver historial de git),
manda este fichero. En la columna Codigo,
`pendiente de implementar (issue de seguimiento)` marca que el codigo actual
difiere de la regla; las citas se comprobaron con `grep` el 2026-11-22.

Las reglas de acceso no se repiten aqui, se enlazan: roles (R-ACC-27), que ve
cada rol (R-ACC-54 a R-ACC-57), que puede hacer el worker en cada modo
(R-ACC-70 y R-ACC-71), edicion de tipos de turno e impuestos por el manager
(R-ACC-72 y R-ACC-73) y alta publica B2C (R-ACC-75 a R-ACC-77).

## Campos

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `id` | UUID | Si | Identificador |
| `name` | texto | Si | 1 a 120 caracteres, sin espacios sobrantes, no unico (R-EMP-01) |
| `is_active` | bool | Si | `true` por defecto. `false` = empresa suspendida (R-EMP-24) |
| `is_managed` | bool | Si | `false` por defecto. `true` = gestionada, `false` = autonoma (R-EMP-28) |
| `tax_config` | JSONB | Si en el alta | Impuestos `nombre: fraccion`; `{}` es valido (R-EMP-36) |
| `worklog_definitions` | JSONB | Si | Tipos de turno por clave (R-EMP-40) |
| `settings` | JSONB | Si | Ajustes de empresa editables por el manager (`default_is_gross` y futuros ajustes, R-EMP-45) |
| ajustes de plataforma | JSONB / campos | Si | Plan, limites y modulos; solo los edita y lee el PA (R-EMP-45, R-EMP-49) |
| `created_at`, `updated_at` | fecha | Si | Los pone el ORM; sin trigger de PostgreSQL |

`fiscal_id` no existe (R-ACC-57).

## Reglas

### Atributos

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-01 | `name` es obligatorio, de 1 a 120 caracteres tras quitar espacios sobrantes, y no es unico; `null` o cadena vacia se rechazan (422) | Cerrado | 4.1 | `backend/schemas.py:normalize_company_name` |
| R-EMP-02 | `is_active` decide el acceso a la empresa; solo el PA lo ve (R-ACC-56) y lo cambia | Cerrado | 4.1, O14 | `backend/routers/v2/schemas.py:CompanyReduced` no lo expone |
| R-EMP-03 | `is_managed` fija el modo de la empresa (R-EMP-28); solo el PA lo cambia | Cerrado | 4.1, S7 | `backend/routers/v2/companies.py:update_company` |
| R-EMP-04 | `updated_at` lo actualiza el ORM; no hay trigger de PostgreSQL | Cerrado | 4.1 (P-16) | `backend/models.py` (`Company.updated_at`, `onupdate`) |
| R-EMP-05 | `owner_id` y `fiscal_id` no existen: la responsabilidad la tienen los managers y el PA | Cerrado | O13, 4.1 | columna `fiscal_id` borrada (PR-23) |

### Quien hace que con la empresa

Las filas de empresa de la matriz de permisos (seccion 3 de
[revision-base.md](../producto/revision-base.md)). Toda accion sobre una
empresa exige ademas las comprobaciones de R-ACC-18 a R-ACC-23.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-06 | Solo el PA crea empresas (`POST /companies`); manager y worker reciben 403 | Cerrado | 4.2 | `backend/routers/v2/companies.py:create_company` |
| R-EMP-07 | Solo el PA edita `name` y los ajustes de plataforma (`PUT /companies/{id}` o `/api/v2/admin/...`); manager y worker reciben 403 | Cerrado | 4.2, S1, Repaso 2026-11-25 (ronda 2 2.8) | `backend/routers/v2/companies.py:update_company` |
| R-EMP-08 | El manager edita `worklog_definitions`, `tax_config` y los ajustes de empresa (`settings`, p. ej. `default_is_gross`) de su empresa activa por un endpoint propio; la regla de acceso es R-ACC-72 y R-ACC-73. Sustituye a "un manager no edita nada de la empresa" (4.2) | Cerrado | S1, Repaso 2026-11-25 (ronda 2 2.8) | `backend/routers/v2/companies.py:read_company_manager_settings`, `update_company_manager_settings` (`CompanyManagerUpdateV2`), `frontend/src/components/admin/company-configuration-tab.tsx` |
| R-EMP-09 | Solo el PA suspende, reactiva y cambia `is_managed`; manager y worker reciben 403 | Cerrado | 4.2, S1 | `backend/routers/v2/companies.py:update_company` |
| R-EMP-10 | Solo el PA borra una empresa (`DELETE /companies/{id}`) y solo si no tiene nada asociado | Cerrado | 4.2 | `backend/routers/v2/companies.py:delete_company` |
| R-EMP-11 | Solo el PA lista todas las empresas (`GET /companies`); manager y worker reciben 403 | Cerrado | 4.2 | `backend/routers/v2/companies.py:list_companies` |
| R-EMP-12 | Manager y worker listan las empresas en las que tienen membresia activa (`GET /me/companies`), recibiendo solo `id`, `name` y `role` (R-ACC-81); el PA no tiene membresias y lista todas desde `/api/v2/admin/...` (R-ACC-26, R-EMP-11) | Cerrado | 4.2, Repaso 2026-11-25 (D2, D9) | `backend/routers/v2/companies.py:read_my_companies` (`MyCompanyOut`) |

### Ciclo de vida

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-13 | El alta crea la empresa sin miembros: el PA no puede tener membresias ni siquiera en el seed (R-ACC-26) | Cerrado | 4.3 (P-7), Repaso 2026-11-25 (D2) | `backend/seed.py`, `backend/dev_seed.py` (PA sin membresias; empresa `"Demo"` con manager y worker demo) |
| R-EMP-14 | El alta exige `tax_config` informado; `{}` es valido. No hay valor por defecto | Cerrado | 4.3, 4.4 | `backend/routers/v2/schemas.py` (`tax_config: TaxConfig` sin default) |
| R-EMP-15 | Todo turno pertenece a una empresa y todo usuario tiene su empresa propia, que es una empresa normal de un solo miembro (no existe tipo "personal", P2). Se crea al registrarse (R-ACC-75 a R-ACC-77) y, para los usuarios ya existentes, una vez con un script | Cerrado | P2, Repaso 2026-11-25 (ronda 2 2.2) | `Company.is_personal` y busqueda por nombre `"Personal"` eliminadas, script `backend/scripts/create_personal_companies.py`; pendiente de implementar (migracion del contexto Turnos): `work_logs.company_id` aun admite nulos |
| R-EMP-16 | `PUT /companies/{id}` sin cambios (incluido `{}` o campos con el mismo valor) responde 200 sin modificar nada ni generar evento de auditoria | Cerrado | 4.3 (P-6), Repaso 2026-11-25 (ronda 2 2.3) | `backend/src/application/use_cases/company/update_company.py:UpdateCompanyUseCase` |
| R-EMP-17 | Cada campo que cambia genera un evento de auditoria con valor anterior y nuevo | Cerrado | 4.3 | `backend/src/application/use_cases/company/update_company.py` |
| R-EMP-18 | Suspender es poner `is_active = false`: lo hace solo el PA y queda en `audit_logs` quien, cuando y el motivo. No hay `archived_at` ni `archived_by` | Cerrado | 4.3 | `update_company.py` (`reason` solo con `is_active`) |
| R-EMP-19 | Reactivar es poner `is_active = true`: solo el PA, auditado igual; la interfaz pide confirmacion | Cerrado | 4.3 | `update_company.py`; la confirmacion en el frontend: por comprobar |
| R-EMP-20 | No hay concepto separado de baja: se usa solo "suspender" (`is_active = false`, solo PA) y no se borra nada. El acceso exige los dos interruptores activos: empresa activa y membresia activa (R-MEM-17) | Cerrado | 4.3, Repaso 2026-11-25 (ronda 2 2.1) | `backend/models.py` (`Company.is_active`) |
| R-EMP-21 | Borrar una empresa con miembros, turnos o suscripciones responde 409 y dice que lo impide; sin cascadas. Con la empresa vacia, el borrado se audita | Cerrado | 4.3 | `backend/src/application/use_cases/company/delete_company.py` |
| R-EMP-22 | Una empresa sin manager es un estado valido: el PA anade un manager o cambia el rol de un worker. No hay guardia de ultimo manager | Cerrado | 4.3 (E7), P3 | `backend/routers/v2/members.py:set_member_role` |
| R-EMP-23 | Suspender o reactivar la empresa no cambia sus membresias ni los turnos; los miembros conservan su rol y su estado | Cerrado | analisis-entidad-empresa.md 10.1 (eliminado, ver historial de git) | `backend/src/application/use_cases/company/update_company.py` solo cambia la columna |

### Empresa suspendida

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-24 | Con `is_active = false`, manager y worker reciben 403 en todo endpoint de la empresa (empresa, miembros, tarifas, turnos, dashboard, billing); solo el PA accede (R-ACC-19, R-ACC-20) | Cerrado | 4.5 | `backend/access_policy.py:authorize_company` |
| R-EMP-25 | A manager y worker no se les emite `cid` de una empresa suspendida y su listado la oculta; el PA la ve y puede cambiar a ella (R-ACC-39, R-ACC-40) | Cerrado | 4.5 (P-4) | `backend/auth.py:resolve_active_company`, `backend/routers/v2/companies.py:read_my_companies` |
| R-EMP-26 | Los modulos que vienen de la empresa dejan de valer mientras esta suspendida. La regla de modulos vive en `R-MOD` (#70) | Cerrado | 4.5 | `backend/routers/modules.py` |
| R-EMP-27 | El frontend muestra un mensaje especifico, el selector no ofrece la empresa y un 403 no se pinta como lista vacia | Cerrado | 4.5 | `frontend/src/components/company-switcher.tsx` (selector); el mensaje especifico y el 403 como lista vacia: por comprobar |

### Empresa gestionada y autonoma

La definicion de la bandera vive aqui. Lo que el worker puede hacer en cada
modo vive en R-ACC-70 y R-ACC-71 y no se repite.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-28 | `is_managed = true` es empresa gestionada; `is_managed = false` es empresa autonoma. Es el unico modo: el modo "personal" esta eliminado y no se crean banderas nuevas hasta que haya una regla propia | Cerrado | S7, S10, T1 | `backend/models.py` (`Company.is_managed`) |
| R-EMP-29 | Solo el PA cambia `is_managed`, y el cambio se audita con valor anterior y nuevo | Cerrado | 4.5, S1 | `update_company.py` |
| R-EMP-30 | El cambio de `is_managed` vale desde la siguiente peticion; un frontend abierto sigue mostrando el modo anterior hasta recargar | Cerrado | 4.5 | `backend/access_policy.py:can_write_work_log` lee la bandera de BD |
| R-EMP-31 | El cambio de `is_managed` no recalcula importes ni toca turnos existentes | Cerrado | 4.5 | `update_company.py` solo cambia la columna |
| R-EMP-32 | De gestionada a autonoma, los workers recuperan edicion y borrado de todos sus turnos, tambien de los creados por un manager; de autonoma a gestionada los pierden | Cerrado | 4.5 | `backend/access_policy.py:can_write_work_log` |
| R-EMP-33 | **Retirada (Repaso 2026-11-25, ronda 2 2.6).** No hay permisos opcionales del worker por plan; lo que depende del plan son los modulos y los limites (`R-MOD-22`) | Retirada | S7, Repaso 2026-11-25 (ronda 2 2.6) | no aplica |

### Contratos de los campos JSON

Todo JSONB con estructura fija lleva un modelo Pydantic con tipos, rangos y
`extra="forbid"`; se valida al escribir.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-34 | `tax_config` es un diccionario de claves libres `nombre: fraccion`; cada empresa nombra sus impuestos | Cerrado | 4.4, O9 | `backend/contracts.py:TaxConfig` |
| R-EMP-35 | Nombre de impuesto de 1 a 50 caracteres, valor entre 0 y 1 como fraccion, maximo 20 impuestos, sin claves obligatorias; un valor de tipo incorrecto se rechaza al escribir | Cerrado | 4.4 (P-12) | `backend/contracts.py:TaxConfig`, `TAX_MAX_ENTRIES` |
| R-EMP-36 | `tax_config: {}` es valido y significa sin impuestos; un valor 0 es valido | Cerrado | 4.4 (P-11) | `backend/contracts.py:TaxConfig` |
| R-EMP-37 | El seed y el `dev_seed` no definen `tax_config`; las pantallas recorren los impuestos que existan en lugar de leer `social_security` | Cerrado | revision-base seccion 8 ("Seed") | `backend/seed.py` y `backend/dev_seed.py` (`tax_config={}`); `frontend/src/app/(app)/admin/companies/CompaniesPageClient.tsx` y `frontend/src/components/reports/CompanyPDFReport.tsx` |
| R-EMP-38 | El uso de `tax_config` en el calculo, los overrides del miembro y el bruto/neto son de `R-TAR` (#69) | Cerrado | S2, S4, #69 | no aplica |
| R-EMP-39 | Cada tipo de turno de `worklog_definitions` lleva `unit` (`hours`, `days` o `fixed`), `label` (1 a 60 caracteres) y sus opciones (pluses); un tipo sin `unit` se rechaza y `is_range` se elimina | Cerrado | 4.4, O18, Repaso 2026-11-25 | `backend/contracts.py:WorklogDefinition` (`unit` obligatorio); `is_range` ya no se lee, lo normaliza la migracion `b7e1a0d10005` |
| R-EMP-40 | La clave de un tipo de turno tiene de 1 a 50 caracteres y es inmutable; solo `label` es editable | Cerrado | revision-base seccion 8 ("Tipos de turno") | `backend/contracts.py:WorklogDefinitions`, `backend/src/application/use_cases/company/update_company.py` y `frontend/src/components/admin/worklog-definition-builder.tsx` (`disabled={!typeObj.isNew}`) |
| R-EMP-41 | Un tipo de turno se puede desactivar (deja de salir al crear turnos, los turnos antiguos lo conservan y se puede reactivar). Borrar un tipo solo se permite si no tiene ningun turno: sus tarifas (valgan 0 o no) se borran con el tras un aviso; si tiene turnos, solo se desactiva | Cerrado | revision-base seccion 8, Repaso 2026-11-25 (ronda 2 2.4) | `backend/routers/v2/companies.py:read_worklog_definition_usage`, `backend/src/application/use_cases/company/update_company.py` y `frontend/src/components/admin/worklog-definition-builder.tsx` |
| R-EMP-42 | Se eliminan las pestanas de edicion en JSON crudo. En su lugar, junto a cada configuracion guardada en JSON (tipos de turno, impuestos, ajustes) el PA tiene un boton para ver el JSON en solo lectura | Cerrado | revision-base seccion 8, Repaso 2026-11-25 | `frontend/src/components/admin/readonly-json-dialog.tsx`, `frontend/src/components/admin/company-configuration-tab.tsx` |
| R-EMP-43 | `fields` se elimina de los tipos de turno (`worklog_definitions`); solo se usan las opciones (pluses) del tipo | Cerrado | 4.4, O18, Repaso 2026-11-25 | `backend/contracts.py:WorklogDefinition` (solo `unit`, `label`, `options`, `is_active`) |
| R-EMP-44 | La unidad "libre" queda aplazada y no se ofrece hasta que un cliente la pida | Cerrado (aplazado) | S6, O18, Repaso 2026-11-25 | no aplica |
| R-EMP-51 | Todo porcentaje se guarda como fraccion entre 0 y 1; la pantalla lo muestra y lo pide en 0-100 % y acepta indistintamente punto o coma como separador decimal | Cerrado | Repaso 2026-11-25 (ronda 2 2.5) | `frontend/src/components/admin/tax-config-builder.tsx`, `frontend/src/components/admin/tax-overrides-fields.tsx` (`parsePercentNumber`) |

### Ajustes de empresa (`settings`)

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-EMP-45 | Los ajustes se separan en dos campos distintos: ajustes de empresa (`settings`, que guarda `default_is_gross` y futuros ajustes editables por el manager) y ajustes de plataforma (plan, limites y modulos; solo PA) | Cerrado | S2, Repaso 2026-11-25 (ronda 2 2.8) | `backend/contracts.py:CompanySettings` (`default_is_gross`) y `PlatformSettings` (`plan`, `limits`, `modules`) |
| R-EMP-46 | `default_is_gross` es el valor de bruto/neto que se copia a los miembros nuevos; el uso en el miembro es de `R-TAR` (#69) | Cerrado | S2 | pendiente de implementar (issue de seguimiento) |
| R-EMP-47 | `settings` se valida con `CompanySettings`; una clave desconocida se rechaza al escribir (422) | Cerrado | 4.4 | `backend/contracts.py:CompanySettings` (`extra="forbid"`) |
| R-EMP-48 | Quedan eliminados, sin migracion de datos, `settings.modules`, `allowed_rates`, `worker_experience` y `ui_customization` (P9, S9), y `business_logic.price_type` (S3): el panel muestra siempre bruto y neto | Cerrado | P9, S3, S9 | `backend/contracts.py:CompanySettings` (solo `default_is_gross`, `extra="forbid"`); constructores obsoletos retirados del frontend |
| R-EMP-49 | Los ajustes de empresa (`settings`) los edita el manager (y el PA desde `/api/v2/admin/...`); los ajustes de plataforma los edita y lee solo el PA. La vista reducida de la empresa no lleva `settings` (R-ACC-55) | Cerrado | 4.4, O19, Repaso 2026-11-25 (ronda 2 2.8) | `backend/routers/v2/schemas.py:CompanyReduced` |
| R-EMP-50 | `CompanyMember.settings` se elimina; la regla es de `R-MEM` (#67) | Cerrado | P8, S9, O10 | no aplica |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| `POST /companies` con `name` vacio o solo espacios | 422 | R-EMP-01 |
| `POST /companies` sin `tax_config` | 422 | R-EMP-14 |
| `POST /companies` con `tax_config: {}` | 201 | R-EMP-14, R-EMP-36 |
| Manager pide `PUT /companies/{id}` para renombrar | 403 | R-EMP-07 |
| `PUT /companies/{id}` con `{}` o con los valores actuales | 200, sin modificar nada ni generar auditoria | R-EMP-16 |
| `settings` con la clave `price_type` | 422 (clave desconocida, eliminado en S3) | R-EMP-47, R-EMP-48 |
| `tax_config` con 21 impuestos, nombre vacio o valor 1,5 | 422 | R-EMP-35 |
| Borrar empresa con un turno | 409 con el motivo | R-EMP-21 |
| Suspender una empresa con miembros | `is_active = false`, auditado; los miembros conservan su membresia | R-EMP-18, R-EMP-20 |
| Worker de empresa suspendida pide sus turnos | 403, no lista vacia | R-EMP-24, R-EMP-27 |
| PA cambia `is_managed` de `true` a `false` | Los workers editan sus turnos desde la siguiente peticion; importes intactos | R-EMP-30 a R-EMP-32 |
| Empresa sin manager | Estado valido | R-EMP-22 |

## Relacion con otras entidades

- Acceso (`R-ACC`): roles, vistas, suspension, modo y alta publica (ver arriba).
- Membresia (`R-MEM`): `default_is_gross` se copia al miembro nuevo; borrar la empresa exige que no haya miembros.
- Tarifa (`R-TAR`): consume `tax_config`, los tipos de turno y `default_is_gross`.
- Modulo (`R-MOD`): la suspension anula los modulos de empresa.
- Auditoria (`R-AUD`): suspension, reactivacion, `is_managed`, edicion y borrado.
