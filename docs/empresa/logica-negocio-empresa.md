# Logica de negocio de Empresa (comportamiento objetivo)

Fecha: 2026-10-16. Rama: `docs/analisis-entidad-empresa`.

## 0. Como leer este documento

Fuentes: `analisis-entidad-empresa.md` (como funciona hoy el codigo, 2026-10-15) y `respuestas-a-comentarios.md` (decisiones y notas del usuario, incluidas las respuestas escritas dentro de ese documento).

Este documento describe como **debe** comportarse el sistema, no como se comporta hoy. Reune en un solo sitio las reglas que estaban repartidas en las dos fuentes. Donde difiere de ellas, manda este. Las fuentes no se han modificado.

Lo que hay que cambiar en el codigo para llegar a este comportamiento esta en `cambios-empresa.md`. Las decisiones sin cerrar estan al final (seccion 11).

Estado de cada regla, entre corchetes:

- **[Cerrado]**: decidido por el usuario.
- **[Confirmar]**: propuesto o derivado de una decision, sin objecion explicita. Valido como punto de partida.
- **[Abierto]**: sin decidir.

No se ha ejecutado ningun test ni se ha leido de nuevo el codigo para este documento: los hechos sobre el estado actual son los del analisis original, que es lectura estatica.

**Convencion de nombres.** Los campos se nombran siempre en `snake_case` (`is_managed`, `is_active`, `company_id`). La API actual serializa en `camelCase` (`alias_generator=to_camel` en `backend/schemas.py`), por eso el frontend ve `isManaged` e `isActive`. La API v2 usara `snake_case` tambien en el JSON (ver X7 en `cambios-empresa.md`). Excepcion: los literales exactos de codigo o URL, como `?companyId=`.

## 1. Principios


| ID  | Principio                                                                                                                                                                                                                                                 | Estado                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| P1  | **El backend decide.** Toda regla de negocio (permisos, validaciones, calculos) vive en el backend, en el dominio. El frontend solo la refleja: oculta lo prohibido y avisa antes de enviar. Un 403 por una accion que la UI ofrecia debe ser excepcional | Cerrado                                |
| P2  | **Un unico punto de politica de permisos.** Ningun handler repite `if not is_platform_admin and ...`. El bypass del PA vive en un solo sitio                                                                                                              | Cerrado (direccion); Confirmar (forma) |
| P3  | **No se borra lo que tiene datos.** La baja es `is_active = false`. El borrado fisico solo existe para lo que no tiene nada asociado                                                                                                                      | Cerrado                                |
| P4  | **Aislamiento por empresa en dos barreras:** filtro por `company_id` en el codigo y, si se decide, Row Level Security en PostgreSQL                                                                                                                       | Cerrado (filtro); Abierto (RLS)        |
| P5  | **Orden de trabajo:** backend definido y probado primero, frontend despues                                                                                                                                                                                | Cerrado                                |
| P6  | Un cambio de datos relevante deja rastro en `audit_logs`, consultable por el PA desde la aplicacion                                                                                                                                                       | Cerrado                                |


## 2. Conceptos y roles

### 2.1 Modelo

- **Empresa = tenant.** Unidad de aislamiento de datos.
- **Usuario = identidad global.** Puede pertenecer a varias empresas. Su perfil, 2FA y sesiones son globales.
- **Membresia** (`company_members`, clave `(user_id, company_id)`): relacion de un usuario con una empresa. Lleva el rol en esa empresa, el estado y las tarifas. Es el eje del modelo.
- **Turno** (`work_logs`): el hecho central del que salen importes, billing e informes. Pertenece al par (usuario, empresa).
- **Worker** no es una entidad: es un rol dentro de una membresia.

### 2.2 Roles


| Rol                 | Donde vive                       | Alcance                                                                                                                                                                                                                |
| ------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Platform admin (PA) | `users.role = admin`             | Toda la plataforma. Accede a cualquier empresa **por privilegio**, sin membresia. Es el unico que gestiona empresas, membresias, roles, estados, modulos y usuarios                                                    |
| Manager             | `company_members.role = manager` | Operativa de su empresa: turnos, tarifas, vision de equipo. No administra la empresa ni su equipo                                                                                                                      |
| Worker              | `company_members.role = worker`  | Sus propios turnos y su perfil dentro de la empresa                                                                                                                                                                    |
| Admin de empresa    | `company_members.role = admin`   | **Reservado.** Hoy no tiene efecto ni hay ninguno. En el futuro creara tipos de turno y anadira usuarios. No se asigna ni se emite en tokens. Donde las decisiones dicen "admin de empresa o PA", hoy solo opera el PA |


Los roles de empresa los cambia solo el PA. Un usuario no puede cambiar su propio rol de plataforma (`UserSelfUpdate` no tiene `role`). [Cerrado]

### 2.3 Usuario, membresia y estados


| Concepto  | Estado                    | Efecto                                          |
| --------- | ------------------------- | ----------------------------------------------- |
| Usuario   | `User.is_active`          | Si es false, no se autentica en la plataforma   |
| Membresia | `CompanyMember.is_active` | Si es false, no accede a esa empresa            |
| Empresa   | `Company.is_active`       | Si es false, nadie accede salvo el PA (ver 4.5) |


## 3. Acceso y sesion

### 3.1 Token

- Access token de 30 min (se mantiene). Firmado RS256; no se puede manipular, el riesgo es emitir claims incorrectos. [Cerrado]
- Claims: `sub`, `cid` (empresa activa), `scope`, `exp`. El token **no lleva** `role` ni `is_admin`: rol de empresa y rol de plataforma se leen de BD (con cache) en cada peticion, y el frontend los obtiene de `/users/me`. [Cerrado]
- `scope`: `full`, `2fa_pending` (solo sirve para verificar el 2FA) e `impersonated` (10 min, solo PA, sus escrituras de turnos se auditan).
- **Modo "ver como" del PA** (plan, P-3 y Q-5): el PA puede ver una empresa con la interfaz y los permisos de `worker` o de `manager`, sin suplantar a ningun usuario y en **solo lectura** (las escrituras responden 403). Los datos "propios" que muestra son los del propio PA, normalmente vacios. El manager **pierde** "entrar como worker": su rol ya incluye al de worker. [Cerrado]
- El `scope` no es un plan ni un permiso de empresa. La cuenta gratuita se modela con `module_subscriptions` (`trial`, `expires_at`) y una empresa personal, nunca con el token.

### 3.2 Comprobaciones en cada peticion

Orden unico, aplicado por la politica central (P2). Un fallo corta la peticion.


| #   | Comprobacion                                                                                                             | Excepcion | Estado    |
| --- | ------------------------------------------------------------------------------------------------------------------------ | --------- | --------- |
| 1   | Token valido, firmado y no caducado                                                                                      |           | Cerrado   |
| 2   | El usuario existe y `User.is_active`                                                                                     |           | Cerrado   |
| 3   | Scope `full` o `impersonated`. `2fa_pending` solo accede a la verificacion del 2FA, en todos los endpoints sin excepcion |           | Cerrado   |
| 4   | La empresa activa (`cid`) tiene `is_active = true`                                                                       | PA        | Cerrado   |
| 5   | El usuario tiene membresia activa en esa empresa                                                                         | PA        | Cerrado   |
| 6   | El rol se lee de la membresia (BD, cache Redis \~60 s); el token no lleva rol                                              | PA        | Cerrado   |
| 7   | El rol cumple lo que exige el endpoint                                                                                   | PA        | Cerrado   |
| 8   | Si el endpoint es de pago, la empresa tiene el modulo (`require_module`)                                                 | PA        | Cerrado   |


Notas:

- La comprobacion 2 no anade coste: el usuario ya se carga de BD en cada peticion. Las comprobaciones 4, 5 y 6 salen de Redis con TTL de ~60 s, con coste de sub-milisegundo.
- **La cache nunca decide sola.** Si Redis falla o no tiene el dato, se lee de BD y la peticion sigue. Al cambiar rol, estado de membresia o `is_active` de empresa se invalida la clave, de modo que el efecto es inmediato y no espera al TTL. [Cerrado]
- La comprobacion 6 es necesaria para que un cambio de rol o una baja de membresia surtan efecto sin esperar 30 min.
- `is_admin` y `role` salen del token (ver 3.1): `users.role` y el rol de la membresia se leen de BD. El frontend los obtiene de `/users/me`. [Cerrado, opcion A]

### 3.3 Empresa activa

- La empresa activa sale del claim `cid`. El cambio se hace con `POST /auth/switch-scope`.
- `switch-scope` valida la membresia activa y la empresa activa. El rol del nuevo token sale de la membresia, **nunca del cliente**. Solo existen `manager` y `worker` como valores emitidos.
- Un manager de A con token en B no gestiona A hasta cambiar de empresa. [Cerrado]
- Si el usuario no tiene membresia activa en la empresa pedida ni en su `default_company_id`, se usa la primera membresia activa de una empresa activa. Si no tiene ninguna, el token **no lleva `cid`**. [Cerrado]
- El PA sin empresa elegida tiene token con `cid` nulo y opera por privilegio.
- El PA **si** puede entrar en una empresa suspendida (`switch-scope` le emite su `cid`); worker y manager no (P-4). [Cerrado]
- La empresa activa sale solo del token. Se elimina `?companyId=` de la URL del frontend: una empresa activa por sesion, sin empresa en la URL. Cambiar de empresa en una pestana la cambia en todas. [Cerrado, O2]

### 3.4 Otras reglas de acceso


| Regla                                                                                                                                  | Estado    |
| -------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| No existe registro publico. Las cuentas las crea el PA y luego las anade a la empresa                                                  | Cerrado   |
| Un usuario con `User.is_active = false` no se autentica, sea PA o no                                                                  | Cerrado   |
| Un usuario sin ninguna empresa puede iniciar sesion y ve "no estas vinculado a ninguna empresa"                                        | Cerrado   |
| Impersonacion: solo PA, 10 min, escrituras de turnos auditadas                                                                         | Cerrado   |
| El seed inicial solo actua al crear la BD y solo si no hay usuarios (o al menos ningun PA). No se ejecuta en cada arranque             | Cerrado   |
| El bypass de desarrollo del login nunca debe poder activarse en produccion (fuera del alcance de empresa, impacto critico). Solo funciona con `ENVIRONMENT=development` y `DEV_LOGIN_BYPASS`; si no, el arranque se aborta (P-9) | Cerrado   |


- Un PA no puede desactivarse ni degradarse a si mismo, ni dejar la plataforma sin ningun PA activo. [Cerrado]

## 4. Empresa

### 4.1 Atributos


| Atributo              | Regla                                                                                                                       | Estado    |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------- | --------- |
| `name`                | Obligatorio, sin espacios sobrantes, longitud 1 a 120 caracteres. No es unico. Rechazar `null` y cadena vacia       | Cerrado   |
| `fiscal_id`           | **Obsoleto.** Sin UNIQUE. Se quita de formularios y respuestas. La columna queda nullable y se borra mas adelante (PR-23), con export previo a backup si hay valores reales | Cerrado   |
| `tax_config`          | Contrato tipado (ver 4.4). Sin default                                                                                      | Cerrado   |
| `worklog_definitions` | Tipos de turno de la empresa. Contrato tipado (unidad `hours` o `days`, ver 4.4)                                          | Cerrado   |
| `settings`            | Catalogo definido en backend (ver 4.4)                                                                                      | Cerrado   |
| `is_active`           | Acceso a la empresa. Solo PA. Es la baja                                                                                    | Cerrado   |
| `is_managed`          | Modo gestionado. Solo PA                                                                                                    | Cerrado   |
| `updated_at`          | Lo pone el ORM. El trigger de PostgreSQL queda fuera del plan (P-16)                        | Cerrado |


### 4.2 Quien hace que con los datos de la empresa


| Accion                                                         | PA                                  | Manager           | Worker |
| -------------------------------------------------------------- | ----------------------------------- | ----------------- | ------ |
| Crear empresa                                                  | SI                                  | NO                | NO     |
| Editar `name`, `tax_config`, `worklog_definitions`, `settings` | SI                                  | NO                | NO     |
| Cambiar `is_active` o `is_managed`                             | SI                                  | NO                | NO     |
| Borrar empresa                                                 | SI (solo si no tiene nada asociado) | NO                | NO     |
| Listar todas las empresas (`GET /companies`)                   | SI                                  | NO                | NO     |
| Listar las suyas (`GET /users/me/companies`)                   | SI                                  | SI                | SI     |
| Ver la empresa completa                                        | SI                                  | NO                | NO     |
| Ver la empresa en version reducida                             | SI                                  | SI                | SI     |


Un manager no edita nada de la empresa. [Cerrado]

### 4.3 Ciclo de vida


| Evento                 | Regla                                                                                                                                                                                                             | Estado  |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| Alta                   | Solo PA. El PA **no** se anade como miembro: accede por ser PA. El alta exige `tax_config` informado (`{}` es valido). Excepcion: el seed (y `dev_seed`) mantiene al PA como `manager` de su empresa inicial (P-7) | Cerrado |
| Edicion                | Solo PA. `PUT /companies/{id}` sin cambios (incluido `{}`) responde 422 (P-6)                                                                                                                                     | Cerrado |
| Suspension             | `is_active = false`. Solo PA. Se registra quien, cuando y motivo en `audit_logs`. No hay `archived_at` ni `archived_by`                                                                                           | Cerrado |
| Reactivacion           | `is_active = true`. Solo PA. Se registra igual. La UI pide confirmacion                                                                                                                                           | Cerrado |
| Baja                   | Es la suspension. No se borra nada                                                                                                                                                                                | Cerrado |
| Borrado                | Solo PA y solo si la empresa **no tiene nada asociado** (miembros, turnos, suscripciones, usuarios con `default_company_id`). Sin cascadas. Si hay algo asociado, responde 409 indicando que lo impide. Se audita | Cerrado |
| Empresa sin manager    | No es un problema: el PA anade un manager o cambia el rol de un worker. No hace falta guardia de ultimo manager; la consulta de datos E7 es solo informativa                                                                                                     | Cerrado |
| Cambio de `is_managed` | Solo PA, auditado, sin recalcular importes existentes (ver 4.5)                                                                                                                                                   | Cerrado |


### 4.4 Contratos de los campos JSON

Los JSONB con estructura fija llevan un modelo Pydantic en el backend con tipos, rangos y `extra="forbid"`. Se valida al escribir y se aplican defaults al leer. El frontend solo consume.

**`tax_config`:** [Cerrado]

- Es un diccionario de **claves libres**: `dict[str, float]`. Cada empresa nombra sus impuestos como quiera ("seguridad social", "SS", "IRPF"...).
- Reglas (P-12): nombre de impuesto de 1 a 50 caracteres, valor numerico entre 0 y 1 como fraccion, maximo 20 impuestos. Sin claves obligatorias. `tax_config: {}` es valido (P-11).
- **Quien decide si se descuentan.** `is_gross` por tarifa (default `False`): con `is_gross=True` el calculo descuenta los impuestos de `tax_config` al calcular el `calculation_snapshot`; con `False` no descuenta nada. Se mantiene el bruto informativo de las tarifas con `is_gross=False` (plan, Q-4). `settings.business_logic.price_type` (default `net`) solo afecta a la vista del dashboard, nunca al calculo (P-10).
- El calculo resta del bruto **todas** las entradas; la etiqueta de la linea del desglose es el nombre. Hoy el codigo lee tres claves fijas (`crud.py:149-210`) y hay que cambiarlo.
- **0 es valido**: resta 0 y no es un error. Un valor de tipo incorrecto se rechaza al escribir (hoy se convierte en 0 sin avisar).
- Sin default de modelo (0.0648), de schema (0.0) ni de UI (0.0). El alta de empresa exige que `tax_config` venga informado.
- El override del miembro (`tax_overrides`) usa la **misma clave** que la empresa. Precedencia: si el miembro tiene valor para esa clave, manda; si no, el de la empresa. Desaparece la discrepancia `irpf_base` frente a `irpf` (O9) y tambien `deduction_irpf`/`deduction_ss` de `schemas.py:140`.
- Coste asumido: no hay informes por concepto fijo.

**`settings`:**

- Un modelo `CompanySettings` en el backend con todos los ajustes, defaults y tipos. Hoy los defaults viven en el frontend (`use-company-settings.ts`); pasan al backend. [Cerrado]
- El catalogo es una **estructura en el codigo del backend**, no una tabla de BD. Una tabla solo compensaria para cambiar definiciones sin desplegar o ligarlas a planes, y hoy es sobreingenieria. [Cerrado]

- Claves vigentes: `business_logic.*` (tipo de precio y recargo), `worker_experience.*` (importes a mano, modo de entrada), `ui_customization.labels`, `allowed_rates`, modulos. Cada opcion debe quedar documentada (para que sirve, tipo, default) al implementar `CompanySettings`.

- Las claves desconocidas que existan hoy en la BD solo se eliminan con `--drop-unknown` explicito y copia previa (Q-7); sin ello la migracion aborta.
- Se eliminan `allow_tutorial`, `allow_coordination` (restos de una version antigua) y `settings.is_managed` (legacy; la regla real es la columna). [Cerrado]
- Solo el PA los edita y los lee completos. Manager y worker reciben la **vista reducida** (ver 9) con la parte de interfaz que necesitan para pintar: modo de entrada, etiquetas, modulos. [Cerrado]

 

**`worklog_definitions` y `rates_config`:** claves dinamicas (tipos de turno y tarifas por tipo); JSONB es correcto. Cada valor lleva modelo de validacion. [Cerrado]

- Contrato de cada tipo de turno: `unit` (`hours` o `days`), `label` (texto visible, 1 a 60 caracteres) y `fields` (lo usan el seed y el frontend).
- `unit` define como se mide el turno y por tanto como se calcula el importe: horas o dias.
- `is_range` se elimina. Es un respaldo heredado: si falta `unit`, `is_range=true` equivale a `days` (`crud.py:105-107`, `create_work_log_use_case.py:63-65`). Se migra a `unit` explicito y se rechaza un tipo sin `unit`.
- "Turno fijo" no existe como unidad hoy. Si se quiere, es una unidad nueva y una decision aparte.

**`CompanyMember.settings`:** ajustes por usuario dentro de la empresa, mezclados sobre los de la empresa al devolverla. Hoy casi no se usan. Falta analizar si aportan algo. Abierto O10.

### 4.5 Empresa gestionada (`is_managed`) y empresa suspendida

**Modo gestionado.** En una empresa gestionada solo escriben el manager y el PA. El worker es de solo lectura.


| Accion                                           | Autonoma            | Gestionada                                                          |
| ------------------------------------------------ | ------------------- | ------------------------------------------------------------------- |
| Worker crea turno propio                         | SI                  | **NO**                                                              |
| Worker edita o borra turno propio                | SI (solo los suyos) | NO                                                                  |
| Worker edita sus tarifas                         | SI                  | NO                                                                  |
| Worker edita sus `settings` de miembro           | SI                  | SI                                                                  |
| Manager crea, edita y borra turnos de la empresa | SI                  | SI                                                                  |
| Manager edita tarifas propias y ajenas           | SI                  | **SI** (propias tambien, para no depender de que haya dos managers) |


Efecto de cambiar `is_managed`: inmediato para peticiones nuevas; un frontend abierto sigue mostrando el modo anterior hasta recargar. De gestionada a autonoma, los workers recuperan edicion y borrado de **todos** sus turnos, incluidos los creados por un manager. De autonoma a gestionada lo pierden. No se recalcula nada. Por eso el cambio se audita y solo lo hace el PA. [Cerrado]

**Empresa suspendida** (`is_active = false`). Bloqueo total para todo usuario `user` (worker o manager), solo accede el PA.


| Accion                                                                            | Resultado                                                                               |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Cualquier endpoint de la empresa (empresa, miembros, tarifas, dashboard, gestion) | BLOQUEA (403, salvo PA)                                                                 |
| Crear, editar, borrar turnos                                                      | BLOQUEA                                                                                 |
| Listar turnos                                                                     | BLOQUEA                                                                                 |
| Billing                                                                           | BLOQUEA                                                                                 |
| `GET /modules/me` y `require_module`                                              | Los modulos que vienen de la empresa dejan de valer; los personales no dependen de ella |
| Emision de token, refresh y `switch-scope`                                        | No se emite `cid` de una empresa suspendida a worker ni manager; al PA si (P-4)         |
| Listados de empresas (`/users/me/companies`)                                      | La oculta (salvo PA)                                                                    |
| Frontend                                                                          | Mensaje especifico; el selector no la ofrece; un 403 no se muestra como lista vacia     |


Un modulo que la empresa paga (o pagaba) no se puede usar si la empresa no esta activa. [Cerrado]

## 5. Membresia


| Accion                                                                                 | PA  | Manager | Worker                            |
| -------------------------------------------------------------------------------------- | --- | ------- | --------------------------------- |
| Anadir un usuario existente a la empresa (`members/add`, por email, entra como worker) | SI  | NO      | NO                                |
| Activar o desactivar una membresia                                                     | SI  | NO      | NO                                |
| Cambiar el rol                                                                         | SI  | NO      | NO                                |
| Resetear contrasena de un usuario (`reset-password-email`)                             | SI  | NO      | NO                                |
| Reordenar miembros (`sort_order`, solo presentacion)                                   | SI  | SI      | NO                                |
| Ver la lista de miembros                                                               | SI  | SI      | NO                                |
| Editar tarifas de un miembro                                                           | SI  | SI      | solo las suyas y solo en autonoma |





| Regla                                                                                                                                                                               | Estado             |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| El rol no viaja en los payloads de tarifas ni de ajustes: es un endpoint propio (solo PA). Se identifica al usuario por su id y el backend consulta su rol                          | Cerrado            |
| Desactivar una membresia: se reasigna `default_company_id` a otra membresia activa o a nulo; los turnos se conservan; el acceso a la empresa se corta de inmediato (comprobacion 5) | Cerrado            |
| Eliminar un miembro de una empresa: solo si no tiene turnos ni nada asociado, sin cascadas. Si los tiene, queda inactivo                                                            | Cerrado            |
| `default_company_id` se valida contra membresia activa al escribirlo                                                                                                                | Cerrado            |
| Un usuario sin empresa es valido (ver 3.4)                                                                                                                                          | Cerrado            |
| Una membresia desactivada no se usa para calcular nada; crear turnos exige membresia activa                                                                                         | Cerrado            |
| Invitaciones por email a usuarios sin cuenta: aplazado hasta que las empresas gestionen sus usuarios. Hoy: PA crea el usuario y luego lo anade                                      | Cerrado (aplazado) |
| Reactivar una membresia: solo PA. Al reactivar vuelve siempre como `worker`; el PA lo asciende despues si hace falta (O8)                     | Abierto            |
| La "empresa personal" actual (`crud.create_user` busca una empresa llamada "Personal") es fragil. Cuando exista el plan gratuito se modela con un campo propio                      | Cerrado (aplazado) |


## 6. Turnos

### 6.1 Quien hace que


| Accion                       | Worker autonoma | Worker gestionada | Manager                 | PA            |
| ---------------------------- | --------------- | ----------------- | ----------------------- | ------------- |
| Crear turno propio           | SI              | **NO**            | SI                      | SI            |
| Crear turno de otro          | NO              | NO                | SI                      | SI            |
| Crear en lote (`/bulk`)      | NO              | NO                | SI                      | SI            |
| Editar o borrar turno propio | SI              | NO                | SI                      | SI            |
| Editar o borrar turno ajeno  | NO              | NO                | SI (de su empresa)      | SI            |
| Editar con `apply_to_group`  | NO              | NO                | SI                      | SI            |
| Listar                       | propios         | propios           | todos los de la empresa | segun filtros |
| Billing                      | NO              | NO                | SI                      | SI            |


Todo bloqueado si la empresa esta suspendida, salvo PA.

### 6.2 Reglas


| Regla                                                                                                                                                                                                                                          | Estado                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| Crear un turno exige que el usuario del turno tenga **membresia activa** en la empresa. Aplica a turno propio, de otro y en lote                                                                                                               | Cerrado                              |
| Editar no puede cambiar `company_id` ni `user_id` del turno                                                                                                                                                                                    | Cerrado                              |
| `apply_to_group` actua solo sobre turnos de la misma empresa. El `group_id` lo genera el servidor, no el cliente. Se crea un `group_id` cuando se marcan varios usuarios al crear el turno                                           | Confirmar                            |
| Todo turno tiene `company_id` (NOT NULL). Los turnos sin empresa existentes se asignan con un script de reparacion previo: la empresa de su unica membresia; si hay varias, el `default_company_id` del usuario si es miembro activo; si no, lista manual. La migracion aborta si quedan turnos sin empresa (plan, PR-09 y secciones 9 y 10) | Cerrado (direccion)                  |
| **Recalculo al editar:** si no cambian tipo, horas ni fechas, se conserva el importe. Si cambian, se recalcula con las tarifas del `calculation_snapshot` del propio turno. Recalcular con la tarifa vigente solo ocurre como accion explicita | Cerrado                              |
| **Limites de listado** (P-12, Q-3): `limit` con tope de 2000, solo para listados paginados de filas. Toda suma o metrica la calcula el backend sobre el rango completo en endpoints de agregados (`GET /work-logs/summary`, dashboard-summary), nunca sumando filas en el frontend. Los listados devuelven el total en la cabecera `X-Total-Count` | Cerrado |
| Sin tarifa y sin importe manual: 400 con mensaje claro, que el frontend muestra                                                                                                                                                                | Cerrado                              |
| Fechas: `inicio <= fin` y rango razonable que evite errores de tecleo (ano 2062). Rango admitido: de 2000-01-01 a hoy + 730 dias (P-12); el manager planifica                                                                                                          | Cerrado                              |
| Validacion de fechas: primero en el backend (dominio); el frontend la replica para avisar antes de enviar                                                                                                                                      | Cerrado                              |
| Solapes de dos turnos del mismo trabajador: permitidos con aviso. El backend crea el turno (201) y devuelve un campo `warnings` en la respuesta; el frontend lo muestra en un toast (O3)                                                                      | Abierto O3                           |
| Identificadores invalidos (UUID mal formado) y `status` libres: 422, nunca 500                                                                                                                                                                 | Confirmar                            |
| Cierre de periodo y aprobacion de turnos                                                                                                                                                                                                       | Aplazado a un modulo futuro (ver 10) |


## 7. Tarifas e impuestos


| Regla                                                                                                                                           | Estado  |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| Las tarifas viven en `company_members.rates_config`, por miembro y empresa                                                                      | Cerrado |
| Las edita el manager (propias y ajenas, en ambos modos) y el PA. El worker solo las suyas y solo en empresa autonoma                            | Cerrado |
| Las ve el propio miembro (perfil) y los managers                                                                                                | Cerrado |
| No hay tabla de historial de tarifas: el cambio queda en `audit_logs` con valor anterior y nuevo, y cada turno guarda su `calculation_snapshot` | Cerrado |
| Impuestos: ver 4.4                                                                                                                              | Cerrado |


## 8. Modulos y billing


| Regla                                                                                                                                                                                                     | Estado                                                   |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Solo el PA activa, cambia o cancela modulos de una empresa                                                                                                                                                | Cerrado                                                  |
| Una suscripcion activa o en `trial` duplicada de la misma empresa y modulo responde 409 (P-15)                                                                                                            | Cerrado                                                  |
| `require_module(code)` protege los endpoints de pago. Devuelve 403 si la empresa o el usuario no tiene el modulo; el PA pasa                                                                              | Cerrado                                                  |
| Los modulos de pago son al menos: parte diario, billing avanzado e informes                                                                                                                               | Cerrado                                                  |
| `GET /modules/me` une los modulos personales y los de la empresa activa, y descarta los de empresa si esta suspendida                                                                                     | Cerrado                                                  |
| **Billing en dos niveles.** Basico: suma de lo trabajado y lo generado, incluido sin modulo. Avanzado: porcentajes, tendencias y analitica, solo con el modulo                                            | Cerrado (direccion); contenido del avanzado: Abierto O11 |
| Parte diario: endpoint propio que devuelve solo lo que necesita (miembros y turnos del dia), de modo que el frontend solo consulta ese endpoint. Sustituye el acceso de un worker a `/companies/detailed` | Cerrado                                                  |
| Billing lo ven manager y PA, no el worker                                                                                                                                                                 | Cerrado                                                  |


## 9. Que ve cada rol


| Dato                                                                                                                                           | PA                      | Manager                      | Worker                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ---------------------------- | ------------------------------------------------- |
| Vista completa de la empresa (`tax_config`, `worklog_definitions`, `settings`, `is_active`)                                                    | SI                      | NO                           | NO                                                |
| Vista reducida: `id`, `name`, `is_managed`, los ajustes de interfaz que el frontend del worker necesita (modo de entrada, etiquetas, modulos) y `worklog_definitions` y `tax_config` en solo lectura (P-2) | SI                      | SI                           | SI                                                |
| `fiscal_id`                                                                                                                                    | no existe en respuestas | no existe                    | no existe                                         |
| `is_active` de la empresa                                                                                                                      | SI                      | SI                           | NO (si esta inactiva, el worker no llega a verla) |
| Tarifas de todos los miembros                                                                                                                  | SI                      | SI                           | NO                                                |
| Empresas de otro usuario (`GET /users/{id}/companies`)                                                                                         | todas                   | solo las que comparte con el | NO                                                |


- La decision D5 dice que al worker le basta el `name`. Pero el frontend del worker necesita `is_managed` (para ocultar acciones) y parte de `settings`. Se resuelve dando al frontend lo que necesita: la vista reducida lleva `id`, `name`, `is_managed`, los ajustes de interfaz y, en solo lectura, `worklog_definitions` y `tax_config` (P-2). La reciben worker y manager; la completa solo el PA. Se implementa en v1 con despliegue coordinado backend+frontend (P-1). [Cerrado, O5]
- **Anti-enumeracion** (P-5): para quien no es PA, una empresa inexistente, ajena o sin membresia responde el mismo 403; el 404 solo lo ve el PA. [Cerrado]
- **Parte diario** (P-14): dos esquemas de respuesta. El del worker no incluye campos de importe (ausentes, no `null`); el de manager y PA si los incluye. [Cerrado]

**Como pinta el frontend.** Al iniciar sesion y al cambiar de empresa consulta `/users/me/companies`: por empresa devuelve la vista reducida y el rol del usuario en ella. Con rol e `is_managed` decide que mostrar (p. ej. worker en empresa gestionada: sin crear ni editar turnos). El backend vuelve a comprobar todo y responde 403 si el frontend se equivoca (P1).

- Los 403 no devuelven datos internos (`is_manager`, ids de usuario). [Cerrado]
- El frontend muestra al usuario el `detail` que envia el backend. Cuando una peticion falla, FastAPI responde `{"detail": "texto"}`; un interceptor unico en `api.ts` (U1) lo muestra en un toast en lugar de un mensaje fijo por pantalla. Por eso el `detail` debe ser claro y no filtrar datos internos. [Cerrado]

## 10. Auditoria

Se registra en `audit_logs` (quien, cuando, que, empresa, valor anterior y nuevo, motivo cuando exista, con un maximo de 500 caracteres). **Cuantos mas eventos, mejor.** [Cerrado]


| Evento                                           | Estado                                                                                    |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Alta de empresa                                  | Cerrado                                                                                   |
| Suspension y reactivacion de empresa (con actor) | Cerrado                                                                                   |
| Cambio de `is_managed`                           | Cerrado                                                                                   |
| Alta, baja y reactivacion de membresia           | Cerrado                                                                                   |
| Cambio de rol                                    | Cerrado                                                                                   |
| Cambio de tarifa (valor anterior y nuevo)        | Cerrado                                                                                   |
| Cambios de `tax_config` y `settings`             | Cerrado                                                                                   |
| Borrado de empresa y borrado de membresia        | Cerrado (coherente con las reglas de borrado)                                              |
| Impersonacion y reset de 2FA                     | Ya existe                                                                                 |


El PA debe poder ver los logs desde la aplicacion sin entrar a la BD: endpoint de lectura solo para PA con filtros (empresa, usuario, tipo, fechas) y pantalla de administracion. Es trabajo propio, posterior a la ampliacion de eventos. [Cerrado]

## 11. Aplazado, descartado y abierto

### 11.1 Aplazado o descartado


| Tema                                | Decision                                                                                                                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cierre de periodo                   | Descartado por ahora. Seria bloquear los turnos de un periodo (un mes) ya facturado o pagado, para que no cambien un total emitido. Sin nomina ni facturacion que dependa de ellos no aporta |
| Aprobacion de turnos                | Aplazado a un modulo propio. Tambien seria la alternativa si algun dia el worker registrara turnos en una empresa gestionada                                                                 |
| Invitaciones por email              | Aplazado hasta que las empresas gestionen sus usuarios                                                                                                                                       |
| `timezone` y `currency` por empresa | Innecesario ahora; apuntado                                                                                                                                                                  |
| `slug`, contacto, `plan`            | Retirados de las carencias. `plan` ya se resuelve con modulos                                                                                                                                |
| `owner_id`                          | Retirado de momento. Si se retoma, hay que decidir a que se vincula: a un usuario de la plataforma o a la empresa. No esta decidido                                                          |
| Guardia de ultimo admin             | Retirada: solo el PA gestiona membresias                                                                                                                                                     |
| `archived_at` y `archived_by`       | Retirados: la baja se registra en `audit_logs`                                                                                                                                               |
| UNIQUE en `name` y en `fiscal_id`   | Descartado                                                                                                                                                                                   |
| Plan o limites por empresa (D16)    | Sin decision, no urgente                                                                                                                                                                     |
| Rol admin de empresa                | Reservado para el futuro                                                                                                                                                                     |


**Migraciones con riesgo de datos** (plan, secciones 9 y 10). Antes de cada migracion de este alcance hay un script de reparacion idempotente con `--dry-run` por defecto y `--apply`; la migracion sigue abortando si quedan datos sin arreglar. El despliegue exige backup previo y rollback definido. Los backups y las listas de decision manual son JSON en `${BACKUP_DIR}/repairs/`, fuera del repo y con permisos 0600 (Q-6). Las claves desconocidas de `settings` solo se eliminan con `--drop-unknown` y copia previa (Q-7). Comportamiento de Komodo ante un fallo de `migrate`: no verificado (Q-9).

### 11.2 Decisiones abiertas


| ID  | Tema                                     | Detalle                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| --- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| O1  | RLS de PostgreSQL por `company_id` (D13) | Segunda barrera de aislamiento, con el PA exento. Recomendado despues de centralizar permisos y con `company_id` NOT NULL, empezando por `work_logs` y `company_members`. Pide `SET LOCAL app.company_id` en cada transaccion, y afecta a funciones SQL y migraciones                                                                                                                                                                                                                                                                                                                                                                                                                           |
| O2  | [CERRADO: se quita de la URL] Empresa en la URL (`?companyId=`) | El frontend la prioriza sobre el token (`layout.tsx:81`). El token va en cookie `HttpOnly` compartida entre pestanas, asi que dos pestanas con empresas distintas envian el mismo `cid`: la UI muestra una empresa y el backend opera sobre otra. Opciones: (a) una sola empresa activa por sesion e ignorar el parametro, o sincronizar con `switch-scope` si difiere; (b) empresa explicita en cada peticion (cabecera o ruta) validada contra la membresia en el servidor, lo que permite varias pestanas y encaja con las comprobaciones por peticion. En ambos casos el backend nunca debe fiarse de lo que muestre la URL - Yo creo que podriamos eliminar lo de companyid en la url no?? |
| O3  | [CERRADO: permitido con aviso] Solapes de turnos | Si dos turnos del mismo trabajador pueden solaparse - Si que pueden, con un warning                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| O4  | [CERRADO: v2 solo del area empresa; Python se mantiene; `crud.py` no se divide] D20, capa `backend/src/` | Completar `backend/src/` como API v2 SOLO del area empresa, con prefijo `/api/v2/` junto a `/api/`, serializada en `snake_case` (X7). v1 se mantiene y sus endpoints de empresa se retiran solo cuando el frontend use v2 en todos; el frontend migra endpoint a endpoint. Los renombrados que rompen contrato (X3) se hacen en v2 y hay pruebas de paridad v1/v2 (Q3). Python se mantiene (X5 cerrada) y `crud.py` no se divide (X4 cerrada), porque v2 lo sustituye. Quedan bloqueados solo F6 y B1 (ver `cambios-empresa.md`, seccion 14)                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| O5  | [CERRADO: se le da lo que necesita] Vista reducida del worker (D5) | Contradiccion entre "basta el `name`" y lo que necesita su frontend - si el front lo necesita, pues se le da                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| O6  | [CERRADO: los totales incluyen a inactivos y el desglose tambien, marcados] Totales del dashboard | Incluyen turnos de miembros inactivos; el desglose por trabajador solo los activos. Decidir cual es el correcto - no deberia de verse turnos de gente inactiva no?? o si? no se, alome si, que alguein este inactivo es que no tiene acceso no?? no es que se haya eliminado                                                                                                                                                                                                                                                                                                                                                                                                                    |
| O7  | [CERRADO: opcion A, token solo con sub, cid, scope, exp] Confirmaciones pendientes | Rol leido de membresia en vez de claim (3.2), `is_admin` desde BD, Redis tolerante, `GET /users/{id}/companies` acotado, `apply_to_group` y `group_id` de servidor, `User.is_active` - hay que unificar lo de los claims, y leer de la bd, dame las opciones,                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| O8  | [CERRADO: vuelve como worker] Reactivar una membresia | Si el PA la reactiva con el rol previo o siempre como worker                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| O9  | [CERRADO: claves libres de impuestos, ver 4.4] Nombre de la clave de IRPF | `irpf_base` (empresa) frente a `irpf` (override) - eso hay que arreglarlo, hay que ver lo de los taxes. lo del override del trabajador                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| O10 | `CompanyMember.settings`                 | Analizar que aportaria usar los ajustes por usuario y cuando                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| O11 | Billing avanzado                         | Que incluye exactamente y como se llama el modulo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
