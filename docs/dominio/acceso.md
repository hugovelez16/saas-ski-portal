# Acceso

Prefijo: `R-ACC`. Tablas: `users`, `company_members`, `user_sessions`. Modelos:
`User`, `CompanyMember`, `UserSession` (`backend/models.py`). Politica:
`backend/access_policy.py`; dependencias: `backend/routers/deps.py`.

Reglas de token, sesion, [empresa activa](../glosario.md), roles,
[suplantacion](../glosario.md) y que ve cada rol. "Ver como" se retira
(2026-11-22, P4 de [revision-base.md](../producto/revision-base.md)).

Las reglas R-ACC-64 a R-ACC-79 y los cambios de R-ACC-27, R-ACC-44 a 49 y
R-ACC-53 vienen de las decisiones de la revision de base (#114, 2026-11-22).
Describen el comportamiento objetivo: el codigo aun no las cumple.
Sustituye a las secciones 2.2, 3 y 9 de
[logica-negocio-empresa.md](../empresa/logica-negocio-empresa.md), que quedan
como historico. En la columna Codigo, "objetivo" significa que la regla no esta
implementada hoy; las citas se comprobaron con `grep` el 2026-11-21.

## Campos

Claims del access token (JWT RS256).

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `sub` | UUID | Si | Usuario del token |
| `cid` | UUID | No | Empresa activa. Ausente si no hay ninguna (PA neutro, usuario sin empresas) |
| `scope` | texto | Si | `full`, `2fa_pending` o `impersonated` |
| `exp` | fecha | Si | Caducidad |
| `view_as` | texto | No | **Retirado (P4).** Era `worker` o `manager`, solo para PA con `cid`. Se elimina junto con "ver como" |
| `admin_user_id` | UUID | No | PA que suplanta. Solo con `scope = impersonated` |
| `iat`, `type`, `jti` | varios | Si | Tecnicos: emision, tipo (`access`, `refresh`) e ID para la lista negra |

## Reglas

### Token y sesion

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-01 | El access token se firma con RS256 y caduca a los 30 min | Cerrado | 3.1 | `backend/auth.py:create_access_token` |
| R-ACC-02 | El access token no lleva `role` ni `is_admin`; solo los claims de la tabla Campos | Cerrado | 3.1, O7 | `backend/auth.py:generate_user_tokens` |
| R-ACC-03 | El rol de plataforma y el de empresa se leen de BD en cada peticion; si el token trae `role` o `is_admin`, se ignoran | Cerrado | 3.1, O7 | `backend/auth.py:_attach_context` |
| R-ACC-04 | El frontend obtiene rol de plataforma, empresa activa y rol activo de `GET /users/me` (el "ver como" se retira, P4) | Cerrado | 3.1 | `backend/routers/users.py:read_users_me` |
| R-ACC-05 | El token se lee de la cookie HttpOnly `access_token` o, si falta, de la cabecera `Authorization: Bearer` | Confirmar | FRD 2.1 | `backend/auth.py:get_token_from_request` |
| R-ACC-06 | El `scope` no es un plan ni un permiso de empresa: la cuenta gratuita se modela con `module_subscriptions` (que incluye y como se registra: O16) | Cerrado | 3.1, O16 | objetivo (no hay cuenta gratuita) |
| R-ACC-07 | Login con contrasena correcta y 2FA activo emite un token `2fa_pending` de 5 min y ningun refresh token | Cerrado | 3.1, FRD RF-03 | `backend/routers/auth.py:login_for_access_token` |
| R-ACC-08 | Un token `2fa_pending` solo vale en `POST /verify-2fa`; en cualquier otro endpoint responde 403 | Cerrado | 3.2 n.3 | `backend/auth.py:get_verified_user`, `backend/routers/auth.py:verify_2fa` |
| R-ACC-09 | `POST /verify-2fa` con un token que no es `2fa_pending` responde 403 | Cerrado | 3.2 n.3 | `backend/routers/auth.py:verify_2fa` |
| R-ACC-10 | Login de un usuario con `users.is_active = false` responde 403, tambien si es PA | Cerrado | 2.3, 3.4 | `backend/routers/auth.py:login_for_access_token` |
| R-ACC-11 | No existe registro publico: solo el PA crea usuarios (`POST /users`). Nota 2026-11-22: vale hasta que se implemente el alta publica B2C (R-ACC-75 a 77), tras migrar Usuarios y Membresias (P1) | Cerrado | 3.4, P1 | `backend/routers/users.py:create_user_admin` |
| R-ACC-12 | El bypass de login de desarrollo solo funciona con `ENVIRONMENT=development` y `DEV_LOGIN_BYPASS` activos | Cerrado | 3.4 (P-9) | `backend/dev_seed.py:is_dev_mode` |
| R-ACC-13 | Si `DEV_LOGIN_BYPASS` esta activo fuera de `ENVIRONMENT=development`, el arranque se aborta | Cerrado | 3.4 (P-9) | `backend/dev_seed.py:assert_dev_bypass_safe` |
| R-ACC-14 | El seed inicial solo crea PA y empresa si no existe ningun PA | Cerrado | 3.4 | `backend/seed.py:seed_initial_data` |

### Comprobaciones en cada peticion

Orden unico; un fallo corta la peticion. R-ACC-18 a R-ACC-23 se aplican en los
endpoints de una empresa, a traves de `deps.authorize`.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-15 | Sin token, o con token mal firmado, caducado o en la lista negra (`jti`), responde 401 | Cerrado | 3.2 n.1 | `backend/auth.py:get_verified_user`. Hallazgo #78: acepta refresh tokens |
| R-ACC-16 | Si el usuario del token no existe o tiene `users.is_active = false`, responde 401 | Cerrado | 3.2 n.2 | `backend/auth.py:get_verified_user` |
| R-ACC-17 | Solo los scopes `full` e `impersonated` acceden a endpoints normales | Cerrado | 3.2 n.3 | `backend/auth.py:get_verified_user` rechaza `2fa_pending`; un scope desconocido no se rechaza (solo los emite el backend) |
| R-ACC-18 | Quien no es PA y no tiene membresia activa en la empresa recibe 403 | Cerrado | 3.2 n.5 | `backend/access_policy.py:authorize_company` |
| R-ACC-19 | Quien no es PA y opera sobre una empresa suspendida recibe 403 | Cerrado | 3.2 n.4, 4.5 | `backend/access_policy.py:authorize_company` |
| R-ACC-20 | La membresia se comprueba antes que la suspension: un no miembro recibe el mismo 403 tanto si la empresa esta suspendida como si no | Cerrado | 9 (P-5) | `backend/access_policy.py:authorize_company` |
| R-ACC-21 | **Retirada (P11, 2026-11-22), sustituida por R-ACC-79.** El rol sale de la membresia en BD con cache Redis de 60 s; si Redis falla o no tiene el dato, se lee de BD y la peticion sigue | Retirada | 3.2 n.6, P11 | `backend/routers/deps.py:load_company_facts`, `backend/access_cache.py` (hasta que se quite la cache) |
| R-ACC-22 | **Retirada (P11, 2026-11-22), sustituida por R-ACC-79.** Cambiar rol o estado de una membresia, o `is_active` de una empresa, invalida su cache de acceso al momento | Retirada | 3.2, P11 | `SqlAlchemyCompanyMemberRepository.save` y `SqlAlchemyCompanyRepository.save` (`backend/src/infrastructure/persistence/sqlalchemy/repositories/company_repository.py`), `backend/crud.py:join_company` |
| R-ACC-23 | Si el rol no alcanza el minimo del endpoint, responde 403 | Cerrado | 3.2 n.7 | `backend/access_policy.py:authorize_company` |
| R-ACC-24 | En un endpoint de pago sin el modulo en la empresa ni en el usuario responde 403; el PA actuando pasa | Cerrado | 3.2 n.8 | `backend/routers/deps.py:require_module`, `backend/routers/deps.py:authorize` |
| R-ACC-25 | El bypass del PA vive en un solo punto; ningun handler repite `if not is_platform_admin` | Confirmar | P2 (direccion cerrada, forma por confirmar) | `backend/access_policy.py:authorize_company`, `backend/routers/deps.py:acting_platform_admin` |
| R-ACC-79 | El rol y el estado de la membresia se leen de BD en cada peticion, sin cache; un cambio de rol o de estado surte efecto en la siguiente peticion. Sustituye a R-ACC-21 y R-ACC-22 | Cerrado | P11 | objetivo (hoy hay cache Redis de 60 s) |

### Roles

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-26 | El PA es el usuario con `users.role = admin` y accede a cualquier empresa sin membresia | Cerrado | 2.2 | `backend/access_policy.py:authorize_company` |
| R-ACC-27 | Los unicos roles de empresa son `manager` y `worker`; el rol admin de empresa no existe. Modificada 2026-11-22 (P3): antes decia que el rol `admin` de membresia existia y se trataba como `manager` | Cerrado | 2.2, P3 | `backend/access_policy.py:normalize_member_role` y el enum `CompanyRole` aun lo contienen: objetivo |
| R-ACC-28 | Un endpoint que exige rol worker admite tambien al manager: su rol incluye el de worker | Cerrado | 3.1 | `backend/access_policy.py:authorize_company` (`_ROLE_RANK`) |
| R-ACC-29 | Solo el PA cambia el rol de una membresia | Cerrado | 2.2 | `backend/routers/v2/members.py:set_member_role` |
| R-ACC-30 | Un usuario no puede cambiar su propio rol de plataforma | Cerrado | 2.2 | `backend/schemas.py:UserSelfUpdate` (sin `role`), `backend/crud.py:ensure_platform_admin_invariants` |
| R-ACC-31 | Un PA no puede desactivarse a si mismo (403) | Cerrado | 3.4 | `backend/crud.py:ensure_platform_admin_invariants` |
| R-ACC-32 | Ningun cambio puede dejar la plataforma sin PA activo (409) | Cerrado | 3.4 | `backend/crud.py:ensure_platform_admin_invariants` |
| R-ACC-64 | El manager anade y desactiva workers de su empresa activa; nunca cambia el rol de una membresia (403). Que tampoco de de alta a un manager es inferencia de la matriz y de P6 ("solo workers") | Cerrado | P6 | objetivo (hoy solo el PA anade y desactiva miembros) |
| R-ACC-65 | El rol de PA solo se concede por seed o comando de servidor, y queda auditado; ningun endpoint de la aplicacion lo concede, tampoco a un PA | Cerrado | P5 | objetivo |

### Empresa activa

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-33 | La empresa activa es la del claim `cid`; el backend nunca la toma de la URL | Cerrado | 3.3, O2 | `backend/auth.py:_attach_context`, `backend/routers/deps.py:authorize` |
| R-ACC-34 | En login y 2FA, el `company_id` del cliente es una sugerencia: vale si es membresia activa de empresa activa; si no, la primera por `sort_order` | Cerrado | 3.3 | `backend/auth.py:resolve_active_company` |
| R-ACC-35 | Un usuario sin membresia activa en ninguna empresa activa recibe un token sin `cid` | Cerrado | 3.3 | `backend/auth.py:resolve_active_company` |
| R-ACC-36 | Un usuario sin empresas puede iniciar sesion y ve "No estas vinculado a ninguna empresa" | Cerrado | 3.4 | `frontend/src/app/(app)/layout.tsx` |
| R-ACC-37 | El PA inicia sesion en contexto neutro (sin `cid`) y opera por privilegio | Cerrado | 3.3 | `backend/routers/auth.py:login_for_access_token` (`force_none`) |
| R-ACC-38 | La empresa activa solo cambia con `POST /auth/switch-scope`, que emite tokens nuevos; el rol nunca lo envia el cliente | Cerrado | 3.3 | `backend/routers/auth.py:switch_scope`. Hallazgo #79: el refresh la reinicia |
| R-ACC-39 | `switch-scope` de un no PA: sin `company_id` 400; empresa inexistente o sin membresia activa 403; empresa suspendida 403 | Cerrado | 3.3 (P-4) | `backend/routers/auth.py:switch_scope` |
| R-ACC-40 | `switch-scope` del PA: sin `company_id` vuelve al contexto neutro; empresa inexistente 404; empresa suspendida permitida | Cerrado | 3.3 (P-4) | `backend/routers/auth.py:switch_scope` |
| R-ACC-41 | Con `cid`, quien no es PA recibe 403 en otra empresa hasta cambiar a ella, sea cual sea el rol exigido | Cerrado | 3.3 | `backend/routers/deps.py:authorize` |
| R-ACC-42 | Durante una suplantacion, `switch-scope` responde 403 | Confirmar | 3.4 (limite de 10 min), #79 | `backend/routers/auth.py:switch_scope` |
| R-ACC-43 | La ultima empresa la guarda el navegador en `localStorage` (`lastCompanyId`) y se envia en el login; nada se guarda en servidor | Cerrado | 3.3 | `frontend/src/lib/last-company.ts`, `frontend/src/context/AuthContext.tsx` |

### Ver como (retirado)

P4 (2026-11-22) elimina "ver como" y el claim `view_as`. Las reglas se
conservan con su ID, marcadas `Retirada`; el codigo las cumple hasta que se
borre. Lo sustituyen la suplantacion de solo lectura (R-ACC-66 a 68) y los
usuarios demo (R-ACC-69).

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-44 | Solo el PA usa "ver como"; `switch-scope` con `view_as` de otro usuario responde 403. El manager no tiene "entrar como worker" | Retirada | 3.1, P4 | `backend/routers/auth.py:switch_scope` |
| R-ACC-45 | "Ver como" exige empresa: `view_as` sin `company_id` responde 422 | Retirada | 3.1, P4 | `backend/routers/auth.py:switch_scope`, `backend/auth.py:generate_user_tokens` |
| R-ACC-46 | Los roles de "ver como" son `worker` y `manager` | Retirada | 3.1, P4 | `backend/access_policy.py:VIEW_AS_ROLES` |
| R-ACC-47 | En "ver como", toda peticion con metodo distinto de GET, HEAD u OPTIONS responde 403, salvo `switch-scope`, `logout` y `refresh-token`. Su sustituta para la suplantacion es R-ACC-66 | Retirada | 3.1, P4 | `backend/access_policy.py:assert_view_as_read_only` |
| R-ACC-48 | En "ver como" el PA tiene los permisos del rol elegido y pierde los de PA | Retirada | 3.1, P4 | `backend/routers/deps.py:acting_platform_admin`, `backend/access_policy.py:authorize_company` |
| R-ACC-49 | En "ver como" worker, los turnos "propios" que se muestran son los del PA | Retirada | 3.1, P4 | `backend/routers/work_logs.py:_resolve_work_log_scope` |

### Suplantacion

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-50 | Solo el PA suplanta (`POST /admin/impersonate/{user_id}`); otro usuario recibe 403 | Cerrado | 3.4, FRD RF-07 | `backend/routers/auth.py:impersonate_user` |
| R-ACC-51 | El token de suplantacion lleva `scope = impersonated`, `admin_user_id` del PA y caduca a los 10 min | Cerrado | 3.4, FRD RF-07 | `backend/routers/auth.py:impersonate_user`. Hallazgo #79: el refresh lo prolonga |
| R-ACC-52 | La sesion del PA se guarda en `admin_access_token` y `admin_refresh_token`, y `POST /admin/stop-impersonation` la restaura | Cerrado | FRD RF-07 | `backend/routers/auth.py:impersonate_user`, `backend/routers/auth.py:stop_impersonation` |
| R-ACC-53 | **Retirada (P4, 2026-11-22), sustituida por R-ACC-66 y R-ACC-67.** Crear, editar o borrar turnos durante una suplantacion registra en `audit_logs` el usuario suplantado y el PA. Con la suplantacion de solo lectura ya no hay escrituras que registrar | Retirada | 3.4, P4 | `backend/routers/work_logs.py:record_impersonation_audit` |
| R-ACC-66 | Durante una suplantacion toda peticion con metodo distinto de GET, HEAD u OPTIONS responde 403, salvo `stop-impersonation` y `logout` (las excepciones, por confirmar; el refresh no entra aqui, #79) | Cerrado | P4 | objetivo (hoy la suplantacion escribe) |
| R-ACC-67 | Cada suplantacion queda auditada: inicio y fin se registran en `audit_logs` con el PA y el usuario suplantado | Cerrado | P4 | objetivo (hoy solo se registran las escrituras, R-ACC-53) |
| R-ACC-68 | Durante una suplantacion el frontend muestra un banner visible con el usuario suplantado y la salida | Cerrado | P4 | objetivo |
| R-ACC-69 | Cada empresa de prueba tiene un usuario demo manager y uno worker, que el PA usa para ver lo que ve cada rol en lugar de "ver como" | Cerrado | P4 | objetivo |

### Que ve cada rol

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-54 | La vista completa de la empresa solo la recibe el PA actuando; manager y worker reciben la reducida. Nota 2026-11-22: se quita "PA en ver como" porque "ver como" se retira (P4) | Cerrado | 9, O5, P4 | `backend/routers/v2/companies.py:read_company`, `backend/routers/v2/companies.py:read_my_companies` |
| R-ACC-55 | La vista reducida lleva `id`, `name`, `is_managed`, los ajustes de interfaz y, en solo lectura, `worklog_definitions` y `tax_config` | Cerrado | 9, O5 | `backend/routers/v2/schemas.py:CompanyReduced` |
| R-ACC-56 | `is_active` de la empresa solo lo ve el PA; manager y worker no lo ven | Cerrado | 9, O14 | la vista reducida (`backend/routers/v2/schemas.py:CompanyReduced`) no lo expone |
| R-ACC-57 | `fiscal_id` no existe en ninguna respuesta | Cerrado | 9 | columna borrada (PR-23, `backend/scripts/repair_fiscal_id.py`) |
| R-ACC-58 | Las tarifas de todos los miembros las ven PA y manager; el worker recibe 403 | Cerrado | 9 | `backend/routers/v2/members.py:list_rates` |
| R-ACC-59 | Empresas de otro usuario: el PA ve todas; el worker recibe 403 | Cerrado | 9 | `backend/routers/v2/companies.py:read_user_companies` |
| R-ACC-60 | Empresas de otro usuario, para el manager: solo ve su empresa activa y ninguna otra del usuario | Cerrado | 9, O14 | `read_user_companies` limita a la empresa del token |
| R-ACC-61 | Para quien no es PA, empresa inexistente, ajena o sin membresia responde el mismo 403; el 404 solo lo ve el PA | Cerrado | 9 (P-5) | `backend/access_policy.py:authorize_company` |
| R-ACC-62 | El parte diario del worker no incluye las claves de importe; el de manager y PA si | Cerrado | 9 (P-14) | `backend/routers/companies.py:read_daily_report` |
| R-ACC-63 | Los 403 no devuelven datos internos (`is_manager`, ids de usuario); el `detail` es un texto claro | Cerrado | 9 | `backend/access_policy.py` (`MSG_*`) |
| R-ACC-78 | En el parte diario (modulo `worker_daily_report`) el worker ve descripcion, horas y tipo de los turnos ajenos, sin importes, y no puede abrir el detalle de un turno ajeno. Un worker con el modulo ve la lista de empresas (por comprobar: hoy el filtro exige manager) | Cerrado | S8 | objetivo; ver R-ACC-62 |

### Modo de empresa y ajustes

`is_managed` se mantiene (S7). La empresa **gestionada** es la `is_managed =
true`; la **libre** es la `is_managed = false` (la "autonoma" del glosario). No
hay modo "personal". Detalle en la seccion 8 de
[revision-base.md](../producto/revision-base.md).

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-70 | En una empresa gestionada el worker es espectador en todo: no crea, edita ni borra turnos y no edita su tarifa, su bruto/neto ni sus impuestos (403) | Cerrado | S7, T1, P7 | `backend/access_policy.py:can_write_work_log`, `can_edit_member_rates` |
| R-ACC-71 | En una empresa libre el worker crea, edita y borra sus propios turnos y edita su tarifa, su bruto/neto y sus impuestos propios; no toca los de otros | Cerrado | S7, T1, P7 | `backend/access_policy.py:can_write_work_log`, `can_edit_member_rates` |
| R-ACC-72 | El manager edita los tipos de turno y los impuestos (`worklog_definitions`, `tax_config`) de su empresa activa mediante un endpoint propio. El PA los crea en el alta | Cerrado | S1 | objetivo (hoy solo el PA edita la empresa) |
| R-ACC-73 | El endpoint de R-ACC-72 no acepta `is_active` ni `is_managed`: solo el PA los cambia | Cerrado | S1 | objetivo |
| R-ACC-74 | El servidor rechaza un override de impuesto de un miembro cuyo nombre no exista en los impuestos de la empresa; al quitar un impuesto de la empresa se limpian los overrides huerfanos | Cerrado | S4 | objetivo |

### Alta publica B2C (objetivo)

Se disena ya y se implementa tras migrar Usuarios y Membresias (P1, O16). El
B2C no es otro producto: es un alta automatica.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-75 | El alta publica crea una empresa con el nombre del usuario y lo hace su unico worker, sin manager | Cerrado | P1 | objetivo |
| R-ACC-76 | La empresa del alta publica nace con impuestos y tipos de turno prefijados | Cerrado | P1 | objetivo |
| R-ACC-77 | Al principio el usuario del alta publica no tiene acceso de manager sobre su empresa. Si mas adelante se concede, se resuelve por rol, no por modo | Cerrado | P1 | objetivo |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Token `2fa_pending` en `GET /users/me` | 403 | R-ACC-08 |
| Usuario desactivado con token aun vigente | 401 en la siguiente peticion | R-ACC-16 |
| Manager de A con `cid` de B pide datos de A | 403 "Cambia a esta empresa para gestionarla" | R-ACC-41 |
| Worker pide una empresa suspendida de la que es miembro | 403 "Empresa inactiva o suspendida" | R-ACC-19 |
| No miembro pide una empresa suspendida | 403 "No tienes acceso a esta empresa" | R-ACC-20 |
| PA pide una empresa inexistente | 404 | R-ACC-61 |
| PA suplantando a un worker hace `POST /work-logs` | 403 de solo lectura | R-ACC-66 |
| Manager intenta cambiar el rol de una membresia | 403 | R-ACC-64 |
| Worker de empresa gestionada intenta editar su tarifa | 403 | R-ACC-70 |
| Worker de empresa libre edita su tarifa | 2xx | R-ACC-71 |
| Membresia degradada a worker | Efecto en la siguiente peticion (se lee de BD, sin cache) | R-ACC-79 |
| Unico PA activo se desactiva | 403 (a si mismo) | R-ACC-31 |
| Otro PA desactiva al unico PA activo restante | 409 | R-ACC-32 |
| Login con `company_id` de una empresa sin membresia | Token con la primera empresa por `sort_order` | R-ACC-34 |

## Relacion con otras entidades

- Empresa (`R-EMP`): suspension e `is_managed` alimentan las comprobaciones de R-ACC-19 y las de escritura.
- Membresia (`R-MEM`): rol y `is_active` deciden R-ACC-18, R-ACC-21 y R-ACC-23.
- Modulo (`R-MOD`): `require_module` aplica R-ACC-24.
- Auditoria (`R-AUD`): R-ACC-53 escribe en `audit_logs`.
