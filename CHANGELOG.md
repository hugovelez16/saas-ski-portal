# Registro de Cambios (CHANGELOG)

Todos los cambios notables en este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y se rige por las directivas de **Versionado Semantico (SemVer)**.

---

## Estandar de Versionado Semantico

El formato sigue el estandar Semantic Versioning utilizando 3 numeros separados por un punto:
`PRINCIPAL.MENOR.PARCHE` (o `MAJOR.MINOR.PATCH`)

- **MAJOR (Principal)**: Cambios incompatibles con versiones anteriores (rompe la API o modelo de datos no migrado).
- **MINOR (Menor)**: Nuevas funcionalidades compatibles con versiones anteriores.
- **PATCH (Parche)**: Correcciones de errores y bugs compatibles.
- **Desarrollo Inicial**: El desarrollo inicial utiliza una version principal `0` (ej: `0.y.z`).
- **Reinicio de contadores**: Al aumentar MINOR, PATCH se restablece a 0; al aumentar MAJOR, MINOR y PATCH se restablecen a 0.

---

## [0.20.0] - 2026-10-27

### Tipo de Cambio SemVer

- **MINOR**: Frontend transversal (PR-19 del plan de empresa; U1, U4, U7, U8, U10 y banner "ver como"). Sin migracion. No toca el backend.

### Funcionalidades y Mejoras

- **Errores de la API (U1)**: interceptor de respuesta en `lib/api.ts` que muestra un toast con el `detail` del backend en 403, 404, 409, 422 y 5xx (el `detail` en lista del 422 se une de forma legible). El 401 no notifica (lo gestiona `AuthContext`). Las peticiones con `meta: { silent: true }` no notifican.
- **Banner "ver como"**: `components/view-as-banner.tsx` en el layout de la app; avisa del modo de solo lectura del administrador de plataforma y permite salir del modo.
- **Empresa suspendida (U4)**: el selector de empresa y el dialogo de ambito no ofrecen empresas inactivas a worker y manager; un 403 al listar turnos se muestra como error y no como lista vacia.
- **Tarifas del perfil (U7)**: solo son editables si la empresa es autonoma (`isManaged === false`); sin empresa cargada, solo lectura.
- **Contacto y tipado (U10)**: toasts del alta de empresa en espanol, `updateCompany` y `tax_config` tipados sin `any`, y `json-editor` rechaza valores no finitos antes de guardar.

### Cambiado

- **Empresa activa (U8)**: desaparece `?companyId=` de la URL; la empresa activa sale solo de `user.activeCompanyId` y se cambia con `switchScope`. Al estar en una cookie compartida, cambiar de empresa en una pestana la cambia en todas las pestanas abiertas. `reports/print` tambien usa la empresa activa (un administrador de plataforma sin empresa activa ve todas).
- **Correo de contacto (U10)**: el correo fijo de la pantalla sin empresa y del dialogo "Request Access" del login pasa a `CONTACT_EMAIL`, leido de `NEXT_PUBLIC_CONTACT_EMAIL`. Sin valor por defecto: si la variable no esta definida, no se muestra. Se anade como `ARG` en `frontend/Dockerfile` y como `build-arg` en `deploy-dev.yml` y `deploy-prod.yml`; requiere la variable de GitHub Actions del mismo nombre (ver `docs/empresa/tareas-manuales-release.md`).
- **Toasts de error**: se eliminan los toasts locales que duplicaban el del interceptor.

---

## [0.19.0] - 2026-10-27

### Tipo de Cambio SemVer

- **MINOR**: API v2: cimientos y alineacion del dominio (PR-16 del plan de empresa; X1 parte 1, arnes de paridad de Q3). Sin migracion. v1 no cambia de comportamiento.

### Funcionalidades y Mejoras

- **API v2**: se monta el router `/api/v2/` (`backend/routers/v2/`) con `GET /v2/ping` (unica ruta publica), `deps.py` con fabricas de repositorios y `schemas.py` con `V2Model` (snake_case, sin alias). Los endpoints del area empresa llegan en PR-17 y PR-18.
- **Manejador de `DomainException`**: `EntityNotFoundException` responde 404, `ConflictException` 409, `ValidationDomainException` 422 y `UnauthorizedDomainActionException` 403.
- **Dominio y persistencia de `backend/src/`**: `Company` con `is_active`, `is_managed` y `updated_at` y sin `fiscal_id`; `CompanyMember` con `settings` y `updated_at`; nuevos puertos `CompanyRepositoryPort`, `CompanyMemberRepositoryPort` y `AuditLogPort` con sus implementaciones SQLAlchemy; `UserRepositoryPort.count_active_platform_admins`.
- **Arnes de paridad v1/v2** en `backend/tests/parity/` (`to_snake`, `assert_parity`, `call_both`, fixture `parity_world`).

### Cambiado

- **`backend/Dockerfile`**: `PYTHONPATH=/app:/app/src`, para que el codigo de produccion pueda importar `backend/src/`.
- **Repositorio de empresa**: antes no se podia importar por un puerto inexistente.

---

## [0.18.0] - 2026-10-27

### Tipo de Cambio SemVer

- **MINOR**: Recalculo y avisos de turnos, dashboard (PR-12 del plan de empresa). Sin migracion.

### Funcionalidades y Mejoras

- **Recalculo al editar un turno**: editar solo campos sin efecto en el importe (por ejemplo la descripcion) ya no modifica `net_amount`, `gross_amount`, `duration` ni `calculation_snapshot`. Si cambian la hora, las fechas o las opciones del turno, se recalcula con la tarifa, la definicion y los impuestos guardados en el snapshot del turno. Si cambia el `type`, se usa la tarifa vigente del miembro (exige membresia activa, si no 422). Un turno sin tarifa ni importe manual responde 400.
- **Turnos con importe manual**: si una edicion cambia hora, fechas, tipo o extras de un turno manual sin `netAmount` ni `recalculate_with_current_rates=true`, `PUT /work-logs/{id}` responde 409 con `detail.code = "manual_amount_choice"` y no modifica nada. El frontend pregunta: "Conservar importe" (reenvia con `keep_manual_amount=true`, cualquier rol; cada turno manual, tambien en un grupo, conserva su propio importe) o "Calcular por tarifa" (`recalculate_with_current_rates=true`, solo manager y administrador de plataforma). Un worker solo puede conservar el importe.
- **Edicion de grupo atomica**: `PUT /work-logs/{id}?apply_to_group=true` aplica todos los turnos del grupo o ninguno; ante un error se deshace el grupo entero y el mensaje nombra al trabajador afectado.
- **`PUT /work-logs/{id}?recalculate_with_current_rates=true`**: recalcula con la tarifa vigente. Solo manager y administrador de plataforma; un worker recibe 403.
- **Avisos de solape**: `POST /work-logs`, `POST /work-logs/bulk` y `PUT /work-logs/{id}` devuelven `warnings` con `code: "overlap"` y los ids en conflicto cuando el turno se solapa con otro del mismo trabajador y empresa. Solo avisa, nunca rechaza. El frontend lo muestra en un aviso tras guardar.
- **Dashboard**: `GET /companies/{id}/dashboard-summary` responde aunque Redis falle; `workersSummary` incluye a los miembros inactivos (`isActive: false`) y la tabla del equipo muestra la insignia "Inactivo".

### Cambiado

- **`calculate_dynamic_work_log`** sin cambios; `crud._update_single_work_log` decide cuando recalcular. Un cambio en `extraData.opciones` tambien fuerza el recalculo.
- **`frontend/`**: se elimina el componente vacio `NotificationsSection` y su uso en el dashboard.

---

## [0.17.0] - 2026-10-27

### Tipo de Cambio SemVer

- **MINOR**: Vista reducida y completa de empresa en v1 (PR-13 del plan de empresa; P7, P8, U11). Sin migracion. CAMBIA LA FORMA DE LAS RESPUESTAS de empresa: backend y frontend se despliegan juntos (P-1).

### Funcionalidades y Mejoras

- **Vista reducida**: `GET /users/me/companies`, `GET /companies/{id}`, `GET /companies/detailed` (con `members`) y `GET /users/{id}/companies` devuelven a worker, manager y platform admin en "ver como" solo `id`, `name`, `isManaged`, `role`, `isActiveMember`, `ratesConfig`, `worklogDefinitions`, `taxConfig` y `settings` de interfaz (`worker_experience`, `ui_customization`, `modules`, `business_logic.price_type`). Ya no llegan `isActive`, `createdAt`, `updatedAt` ni `allowed_rates`.
- **Vista completa**: solo el platform admin actuando recibe la empresa completa.
- **`GET /users/{id}/companies` (P8)**: el platform admin ve todas las empresas del usuario (incluidas inactivas); el manager solo la empresa del token, si es manager de ella y el usuario es miembro activo; el resto recibe 403. En "ver como", worker recibe 403 y manager queda limitado a la empresa del token.
- **`GET /modules/subscriptions`**: para quien no es platform admin, la empresa embebida solo lleva `id` y `name`.
- **`settings` de miembro**: al leer, solo se fusionan las claves de la lista blanca.

### Cambiado

- **`frontend/`**: `Company` pasa a vista reducida con `isActive`, `createdAt` y `updatedAt` opcionales; nuevo tipo `CompanyFull` para los endpoints solo de platform admin.

---

## [0.16.0] - 2026-10-27

### Tipo de Cambio SemVer

- **MINOR**: Contratos de `settings`, tipos de turno y tarifas (PR-11 del plan de empresa). Con migracion de datos: antes de desplegar hay que hacer backup y ejecutar `backend/scripts/repair_settings_definitions.py` en `--dry-run` y despues con `--apply` (seccion 10 de `docs/empresa/plan-implementacion-empresa.md`).

### Funcionalidades y Mejoras

- **Rollback**: el `downgrade` de la migracion `b7e1a0d10005` es incompleto (solo restaura `is_range` a partir de `unit == "days"`; no recrea las claves retiradas ni los `settings` antiguos). El rollback de esta version requiere RESTAURAR EL BACKUP previo al despliegue (seccion 10, paso d). Los ficheros `settings_definitions_before_<ts>.json` del script permiten recuperar solo esos datos.
- **`settings` de empresa**: contrato estricto (`CompanySettings`) con `business_logic.price_type` (por defecto `net`), `worker_experience`, `ui_customization`, `modules` y `allowed_rates`. `PUT /companies/{id}` con claves desconocidas o tipos incorrectos responde 422. Las respuestas devuelven los `settings` con los valores por defecto aplicados y la lectura de empresas existentes es tolerante (descarta claves desconocidas con aviso).
- **Tipos de turno**: `unit` (`hours`, `days` o `fixed`) es obligatorio y `label` tiene de 1 a 60 caracteres. Un turno cuyo tipo no tiene `unit` responde 422 ("El tipo de turno no tiene unidad definida (unit)").
- **Tarifas**: `PUT .../members/{userId}/rates` valida `base_rate`, `extras` e impuestos (finitos y mayores o iguales que 0), limita a 50 tipos y 64 KiB, y rechaza con 422 los tipos de turno nuevos que la empresa no define.
- **`settings` de miembro**: solo admiten una lista blanca de claves (`notifications`, `ui_preferences`) con tope de 8 KiB.
- **Valores por defecto en el frontend**: se retiran los valores propios del cliente; ahora los entrega el backend. `price_type` pasa de `gross` a `net` y `modules` queda vacio por defecto.

### Cambiado

- **Migracion `b7e1a0d10005`**: solo actualiza datos JSONB de `companies.settings` y `companies.worklog_definitions`, sin alterar columnas. Mapea `features` a `modules`, `billing.price_type` a `business_logic.price_type` e `input_mode` a `worker_experience.input_mode`; retira `allow_tutorial`, `allow_coordination`, `is_managed`, `business_logic.cost_markup` y `billing.cost_markup_percent`; fija `unit` a partir de `is_range` y borra `is_range`. Valida antes de escribir y aborta con `RuntimeError` si hay claves o tipos que no puede normalizar.
- **`frontend/`**: los constructores de `settings` y tipos de turno escriben solo `unit`; se retiran `settings.is_managed`, `cost_markup` y los respaldos a claves antiguas. Se elimina `company-settings-dialog.tsx` (sin uso).
- **`backend/seed.py`**: siembra `modules.worker_daily_report` en lugar de `features`.

### Cambios Internos

- **`backend/scripts/repair_settings_definitions.py`**: script de reparacion previo a la migracion (`--dry-run` por defecto, `--apply` escribe la copia de seguridad, `--apply --drop-unknown CLAVE[,CLAVE]` elimina claves desconocidas).
- **Defaults JSONB mutables**: los `default={}` de `models.py` pasan a `default=dict`.
- **Pendiente (O10)**: `allow_tutorial` y `allow_coordination` siguen en la lista blanca de `settings` de miembro (`MEMBER_SETTINGS_ALLOWED_KEYS` en `backend/contracts.py`) solo porque `member-settings-dialog.tsx` aun los guarda. Hay que eliminarlas de la lista cuando se retire ese dialogo.

---

## [0.15.1] - 2026-10-27

### Tipo de Cambio SemVer

- **PATCH**: Las migraciones `b7e1a0d10007` y `b7e1a0d10002` se aplican sobre bases con vistas manuales de PostgreSQL. Antes de desplegar, inventariar las vistas (paso "a bis" de la seccion 10 de `docs/empresa/plan-implementacion-empresa.md`).

### Corregido

- **Migracion `b7e1a0d10007`**: si la vista manual "Usuarios" lee `users.default_company_id`, se recrea sin la columna (sin `default_company_name`) conservando propietario y privilegios; si otra vista depende de la columna, aborta con `RuntimeError` que la nombra. `downgrade` restaura la columna y la definicion original de "Usuarios".
- **Migracion `b7e1a0d10002`**: elimina y recrea todas las vistas que dependen de `companies.name` (incluidas las que dependen de otras vistas) con su definicion, propietario y privilegios, en lugar de solo "Work Logs".

### Cambios Internos

- **`backend/migration_helpers.py`**: utilidades reutilizables por migraciones para localizar, eliminar y recrear vistas dependientes de una columna.
- **Pruebas**: `backend/tests/test_migration_manual_views.py` (marcador `postgres`, base desechable por prueba).

---

## [0.15.0] - 2026-10-26

### Tipo de Cambio SemVer

- **MINOR**: Impuestos con claves libres (PR-10 del plan de empresa). Con migracion de datos: antes de desplegar hay que ejecutar `backend/scripts/repair_tax_values.py` (seccion 10 de `docs/empresa/plan-implementacion-empresa.md`).

### Anadido

- **`backend/contracts.py`**: `TaxConfig` (nombre libre de 1 a 50 caracteres, tasa numerica de 0 a 1 con 0 permitido, maximo 20 entradas, sin duplicados tras `strip`), `validate_tax_overrides` y `resolve_taxes`.
- **`frontend/`**: `tax-overrides-fields.tsx` y editor de pares nombre/tasa en `tax-config-builder.tsx`.

### Cambiado

- **`POST /companies`**: `taxConfig` es obligatorio (`{}` es valido); `null` o ausente responde 422. `PUT /companies/{id}` y `PUT .../members/{userId}/rates` validan impuestos y `tax_overrides` (422 si no son validos).
- **Calculo de importes (`crud.calculate_dynamic_work_log`)**: los impuestos son las claves libres de la empresa mas los overrides del miembro. Con `is_gross=true` se descuentan todos del bruto; con `is_gross=false` (por defecto) la tarifa es neta y no se deduce ninguno (el bruto devuelto es informativo). El snapshot incluye `tax_applied` y su version pasa a `2.3-free-taxes`. Los turnos ya guardados no cambian.
- **Migracion `b7e1a0d10004`**: renombra `ss` a `social_security` e `irpf` a `irpf_base` en los `tax_overrides` de las tarifas y elimina los `extra` a 0 que la empresa no define. Aborta sin cambios si hay valores no validos.
- **`frontend/`**: los formularios de tarifas y de empresa usan impuestos libres; el control `is_gross` se rotula "Tarifa bruta (se descuentan los impuestos)" / "Tarifa neta (sin deduccion)".

### Cambios Internos

- **`backend/scripts/repair_tax_values.py`**: script de reparacion previo a la migracion (`--dry-run` por defecto, `--apply` explicito).
- **Divergencia temporal**: `backend/src` conserva las tres tasas fijas hasta PR-18.

---

## [0.14.0] - 2026-10-25

### Tipo de Cambio SemVer

- **MINOR**: Consulta de logs de auditoria (PR-15 del plan de empresa). Solo lectura, sin migracion.

### Anadido

- **`GET /audit-logs`**: consulta paginada (`limit` 1..200, por defecto 50; `offset`) de los eventos de auditoria, solo para el administrador de plataforma (manager y worker reciben 403, el administrador en "ver como" tambien). Filtros `company_id`, `actor_user_id`, `target_user_id`, `action` (igualdad exacta), `from` y `to` (422 si `from` > `to`). Orden por fecha descendente y `total` del conjunto filtrado.
- **`GET /audit-logs/actions`**: catalogo de acciones de auditoria.
- **`frontend/`**: pagina `admin/audit-logs` con tabla, filtros, paginacion y detalle JSON de `oldValue`, `newValue` y `extraData`; enlace "Auditoria" en el menu del administrador; `lib/api/audit-logs.ts`.
- **Pruebas**: `backend/tests/routers/test_audit_logs.py` y pruebas vitest de la API y de la pagina.

---

## [0.13.0] - 2026-10-25

### Tipo de Cambio SemVer

- **MINOR**: Parte diario y modulos (PR-14 del plan de empresa). Cambio incompatible en 0.y.z: el worker con el modulo `worker_daily_report` deja de ver la empresa en `GET /work-logs` y `GET /companies/detailed`; la vista de empresa pasa al nuevo endpoint del parte diario.

### Anadido

- **`GET /companies/{company_id}/daily-report?date=`**: miembros activos (y los inactivos con turno ese dia) y turnos del dia de toda la empresa, incluidos los que cruzan medianoche. Exige el modulo `worker_daily_report`. Manager y administrador de plataforma reciben `netAmount` y `grossAmount`; el worker, incluido el administrador en "ver como" worker, recibe un esquema sin esas claves (ausentes, no `null`). `workTypes` devuelve la definicion de cada tipo de turno y cada turno incluye `companyId`.
- **`backend/tests/routers/test_daily_report.py`** y **`test_subscriptions.py`**: pruebas del parte diario, de la retirada de la vista de empresa y de las validaciones de suscripcion.

### Cambiado

- **`backend/schemas.py` y `backend/crud.py`**: `scope`, `status` y `target_scope` de modulos y suscripciones pasan a valores cerrados (422 si no son validos); `scope` exige `companyId` o `userId` coherente; el `target_scope` del modulo debe admitir el `scope`; el alta o la reactivacion de una suscripcion `active` o `trial` duplicada de la misma empresa o usuario y modulo responde 409. Solo afecta a altas nuevas; no hay migracion.
- **`GET /work-logs` y `GET /companies/detailed`**: se elimina la rama "worker con modulo ve la empresa".
- **`frontend/`**: `manager/daily-reports/page.tsx` y `admin/daily-reports/DailyReportPageClient.tsx` usan `getDailyReport` en lugar de `getCompaniesDetailed` y `getWorkLogs` con `limit: 2000`; la pagina de administrador muestra la empresa elegida con un selector. Nuevos `getDailyReport` y tipos del parte diario.

### Cambios Internos

- **Pruebas**: `test_company_access.py` y `test_work_logs_supervisor.py` pasan a esperar que el worker con modulo no vea la empresa.

---

## [0.12.1] - 2026-10-20

### Tipo de Cambio SemVer

- **PATCH**: Reglas de turnos (PR-08 del plan de empresa): membresia activa obligatoria, solo lectura del worker en empresa gestionada, turno inmutable en empresa y usuario, grupo generado por el servidor, validaciones de entrada y tope de `limit`.

### Corregido

- **`backend/routers/work_logs.py`**: crear un turno exige que el usuario del turno sea miembro activo de la empresa (tambien para el administrador de plataforma); `POST /work-logs/bulk` comprueba a todos los usuarios antes de crear ninguno y descarta usuarios duplicados. El worker en empresa gestionada no puede crear, editar ni borrar. `PUT /work-logs/{id}` rechaza (422) cambiar empresa o usuario del turno. Para quien no es administrador de plataforma, un turno inexistente responde 403 igual que uno ajeno.
- **`backend/crud.py`**: `update_work_log` ya no falla con 500 en `apply_to_group` (el grupo se busca en `extra_data` y solo dentro de la misma empresa; la validacion es todo o nada). `update_work_log` y `delete_work_log` filtran por `company_id`. `create_work_log` y `create_work_log_bulk` rechazan miembros inactivos y generan siempre el `group_id` del lote; el `groupId` enviado por el cliente se ignora. Los turnos antiguos de miembros inactivos siguen siendo editables.
- **`backend/schemas.py`**: `companyId` obligatorio al crear; fechas entre 2000-01-01 y hoy + 730 dias y `startDate <= endDate`; `duration`, `netAmount`, `grossAmount` y `amount` no negativos; `userIds` de 1 a 500; nuevo `WorkLogUpdate` con campos opcionales; `WorkLogResponse.groupId` se rellena desde `extra_data`. Las reglas de entrada no se aplican a las respuestas, para no romper la lectura de turnos antiguos.
- **`GET /work-logs`**: `limit` limitado a 1..2000 (decision P-12); `X-Total-Count` sigue reflejando el total real.
- **`frontend/`**: `list/page.tsx`, `calendar/page.tsx`, `work-logs-table.tsx` y `details-dialog.tsx` ocultan crear, editar y borrar turnos segun `usePermissions`; el worker en empresa gestionada ve el aviso "En esta empresa los turnos los registra el equipo gestor". `user-dialog.tsx` muestra el `detail` del 422 del backend y conserva el titular original al editar. `lib/types.ts` retira `groupId` de `WorkLogCreate`.

### Cambios Internos

- **Pruebas**: nuevo `backend/tests/routers/test_work_log_rules.py` y `frontend/src/__tests__/components/work-log-permissions.test.tsx`; `test_company_access.py` pasa a esperar 422 con `limit` por encima de 2000.
- **`docs/empresa/plan-implementacion-empresa.md`**: decision sobre la carrera de `crud.remove_member` anotada en los seguimientos de PR-05.

---

## [0.12.0] - 2026-10-20

### Tipo de Cambio SemVer

- **MINOR**: Gestion de empresa solo plataforma, con migracion y script de reparacion de nombres (PR-06 del plan de empresa). Cambio incompatible en 0.y.z: manager y worker pierden los endpoints de lista, alta y edicion de empresa, y se retira `fiscalId` de las respuestas.

### Anadido

- **`backend/routers/companies.py`**: `DELETE /companies/{company_id}` (204) solo para el administrador de plataforma; responde 409 con los motivos si la empresa tiene miembros, turnos o suscripciones, sin cascadas.
- **`backend/audit.py`**: eventos de empresa `company.created`, `company.updated`, `company.suspended`, `company.reactivated`, `company.managed_changed`, `company.tax_config_changed`, `company.settings_changed`, `company.worklog_definitions_changed` y `company.deleted`, con `reason` opcional al suspender o reactivar.
- **`backend/crud.py`**: `get_company_for_actor`; `update_company` y `create_company` reciben el actor y registran auditoria.
- **`frontend`**: confirmacion con motivo opcional antes de suspender, reactivar o cambiar `isManaged`, y edicion del nombre en el detalle de empresa.

### Seguridad

- **Empresa solo plataforma**: `GET`, `POST`, `PUT` y `DELETE /companies` devuelven 403 a manager, worker y administrador en modo "ver como". Un `PUT` sin cambios responde 422 (`No hay cambios que guardar`).
- El nombre de empresa se normaliza (sin espacios sobrantes, de 1 a 120 caracteres) y `null` o vacio responde 422 en lugar de 500.

### Cambiado

- **`fiscalId`**: se retira de los esquemas, respuestas, seeds, dominio y frontend; la columna se conserva hasta PR-23.
- **`frontend`**: el manager solo ve la tarjeta de modulos activos en la configuracion de empresa; la lista de empresas deja de ofrecer acciones de edicion sin permiso.
- **`docs/empresa/analisis-entidad-empresa.md`**: una empresa sin manager es un estado valido; se documenta el procedimiento de recuperacion (E7).

### Cambios Internos

- **Migracion `b7e1a0d10002`**: limita `companies.name` a 120 caracteres (recrea la vista `"Work Logs"` porque depende de la columna) y aborta con `RuntimeError` si quedan nombres no validos; `downgrade` completo. Requiere el paso previo de despliegue de la seccion 10 del plan.
- **Nuevo `backend/scripts/repair_company_names.py`** (con `repair_common.py`): obligatorio ejecutarlo en `--dry-run` y despues `--apply --backup-dir <directorio fuera del repo>` antes de desplegar (seccion 10 del plan).

## [0.11.0] - 2026-10-20

### Tipo de Cambio SemVer

- **MINOR**: Membresias solo plataforma y endpoints de miembro, con la retirada de `users.default_company_id` (PR-05 del plan de empresa). Cambio incompatible en 0.y.z: se elimina una ruta y cambian los permisos de membresia.

### Anadido

- **`backend/routers/companies.py`**: endpoints `PUT /companies/{company_id}/members/{user_id}/role`, `PUT .../rates`, `PUT .../settings` y `DELETE .../members/{user_id}` (con turnos desactiva la membresia en lugar de borrarla). `GET /companies/{company_id}/members` acepta `status=active|inactive`.
- **`backend/audit.py`**: eventos `member.added`, `member.reactivated`, `member.deactivated`, `member.removed`, `member.role_changed` y `member.rates_changed`.
- **`frontend`**: hook `usePermissions` y funciones `updateMemberRole`, `updateMemberRates`, `updateMemberSettings` y `removeCompanyMember`.

### Seguridad

- **Membresias solo plataforma**: anadir miembro, cambiar estado, cambiar rol, eliminar miembro y `POST /users/{id}/reset-password-email` solo para el administrador de plataforma (403 para manager y worker, y para el administrador en modo "ver como"). Reactivar una membresia fuerza el rol `worker`. Tarifas y ajustes siguen la politica central (`can_edit_member_rates`, `can_edit_member_settings`).
- **Administradores de plataforma (M9)**: un administrador no puede desactivarse ni degradarse a si mismo (403); un cambio que deje la plataforma sin administradores activos se rechaza (409), con bloqueo de filas para evitar la carrera entre dos cambios simultaneos.
- **`PUT /users/me`**: ya no borra nombre y apellidos cuando no se envian o llegan nulos (M4).

### Cambiado

- **Ruta eliminada**: `PUT /companies/{company_id}/members/{user_id}` se sustituye por `role`, `rates` y `settings`.
- **`backend/crud.py`**: `create_user` ya no une al usuario a la empresa "Personal" (sin empresas "Personal" en produccion, M8).
- **`frontend`**: la interfaz oculta a quien no es administrador de plataforma el estado de membresia, el selector de rol, el alta de miembros y el reinicio de contrasena; se retira el selector de empresa por defecto del perfil y el aviso de "no hay empresa por defecto".

### Cambios Internos

- **Migracion `b7e1a0d10007`**: elimina `users.default_company_id`; `downgrade` la recrea nullable y sin datos (el rollback con datos es restaurar el backup). Requiere el paso previo de despliegue con backup (seccion 10 del plan). El codigo deja de leer y escribir la columna en backend v1 y v2, seeds y frontend.

## [0.10.0] - 2026-10-19

### Tipo de Cambio SemVer

- **MINOR**: Agregados de turnos y migracion de pantallas (PR-07 del plan de empresa).

### Anadido

- **`backend/routers/work_logs.py`**: `GET /work-logs/summary` (totales, por tipo, por dia y por usuario sobre el rango completo, con la misma visibilidad que `GET /work-logs`; un worker solo recibe sus propios datos) y cabecera `X-Total-Count` en `GET /work-logs`, expuesta por CORS.
- **`backend/crud.py`**: `count_work_logs` y `get_work_log_summary` con agregacion SQL y cache Redis de 300 s invalidada con `invalidate_dashboard_summary`.
- **`frontend/src/lib/api/work-logs.ts`**: `getWorkLogsPage`, `getAllWorkLogs` (falla si el total supera `maxRows`) y `getWorkLogSummary`.

### Cambiado

- **`backend/crud.py`**: `get_work_logs` ordena con desempate por `id` para que la paginacion sea estable.
- **`frontend`**: el dashboard de empresa, los informes (PDF, impresion y texto), la tabla de turnos de usuario del administrador y el calendario dejan de sumar filas de una pagina o de usar `limit` altos; los totales salen del resumen y los bloques por tipo usan las definiciones de turno de la empresa. El calendario consulta solo el rango visible.

## [0.9.3] - 2026-10-19

### Tipo de Cambio SemVer

- **PATCH**: Token minimo, emision de contexto y "ver como" del administrador de plataforma (PR-04 del plan de empresa).

### Seguridad

- **`backend/auth.py`**: el access token solo lleva `sub`, `scope` y, si hay empresa activa, `cid` (mas `exp`, `iat`, `type` y `jti`); desaparecen `role`, `is_admin` y `cid` nulo. Nuevo `resolve_active_company`: la empresa del token es siempre una membresia activa de una empresa activa (sugerencia del cliente, si no la primera por `sort_order` y `joined_at`); ya no se lee `users.default_company_id`. `view_as` solo se emite para el administrador de plataforma con empresa.
- **`backend/routers/auth.py`**: `POST /auth/switch-scope` deja de aceptar el rol del cliente y acepta `viewAs` (solo administrador de plataforma). Inexistente, ajena o sin membresia responden igual (403); empresa suspendida bloquea a worker y manager pero no al administrador. El login (`company_id` en el formulario) y `POST /verify-2fa` (`companyId`) aplican la misma regla; el token provisional de 2FA no lleva empresa. `switch-scope` se rechaza (403) con un token de impersonacion, que antes se reemitia con 30 min y sin `admin_user_id`.

### Cambiado

- **`frontend`**: `switchScope(companyId, viewAs?)` sin rol; el administrador de plataforma ve "Gestionar", "Ver como manager" y "Ver como worker" (solo lectura); worker y manager un unico boton "Entrar". La ultima empresa se recuerda en `localStorage` (clave `lastCompanyId`) y se envia al login y al paso 2FA.

## [0.9.2] - 2026-10-18

### Tipo de Cambio SemVer

- **PATCH**: Politica central de permisos, cache de acceso y modo "ver como" de solo lectura (PR-03 del plan de empresa).

### Seguridad

- **`backend/access_policy.py`** (nuevo, modulo puro sin FastAPI ni SQLAlchemy): unico sitio que decide quien puede que sobre una empresa. Anti-enumeracion: empresa inexistente, ajena o sin membresia responden igual (403 `No tienes acceso a esta empresa`); el 404 queda solo para el administrador de plataforma.
- **`backend/routers/deps.py`** (nuevo): `authorize`, `require_company`, `require_platform_admin`, `manages_user`, `require_active_member` y `require_module`. Un usuario que no es administrador de plataforma y tiene empresa activa en el token no accede a otra empresa hasta cambiar de scope.
- **`backend/auth.py`**: el rol de plataforma sale de la BD (el claim `is_admin` se ignora) y el rol de empresa de la membresia activa (el claim `role` se ignora). El manager pierde "entrar como worker". El claim `view_as` solo se respeta para un administrador de plataforma con empresa activa; en ese modo todo metodo no seguro se rechaza con `Modo 'ver como' de solo lectura`.
- **`backend/access_cache.py`** (nuevo), **`backend/crud.py`**: cache de acceso (usuario y empresa) con TTL de 60 s e invalidacion al cambiar rol o estado de membresia y estado o modo de la empresa; con Redis caido se lee de BD.
- **`backend/routers/companies.py`, `work_logs.py`, `modules.py`, `users.py`**: los handlers usan `deps` en lugar de las comprobaciones `is_platform_admin` dispersas; los parametros `company_id`, `user_id` y `work_log_id` pasan a `UUID`.

### Corregido

- Una empresa suspendida bloquea para no-administradores los turnos, el billing, el dashboard y `GET /modules/me` (ignora sus suscripciones de empresa).
- Los 403 dejan de incluir `is_manager`, `is_self` e ids.
- **`backend/crud.py`**: `user_has_module` ignora la suscripcion de una empresa suspendida.
- **`backend/routers/work_logs.py`**: `GET /work-logs` valida `skip >= 0` y `limit >= 1`.

### Cambios Internos

- **`backend/redis_config.py`**: backoff de 30 s tras un fallo de Redis para no esperar el timeout en cada llamada.
- **`backend/schemas.py`**: `UserResponse` anade `view_as` e `is_read_only_view`.
- Eliminados `backend/routers/utils.py` y `crud.get_subscriptions` (sin uso); los `print` de depuracion pasan a `logging`.
- **`backend/tests/`**: nuevos `policy/` y `routers/test_company_access.py`; los tests de `governance`, `work_logs_supervisor`, `modules`, `dashboard_summary` y `billing_summary` invocan por HTTP.

---

## [0.9.1] - 2026-10-18

### Tipo de Cambio SemVer

- **PATCH**: Seguridad inmediata de autenticacion (PR-01 del plan de empresa).

### Seguridad

- **`backend/routers/companies.py`**: `update_member_status`, `read_company`, `read_company_rates` y `update_company_member` usan `get_verified_user`; los tokens `2fa_pending` se rechazan en los endpoints de empresa.
- **`backend/auth.py`, `backend/routers/auth.py`**: los usuarios desactivados (`is_active` falso) no acceden con token vigente (401), no inician sesion (403) y su refresh revoca la sesion (401).
- **`backend/routers/users.py`**: eliminado el registro publico `POST /users/`. `POST /users` sigue exigiendo administrador de plataforma.
- **`backend/dev_seed.py`, `backend/main.py`**: el bypass de desarrollo exige `ENVIRONMENT=development` y `DEV_LOGIN_BYPASS` verdadero (`NODE_ENV` ya no cuenta). El arranque aborta si `DEV_LOGIN_BYPASS` esta activo fuera de `development`.
- **`backend/main.py`, `backend/seed.py`**: el sembrado inicial sale del arranque; `seed_initial_data` se omite si ya existe un administrador de plataforma. La membresia sembrada en desarrollo usa el rol `manager`.

### Cambios Internos

- **`backend/tests/routers/test_auth_security.py`**: nuevos tests de PR-01; `test_auth_dev_bypass.py` actualizado al nuevo contrato; `conftest.py` acepta cadenas en columnas UUID bajo SQLite.

---

## [0.9.0] - 2026-10-18

### Tipo de Cambio SemVer

- **MINOR**: Base del registro de auditoria de empresa y membresias (modelo, migracion y helper). Los eventos concretos se emiten en bloques posteriores.

### Funcionalidades y Mejoras

- **`backend/models.py`**: `AuditLog` admite actor, empresa, usuario objetivo, valor anterior, valor nuevo y motivo (`actor_user_id`, `company_id` sin clave foranea, `target_user_id`, `old_value`, `new_value`, `reason`); `impersonated_user_id` y `admin_user_id` pasan a nulos.
- **`backend/migrations/versions/b7e1a0d10001_extend_audit_logs.py`**: migracion reversible que anade las columnas, rellena `actor_user_id` con `admin_user_id` y crea los indices `ix_audit_logs_company_created` e `ix_audit_logs_action`. Compatible con el codigo anterior (solo anade y relaja `NOT NULL`).
- **`backend/audit.py`**: nuevo `AuditAction` y `record_audit`, que anade la entrada a la sesion sin confirmar la transaccion.
- **`backend/routers/users.py`, `backend/routers/work_logs.py`**: las entradas `2fa_reset` y de impersonacion rellenan tambien `actor_user_id`.

### Cambios Internos

- **`backend/tests/test_audit.py`**: pruebas del helper y de los dos escritores existentes.

---

## [0.8.1] - 2026-10-08

### Tipo de Cambio SemVer

- **PATCH**: Migraciones Alembic automaticas en el despliegue de produccion.

### Corregido

- **`docker-compose.prod.yml`**: nuevo servicio one-shot `migrate` que ejecuta `python3 -m alembic upgrade head` con la imagen del backend. El `backend` depende de `migrate` con `service_completed_successfully`, de modo que no arranca si la migracion falla. Tras el paso a Komodo ningun paso aplicaba las migraciones y las bases nuevas quedaban sin esquema.

---

## [0.8.0] - 2026-10-08

### Tipo de Cambio SemVer

- **MINOR**: Habilitacion del 2FA con aplicacion autenticadora (TOTP) desde el perfil, endurecimiento de la verificacion y reset de 2FA por el administrador de la plataforma.

### Funcionalidades y Mejoras

- **Perfil (`frontend/src/components/auth/two-factor-card.tsx`)**:
  - Tarjeta "Two-Factor Authentication" con el estado del 2FA. Activacion con codigo QR, clave manual y codigo de 6 digitos; desactivacion confirmada con un codigo valido.
  - Dependencia nueva `qrcode.react` para generar el QR en el navegador.
- **Panel de administracion (`frontend/src/components/admin/user-edit-dialog.tsx`)**:
  - Boton "Reset 2FA" en la ficha del usuario, visible solo si tiene el 2FA activo, con confirmacion previa.
- **Reset de 2FA (`POST /users/{user_id}/reset-2fa`)**:
  - Solo para el administrador de la plataforma. Desactiva el 2FA, elimina el secreto, cierra las sesiones activas del usuario y pone a cero su contador de intentos fallidos.
  - Registra la accion `2fa_reset` en `AuditLog` con el administrador y el usuario afectado.

### Seguridad

- **Verificacion de 2FA (`backend/auth.py` y `backend/routers/auth.py`)**:
  - `/verify-2fa` exige el token provisional (`2fa_pending`) y lo invalida tras verificar.
  - Limite de 5 fallos cada 10 minutos por usuario (429) en `/verify-2fa`, `/2fa/activate` y `/2fa/disable`. Fallo cerrado: si Redis no responde, 503.
  - Proteccion anti-replay: un mismo codigo solo se acepta una vez. Tolerancia de un paso (30 s) de desfase de reloj.
  - `/2fa/setup` devuelve 409 si el 2FA ya esta activo y `/2fa/disable` exige un codigo valido.
  - El emisor del QR se lee de `TOTP_ISSUER_NAME`.

### Cambios Internos

- Eliminados `resend2FA`, el boton "Resend Code" y la opcion "confiar en este dispositivo", que apuntaban a un endpoint inexistente. El login muestra mensajes especificos para los errores 429, 403 y 503.
- Corregido el comentario de `User.otp_secret`: el secreto ya se cifraba con Fernet.
- **Pruebas**: tests de backend para verificacion protegida, endpoints de 2FA y reset por administrador, y tests de vitest para la tarjeta del perfil, `verify2FA` y el cliente de API.

### Nota de despliegue

- Fijar `ENCRYPTION_KEY` en produccion: sin ella se genera una clave efimera y los secretos de 2FA quedan ilegibles tras cada reinicio.

---

## [0.7.1] - 2026-10-06

### Tipo de Cambio SemVer

- **PATCH**: Cabeceras de seguridad HTTP en el gateway Nginx.

### Seguridad

- **Gateway Nginx (`gateway/nginx.conf` y `gateway/nginx.dev.conf`)**:
  - `server_tokens off` para no exponer la version de Nginx.
  - Cabeceras `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` y `Permissions-Policy` restrictiva, todas con `always`.
  - `Content-Security-Policy-Report-Only` compatible con Next.js y react-pdf. En desarrollo permite ademas `'unsafe-eval'` y `ws:` por el HMR. Pendiente de pasar a modo `Content-Security-Policy` tras revisar la consola del navegador.
  - `proxy_hide_header X-Powered-By` en la ruta del frontend.
  - HSTS no incluido: la terminacion TLS esta fuera de este repositorio y debe confirmarse antes de anadirlo.

---

## [0.7.0] - 2026-10-05

### Tipo de Cambio SemVer

- **MINOR**: Integracion de analitica de producto con PostHog: inyeccion en build-time, inicializacion condicionada a la clave e identificacion de usuario sin datos personales.

### Funcionalidades y Mejoras

- **Analitica (`frontend/src/components/providers.tsx`)**:
  - Inicializacion de `posthog-js` solo si `NEXT_PUBLIC_POSTHOG_KEY` esta definida; sin clave no hace nada (desarrollo y tests).
  - Host por defecto `https://eu.i.posthog.com`, perfiles solo para usuarios identificados y grabacion de sesion con enmascarado de campos.
  - **Pageviews en SPA**: `capture_pageview: "history_change"` para capturar cambios de ruta en App Router sin reloads.
  - **Sanitizacion de URLs**: helper `sanitizeEvent` elimina query string y fragmentos en `$current_url`, `$referrer`, `$initial_current_url`, `$initial_referrer` (con tolerancia a valores no-URL) para evitar filtrar tokens en URLs como `/reset-password?token=...`.
  - **Proteccion en pagina de reset**: `disable_session_recording` desactiva la grabacion en `/reset-password` para no capturar el token en la sesion.
  - **Privacidad**: `persistence: "memory"` (sin almacenamiento entre sesiones) y `maskTextSelector: "*"` (enmascarado total de texto en replay).
- **Ciclo de vida de autenticacion (`frontend/src/context/AuthContext.tsx`)**:
  - `posthog.identify` con el id de usuario, el rol y el id de empresa; no se envia email ni nombre.
  - `posthog.reset` al cerrar sesion.
- **CI/CD**:
  - `frontend/Dockerfile` y workflows `deploy-dev.yml` y `deploy-prod.yml` pasan `NEXT_PUBLIC_POSTHOG_KEY` y `NEXT_PUBLIC_POSTHOG_HOST` como `build-args`.
- **Pruebas**: tests de vitest para `Providers` y `AuthProvider` (caso sin clave, identify y reset).

---

## [0.6.1] - 2026-10-05

### Tipo de Cambio SemVer

- **PATCH**: Endurecimiento operativo del despliegue de produccion: rotacion de logs, limites de recursos y workers de Uvicorn parametrizables.

### Funcionalidades y Mejoras

- **Despliegue (`docker-compose.prod.yml`)**:
  - Rotacion de logs `json-file` (`max-size: 20m`, `max-file: 5`) en todos los servicios mediante el ancla `x-logging`.
  - Limites de CPU y memoria (`deploy.resources.limits`) en `postgres`, `backend` y `frontend`, parametrizables con `POSTGRES_*_LIMIT`, `BACKEND_*_LIMIT` y `FRONTEND_*_LIMIT`.
  - Variable `WEB_CONCURRENCY` (por defecto 2) propagada al backend.
- **Backend (`backend/Dockerfile`)**:
  - `WEB_CONCURRENCY=2` por defecto para que Uvicorn arranque con 2 workers en produccion.
- **Documentacion**:
  - Nuevo analisis tecnico `docs/ANALISIS_DOCKER_COMPOSE.md` de los manifiestos Docker Compose.

---

## [0.6.0] - 2026-09-29

### Tipo de Cambio SemVer

- **MINOR**: Renovacion integral del Dashboard de Gestores con operativa en tiempo real, KPIs adaptativos, cache Redis e implementacion de bypass de autenticacion para desarrollo local.

### Funcionalidades y Mejoras

- **Dashboard de Gestores Modular (`frontend/src/components/manager/`)**:
  - `DashboardTodayCard`: Panel de operativa en tiempo real con conteo de monitores activos, horas programadas, resumen de tipos de turnos y listado cronologico de la jornada.
  - `DashboardKpis`: Selector de periodo (Hoy, Semana, Mes, Mes Anterior, Temporada, Personalizado) y tarjetas de KPIs adaptativas. Si la empresa no distingue bruto y neto, presenta una metrica unificada de liquidacion sin duplicar cifras.
  - `DashboardCharts`: Graficos dinamicos con Recharts y selector de metrica (Horas vs Coste). Muestra distribucion por servicios si hay 2+ tipos de turnos activos, o carga semanal acumulada por dias si hay 1 solo tipo.
  - `DashboardTeamTable`: Resumen de plantilla respetando el orden definido por el gestor (`sort_order`), eliminando clasificaciones de tipo ranking.
  - `DashboardHeaderActions`: Barra de acciones con boton principal para añadir partes de trabajo y exportacion en formato CSV.
- **Gestion y Administracion de Empresas**:
  - Ordenacion inteligente de empresas: activas primero y suspendidas al final, con ordenacion alfabetica secundaria.
  - Creacion de funcion de utilidad `formatPercentage` para evitar artefactos de punto flotante IEEE-754 en tipos de Seguridad Social.
  - Traduccion al espanol de todos los dialogos y componentes de administracion.
- **Backend y Rendimiento**:
  - Nuevo endpoint analitico `GET /companies/{company_id}/dashboard-summary` con agregacion optimizada de metricas del periodo, jornada actual y desglose por trabajador.
  - Integracion de cache Redis con TTL de 300 segundos e invalidacion reactiva ante mutaciones de partes de trabajo y cambios en ordenacion de miembros.
  - Manejo robusto de claves RSA no encriptadas en entornos locales de desarrollo.
- **Bypass de Desarrollo y Auto-Login**:
  - Creacion del modulo `dev_seed.py` para sembrado y garantia de existencia del usuario administrador (`admin@vesotel.com`) y empresa predeterminada.
  - Endpoints dedicados `GET /api/auth/dev-status` y `POST /api/auth/dev-login` para emision directa de cookies de sesion HttpOnly sin credenciales en entorno local.
  - Integracion en frontend (`AuthContext.tsx` y `LoginPage`) para detectar modo desarrollo, iniciar sesion automaticamente y auto-recuperar la sesion ante reinicios del backend (error 401).
- **Seguridad**:
  - Variable `ENCRYPTION_KEY` eliminada de la plantilla `env.example`; se documenta como comentario el comando para generarla.
- **Suite de Pruebas**:
  - Nuevos tests frontend en `manager-dashboard.test.tsx`, `companies.test.ts` y `utils.test.ts` (85 pruebas unitarias passing).
  - Nuevos tests backend en `test_dashboard_summary.py` (calculo de metricas, control de acceso y RBAC).
  - Pruebas de bypass de desarrollo y optimizaciones de compilacion frontend.

---

## [0.5.0] - 2026-09-29

### Tipo de Cambio SemVer

- **MINOR**: Transicion estructural a Arquitectura Hexagonal (Puertos y Adaptadores) y Clean Architecture, desacoplamiento del motor de calculo salarial y fiscal en capas de dominio puras, proteccion de endpoints y saneamiento contra replay attacks.

### Funcionalidades y Mejoras

- **Arquitectura Hexagonal en Backend (`backend/src/`)**:
  - Implementadas entidades de dominio puras (`User`, `Company`, `CompanyMember`, `WorkLog`) y Value Objects inmutables (`Money`, `WorkDuration`, `TaxConfiguration`, `RateDefinition`, `CalculationSnapshot`).
  - Creado `WorkLogCalculationService` para liquidacion de jornadas y retenciones impositivas, 100% aislado de SQLAlchemy, FastAPI y Redis.
  - Definidos puertos abstractos de repositorio (`UserRepositoryPort`, `CompanyRepositoryPort`, `WorkLogRepositoryPort`).
  - Desarrollados casos de uso de aplicacion (`CreateWorkLogUseCase`).
  - Implementados adaptadores y mappers de persistencia bidireccionales (`SqlAlchemyUserMapper`, `SqlAlchemyCompanyMapper`, `SqlAlchemyWorkLogMapper`, `SqlAlchemyWorkLogRepository`, `SqlAlchemyUserRepository`, `SqlAlchemyCompanyRepository`).
- **Seguridad, Autenticacion y Endpoints**:
  - Protegido el endpoint `GET /companies` requiriendo autenticacion obligatoria con `auth.get_verified_user` y filtrado multi-tenant por rol.
  - Subsanada vulnerabilidad de replay attack en reseteo de contrasenas mediante un solo uso de `jti` en tokens criptograficos.
  - Prevenido bypass de 2FA en incorporacion de miembros de empresa (`add_company_member`).
- **Clean Architecture en Frontend (`frontend/src/`)**:
  - Implementados Value Objects (`Money.ts`), entidades de dominio (`WorkLog.ts`) y servicios de calculo mensuales desacoplados (`WorkLogCalculationService.ts`).
  - Creado cliente HTTP tipado (`AxiosHttpClient.ts`) implementando el puerto `IHttpClient.ts`.
  - Desarrollados mappers (`WorkLogMapper.ts`) y repositorios API (`ApiWorkLogRepository.ts`).
- **Aseguramiento de Calidad**:
  - 100% de aprobacion en las suites de pruebas automatizadas en Pytest (backend) y Vitest (frontend).

---

## [0.4.0] - 2026-09-29

### Tipo de Cambio SemVer

- **MINOR**: Gobernanza visual de empresas (Fase 2 UI), aislamiento multi-tenant en supervision de miembros, desacoplamiento dinamico de turnos en partes, liquidaciones e informes PDF/impresion.

### Funcionalidades y Mejoras

- **Gobernanza de Empresas en UI**:
  - Incorporados switches y distintivos visuales de estado (Activa vs Suspendida, Gestionada vs Autonoma) en el panel de administracion de empresas (`CompaniesPageClient.tsx`) y dialogo de alta (`CompanyDialog.tsx`).
  - Incorporado alternador entre vista de tarjetas y vista de lista compacta con persistencia permanente en `localStorage` (`admin_companies_view_mode`).
  - Posibilidad de conmutar directamente el estado operativo y de gestion con persistencia inmediata.
- **Seguridad Multi-Tenant y Restriccion RBAC**:
  - Corregida fuga de datos en la vista de detalle de trabajador (`manager/users/[userId]/page.tsx`), garantizando que los registros filtrados pertenezcan estrictamente al conjunto de empresas visibles.
  - Bloqueada la alteracion no autorizada de roles en la edicion de miembros por parte de managers mediante conversion del selector a distintivo informativo de solo lectura.
  - Subsanado error de tipo en base de datos al activar/desactivar miembros con normalizacion booleana estricta y soporte para administradores de plataforma con contexto activo.
  - Protegida la configuracion de tasas contra valores invalidos (NaN) y solventado el bucle de renderizado en `CompanyMemberConfigCard`.
  - Auto-seleccion de la primera empresa gestionada en el panel de supervision de miembros (`manager/users/page.tsx`).
- **Gobernanza de Tarifas en Perfil**:
  - Resuelto error 403 Forbidden para trabajadores en la consulta de tarifas mediante eliminacion de dependencia con `/companies/detailed`.
  - Deteccion de modo gestionado en perfil de usuario con desactivacion de formulario, aviso informativo destacado y preservacion de configuraciones existentes.
- **Liquidaciones y Partes Diarios**:
  - Correccion en el conteo de servicios fijos (`unit === 'fixed'`) usando `logsCount` en lugar de `uniqueDays` en el resumen mensual de facturacion.
  - Formato de exportacion CSV compatible con hojas de calculo en Espana (separador punto y coma, coma decimal y codificacion BOM UTF-8).
  - Sustitucion de la pagina bloqueante de ajustes de manager por el panel completo de configuracion de escuela (`CompanyConfigurationTab`).
  - Soporte de turnos por rango de fechas (multidia) en partes diarios diarios para cualquier tipo configurado, sin restriccion estatica a turnos 'tutorial'.
  - Eliminacion de texto de depuracion y limites rigidos que descartaban franjas horarias tempranas o nocturnas.
- **Informes, Impresion y Exportacion**:
  - Erradicado el multiplicador fijo de 6 horas para tutoriales en informes visuales e impresion.
  - Calculo financiero basado en los campos efectivos de importes netos y brutos (`netAmount`, `grossAmount`).
  - Habilitado el filtrado por empresa y trabajador en la vista de impresion `/reports/print`.
  - Redisenado el informe PDF corporativo (`CompanyPDFReport.tsx`) con desglose de retenciones estimadas de IRPF y Seguridad Social segun `taxConfig`.

---

## [0.3.0] - 2026-09-28

### Tipo de Cambio SemVer

- **MINOR**: Gobernanza de empresas, modo empresa gestionada vs autonoma, control de actividad y restricciones estrictas RBAC.

### Funcionalidades y Mejoras

- **Base de Datos y Modelos**:
  - Migracion Alembic reversible \`8f10a2b3c4d5_anadir_is_active_e_is_managed_a_companies\` que anade columnas \`is_active\` e \`is_managed\` a la tabla \`companies\`.
  - Actualizados modelos SQLAlchemy y esquemas Pydantic con soporte camelCase (\`isActive\`, \`isManaged\`).
- **Gobernanza y RBAC**:
  - Restriccion estricta en cambio de roles: Se elimina la posibilidad de que un manager altere el rol de un usuario. Solo los administradores de empresa o administradores de plataforma pueden modificar roles.
  - Modo Empresa Gestionada (\`is_managed = True\`): Los trabajadores tienen sus tarifas (\`rates_config\`) en solo lectura y no pueden alterar turnos directamente.
  - Desactivacion de Empresa (\`is_active = False\`): Bloqueo total de operaciones, conmutacion de ambito y registro de turnos para usuarios regulares, permitiendo acceso administrativo unicamente a la administracion de plataforma.
- **Suite de Pruebas**:
  - Cobertura completa de politicas de gobernanza con \`test_governance.py\` (8/8 pruebas unitarias superadas).

---

## [0.2.0] - 2026-09-28

### Tipo de Cambio SemVer

- **MINOR**: Rediseño data-driven completo del dashboard de usuario y calculo dinamico de turnos laborales.

### Funcionalidades y Mejoras

- **Dashboard de Usuario Data-Driven**:
  - Eliminado el calculo estatico obsoleto de 6 horas por dia para turnos tutoriales (`days * 6`).
  - Agrupacion automatica y dinamica de metricas segun las unidades configuradas en la empresa (`hours`, `days`, turnos fijos o combinaciones hibridas) leyendo de `company.worklogDefinitions`.
  - Sustitucion de la tarta binaria rigida por tarjetas de ingresos y actividad real desglosada por tipo de turno.
  - Grafico de area interactivo y responsivo con Recharts adaptado a la tendencia mensual.
  - Internacionalizacion completa de fechas con soporte regional en espanol (`date-fns/locale/es`).

---

## [0.1.0] - 2026-09-24

### Tipo de Cambio SemVer

- **MINOR**: Version inicial del portal SaaS Ski (saas_ski_vesotel) con autenticacion, gestion de monitores, clases, jornadas y despliegue CI/CD en Komodo.

### Funcionalidades Iniciales

- **Arquitectura Monorepo y Gateway**:
  - Pasarela Nginx (gateway) unificando frontend Next.js en `/` y backend FastAPI en `/api/`.
  - Configurado entorno de desarrollo y produccion con Docker Compose.
- **Backend (FastAPI)**:
  - Modulos de autenticacion JWT y gestion de sesiones.
  - CRUD de usuarios, empresas, partes de trabajo (work logs) y modulos.
  - Base de datos PostgreSQL con migraciones Alembic y cache Redis.
- **Frontend (Next.js 16 / React 19)**:
  - Panel administrativo, planificador interactivo, gestion de monitores y partes.
  - Componentes de diseno accesibles con Tailwind CSS y Radix UI.
- **Pipelines CI/CD (GitHub Actions)**:
  - Flujo de integracion continua con linters, pruebas unitarias y comprobacion de tipos.
  - Workflows de despliegue continuo para desarrollo (`deploy-dev.yml`) y produccion (`deploy-prod.yml`) hacia Komodo con publicacion de imagenes en GHCR etiquetadas mediante SemVer.
