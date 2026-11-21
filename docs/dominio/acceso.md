# Acceso

Prefijo: `R-ACC`. Tablas: `users`, `company_members`, `user_sessions`. Modelos:
`User`, `CompanyMember`, `UserSession` (`backend/models.py`). Politica:
`backend/access_policy.py`; dependencias: `backend/routers/deps.py`.

Reglas de token, sesion, [empresa activa](../glosario.md), roles,
[ver como](../glosario.md), [suplantacion](../glosario.md) y que ve cada rol.
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
| `view_as` | texto | No | `worker` o `manager`. Solo para PA con `cid` |
| `admin_user_id` | UUID | No | PA que suplanta. Solo con `scope = impersonated` |
| `iat`, `type`, `jti` | varios | Si | Tecnicos: emision, tipo (`access`, `refresh`) e ID para la lista negra |

## Reglas

### Token y sesion

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-01 | El access token se firma con RS256 y caduca a los 30 min | Cerrado | 3.1 | `backend/auth.py:create_access_token` |
| R-ACC-02 | El access token no lleva `role` ni `is_admin`; solo los claims de la tabla Campos | Cerrado | 3.1, O7 | `backend/auth.py:generate_user_tokens` |
| R-ACC-03 | El rol de plataforma y el de empresa se leen de BD en cada peticion; si el token trae `role` o `is_admin`, se ignoran | Cerrado | 3.1, O7 | `backend/auth.py:_attach_context` |
| R-ACC-04 | El frontend obtiene rol de plataforma, empresa activa, rol activo y "ver como" de `GET /users/me` | Cerrado | 3.1 | `backend/routers/users.py:read_users_me` |
| R-ACC-05 | El token se lee de la cookie HttpOnly `access_token` o, si falta, de la cabecera `Authorization: Bearer` | Confirmar | FRD 2.1 | `backend/auth.py:get_token_from_request` |
| R-ACC-06 | El `scope` no es un plan ni un permiso de empresa: la cuenta gratuita se modela con `module_subscriptions` | Cerrado | 3.1 | objetivo (no hay cuenta gratuita) |
| R-ACC-07 | Login con contrasena correcta y 2FA activo emite un token `2fa_pending` de 5 min y ningun refresh token | Cerrado | 3.1, FRD RF-03 | `backend/routers/auth.py:login_for_access_token` |
| R-ACC-08 | Un token `2fa_pending` solo vale en `POST /verify-2fa`; en cualquier otro endpoint responde 403 | Cerrado | 3.2 n.3 | `backend/auth.py:get_verified_user`, `backend/routers/auth.py:verify_2fa` |
| R-ACC-09 | `POST /verify-2fa` con un token que no es `2fa_pending` responde 403 | Cerrado | 3.2 n.3 | `backend/routers/auth.py:verify_2fa` |
| R-ACC-10 | Login de un usuario con `users.is_active = false` responde 403, tambien si es PA | Cerrado | 2.3, 3.4 | `backend/routers/auth.py:login_for_access_token` |
| R-ACC-11 | No existe registro publico: solo el PA crea usuarios (`POST /users`) | Cerrado | 3.4 | `backend/routers/users.py:create_user_admin` |
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
| R-ACC-21 | El rol sale de la membresia en BD con cache Redis de 60 s; si Redis falla o no tiene el dato, se lee de BD y la peticion sigue | Cerrado | 3.2 n.6 | `backend/routers/deps.py:load_company_facts`, `backend/access_cache.py` |
| R-ACC-22 | Cambiar rol o estado de una membresia, o `is_active` de una empresa, invalida su cache de acceso al momento | Cerrado | 3.2 | `SqlAlchemyCompanyMemberRepository.save` y `SqlAlchemyCompanyRepository.save` (`backend/src/infrastructure/persistence/sqlalchemy/repositories/company_repository.py`), `backend/crud.py:join_company` |
| R-ACC-23 | Si el rol no alcanza el minimo del endpoint, responde 403 | Cerrado | 3.2 n.7 | `backend/access_policy.py:authorize_company` |
| R-ACC-24 | En un endpoint de pago sin el modulo en la empresa ni en el usuario responde 403; el PA actuando pasa | Cerrado | 3.2 n.8 | `backend/routers/deps.py:require_module`, `backend/routers/deps.py:authorize` |
| R-ACC-25 | El bypass del PA vive en un solo punto; ningun handler repite `if not is_platform_admin` | Confirmar | P2 (direccion cerrada, forma por confirmar) | `backend/access_policy.py:authorize_company`, `backend/routers/deps.py:acting_platform_admin` |

### Roles

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-26 | El PA es el usuario con `users.role = admin` y accede a cualquier empresa sin membresia | Cerrado | 2.2 | `backend/access_policy.py:authorize_company` |
| R-ACC-27 | Los unicos roles de empresa con efecto son `manager` y `worker`; el rol `admin` de membresia se trata como `manager` | Cerrado | 2.2 | `backend/access_policy.py:normalize_member_role` |
| R-ACC-28 | Un endpoint que exige rol worker admite tambien al manager: su rol incluye el de worker | Cerrado | 3.1 | `backend/access_policy.py:authorize_company` (`_ROLE_RANK`) |
| R-ACC-29 | Solo el PA cambia el rol de una membresia | Cerrado | 2.2 | `backend/routers/v2/members.py:set_member_role` |
| R-ACC-30 | Un usuario no puede cambiar su propio rol de plataforma | Cerrado | 2.2 | `backend/schemas.py:UserSelfUpdate` (sin `role`), `backend/crud.py:ensure_platform_admin_invariants` |
| R-ACC-31 | Un PA no puede desactivarse a si mismo (403) | Cerrado | 3.4 | `backend/crud.py:ensure_platform_admin_invariants` |
| R-ACC-32 | Ningun cambio puede dejar la plataforma sin PA activo (409) | Cerrado | 3.4 | `backend/crud.py:ensure_platform_admin_invariants` |

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

### Ver como

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-44 | Solo el PA usa "ver como"; `switch-scope` con `view_as` de otro usuario responde 403. El manager no tiene "entrar como worker" | Cerrado | 3.1 | `backend/routers/auth.py:switch_scope` |
| R-ACC-45 | "Ver como" exige empresa: `view_as` sin `company_id` responde 422 | Cerrado | 3.1 | `backend/routers/auth.py:switch_scope`, `backend/auth.py:generate_user_tokens` |
| R-ACC-46 | Los roles de "ver como" son `worker` y `manager` | Cerrado | 3.1 | `backend/access_policy.py:VIEW_AS_ROLES` |
| R-ACC-47 | En "ver como", toda peticion con metodo distinto de GET, HEAD u OPTIONS responde 403, salvo `switch-scope`, `logout` y `refresh-token` | Cerrado | 3.1 | `backend/access_policy.py:assert_view_as_read_only` |
| R-ACC-48 | En "ver como" el PA tiene los permisos del rol elegido y pierde los de PA | Cerrado | 3.1 | `backend/routers/deps.py:acting_platform_admin`, `backend/access_policy.py:authorize_company` |
| R-ACC-49 | En "ver como" worker, los turnos "propios" que se muestran son los del PA | Cerrado | 3.1 | `backend/routers/work_logs.py:_resolve_work_log_scope` |

### Suplantacion

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-50 | Solo el PA suplanta (`POST /admin/impersonate/{user_id}`); otro usuario recibe 403 | Cerrado | 3.4, FRD RF-07 | `backend/routers/auth.py:impersonate_user` |
| R-ACC-51 | El token de suplantacion lleva `scope = impersonated`, `admin_user_id` del PA y caduca a los 10 min | Cerrado | 3.4, FRD RF-07 | `backend/routers/auth.py:impersonate_user`. Hallazgo #79: el refresh lo prolonga |
| R-ACC-52 | La sesion del PA se guarda en `admin_access_token` y `admin_refresh_token`, y `POST /admin/stop-impersonation` la restaura | Cerrado | FRD RF-07 | `backend/routers/auth.py:impersonate_user`, `backend/routers/auth.py:stop_impersonation` |
| R-ACC-53 | Crear, editar o borrar turnos durante una suplantacion registra en `audit_logs` el usuario suplantado y el PA | Cerrado | 3.4 | `backend/routers/work_logs.py:record_impersonation_audit` |

### Que ve cada rol

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-ACC-54 | La vista completa de la empresa solo la recibe el PA actuando; manager, worker y PA en "ver como" reciben la reducida | Cerrado | 9, O5 | `backend/routers/v2/companies.py:read_company`, `backend/routers/v2/companies.py:read_my_companies` |
| R-ACC-55 | La vista reducida lleva `id`, `name`, `is_managed`, los ajustes de interfaz y, en solo lectura, `worklog_definitions` y `tax_config` | Cerrado | 9, O5 | `backend/routers/v2/schemas.py:CompanyReduced` |
| R-ACC-56 | `is_active` de la empresa lo ven PA y manager, no el worker | Abierto (O14) | 9 | la vista reducida (`backend/routers/v2/schemas.py:CompanyReduced`) no lo expone, ni al manager |
| R-ACC-57 | `fiscal_id` no existe en ninguna respuesta | Cerrado | 9 | columna borrada (PR-23, `backend/scripts/repair_fiscal_id.py`) |
| R-ACC-58 | Las tarifas de todos los miembros las ven PA y manager; el worker recibe 403 | Cerrado | 9 | `backend/routers/v2/members.py:list_rates` |
| R-ACC-59 | Empresas de otro usuario: el PA ve todas; el worker recibe 403 | Cerrado | 9 | `backend/routers/v2/companies.py:read_user_companies` |
| R-ACC-60 | Empresas de otro usuario, para el manager: solo las que comparte con el | Abierto (O14) | 9 | `read_user_companies` limita a la empresa del token |
| R-ACC-61 | Para quien no es PA, empresa inexistente, ajena o sin membresia responde el mismo 403; el 404 solo lo ve el PA | Cerrado | 9 (P-5) | `backend/access_policy.py:authorize_company` |
| R-ACC-62 | El parte diario del worker no incluye las claves de importe; el de manager y PA si | Cerrado | 9 (P-14) | `backend/routers/companies.py:read_daily_report` |
| R-ACC-63 | Los 403 no devuelven datos internos (`is_manager`, ids de usuario); el `detail` es un texto claro | Cerrado | 9 | `backend/access_policy.py` (`MSG_*`) |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Token `2fa_pending` en `GET /users/me` | 403 | R-ACC-08 |
| Usuario desactivado con token aun vigente | 401 en la siguiente peticion | R-ACC-16 |
| Manager de A con `cid` de B pide datos de A | 403 "Cambia a esta empresa para gestionarla" | R-ACC-41 |
| Worker pide una empresa suspendida de la que es miembro | 403 "Empresa inactiva o suspendida" | R-ACC-19 |
| No miembro pide una empresa suspendida | 403 "No tienes acceso a esta empresa" | R-ACC-20 |
| PA pide una empresa inexistente | 404 | R-ACC-61 |
| PA en "ver como" worker hace `POST /work-logs` | 403 de solo lectura | R-ACC-47 |
| PA en "ver como" llama a un endpoint solo de PA | 403 | R-ACC-48 |
| Membresia degradada a worker con cache de 60 s vigente | Efecto inmediato (cache invalidada) | R-ACC-22 |
| Redis caido | Se lee de BD; la peticion sigue | R-ACC-21 |
| Unico PA activo se desactiva | 403 (a si mismo) | R-ACC-31 |
| Otro PA desactiva al unico PA activo restante | 409 | R-ACC-32 |
| Login con `company_id` de una empresa sin membresia | Token con la primera empresa por `sort_order` | R-ACC-34 |

## Relacion con otras entidades

- Empresa (`R-EMP`): suspension e `is_managed` alimentan las comprobaciones de R-ACC-19 y las de escritura.
- Membresia (`R-MEM`): rol y `is_active` deciden R-ACC-18, R-ACC-21 y R-ACC-23.
- Modulo (`R-MOD`): `require_module` aplica R-ACC-24.
- Auditoria (`R-AUD`): R-ACC-53 escribe en `audit_logs`.
