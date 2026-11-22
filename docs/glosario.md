# Glosario

Terminos de negocio de la plataforma, su nombre en el codigo y donde viven.
Las reglas de cada entidad estan en [dominio/](dominio/README.md); las
decisiones sin cerrar, en [preguntas-abiertas.md](preguntas-abiertas.md).

Convencion: los campos van en `snake_case`. La API v1 serializa en `camelCase`
(`isManaged`), la v2 en `snake_case`. Si un termino tiene dos nombres en el
codigo, se indican los dos. Abreviaturas: PA = administrador de plataforma.

## Organizacion y personas

| Termino | Nombre en codigo | Donde vive | Definicion |
|---|---|---|---|
| Empresa | `Company`, tabla `companies` | `backend/models.py`, `backend/src/domain/entities/company.py` | Escuela cliente. Es el tenant: la unidad de aislamiento de datos. Todo dato operativo lleva `company_id` |
| Empresa gestionada | `Company.is_managed = true` | `companies.is_managed` | Empresa en la que solo escriben manager y PA. El worker ve sus turnos pero no los crea, edita ni borra, ni cambia sus tarifas. Lo cambia solo el PA |
| Empresa autonoma | `Company.is_managed = false` | `companies.is_managed` | Lo contrario de gestionada: el worker registra y edita sus propios turnos y edita su tarifa, su bruto/neto y sus impuestos propios |
| Empresa suspendida | `Company.is_active = false` | `companies.is_active` | Bloqueo total: ningun worker ni manager accede a ella ni a sus datos (403). Solo el PA. Los modulos de la empresa dejan de valer. Es la baja: la empresa no se borra si tiene datos |
| Empresa activa | claim `cid` del token | `backend/auth.py`, `POST /auth/switch-scope` | Empresa sobre la que opera la sesion. Se elige al iniciar sesion o al cambiar de empresa; el backend la valida contra la membresia en cada peticion |
| Usuario | `User`, tabla `users` | `backend/models.py`, `backend/src/domain/entities/user.py` | Identidad global de una persona. Puede pertenecer a varias empresas. Perfil, 2FA y sesiones son globales. `users.is_active = false` impide autenticarse |
| Membresia | `CompanyMember`, tabla `company_members` | `backend/models.py`, `backend/src/domain/entities/company_member.py` | Relacion de un usuario con una empresa, clave `(user_id, company_id)`. Lleva rol, estado (`is_active`) y tarifas (`rates_config`). Su columna `settings` se elimina (P8, S9; #67). Es el eje del modelo |
| Membresia inactiva | `CompanyMember.is_active = false` | `company_members.is_active` | El usuario no accede a esa empresa. Sus turnos se conservan y cuentan en totales. Al reactivarla vuelve como worker |
| Administrador de plataforma | `UserRole.admin`, `users.role = admin`, `is_platform_admin` | `backend/models.py`, `backend/access_policy.py` | PA. Opera sobre toda la plataforma y entra en cualquier empresa por privilegio, sin membresia. Es el unico que gestiona empresas, membresias, roles, estados, modulos y usuarios |
| Usuario de plataforma | `UserRole.user` | `users.role = user` | Cualquier usuario que no es PA. Su acceso a una empresa depende de su membresia |
| Manager | `CompanyRole.manager`, `ROLE_MANAGER` | `company_members.role`, `backend/access_policy.py` | Rol en una empresa. Lleva la operativa: turnos de todo el equipo, tarifas propias y ajenas, billing y vision de equipo. No administra la empresa ni su equipo |
| Worker | `CompanyRole.worker`, `ROLE_WORKER` | `company_members.role`, `backend/access_policy.py` | Rol en una empresa (no es una entidad). Ve sus propios turnos y su perfil. En empresa autonoma los registra y edita; en gestionada solo los consulta |
| Admin de empresa (retirado) | `CompanyRole.admin`, `normalize_member_role` | `company_members.role`, `backend/access_policy.py` | Retirado (P3, 2026-11-22): el rol no existe; los unicos roles de empresa son manager y worker (R-ACC-27). El codigo aun lo contiene hasta que se elimine |
| Ver como (retirado) | claim `view_as`, `VIEW_AS_ROLES` | `backend/auth.py`, `backend/access_policy.py`, `frontend/src/components/view-as-banner.tsx` | Retirado (P4, 2026-11-22). Lo sustituyen la suplantacion de solo lectura y los usuarios demo manager y worker (R-ACC-66 a R-ACC-69). El codigo lo conserva hasta que se borre |
| Contexto neutro | token sin `cid` | `backend/auth.py:resolve_active_company` | Sesion sin empresa activa. Es la del PA al iniciar sesion y la de un usuario sin membresias activas |
| PA actuando | `acting_platform_admin` | `backend/routers/deps.py` | PA que opera con sus permisos de PA. Con "ver como" retirado (P4) coincide con cualquier PA que no suplanta; el termino se conserva porque el codigo lo usa |
| Scope del token | claim `scope`: `full`, `2fa_pending`, `impersonated` | `backend/auth.py`, `backend/routers/auth.py` | Tipo de sesion. `2fa_pending` solo sirve para verificar el 2FA. No es un plan ni un permiso de empresa |
| Vista completa y vista reducida | `CompanyFull`, `CompanyReduced` | `backend/routers/v2/schemas.py` | Dos respuestas de empresa: la completa solo para el PA actuando; la reducida para manager y worker (R-ACC-54) |
| Suplantacion (impersonacion) | scope `impersonated`, `/admin/impersonate/{user_id}` | `backend/routers/auth.py` | El PA inicia sesion como un usuario concreto, para soporte (token de 10 min). Es de solo lectura (R-ACC-66) y cada suplantacion queda auditada (R-ACC-67); hoy el codigo aun permite escribir |

## Trabajo e importes

| Termino | Nombre en codigo | Donde vive | Definicion |
|---|---|---|---|
| Turno (work log) | `WorkLog`, tabla `work_logs` | `backend/models.py`, `backend/src/domain/entities/work_log.py` | Hecho central: trabajo de un usuario en una empresa (tipo, fechas, horas, importe). De el salen importes, billing e informes. Pertenece al par (usuario, empresa) |
| Tipo de turno | `worklog_definitions` | `companies.worklog_definitions` | Catalogo de tipos de turno de cada empresa (por ejemplo, clase particular). Cada tarifa del miembro se asocia a un tipo |
| Grupo de turnos | `group_id`, `apply_to_group` | `work_logs.extra_data`, `backend/crud.py` | Turnos creados a la vez para varios usuarios. `apply_to_group` edita todos los del grupo dentro de la misma empresa. El `group_id` lo genera el servidor |
| Creacion en lote | `POST /work-logs/bulk` | `backend/routers/work_logs.py` | Alta de varios turnos en una peticion. Solo manager y PA |
| Snapshot de calculo | `calculation_snapshot` | `work_logs.calculation_snapshot`, `backend/src/domain/value_objects/calculation_snapshot.py` | Copia de tarifas e impuestos usados al calcular el importe de un turno. Editar sin cambiar tipo, horas ni fechas conserva el importe; si cambian, se recalcula con este snapshot |
| Parte diario | modulo `worker_daily_report`, `GET /companies/{company_id}/daily-report` | `backend/routers/companies.py`, `frontend/src/lib/types.ts` | Vista de los miembros y turnos de un dia. Es modulo de pago. El worker la recibe sin campos de importe; manager y PA, con ellos |
| Tarifa | `rates_config` | `company_members.rates_config`, `backend/src/domain/value_objects/rate_definition.py` | Precio por tipo de turno de un miembro en una empresa (`base_rate`, `is_gross`, `tax_overrides`). No hay historial: el cambio queda en `audit_logs` y en el snapshot de cada turno |
| Bruto y neto | `is_gross` | `rates_config.<tipo>.is_gross` | Con `is_gross = true` la tarifa es bruta y el calculo descuenta los impuestos; con `false` no descuenta nada |
| Impuesto | `tax_config` | `companies.tax_config`, `backend/src/domain/value_objects/tax_configuration.py` | Diccionario de claves libres `nombre: fraccion` (0 a 1, maximo 20) que la empresa descuenta del bruto. `{}` es valido |
| Override de impuesto | `tax_overrides` | `company_members.rates_config.<tipo>.tax_overrides` | Valor de un impuesto propio del miembro, con la misma clave que en `tax_config`. Si existe, manda sobre el de la empresa |
| Importe | `gross_amount`, `net_amount`, `Money` | `work_logs`, `backend/src/domain/value_objects/money.py` | Lo generado por un turno, calculado con tarifa e impuestos. No hay importe manual (S6); los turnos antiguos con `manual_override` se siguen leyendo |

## Producto y facturacion

| Termino | Nombre en codigo | Donde vive | Definicion |
|---|---|---|---|
| Modulo | `AppModule`, tabla `app_modules`, `code_name` | `backend/models.py` | Funcionalidad de pago del catalogo (parte diario, billing avanzado, informes). `target_scope` indica si se asigna a empresa, a usuario o a ambos |
| Suscripcion | `ModuleSubscription`, tabla `module_subscriptions` | `backend/models.py` | Asignacion de un modulo a una empresa (`scope = company`) o a un usuario (`scope = user`), con estado `active`, `trial`, `cancelled` o `expired`. Solo la gestiona el PA |
| Modulos efectivos | `GET /modules/me` | `backend/routers/modules.py` | Union de los modulos personales y los de la empresa activa. Los de empresa se descartan si esta suspendida |
| Guardia de modulo | `require_module(code_name)` | `backend/routers/deps.py` | Dependencia que devuelve 403 si ni la empresa ni el usuario tienen el modulo. El PA pasa |
| Billing basico | `GET /work-logs/billing-summary` | `backend/routers/work_logs.py` | Suma de lo trabajado y lo generado. Sin modulo. Lo ven manager y PA |
| Billing avanzado | modulo (aplazado hasta que lo pida un cliente, O11) | sin implementar | Porcentajes, tendencias y analitica. Solo con modulo |
| Ajustes de empresa | `settings`, `CompanySettings` | `companies.settings`, `backend/contracts.py` | Hoy solo `default_is_gross`, el bruto/neto que se copia a los miembros nuevos (S2); los demas ajustes (`price_type`, `worker_experience`, `ui_customization`, `modules`, `allowed_rates`) estan eliminados (S3, S9). Los nuevos son claves del mismo contrato. Reglas: R-EMP-45 a R-EMP-49 |
| Auditoria | `AuditLog`, tabla `audit_logs` | `backend/models.py` | Registro de quien, cuando, que, empresa, valor anterior y nuevo y motivo de cada cambio relevante. Solo lo consulta el PA. Reglas en [dominio/auditoria.md](dominio/auditoria.md) |
