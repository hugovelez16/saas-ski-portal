# Analisis de la entidad Empresa (Company)

Rama analizada: `develop`. Fecha: 2026-10-15.

## 0. Alcance y fiabilidad

Documento de referencia sobre que es una empresa en el sistema, que puede hacer cada rol con ella y que esta sin decidir. Esta pensado para que cualquier pregunta basica ("un trabajador puede anadir un turno si la empresa es gestionada?") tenga respuesta escrita.

Metodo: lectura estatica del codigo por 18 agentes con tareas acotadas. Sus fragmentos completos, con evidencia `fichero:linea`, estan en `docs/empresa/anexos/` (ver seccion 12). **No se ha ejecutado ningun test ni se ha probado ninguna peticion real.**

Niveles de confianza usados en las tablas de hallazgos:

- **V**: verificado leyendo el codigo directamente en esta sesion (ademas del agente).
- **L**: afirmado por un agente tras leer el codigo; no reproducido.
- **P**: plausible por inferencia (por ejemplo, un 500 por violacion NOT NULL); requiere prueba.

Convenciones: "platform admin" = `User.role == admin` (claim `is_admin` del JWT). "Manager" = rol de empresa `manager` o `admin` en la membresia. "Worker" = rol `worker`. "Gestionada" = `Company.is_managed = true`. "Suspendida" = `Company.is_active = false`.

### Aclaracion sobre "scope"

El token JWT tiene un claim `scope` con valores `full` (defecto), `2fa_pending` e `impersonated`. **No existe un scope `manager`.** "manager" es un valor del claim `role`, que se fija al emitir el token (`auth.py:273-278`) o al cambiar de empresa (`POST /auth/switch-scope`).

Consecuencia practica: el `scope` solo hace dos cosas. `2fa_pending` bloquea todo lo que use `get_verified_user`; `impersonated` genera registro en `audit_logs` al escribir turnos. **No restringe ningun permiso de empresa.** Lo que decide los permisos de empresa son los claims `cid` (empresa activa) y `role`, mas el flag `is_admin`.

## 1. Respuesta directa a la pregunta de partida

> Un usuario puede anadir un turno si la empresa tiene `is_managed`?


| Caso                                                                | Resultado                                                    | Evidencia                                                                    |
| ------------------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Worker crea turno propio, empresa gestionada y activa               | **SI** (el POST no consulta `is_managed`)                    | `routers/work_logs.py:31-63` (V por lectura de agente y auditoria previa S3) |
| Worker edita o borra su turno, empresa gestionada                   | NO, 403                                                      | `routers/work_logs.py:262-265, 303-306`                                      |
| Worker crea turno propio, empresa autonoma y activa                 | SI                                                           | `routers/work_logs.py:44-63`                                                 |
| Worker edita o borra su turno, empresa autonoma                     | SI (solo los suyos)                                          | `routers/work_logs.py:256-260`                                               |
| Cualquier no-platform-admin crea, edita o borra, empresa suspendida | NO, 403                                                      | `routers/work_logs.py:45, 253, 294`                                          |
| Manager crea turnos a nombre de otro, cualquier modo                | SI, sin validar que el destino sea miembro                   | `routers/work_logs.py:49-51`; `crud.py:436-447`                              |
| Scope (`full`, `2fa_pending`, `impersonated`)                       | No cambia el resultado, salvo `2fa_pending` que bloquea todo | `auth.py:377`                                                                |


Decision pendiente: D1 (seccion 9). El caso "worker crea en gestionada" es coherente con "no puede modificar"? Hoy permite crear y luego impide corregir.

## 2. Que es una empresa

Una empresa es el **tenant** del sistema. Agrupa:

- Miembros (`company_members`) con rol por empresa y su "contrato" (`rates_config`).
- Turnos (`work_logs`), con importes calculados con las tarifas del miembro y los impuestos de la empresa.
- Definiciones de tipos de turno (`worklog_definitions`) y configuracion fiscal (`tax_config`).
- Suscripciones a modulos (`module_subscriptions`).
- Ajustes libres (`settings`).

Un usuario puede pertenecer a varias empresas con roles distintos (PK compuesta `(user_id, company_id)`), pero cada token tiene **una sola empresa activa** (`cid`) y un solo `role`.

### 2.1 Columnas de `companies`


| Columna                    | Tipo / default                                      | Se usa                      | Observacion                                                                                          |
| -------------------------- | --------------------------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------- |
| `id`                       | UUID, generado en app                               | si                          |                                                                                                      |
| `name`                     | String NOT NULL, sin longitud                       | si                          | Sin UNIQUE. Acepta cadena vacia. `crud.create_user` busca la empresa "Personal" por nombre           |
| `fiscal_id`                | String nullable                                     | si (se muestra y se guarda) | Sin UNIQUE ni validacion de formato. El alta desde UI envia `""`                                     |
| `tax_config`               | JSONB, default modelo `{"social_security": 0.0648}` | si, en calculo de importes  | Tres defaults distintos (modelo, schema, UI). Claves leidas: `social_security`, `irpf_base`, `extra` |
| `worklog_definitions`      | JSONB, default `{}`                                 | si                          | Backend lee `unit`, `is_range`, `label`. La clave `fields` la usan seed y frontend, no el backend    |
| `is_active`                | Boolean NOT NULL, server default true               | si                          | Suspension. Solo platform admin la cambia                                                            |
| `is_managed`               | Boolean NOT NULL, server default false              | si                          | Modo gestionado. Solo platform admin la cambia                                                       |
| `settings`                 | JSONB, default `{}`                                 | si, sobre todo frontend     | Dict libre. Backend no lee claves de negocio                                                         |
| `created_at`, `updated_at` | DateTime sin zona, `utcnow`                         | solo serializacion          | `updated_at` solo se actualiza por ORM                                                               |


### 2.2 Que sobra


| Elemento                                                                                                  | Motivo                                                                                                                             |
| --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Capa `backend/src/` completa (entidades, mapper, repositorio, `CreateWorkLogUseCase`, `TaxConfiguration`) | Ningun router la usa; solo tests. Duplica la logica viva de `crud.py` con diferencias (ver 7)                                      |
| La entidad de dominio `Company`                                                                           | No tiene `is_active`, `is_managed` ni `updated_at`; el repositorio no los escribe                                                  |
| `settings.is_managed` en el frontend                                                                      | El backend nunca escribe esa clave; la regla real es la columna. Lo leen `CompaniesPageClient.tsx:137,262` y `profile/page.tsx:94` |
| `(currentCompany as any)?.is_managed` en `profile/page.tsx:95`                                            | El backend serializa `isManaged` (camelCase); la clave snake\_case nunca llega                                                     |
| `company-settings-dialog.tsx` (y su campo `social_security_deduction`)                                    | No se importa en ningun sitio; el backend descartaria el campo                                                                     |
| `crud.get_subscriptions`                                                                                  | Sin llamadas fuera de `crud.py`                                                                                                    |
| `routers/utils.require_module`                                                                            | Definido, no usado por ningun endpoint                                                                                             |
| `backend/test_rates.py`                                                                                   | No es un test: ejecuta una consulta a BD al importarse y no aserta                                                                 |
| `print` de depuracion en `routers/companies.py:70,340-343,348` y `crud.py:841,848`                        | Vuelcan emails, ids y payloads completos a stdout                                                                                  |


### 2.3 Que falta

Sugerencias, no hechos. Marcadas por prioridad de negocio estimada.


| Falta                                                                                  | Por que                                                                      |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Borrado o archivado real (fecha y autor de baja)                                       | Hoy solo existe `is_active`; no hay `DELETE` ni FK con `ondelete`            |
| UNIQUE (o aviso) en `fiscal_id` y `name`                                               | Dos empresas pueden tener el mismo CIF; `Personal` se busca por nombre       |
| Edicion de `name` y `fiscal_id` en la UI                                               | Solo se fijan al crear; el backend los acepta en PUT                         |
| Validacion de forma de `tax_config`, `worklog_definitions`, `rates_config`, `settings` | Hoy solo `dict[str, float]` o `dict[str, Any]`                               |
| Guardia de ultimo admin/manager                                                        | Una empresa puede quedarse sin gestores                                      |
| Auditoria de cambios de empresa, membresia, rol y tarifa                               | `audit_logs` solo cubre impersonacion y reset de 2FA                         |
| Historial de tarifas                                                                   | Solo existe `calculation_snapshot` por turno                                 |
| Invitaciones por email                                                                 | Solo se anade a usuarios ya existentes                                       |
| `owner_id`, contacto, `timezone`, `currency`, `slug`, `plan`                           | No existen. `plan` podria resolverse por modulo (ya modelado)                |
| Estado de cierre o aprobacion de turnos                                                | Ningun endpoint de escritura lo consulta; no hay estado en el flujo revisado |


## 3. Roles y como se resuelven


| Concepto               | Valores                                          | Donde vive                     | Nota                                                                          |
| ---------------------- | ------------------------------------------------ | ------------------------------ | ----------------------------------------------------------------------------- |
| `UserRole`             | `admin`, `user`                                  | `users.role`; claim `is_admin` | Nivel plataforma. No se revalida contra BD hasta que caduca el token (30 min) |
| `CompanyRole`          | `admin`, `manager`, `worker`                     | `company_members.role`         | El comentario de `admin` dice "Deprecated or specific"                        |
| Claim `role` del token | `manager`, `worker` (y `admin` por switch-scope) | JWT                            | Membresia admin o manager emite `manager`                                     |
| Claim `cid`            | UUID de la empresa activa                        | JWT                            | Unica fuente de la "empresa activa". No hay header ni query de contexto       |
| `scope`                | `full`, `2fa_pending`, `impersonated`            | JWT                            | Ver seccion 0                                                                 |


Regla efectiva (`routers/utils.py:11-53`): `is_manager_of_company` y `check_manager_access` **no consultan la BD**. Devuelven true si eres platform admin, o si `cid == company_id` y `role in (manager, admin)`. Consecuencias:

1. Para casi todos los permisos, **admin de empresa y manager son iguales**. La unica diferencia real esta en `PUT /companies/{id}/members/{uid}`, que calcula `is_company_admin` desde la BD: solo el admin de empresa (o platform admin) puede cambiar roles.
2. Un cambio de rol, una baja de membresia o una suspension de empresa **no tienen efecto hasta que caduca el access token** (30 min).
3. Solo se opera sobre la empresa del token. Un manager de A con token en B no gestiona A hasta cambiar de empresa.

## 4. Matriz de permisos por endpoint de empresa

Leyenda: SI / NO / (nota). "Suspendida" = bloquea a todos salvo platform admin. PA = platform admin. Manager incluye admin de empresa. "Ajeno" = autenticado sin membresia en esa empresa.


| Endpoint                                   | PA                           | Manager                                                                                                                               | Worker                                                                                                            | Ajeno                | Detalles                                                                                                                                                                               |
| ------------------------------------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /companies`                           | todas, incluso suspendidas   | solo sus empresas con membresia activa y empresa activa                                                                               | idem                                                                                                              | lista vacia (no 403) | `limit` sin tope                                                                                                                                                                       |
| `POST /companies`                          | SI                           | NO (403)                                                                                                                              | NO                                                                                                                | NO                   | No crea membresia para el creador. Acepta cualquier valor de `is_active`/`is_managed`                                                                                                  |
| `PUT /companies/{id}`                      | todos los campos             | `name`, `fiscal_id`, `tax_config`, `worklog_definitions`, `settings` (si es la empresa del token). `is_active`/`is_managed` -&gt; 403 | NO                                                                                                                | NO                   | `{}` da 200 sin cambios. `name: null` probablemente da 500 (P). Enviar `is_managed` con el mismo valor tambien da 403                                                                  |
| `GET /companies/detailed`                  | todas con todos los miembros | empresas donde es manager                                                                                                             | solo si la empresa tiene el modulo `worker_daily_report`                                                          | 403                  | Devuelve todos los miembros, incluso inactivos                                                                                                                                         |
| `GET /companies/{id}`                      | SI                           | SI                                                                                                                                    | SI (cualquier miembro activo)                                                                                     | 403                  | Devuelve `fiscal_id`, `tax_config`, `settings` a todos los roles                                                                                                                       |
| `GET /companies/{id}/members`              | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   |                                                                                                                                                                                        |
| `POST /companies/{id}/members/add`         | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   | Solo usuarios existentes (404 si el email no existe: permite averiguar si un email tiene cuenta). Si ya existe y estaba inactivo, lo reactiva conservando el rol previo. No recibe rol |
| `PUT /companies/{id}/members/order`        | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   | No se ha verificado que ids ajenos a la empresa se ignoren (crud filtra por empresa y lista de ids: L)                                                                                 |
| `PUT /companies/{id}/members/{uid}/status` | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   | Usa `get_current_user` (no `get_verified_user`). Sin guardia de ultimo admin ni de auto-desactivacion                                                                                  |
| `GET /companies/{id}/rates-v2`             | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   | Devuelve tarifas de todos, incluidos inactivos. No consulta `is_managed`                                                                                                               |
| `PUT /companies/{id}/members/{uid}`        | todo                         | `rates_config`, `settings`, `is_active`, `sort_order` de cualquiera; `role` solo si no cambia                                         | solo a si mismo: `settings` siempre; `rates_config` solo si la empresa no es gestionada; `role` solo si no cambia | NO                   | Ver 5                                                                                                                                                                                  |
| `GET /companies/{id}/dashboard-summary`    | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   | Cache Redis por empresa y rango; si Redis cae, 500                                                                                                                                     |
| `GET /work-logs/billing-summary`           | SI                           | SI                                                                                                                                    | NO                                                                                                                | NO                   | No comprueba `is_active` de empresa                                                                                                                                                    |


### 4.1 Gestion de modulos por empresa


| Endpoint                                 | Quien                                           | Notas                                                                                                        |
| ---------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `GET /modules`                           | cualquier autenticado                           | Solo PA ve modulos inactivos                                                                                 |
| `POST/PUT /modules`, `GET /modules/{id}` | solo PA                                         |                                                                                                              |
| `GET /modules/subscriptions`             | PA todas; manager solo las de su empresa activa | Incluye expiradas y canceladas; no mira `is_active` de la empresa                                            |
| `POST/PUT/DELETE /modules/subscriptions` | solo PA                                         | Duplicados empresa+modulo permitidos; `scope` y `target_scope` sin validar; `PUT` con status invalido da 500 |
| `GET /modules/me`                        | cualquier autenticado                           | Une suscripciones personales y de la empresa activa. No usa rol ni `is_active` de empresa                    |


### 4.2 Usuarios y empresa


| Endpoint                                                               | Quien                                                                  | Notas                                                                                   |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `POST /users` (publico)                                                | cualquiera                                                             | Une al usuario a la empresa "Personal" como worker, si existe                           |
| `POST /users` (admin)                                                  | PA                                                                     | Con `company_id`, hace `join_company` como worker sin validar que exista ni este activa |
| `GET /users`, `PUT /users/{id}`, `PUT /users/{id}/status`, `reset-2fa` | solo PA                                                                |                                                                                         |
| `GET /users/{id}`                                                      | PA o manager con el target como miembro activo de la empresa del token |                                                                                         |
| `GET /users/{id}/companies`                                            | PA o manager de la empresa activa                                      | Devuelve **todas** las empresas del target, incluso inactivas y ajenas                  |
| `POST /users/{id}/reset-password-email`                                | PA o manager sobre miembro de su empresa activa                        |                                                                                         |
| `PUT /users/me`                                                        | el propio usuario                                                      | Acepta cualquier `default_company_id` sin validar membresia                             |
| `POST /auth/switch-scope`                                              | usuario con membresia activa y empresa activa                          | Ver H1                                                                                  |


## 5. Matrices de comportamiento

### 5.1 Turnos (`work_logs`) por modo de empresa


| Accion                                                 | Worker, autonoma                   | Worker, gestionada | Manager, cualquiera                      | PA                                                 |
| ------------------------------------------------------ | ---------------------------------- | ------------------ | ---------------------------------------- | -------------------------------------------------- |
| Crear turno propio                                     | SI                                 | **SI**             | SI                                       | SI                                                 |
| Crear turno de otro                                    | NO                                 | NO                 | SI, sin validar que sea miembro          | SI                                                 |
| Crear en lote (`/bulk`)                                | NO                                 | NO                 | SI, sin validar miembros                 | SI (`is_manager_of_company` devuelve true para PA) |
| Editar turno propio                                    | SI                                 | NO                 | SI (cualquier turno de su empresa)       | SI                                                 |
| Borrar turno propio                                    | SI                                 | NO                 | SI                                       | SI                                                 |
| Editar con `apply_to_group`                            | NO                                 | NO                 | SI                                       | SI                                                 |
| Listar sin filtros                                     | solo propios, de la empresa activa | idem               | todos los de la empresa con `company_id` | segun filtros                                      |
| Listar con modulo `worker_daily_report` y `company_id` | todos los de la empresa            | idem               | n/a                                      | n/a                                                |
| Billing summary                                        | NO                                 | NO                 | SI                                       | SI                                                 |


Con la empresa **suspendida**: crear, editar y borrar dan 403 a todos salvo PA. **Listar y billing siguen permitidos.**

Turnos con `company_id` NULL (columna nullable, heredados): se saltan las guardias de empresa suspendida y gestionada; solo cuenta ser propietario.

### 5.2 Miembros y tarifas por modo de empresa


| Accion                                   | Autonoma                          | Gestionada                                            |
| ---------------------------------------- | --------------------------------- | ----------------------------------------------------- |
| Worker edita su `rates_config`           | SI                                | NO (403 si lo envia; si no lo envia se fuerza `None`) |
| Worker envia `role` aunque sea el actual | permitido si no cambia            | 403 siempre                                           |
| Worker edita su `settings`               | SI                                | SI                                                    |
| Manager edita tarifas propias o ajenas   | SI                                | **SI** (el bloqueo excluye a managers)                |
| Manager cambia el rol de alguien         | NO (solo mantener el actual)      | NO                                                    |
| Admin de empresa cambia roles            | SI                                | SI                                                    |
| Manager desactiva a un admin de empresa  | SI (`is_active` sin lista blanca) | SI                                                    |


### 5.3 Empresa suspendida (`is_active = false`)


| Accion                                                                                  | Resultado                                                                                 |
| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Login y emision de token                                                                | PERMITE (no se mira la empresa); el `cid` suspendido queda en el JWT                      |
| `POST /auth/refresh-token`                                                              | PERMITE                                                                                   |
| `POST /auth/switch-scope` a la empresa                                                  | BLOQUEA (unico punto en auth)                                                             |
| Peticiones con un token ya emitido                                                      | PERMITE hasta que cada endpoint compruebe la empresa                                      |
| `GET /companies`, `/users/me/companies`                                                 | La oculta (no PA)                                                                         |
| `GET /companies/{id}`, miembros, tarifas, dashboard, `PUT` empresa, gestion de miembros | BLOQUEA (403, salvo PA)                                                                   |
| Crear, editar, borrar turnos                                                            | BLOQUEA (salvo PA)                                                                        |
| Listar turnos                                                                           | PERMITE                                                                                   |
| Billing summary                                                                         | PERMITE                                                                                   |
| `GET /modules/me`, `require_module`, `user_has_module`                                  | PERMITE                                                                                   |
| Frontend                                                                                | No lo refleja: no hay mensaje especifico ni guarda; el 403 se muestra como toast generico |
| Reactivar                                                                               | Solo PA, via `PUT /companies/{id}` con `isActive` (sin confirmacion en UI)                |


## 6. Hallazgos

Ordenados por severidad estimada. Ninguno esta probado en ejecucion.


| ID  | Sev.      | Hallazgo                                                                                                                                                                                                                                                                                                                                                                                            | Evidencia                                                                  | Conf.                                |
| --- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------ |
| H1  | Alta      | **Escalada worker -&gt; manager.** `switch-scope` solo valida `company_role == "manager"`. Con `"admin"` (o cualquier string) no se valida la membresia, y `is_manager_of_company` y `check_manager_access` aceptan `"admin"`. Un worker con membresia activa obtiene token con poder de manager en su empresa: puede editar/borrar cualquier turno, ver tarifas y dashboard, saltarse `is_managed` | `routers/auth.py:345-356`; `auth.py:273-288`; `routers/utils.py:24,51`     | V                                    |
| H2  | Alta      | **`User.is_active` no se aplica.** Ni login ni `get_current_user` ni `get_verified_user` lo leen. Desactivar a un usuario no impide autenticarse                                                                                                                                                                                                                                                    | `auth.py:294-402` (sin `is_active` de usuario); `routers/users.py:150-162` | V en `auth.py`; L en login           |
| H3  | Alta      | **Usuario sin membresia puede crear turnos con importe manual** en cualquier empresa activa: el router no comprueba membresia y `crud.create_work_log` usa `rates = {}` si no hay miembro, fallando solo sin `amount`/`net_amount`                                                                                                                                                                  | `crud.py:354-376`; `routers/work_logs.py:31-63`                            | V en crud; L en router               |
| H4  | Media     | **Permisos y estado cacheados en el JWT (30 min).** Baja de membresia, cambio de rol, suspension de empresa o degradacion de platform admin no se aplican hasta que caduca el token. Revocar la `UserSession` no invalida el access token                                                                                                                                                           | `routers/utils.py:41-54`; `auth.py:29,283,322`                             | V                                    |
| H5  | Media     | **Manager sin restricciones en empresa gestionada:** puede fijar tarifas propias y ajenas y desactivar a un admin de empresa (mass assignment sin lista blanca)                                                                                                                                                                                                                                     | `routers/companies.py:382,393-399`                                         | V                                    |
| H6  | Media     | **`POST /work-logs` ignora `is_managed`** (ver D1)                                                                                                                                                                                                                                                                                                                                                  | `routers/work_logs.py:31-63`                                               | L, coherente con auditoria previa S3 |
| H7  | Media     | **`PUT /work-logs/{id}` toma `company_id` y `user_id` del body** para tarifas e impuestos sin validar membresia en la empresa destino; la autorizacion usa el turno original                                                                                                                                                                                                                        | `crud.py:574-576,589-598`; `routers/work_logs.py:277-312`                  | L                                    |
| H8  | Media     | **`group_id` lo aporta el cliente** y `apply_to_group` busca por `group_id` sin filtrar empresa ni usuario                                                                                                                                                                                                                                                                                          | `crud.py:423,537-546`                                                      | L                                    |
| H9  | Media     | **Sin guardia de ultimo admin/manager** ni de auto-desactivacion; `create_company` tampoco crea membresia. Una empresa puede quedar sin gestor; la recuperacion exige PA o SQL manual                                                                                                                                                                                                               | `routers/companies.py:42-50,239-265`; `crud.py:750-783`                    | L                                    |
| H10 | Media     | **Reactivar via `members/add` conserva el rol previo:** un manager puede devolver el rol `admin` a un ex-admin                                                                                                                                                                                                                                                                                      | `routers/companies.py:220-226`                                             | L                                    |
| H11 | Media     | **`Company.is_active` no se comprueba en** listado de turnos, billing, modulos, login, refresh ni `require_module` (ver 5.3)                                                                                                                                                                                                                                                                        | seccion 5.3                                                                | L                                    |
| H12 | Media     | **Datos de empresa sensibles visibles para workers:** `GET /companies/{id}` y `/users/me/companies` devuelven `fiscal_id`, `tax_config` y `settings` a cualquier miembro. `GET /companies/detailed` da la lista completa de miembros a un worker con el modulo `worker_daily_report`                                                                                                                | `routers/companies.py:19-38,268-299`; `crud.py:673-686`                    | L                                    |
| H13 | Media     | **`GET /users/{id}/companies`** revela a un manager todas las empresas del usuario objetivo, incluso inactivas y ajenas                                                                                                                                                                                                                                                                             | `routers/users.py:282-289`                                                 | L                                    |
| H14 | Media     | **Manager puede cambiar `tax_config` y `worklog_definitions`** de su empresa: altera el calculo de importes de todos (ver D4)                                                                                                                                                                                                                                                                       | `routers/companies.py:73-82`                                               | L                                    |
| H15 | Media     | **Aislamiento no cubierto por tests:** ningun test cruza empresas (manager de A sobre B)                                                                                                                                                                                                                                                                                                            | `16-tests.md`                                                              | L                                    |
| H16 | Baja      | Debug en produccion: `print` con email/ids/payload y 403 que devuelve `is_manager`, `is_self`, `user_id`, `current_user_id`                                                                                                                                                                                                                                                                         | `routers/companies.py:70,340-348`; `crud.py:841,848`                       | L                                    |
| H17 | Baja      | Enumeracion de ids de empresa: varios endpoints devuelven 404 antes de autorizar; los mensajes de 403 distinguen empresa suspendida                                                                                                                                                                                                                                                                 | `routers/companies.py:152,272,307,417`                                     | L                                    |
| H18 | Baja      | Validaciones ausentes: `name` vacio o `null` (probable 500, P), `fiscal_id` sin formato ni unicidad, `limit` sin tope, UUID invalido en `DELETE/PUT /work-logs/{id}` da 500 (P), `status` de miembro como string libre                                                                                                                                                                              | `schemas.py:165-190`; `routers/work_logs.py:245`                           | L/P                                  |
| H19 | Baja      | `tax_config`: tres defaults distintos (modelo 0.0648, schema 0.0, UI 0.0). Claves de empresa `irpf_base` frente a override `irpf`. Tipos incorrectos se convierten en 0 sin aviso; `tax_overrides: null` puede dar `AttributeError`                                                                                                                                                                 | `models.py:87`; `schemas.py:168`; `crud.py:111-156`                        | L                                    |
| H20 | Baja      | Defaults mutables en `Column(JSONB, default={...})` (riesgo bajo; hoy no hay mutacion in-place)                                                                                                                                                                                                                                                                                                     | `models.py:87,91,97,120,123`                                               | L                                    |
| H21 | Baja      | Totales del dashboard incluyen turnos de miembros inactivos; el desglose por trabajador solo los activos                                                                                                                                                                                                                                                                                            | `crud.py:1057-1083`                                                        | L                                    |
| H22 | Baja      | `GET /companies/{id}/dashboard-summary`: la lectura de Redis esta fuera del `try`; forma de respuesta distinta entre cache y miss                                                                                                                                                                                                                                                                   | `routers/companies.py:430-450`                                             | L                                    |
| H23 | Baja      | Para PA, `GET /users/me/companies` omite `is_active` e `is_managed` (el schema pone true/false por defecto)                                                                                                                                                                                                                                                                                         | `routers/users.py:69-82`                                                   | L                                    |
| H24 | Baja      | `PUT /users/me` acepta `default_company_id` ajeno y podria borrar nombres (`UserSelfUpdate(**user.dict())` incluye `None`)                                                                                                                                                                                                                                                                          | `routers/users.py:165-173`; `crud.py:862-875`                              | L/P                                  |
| H25 | Baja      | `GET /work-logs` usa solo `is_platform_admin`; las escrituras tambien aceptan `role == admin`                                                                                                                                                                                                                                                                                                       | `routers/work_logs.py:44,79,125`                                           | L                                    |
| H26 | Info      | Frontend (ver 8)                                                                                                                                                                                                                                                                                                                                                                                    |                                                                            |                                      |
| H27 | Adyacente | **Bypass de desarrollo:** con `ENVIRONMENT` o `NODE_ENV` = development o `DEV_LOGIN_BYPASS` = true/1/yes, el login entra como admin sin comprobar clave. `docker-compose.prod.yml` no fija estas variables; depende del `.env` de produccion (no revisado). Fuera del alcance de empresa, pero de impacto critico si se activa                                                                      | `dev_seed.py:11-16`; `routers/auth.py:95-100`                              | L                                    |


Hallazgo descartado: el agente 05 senalo que PA no tenia bypass en `rates-v2`. `is_manager_of_company` devuelve true para PA (`routers/utils.py:45`), asi que no hay problema.

## 7. Dos implementaciones de la misma logica


| Regla              | Camino vivo                                              | Camino muerto (`backend/src/`)         | Divergencia                                                                 |
| ------------------ | -------------------------------------------------------- | -------------------------------------- | --------------------------------------------------------------------------- |
| Crear turno        | `crud.create_work_log`                                   | `CreateWorkLogUseCase`                 | El use case lanza error si no hay membresia activa; `crud` usa `{}` y sigue |
| Impuestos          | `crud._safe_float` y `.get`                              | `TaxConfiguration` (Decimal)           | Float tolerante frente a Decimal que lanza `InvalidOperation`               |
| Es manager         | `routers/utils.is_manager_of_company` (claims del token) | `CompanyMember.is_manager` (rol de BD) | Distinta fuente de verdad                                                   |
| Empresa "Personal" | `crud.create_user` (por nombre)                          | `Company.is_personal`                  | Solo la de `crud` se usa                                                    |
| Estado de empresa  | columnas `is_active`/`is_managed`                        | no existe en la entidad                | El repositorio no puede escribirlos                                         |


Los tests de gobernanza (`test_governance.py`) prueban contra el ORM y los routers, no contra `src/`.

## 8. Frontend


| Aspecto                        | Estado                                                                                                                                                                                                                                     |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Acciones en `/admin/companies` | Crear, activar/suspender, modo gestionada, miembros, tarifas, JSON de config. No hay editar nombre/CIF ni borrar                                                                                                                           |
| Guardas de rol en cliente      | Solo ocultan el enlace de menu; la pagina de admin no comprueba rol. Un manager vera los switches y recibira error                                                                                                                         |
| Confirmaciones                 | Ninguna al suspender o cambiar a gestionada                                                                                                                                                                                                |
| Errores                        | Toast generico; no se lee `detail` del backend. Un 403 al listar aparece como lista vacia                                                                                                                                                  |
| Idioma                         | Toasts del alta en ingles; resto en espanol                                                                                                                                                                                                |
| `/list` (turnos del worker)    | No comprueba `isManaged` ni rol: muestra alta, editar y borrar siempre. Los componentes internos pueden tener guardas (no verificado)                                                                                                      |
| `profile/page.tsx`             | Tarifas en solo lectura si `settings.is_managed` o `is_managed`; si la empresa activa no esta en la lista, **falla abierto** (editable). El campo real que envia el backend es `isManaged`, asi que la guarda puede no activarse nunca (P) |
| Rutas `/manager/*`             | Sin guarda de rol en el layout del cliente; solo menu condicional                                                                                                                                                                          |
| Empresa suspendida             | Sin tratamiento; el selector no filtra                                                                                                                                                                                                     |
| Contacto hardcodeado           | `layout.tsx` (\~269) incluye un correo de contacto en el JSX                                                                                                                                                                               |
| Tipos                          | `updateCompany(data: any)`; `taxConfig` marcado requerido pese a ser opcional en backend                                                                                                                                                   |
| Edicion de JSON                | Master Config (solo admin) y builders (admin o manager activo). Sin validacion de esquema; `parseFloat` sin control de NaN                                                                                                                 |


## 9. Decisiones de producto pendientes

El codigo no decide estas cuestiones. Cada una incluye una propuesta de partida, no un hecho.

Rellena la columna **Respuesta** (puedes escribir "acepto" para dar por buena la propuesta, o la alternativa que prefieras). Las filas con "Hallazgos" indican que codigo queda bloqueado hasta que se decida.


| ID  | Pregunta                                                                          | Propuesta                                                                                                                                                      | Hallazgos | Respuesta                                                                                                                                                                                            |
| --- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | En empresa gestionada, el worker puede crear turnos?                              | Decidir entre: (a) no puede crear (coherente con "no puede modificar"); (b) puede crear pero quedan "pendientes de aprobacion". Hoy: puede crear y no corregir | H6        | a                                                                                                                                                                                                    |
| D2  | En gestionada, el manager puede editar tarifas propias y ajenas?                  | Tarifas propias de un manager solo por admin de empresa                                                                                                        | H5        | si, admin de empresa ahora mismo no esta "habilitado" como tal, no hay nada que este hecho para admin de empres                                                                                      |
| D3  | Que distingue a admin de empresa y a manager?                                     | Hoy solo cambiar roles. Documentar o separar permisos (tarifas, `tax_config`, altas)                                                                           | H5, H10   | como he dicho en d2, admin empresa ahora mismo no es para nada, mas adelante será el que pueda crear los tipos de turnos, añadir usuarios...                                                         |
| D4  | Quien edita `tax_config`, `worklog_definitions` y `settings`?                     | Solo admin de empresa o PA para `tax_config`                                                                                                                   | H14       | PA y company admin, los dos, pero ahora mismo no hay ningun CA ni pretendo ponerlo                                                                                                                   |
| D5  | Que datos de empresa ve un worker?                                                | Solo `id`, `name`, `isManaged`, `isActive`; ocultar `fiscal_id` y `tax_config`                                                                                 | H12       | pues diria yo que depende de si la empresa es managed o no no?? o en verdad daria igual, con ver el name es mas que suficiente no?                                                                   |
| D6  | Con empresa suspendida: lectura permitida? sesiones abiertas? billing?            | Tratar `is_active` como bloqueo total en una dependencia comun, con mensaje claro en frontend                                                                  | H11       | is active yo lo entiendo como que la empresa es accesible, asique si es false no se deberia poder acceder de ninguna manera. Solo el PA (obviamente)                                                 |
| D7  | Regla de ultimo admin y de auto-desactivacion                                     | Bloquear degradar o desactivar al ultimo `admin`                                                                                                               | H9        | no entiendo esto                                                                                                                                                                                     |
| D8  | Baja de empresa: archivar con fecha y autor, o borrar? Retencion de datos?        | Archivar (`archived_at`, `archived_by`); no borrar fisicamente                                                                                                 |           | que es archivar?? archivar el que?? yo diria que no se deberia borrar nada                                                                                                                           |
| D9  | Invitar por email usuarios inexistentes?                                          | Flujo de invitacion con token y caducidad                                                                                                                      |           | invitarlos cuando?? necesito mas contexto, pero si, deberia de enviar un email no??                                                                                                                  |
| D10 | Unicidad de `name` y `fiscal_id`                                                  | UNIQUE parcial en `fiscal_id` (no nulo) y aviso en `name`                                                                                                      | H18       | Name no hace falta que sea unique, y fiscal id, la vd que podriamos omitirlo un poco no?? pq no sirve para absolutamente nada, podriamos quitarlo de los forms y esas cosas no?                      |
| D11 | Se exige membresia activa para crear turnos?                                      | Si, siempre                                                                                                                                                    | H3        | si                                                                                                                                                                                                   |
| D12 | Cambiar `is_managed` de true a false (y al reves): efecto sobre turnos existentes | Sin recalculo; registrar el cambio en auditoria                                                                                                                |           | no entiendo, que efecto va a tener?                                                                                                                                                                  |
| D13 | Turnos con `company_id` NULL                                                      | Migrar o asignar empresa y pasar la columna a NOT NULL                                                                                                         |           | efectivamente, haz eso, no debe haber turnos sin company\_id, es lo que separa unos datos de otros, ademas de que deberiamos activar el RLS en postgres para el company\_id no? (excepto para el PA) |
| D14 | Vida del token y revocacion al bajar una membresia o suspender                    | Revalidar membresia y `is_active` de empresa en una dependencia (cache Redis \~60 s), o acortar el TTL                                                         | H4        | vale, bien                                                                                                                                                                                           |
| D15 | Turnos aprobados o cerrados (nomina/periodo)                                      | Estado de cierre que bloquee edicion y borrado, tambien para managers                                                                                          |           | yo creo que no haria falta no? para que vas a bloquearlo?                                                                                                                                            |
| D16 | Plan o limites por empresa o por modulo                                           | Mantener por modulo (`module_subscriptions`) y anadir limites en `settings` o columna                                                                          |           | no entiendo lo de plan o limites                                                                                                                                                                     |
| D17 | Auditoria de cambios de empresa                                                   | Ampliar `audit_logs` a empresa, membresia, rol, tarifa e `is_managed`                                                                                          |           | me parece bien, cuantos mas logs mejor, nunca estan de mas, ademas, deberia haber alguna manera para que el PA los pueda ver facilmente no? porque sino tendria que meterme a la bd a verlos no?     |
| D18 | `timezone` y `currency` por empresa                                               | Anadir si se preve multi-pais                                                                                                                                  |           | secundario (puedes dejarlo apuntado) pero innecesario ahora mismo                                                                                                                                    |
| D19 | Un manager puede reactivar a un ex-admin con su rol?                              | Reactivar siempre como worker                                                                                                                                  | H10       | reactivar?? ahora mismo un manager puede activar o desactivar usuarios??                                                                                                                             |
| D20 | Que capa manda: `crud`/routers o `backend/src/`?                                  | Elegir una; eliminar la otra o cablearla con tests de paridad                                                                                                  |           | no entiendo esto la vd, por lo que parece, hay una inconsistencia en el codigo del back no?                                                                                                          |
| D21 | Admin de plataforma crea empresa: se anade como miembro?                          | No; mantener el acceso por privilegio de plataforma                                                                                                            |           | no, efectivamente, el acceso se hace por ser PA                                                                                                                                                      |


## 10. Preguntas basicas y respuestas

Formato: pregunta, respuesta, estado (D = definido en codigo, H = hallazgo, ? = no definido, ver seccion 9).

### 10.1 Ciclo de vida


| Pregunta                                        | Respuesta                                                                                                                                                                 | Estado     |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Quien crea empresas?                            | Solo platform admin, via `POST /companies` o el seed inicial                                                                                                              | D          |
| La empresa creada tiene miembros?               | No. El creador no queda como miembro                                                                                                                                      | D, ver D21 |
| El seed crea empresa?                           | Si, si `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD` estan definidos y el email no existe. Se reutiliza la empresa si el nombre ya existe. Se ejecuta en cada arranque | D          |
| Rol del primer admin en el seed?                | `UserRole.admin` y membresia `manager` (el `dev_seed` usa `CompanyRole.admin`)                                                                                            | D          |
| Se puede borrar una empresa?                    | No hay endpoint ni funcion. Un DELETE SQL falla por FK si tiene miembros, turnos, suscripciones o usuarios con `default_company_id`                                       | D, ver D8  |
| Como se da de baja?                             | `is_active = false` por platform admin. No guarda fecha, motivo ni autor                                                                                                  | D, ver D8  |
| Que pasa con los miembros al suspender?         | Nada: conservan membresia y `default_company_id`. El token sigue valido hasta caducar                                                                                     | D, H4      |
| Se puede renombrar?                             | El backend si (`PUT`); la UI no                                                                                                                                           | D          |
| Hay historial de cambios?                       | No                                                                                                                                                                        | D, ver D17 |
| Una empresa puede quedarse sin gestor?          | Si                                                                                                                                                                        | H9, ver D7 |
| Quien recupera una empresa sin gestor?          | Platform admin cambiando de contexto; no hay procedimiento escrito                                                                                                        | ?          |
| Que pasa al pasar `is_managed` de true a false? | Solo cambian permisos en tiempo de peticion; los importes de turnos existentes no se recalculan                                                                           | D, ver D12 |


### 10.2 Membresia


| Pregunta                                                          | Respuesta                                                                                                                                                                 | Estado    |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| Un usuario puede estar en varias empresas?                        | Si, con rol por empresa                                                                                                                                                   | D         |
| Como entra un usuario a una empresa?                              | Registro publico (empresa "Personal" si existe), alta por platform admin con `company_id`, o `members/add` por email de un manager                                        | D         |
| Rol inicial al unirse?                                            | `worker` siempre                                                                                                                                                          | D         |
| Se puede invitar a alguien sin cuenta?                            | No                                                                                                                                                                        | D, ver D9 |
| Quien cambia el rol de empresa?                                   | Admin de empresa o platform admin, via `PUT members/{uid}`; un manager no                                                                                                 | D         |
| Quien desactiva a un miembro?                                     | Manager o superior, via `status` o via `PUT members/{uid}`                                                                                                                | D         |
| Que pasa al desactivarlo?                                         | Se reasigna su `default_company_id`; los turnos se conservan; su token sigue valido; `get_company_member` no filtra `is_active`, asi que sigue calculandose con su tarifa | D, H3, H4 |
| Se puede borrar una membresia?                                    | No existe                                                                                                                                                                 | D         |
| Un manager puede desactivarse a si mismo?                         | Si, no hay guardia                                                                                                                                                        | H9        |
| `default_company_id` apunta a una empresa donde ya no es miembro? | Posible. Al emitir el token se usa la primera membresia activa si no hay membresia en el default; si no hay ninguna queda el `cid` con `role` nulo                        | D         |
| Usuario sin ninguna membresia activa?                             | Puede iniciar sesion y ver sus propios turnos; el frontend muestra "no estas vinculado a ninguna empresa". No ve empresas                                                 | D, H3     |
| El orden de miembros afecta a algo?                               | Solo a la presentacion (`sort_order`)                                                                                                                                     | D         |


### 10.3 Roles y tokens


| Pregunta                                             | Respuesta                                                                                                                                       | Estado |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Que significa el scope del token?                    | Ver seccion 0. No gobierna permisos de empresa                                                                                                  | D      |
| Como sabe el backend la empresa activa?              | Solo por el claim `cid`; el cambio es via `POST /auth/switch-scope`                                                                             | D      |
| Puede un manager actuar sobre otra empresa a la vez? | No; debe cambiar de empresa (nuevo token)                                                                                                       | D      |
| Platform admin sin empresa elegida?                  | Token con `cid` nulo; puede operar via bypass en cada endpoint                                                                                  | D      |
| Cuanto dura un access token?                         | 30 min (`auth.py:29`)                                                                                                                           | D      |
| Un cambio de rol surte efecto de inmediato?          | No; al caducar el token o al hacer `switch-scope`                                                                                               | H4     |
| Quien puede impersonar?                              | Solo platform admin; el token dura 10 min y sus escrituras de turnos se auditan                                                                 | D      |
| El token `2fa_pending` sirve para empresas?          | No: `get_verified_user` lo rechaza. Pero `get_current_user` lo acepta; usan ese: `GET /companies/{id}`, `rates-v2` y `PUT members/{uid}/status` | D, H   |


### 10.4 Turnos


| Pregunta                                                             | Respuesta                                                                                                 | Estado     |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------- |
| Un worker puede crear un turno si la empresa es gestionada?          | Si                                                                                                        | H6, ver D1 |
| Un worker puede editar o borrar un turno suyo si es gestionada?      | No                                                                                                        | D          |
| Y si no es gestionada?                                               | Si, solo los suyos                                                                                        | D          |
| Un worker puede crear turnos para otro usuario?                      | No                                                                                                        | D          |
| Un manager puede crear turnos para un usuario que no es miembro?     | Si, no se valida                                                                                          | H          |
| Un manager puede editar o borrar turnos de su empresa en gestionada? | Si                                                                                                        | D          |
| Puede un worker cambiar un turno a otra empresa?                     | `PUT` toma `company_id` del body; no se valida la empresa destino                                         | H7         |
| Hay turnos bloqueados/aprobados?                                     | No hay estado de cierre en el flujo revisado                                                              | ?, ver D15 |
| Se validan fechas pasadas, futuras o solapes?                        | No en el router; solapes no definidos en `crud`                                                           | ?          |
| Que ve un worker al listar?                                          | Sus turnos de la empresa activa; con modulo `worker_daily_report` y `company_id`, todos los de la empresa | D, H12     |
| Quien ve billing?                                                    | Manager y platform admin                                                                                  | D          |
| Que pasa con turnos sin empresa?                                     | Escapan a las guardias de suspension y gestionada                                                         | H          |
| Quien paga el importe si la tarifa no existe?                        | Si no hay `base_rate` y no hay importe manual, `ValueError` (400 en POST)                                 | D          |
| Cuando se fija el importe?                                           | Al crear o editar; se guarda `calculation_snapshot`. Cambiar la tarifa despues no recalcula               | D          |


### 10.5 Tarifas e impuestos


| Pregunta                  | Respuesta                                                                                  | Estado        |
| ------------------------- | ------------------------------------------------------------------------------------------ | ------------- |
| Donde viven las tarifas?  | `company_members.rates_config` (por miembro y por empresa)                                 | D             |
| Quien las edita?          | El propio miembro si la empresa no es gestionada; manager (siempre); admin de empresa y PA | D, H5, ver D2 |
| Quien las ve?             | El propio miembro (en su perfil) y los managers. Los workers no leen `rates-v2`            | D             |
| Precedencia de impuestos? | `tax_overrides` del miembro si no es `None`; si no, `tax_config` de la empresa; si no, 0   | D             |
| Y si faltan claves?       | Cero silencioso, sin error                                                                 | H19           |
| Se valida la estructura?  | No (back); front valida &gt;= 0 y 0-100                                                    | H             |
| Hay historial de tarifas? | No                                                                                         | ?, ver D17    |


### 10.6 Modulos y configuracion


| Pregunta                                   | Respuesta                                                                                                                                                                  | Estado    |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| Quien activa un modulo para una empresa?   | Solo platform admin                                                                                                                                                        | D         |
| Cuando ve un manager un modulo?            | Suscripcion activa o trial, no expirada, modulo activo global; rol no interviene en `/modules/me`                                                                          | D         |
| La suspension corta modulos?               | No                                                                                                                                                                         | H11       |
| La expiracion es automatica?               | Solo se filtra en consulta; no hay job conocido                                                                                                                            | ?         |
| Hay feature-gating en endpoints?           | Solo `worker_daily_report` en el listado de turnos y `/companies/detailed`; `require_module` no se usa                                                                     | D         |
| Que claves de `settings` usa el frontend?  | `modules`/`features`, `business_logic.*`, `worker_experience.*`, `ui_customization.labels`, `allow_tutorial`, `allow_coordination`, `allowed_rates`, `is_managed` (legacy) | D         |
| Quien puede cambiar `settings`?            | Manager de la empresa y PA; reemplaza el objeto completo                                                                                                                   | D, ver D4 |
| El backend rellena defaults de `settings`? | No; solo el frontend                                                                                                                                                       | D         |


### 10.7 Seguridad y aislamiento


| Pregunta                                       | Respuesta                                                                                                                                                                                                                                              | Estado     |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| Puede un manager de A ver o editar datos de B? | Las rutas de empresa comparan `cid` con el `company_id` de la ruta, y las consultas de `crud` filtran por empresa. Aun asi, `delete_work_log`, `update_work_log (group)`, `get_company` y `update_company` buscan por id global y confian en el router | L, H8      |
| Existe cache compartida entre empresas?        | Redis: `dashboard_summary:{company}:{rango}` y `company_rates:{id}`; la clave incluye la empresa y la autorizacion precede a la lectura                                                                                                                | D          |
| Se registran accesos o cambios?                | Solo impersonacion y reset de 2FA                                                                                                                                                                                                                      | D, ver D17 |
| Hay secretos de empresa en `settings`?         | No hay evidencia; contenido real no inspeccionado                                                                                                                                                                                                      | ?          |


## 11. Cobertura de tests

Se han inventariado los tests relacionados con empresa. Cubierto: gobernanza basica (manager no cambia rol, worker/modo gestionado, empresa suspendida en lectura de empresa y en alta de turno), modulos, supervisor, dashboard, billing.

Casos que **no** existen (resumen; la lista completa de 45 esta en el anexo 16):

- Aislamiento entre empresas en dashboard, billing, turnos, miembros y modulos.
- Escalada via `switch-scope`.
- Worker crea turno en gestionada y en autonoma.
- Platform admin sobre empresa suspendida (escritura).
- Manager cambia `is_active`/`is_managed`; manager desactiva miembros; ultimo admin.
- Cambio `is_managed` true -&gt; false; edicion de turnos por managers en gestionada.
- Token `2fa_pending`, `impersonated`, caducado.
- Usuario desactivado y membresia desactivada con token vigente.

Problemas del entorno de test:

- `CLAUDE.md` indica `cd backend && pytest tests/`, que **no ejecuta** los ocho ficheros de la raiz (`test_governance.py`, `test_modules.py`, etc.). Hay que ejecutar `pytest` sin argumentos o listarlos.
- Los tests de la raiz son `unittest.TestCase` contra la BD real salvo `test_governance.py`, que fuerza SQLite al importarse y probablemente no surte efecto en una ejecucion completa (P).
- `test_governance.py` hace `commit` sin rollback; `test_rates.py` no es un test.

## 12. Anexos

Fragmentos originales, con evidencia por fila, en `docs/empresa/anexos/`:


| Fichero                 | Contenido                                                       |
| ----------------------- | --------------------------------------------------------------- |
| `01-modelo.md`          | Columnas, indices, FK, uso real                                 |
| `02-schemas.md`         | Schemas Pydantic y validaciones                                 |
| `03-router-crud.md`     | `GET/POST/PUT /companies`, `/detailed`                          |
| `04-router-miembros.md` | Miembros: alta, orden, estado                                   |
| `05-router-tarifas.md`  | Tarifas, edicion de miembro, dashboard                          |
| `06-auth-roles.md`      | Roles, scope, helpers de permisos, bypass dev                   |
| `07-worklogs.md`        | Matriz de turnos                                                |
| `08-crud.md`            | Aislamiento en `crud.py`, funciones muertas                     |
| `09-is-active.md`       | Comportamiento con empresa suspendida                           |
| `10-modulos.md`         | Modulos y suscripciones                                         |
| `11-usuarios.md`        | Usuarios, `default_company_id`, switch-scope                    |
| `12-dominio.md`         | Capa `backend/src/`                                             |
| `13-jsonb.md`           | `tax_config`, `worklog_definitions`, `settings`, `rates_config` |
| `14-front-admin.md`     | Pantalla de administracion                                      |
| `15-front-contexto.md`  | Empresa activa en el cliente                                    |
| `16-tests.md`           | Inventario y huecos de pruebas                                  |
| `17-ciclo-vida.md`      | FK, huerfanos, baja, auditoria                                  |
| `18-seeds-billing.md`   | Seeds, `get_billing_summary`, arranque                          |


Los anexos son salida directa de los agentes. Cuando un anexo y este documento difieran, prevalece este documento, que contiene las correcciones tras verificar los hallazgos graves (H1, H2, H3, H4, H5).

## 13. Proximos pasos sugeridos

1. Decidir D1 a D7, que condicionan la correccion de H1 a H6.
2. Escribir tests que reproduzcan H1, H2, H3 y H5 antes de corregirlos.
3. Corregir H1 (validar `company_role` contra la membresia y rechazar valores distintos de `manager`/`worker`) como primer cambio, por ser una escalada de privilegios.
4. Una vez decidido, volcar las reglas aceptadas a `CLAUDE.md` o a un documento de gobernanza, y aplicar el versionado SemVer cuando haya cambios de codigo.