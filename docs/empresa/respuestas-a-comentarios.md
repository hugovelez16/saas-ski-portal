# Respuestas a los comentarios sobre el analisis de Empresa

Complementa `analisis-entidad-empresa.md`. Fecha: 2026-10-16.

## 0. Estado de la tabla de decisiones

La primera vez que lei la columna **Respuesta** de la seccion 9 estaba vacia; ya esta guardada (2026-10-16) y la seccion 1 de este documento la recoge. Donde la tabla y mis inferencias previas diferian, manda la tabla (D2 y D5 corregidos). Las filas que son preguntas tuyas a mi se contestan en la seccion 5.

## 1. Decisiones inferidas de tus comentarios

Estado: **OK** = lo dijiste claro. **Confirmar** = lo interprete; dime si es correcto.

| Tema | Decision | Estado |
|---|---|---|
| D1 Worker en empresa gestionada | Solo lectura. No crea, edita ni borra turnos. Solo escribe el manager (y PA) | OK |
| D2 Tarifas en gestionada | El manager **si** edita tarifas propias y ajenas. El worker no las toca. `CompanyRole.admin` no esta habilitado y no hay nada hecho para el | OK (respondido en la tabla; corrige mi interpretacion anterior) |
| D3 Admin de empresa | Hoy no sirve para nada. Mas adelante podra crear tipos de turno, anadir usuarios, etc. Los roles los cambia solo PA | OK |
| D4 Quien edita datos de empresa | PA y company admin, pero no hay ningun company admin ni se pretende. En la practica solo PA. Un manager no edita nada de la empresa | OK |
| D5 Que ve un worker de la empresa | Con ver el `name` basta. Respuesta minima para workers | OK |
| D6 Empresa suspendida | Ningun `User.user` (worker o manager) accede a nada de esa empresa: ni turnos, ni billing, ni listados. Solo PA | OK |
| D7 Ultimo admin | No hace falta guardia: solo PA gestiona membresias y roles, y PA siempre puede anadir gente. Retiro H9 como hallazgo medio. Tu dijiste "no entiendo esto": ver seccion 5 | OK |
| D8 Baja de empresa | No se borra nada. `is_active=false` es la baja. Borrado solo si no tiene **nada** asociado, sin cascadas. La baja se registra en logs. Sin `archived_at`/`archived_by` | OK |
| D9 Invitaciones | Si, por email. Aplazado hasta que las empresas gestionen sus usuarios. Hoy: PA crea el usuario y luego lo anade | OK |
| D10 Unicidad | `name` no necesita ser unico. `fiscal_id` sin UNIQUE y se quita de forms y respuestas (obsoleto) | OK |
| D11 Membresia para crear turno | Si, validar (turno propio, de otro y bulk) | OK |
| D12 `is_managed` true a false | Pediste que te explique las situaciones. Ver 2.9 | Pendiente |
| D13 Turnos sin empresa | Asignar empresa (o decidir que hacer con los existentes tras comprobar la BD) y pasar a NOT NULL. Valorar RLS de PostgreSQL por `company_id`, excepto PA (ver seccion 5) | OK, RLS pendiente |
| D14 Vida del token | Dejar el TTL de 30 min. Cada peticion comprueba empresa y membresia activas en BD (cache Redis ~60 s) | OK |
| D15 Cierre/aprobacion de turnos | No hace falta por ahora (antes: futuro en un modulo) | OK |
| D16 Plan o limites | No entendiste la pregunta; ver seccion 5. Sin decision | Pendiente |
| D17 Auditoria | Si, cuantos mas logs mejor, y el PA debe poder verlos desde la aplicacion sin entrar a la BD. Falta decidir eventos | OK, eventos pendientes |
| D18 `timezone`, `currency` | Innecesario ahora; dejarlo apuntado | OK |
| D19 Reactivar ex-admin | Hoy un manager si puede activar y desactivar miembros (ver seccion 5). Decision: no puede, solo PA | OK |
| D20 Capa `src/` | Preguntaste si hay una inconsistencia: si. Ver seccion 5 | Pendiente |
| D21 PA y empresa nueva | No se anade como miembro; accede por ser PA | OK |

Decisiones adicionales que salen de los comentarios:

| Decision | Estado |
|---|---|
| `GET /companies` solo para PA. Los demas usan `GET /users/me/companies` (ya es lo que hace el front) | OK |
| Un manager **no** anade miembros por ahora (`POST members/add` solo PA) | OK |
| Un manager **no** activa/desactiva miembros (`PUT members/{uid}/status` solo PA) | OK |
| Los roles de empresa solo los cambia PA | OK |
| Un manager **no** resetea contrasenas (`reset-password-email` solo PA) | OK |
| `GET /users/{id}/companies`: validar y acotar (ver 2.8) | Confirmar |
| Validar que `user_id` pertenece a la empresa al crear turnos (individual y bulk) | OK |
| `PUT /work-logs/{id}` no puede cambiar `company_id` ni `user_id` | OK |
| Validar `default_company_id` contra membresia activa | OK |
| Quitar el `default` de `tax_config` | OK |
| Rechazar `name` vacio | OK |
| Editar `name` y `fiscal_id` en la UI | OK |
| Revisar rate limit en toda la API (gateway o por endpoint) | OK |
| Si la cache Redis falla, el endpoint sigue funcionando sin cache | Confirmar |
| Quitar los `print` de depuracion | Confirmar |
| Registrar quien suspende o reactiva una empresa | OK |
| Mostrar el mensaje de error del backend al usuario (ver 2.12) | Confirmar |
| Orden de trabajo: primero backend definido y probado, luego frontend (el front solo oculta lo que el backend ya prohibe) | OK |
| Eliminar un worker de una empresa: solo si no tiene turnos; si los tiene, queda inactivo (ver 2.6) | Confirmar |

## 2. Respuestas a tus preguntas

### 2.1 Seguridad y tokens

**Que es un token.** Una cadena firmada que el servidor entrega al hacer login y que el navegador devuelve en cada peticion (aqui va en una cookie `HttpOnly`). Dentro lleva datos (los *claims*): `sub` (id de usuario), `cid` (empresa activa), `role`, `scope`, `is_admin`, `exp` (caducidad). El servidor lo verifica con la firma, sin consultar la BD.

**Que es un claim.** Cada campo dentro del token.

**Que tipos de token hay.** El access token (30 min), el refresh token (se contrasta con la sesion en BD), el de reseteo de contrasena, y dos variantes del access token segun su `scope`: `2fa_pending` (login a medias, falta el segundo factor) e `impersonated` (10 min, un PA actuando como otro usuario).

**Puede alguien cambiar el rol o el scope del JWT a mano.** No, si la firma es correcta. Se firma con RS256 y la clave privada solo la tiene el servidor (`auth.py:28`). Si alguien edita el contenido, la firma no coincide y se rechaza. El problema real no es la manipulacion sino que el **servidor emita claims incorrectos**, que es lo que pasa en H1.

**Por que existe `is_admin` si ya hay un rol.** `users.role` (`UserRole`) es el rol de plataforma. El claim `is_admin` es una copia de esa columna hecha al emitir el token, para no consultar la BD. Como `get_current_user` ya carga al usuario desde BD, la copia es redundante: se podria leer `user.role` directamente y se eliminaria el retraso de 30 min al degradar a un PA. Lo recomiendo.

**Platform admin, segun quien.** Segun `users.role == admin` en BD. Se asigna con el seed inicial, con `PUT /users/{id}` (solo PA) o por SQL. Un usuario no puede ascenderse: `UserSelfUpdate` no tiene campo `role`.

**Free trial o cuenta gratuita.** No con el scope. El scope describe el estado de la sesion, no el plan. Lo coherente es lo que ya existe: `module_subscriptions` con `status=trial` y `expires_at`, y para el worker free una empresa personal propia. Los limites se miran en BD, no en el token.

**Que es el scope `2fa_pending` "sirviendo para empresas".** Es el token que se entrega tras la contrasena correcta pero antes del codigo de 2FA. Deberia no servir para nada salvo para verificar el 2FA. Hay cuatro endpoints de empresa que usan `get_current_user` en vez de `get_verified_user`, y `get_current_user` no rechaza ese scope. Ver nuevo hallazgo H28.

**Hay un bypass de PA en cada endpoint.** Si: cada handler repite `if not is_platform_admin and ...`. Es codigo duplicado y facil de olvidar. Mejor una dependencia unica de permisos (ver 2.5).

**Nota sobre `cid`.** Que la empresa activa viva solo en el token es simplemente una descripcion de como funciona, ni buena ni mala. Coincide con tu idea de "actuar sobre otra app" al cambiar de empresa. Una matiz: el frontend tambien acepta `?companyId=` en la URL y le da prioridad (`layout.tsx:81`), asi que puede mostrar una empresa distinta de la que el backend usa. Hallazgo H32.

**Cambios de rol y baja de membresia con 30 min de retraso.** Si aceptas el TTL, el riesgo se reduce a esa ventana. Las comprobaciones por peticion (empresa activa, membresia activa) lo cierran donde importa.

### 2.2 Modelo y conceptos

**Tenant.** Es la unidad de aislamiento de datos: lo que no debe verse entre clientes. Aqui es la empresa. El usuario es una **identidad global** que puede pertenecer a varios tenants; sus datos propios (perfil, 2FA, sesiones) son globales, y sus turnos y tarifas pertenecen al par (usuario, empresa). Tu idea de "empresa personal" para usuarios free encaja: cada uno seria su propio tenant.

**Todo debe girar en torno a los worklogs.** Son el hecho central (de ahi salen importes, billing e informes), pero la estructura que los sostiene es empresa + membresia, porque las tarifas viven en la membresia. Diria: worklogs como nucleo del valor, membresia como eje del modelo.

**`crud.create_user` busca la empresa "Personal".** Al registrar un usuario, busca una empresa llamada literalmente "Personal", lo une como worker y la fija como `default_company_id` (`crud.py:64-74`). El seed no crea esa empresa, asi que probablemente no existe. Es un germen de la "empresa personal" pero por coincidencia de nombre, que es fragil. Cuando se haga el plan free habra que modelarlo con un campo propio.

**`name` vacio.** Si, hay que evitarlo (min 1 caracter tras quitar espacios, y un maximo).

**`fiscal_id` obsoleto.** Me parece buen camino: (1) dejar de pedirlo en la UI y de devolverlo en `CompanyResponse`, (2) quitar las referencias (seed, dialogo de alta, tarjetas, pagina de modulos, mapper), (3) mantener la columna nullable y borrarla mas adelante. Si quieres, preparo la lista exacta de referencias.

**Default de `tax_config`.** De acuerdo, quitarlo (modelo `{}` y schema `{}`). Consecuencia: una empresa sin `social_security` calcularia 0 sin avisar (H19), asi que el alta debe exigir los valores o el calculo debe fallar de forma visible.

> Pero que pasa si SS es 0?? deberia dar igual, es un tax que no se aplica, los tax se restan al bruto, si el tax es 0, se resta 0 no?

**JSONB con claves fijas: es correcto?** Depende de la clave:

- Claves **dinamicas** (tipos de turno definidos por la empresa en `worklog_definitions`, tarifas por tipo en `rates_config`): JSONB es la herramienta adecuada.
- Claves **fijas y conocidas** (`tax_config`: `social_security`, `irpf_base`, `extra`; la mayor parte de `settings`): JSONB funciona, pero hace falta un **contrato**. Se define como modelo Pydantic con tipos, rangos (por ejemplo 0 a 1) y `extra="forbid"`, y se usa para validar al escribir y para aplicar defaults al leer.
- Una clave desconocida en `tax_config` hoy se guarda y **no se usa** (solo se leen las tres conocidas), como sospechas.

**Catalogo de ajustes.** Si. Lo ideal: un modelo `CompanySettings` en el backend con todos los ajustes, sus defaults y su tipo, y el frontend solo los consume. Hoy los defaults viven en el frontend (`use-company-settings.ts`), que **no es buena practica**: dos clientes distintos podrian divergir. Es aplicable a los demas JSONB.

**Que hay en `settings` y para que sirve.** Comportamiento por empresa que lee el frontend: tipo de precio y recargo (`business_logic.*`), si el worker puede escribir importes a mano y el modo de entrada (`worker_experience.*`), etiquetas renombradas (`ui_customization.labels`), `allow_tutorial`, `allow_coordination`, `allowed_rates`, y la lista de modulos. Estoy de acuerdo en que un manager no deberia editarlos (D4).

> Vale, tutorial y coordination son restos de una version antigua de la aplicacion, asique deberiamos eliminarlos, cuando ajustemos bien el catalogo de settings

**`settings` de la membresia.** `CompanyMember.settings` son ajustes por usuario dentro de una empresa; el backend los mezcla encima de `Company.settings` al devolver las empresas (`crud.py:662-668`). Hoy casi no se usan.

> Si no se utilizan los settings de usuario, podriamos analizar como de bien nos vendria utilizarlos o no y en que nos beneficiarian

**"Solo se actualiza via ORM" (`updated_at`).** Quise decir que `updated_at` lo pone SQLAlchemy; un `UPDATE` por SQL directo no lo toca. No hay problema practico hoy. Mover la regla a un trigger de PostgreSQL es barato (una migracion) y tiene sentido cuando llegue la auditoria. No es prioritario.

### 2.3 Registros, seed y logs

**Seed en produccion.** `seed_initial_data()` se ejecuta en **cada arranque**, en dev y en prod (`main.py:102-108`), pero solo actua si estan definidas las variables `INITIAL_ADMIN_*` y el email no existe. Coincido en que deberia lanzarse solo al crear la BD, con `./bin/seed`. Propuesta: quitarlo del arranque, o limitarlo a "no existe ningun usuario".

> Efectivamente, creo que solo deberia pasar al arranque de la bd y solo si no hay usuarios (o por lo menos un PA)

**Para que los `print`.** Son restos de depuracion. No aportan nada en produccion y vuelcan datos personales. Hay que sustituirlos por `logging` con nivel y sin datos sensibles.

**Guardar la baja en los logs.** Mejor en la tabla `audit_logs` (quien, cuando, que, motivo) que solo en logs de aplicacion, porque se consulta desde la propia app. Con eso no hacen falta columnas `archived_at`/`archived_by`.

**Que cambios auditar (D17).** Propuesta inicial: alta, suspension y reactivacion de empresa; cambio de `is_managed`; alta, baja y reactivacion de membresia; cambio de rol; cambio de tarifa (valor anterior y nuevo); cambios de `tax_config` y `settings`. Dime cuales sobran.

> Los veo bien

### 2.4 Estructura que "falta"

**`owner_id`, contacto, `slug`, `plan`.** `owner_id` seria el titular de la cuenta (responsable legal y de facturacion de la empresa cliente). Contacto: email y telefono para facturacion y soporte. `slug`: identificador legible y unico para URLs o subdominios. `plan`: nivel de suscripcion (free, pro...). Como ya hay suscripciones por modulo, `plan` no hace falta, y `timezone`/`currency` los descartas. Propongo retirarlos todos de la lista de carencias.

> Dices "titular de la cuenta". Pero que cuenta?? para las suscripciones de modulos?? digo yo que la cosa seria vincularlo con cada usuario de la plataforma o con una empresa no?

**Estado de cierre y aprobacion de turnos.** Cierre: bloquear un periodo (por ejemplo un mes) cuando ya se ha facturado o pagado, para que nadie cambie turnos que alteran un total ya emitido. Aprobacion: un manager valida un turno antes de que cuente. Lo dejas para un modulo futuro; la aprobacion tambien seria la alternativa a D1 si algun dia el worker pudiera registrar en gestionada.

> Efectivamente, lo dejamos para mas adelante, es buena opcion, pero para un modulo

**Validar fechas pasadas o futuras.** No hace falta limitar el pasado ni el futuro (el manager planifica turnos futuros en el calendario). Lo util es validar `inicio <= fin`, un rango razonable que evite errores de tecleo (ano 2062) y, como decision de negocio, si dos turnos del mismo trabajador pueden solaparse.

> El validar las fechas creo que ya se hace en el front, pero efectivamente debe hacerse en el back primordialmente, y ya luego que el front lo compruebe para dar error antes de mandar nada (pero es lo hace por que el back es el que lo dicta). La logica de negocio debe de estar en el domino y no en el front

### 2.5 Arquitectura: `crud.py` y `src/`

**`crud.py` es un unico fichero con todo.** Si: 1257 lineas con usuarios, empresas, membresias, turnos, modulos, tarifas y dashboard. No es buena practica; mezcla responsabilidades y es dificil de probar.

**Entonces que se usa, y no se deberian usar entidades de dominio.** El camino vivo es: router, `crud.py`, modelos SQLAlchemy (que hacen de entidad). Las entidades de dominio de `backend/src/` no se usan en produccion, solo en tests.

**`src/` es la arquitectura limpia.** Si: `domain`, `application` (casos de uso) e `infrastructure` (repositorios y mapeadores) son los tres anillos de una arquitectura hexagonal. Esta empezada pero no conectada a la API, y las reglas importantes (por ejemplo `is_managed`) viven fuera de ella.

> Pues se deberia dar un repaso, y intentar completarla como api v2 por ejemplo, asi podemos seguir utilizando la api de crud.py y mientras, poco a poco, vamos probando la nueva. Lo que si que quiero valorar es, ¿Pyhton es el mejor lenguaje para el back? Que ventajas y desventajas tiene?

Opciones para D20:
| Opcion | Coste | Cuando compensa |
|---|---|---|
| A. Migrar a `src/` caso de uso a caso de uso | Alto, semanas, sin valor visible al principio | Si prevés que las reglas de negocio crezcan mucho |
| B. Dividir `crud.py` en modulos por area (usuarios, empresas, membresias, turnos...) y centralizar los permisos en una politica | Medio, mecanico y reversible | Ahora |
| C. No hacer nada | Cero | Deuda creciente |

Recomiendo B ahora y decidir A mas adelante. Si se hace B, eliminar o archivar `src/` evita mantener dos versiones de la misma logica.

**"Esta bien que `crud` confie en el router".** Funciona mientras cada router recuerde comprobar. Es fragil: basta un olvido para abrir un hueco. Mejor que las funciones sensibles reciban la empresa y el actor, y filtren por ellos.

### 2.6 Usuarios, miembros y estados

Hay tres cosas distintas que conviene no mezclar:

| Concepto | Que es | Estado |
|---|---|---|
| Usuario | La cuenta global | `User.is_active` (desactiva el acceso a la plataforma; hoy no se aplica, H2) |
| Membresia | La relacion de un usuario con una empresa | `CompanyMember.is_active` |
| Worker | Un **rol** dentro de una membresia | `CompanyMember.role = worker` |

**Se puede eliminar un worker de una empresa.** Hoy no existe: solo se desactiva la membresia. Propuesta (mismo criterio que la empresa): borrar la membresia solo si no tiene turnos ni nada asociado, sin cascadas; si los tiene, queda inactiva. Lo acordado sobre desactivar (solo PA) aplica a la membresia.

> Me parece perfecta la propuesta

**Que pasa al desactivar una membresia.** Se reasigna `default_company_id` a otra membresia activa o a nulo, los turnos se conservan, y su token sigue valido hasta caducar (a la empresa deja de entrar por las comprobaciones por peticion).

**Puede un usuario no tener ninguna empresa.** Si: registro sin empresa "Personal", o todas sus membresias desactivadas. Inicia sesion y el frontend muestra "no estas vinculado a ninguna empresa". Ya lo cubre el diseno actual.

**Para que sirve `default_company_id`.** Para elegir la empresa activa al emitir el token tras el login o el refresh (`auth.py:254`). Si apunta a una empresa sin membresia activa, el codigo toma otra. Hay que validarlo al escribirlo, como dices.

**Como se emite el token con el default (la fila que no entendiste).** Orden: (1) empresa pedida, si no (2) `default_company_id`; se busca una membresia activa de esa empresa; (3) si no la hay, se usa la primera membresia activa que tenga; (4) si no tiene ninguna, el token queda con `cid` de esa empresa pero `role` nulo, es decir, sin permisos. Es un caso raro; la correccion es no ponerle `cid` cuando no hay membresia.

**"Target".** Es el usuario sobre el que se actua (el del `{user_id}` de la ruta), frente al que hace la peticion. Lo sustituyo por "usuario objetivo".

> No hace falta que lo sustituyas, con target me entero

**`GET /users/{id}/companies`.** Si: un manager ve todas las empresas a las que pertenece cualquier worker de la suya, incluidas inactivas y ajenas. Propongo devolver solo las empresas en comun con el manager, o dejarlo solo para PA.

**Reset de contrasena por un manager.** El endpoint envia un email al propio usuario (no revela la contrasena), pero estoy de acuerdo en quitarlo. Solo PA.

**Registro publico.** `POST /users/` (con barra final) no tiene autenticacion: cualquiera puede crear una cuenta. Existe aparte `POST /users` (sin barra), que es el de PA. Dos rutas casi iguales es confuso. El frontend solo llama a la version de PA (`users.ts:41`), asi que el registro publico probablemente no se usa. Propongo eliminarlo. Ademas devuelve el schema `UserCreate`, que incluye `password`. Hallazgo H29.

### 2.7 Endpoints de empresa

| Endpoint | Que hace | Nota |
|---|---|---|
| `GET /companies` | Lista de empresas. Hoy: PA todas, el resto las suyas | El front lo usa solo para PA; los demas usan `/users/me/companies`. Pasa a PA solo |
| `GET /companies/detailed` | Cada empresa con sus miembros incluidos (usuario, rol, estado) | Lo usa la pagina de administracion. El nombre es poco descriptivo; algo como `?include=members` lo seria mas |
| `GET /companies/{id}/members` | Miembros de **una** empresa, con filtro de estado | Solapa con `detailed`; la diferencia es una empresa frente a todas |
| `GET /companies/{id}/rates-v2` | Tarifas de todos los miembros de la empresa | En `companies.py` no existe una version v1: el sufijo es herencia del paso a `rates_config`. Conviene renombrarlo |
| `GET /companies/{id}/dashboard-summary` | Resumen para el panel del manager: horas e importes del periodo y de hoy, desglose por tipo y por dia, y resumen por trabajador | |
| `PUT /companies/{id}/members/order` | Guarda el orden de presentacion de los miembros (`sort_order`), usado en la pagina de usuarios del manager | Solo presentacion; puede seguir permitido a un manager |
| `PUT /companies/{id}/members/{uid}/status` | Activa o desactiva la membresia. Lo usa la pagina de administracion de PA | Pasa a PA solo |
| `POST /companies/{id}/members/add` | Anade a un usuario existente por email | "No recibe rol": el cuerpo solo lleva el email y entra siempre como worker; para otro rol PA lo cambia despues. Pasa a PA solo |
| `PUT /companies/{id}/members/{uid}` | Edita tarifas, ajustes, estado y rol de un miembro | Ver abajo |

**`detailed` y `worker_daily_report`.** El modulo del parte diario necesita ver a los miembros de la empresa, y se resolvio dejando entrar a un worker con ese modulo en `detailed`. Es un acoplamiento raro: lo limpio es un endpoint propio del parte diario que devuelva solo lo que necesita.

> Pues podemos crearlo si, para que el front no tenga que hacer mucho, sino que solo tenga que consultar ese endpoint

**Que ven los workers de su empresa (D5).** Hoy `GET /companies/{id}` devuelve a cualquier miembro `fiscal_id`, `tax_config`, `settings` y `is_managed`. Algo de `settings` es necesario para que el frontend del worker funcione (modo de entrada, etiquetas, modulos). Propuesta: dos respuestas, una publica (`id`, `name`, `isManaged`, `isActive` y los ajustes de interfaz del worker) y otra completa para manager y PA.

> En vd no creo que sea necesario el is active, si no esta active un worker no va a poder verlo directamente

**"Role solo si no cambia".** El frontend a veces reenvia el rol actual junto con otros campos, y el backend lo tolera si coincide. No es una funcion: es un efecto de usar un unico endpoint para todo. Con "roles solo PA", el campo `role` se acepta solo de PA y se rechaza o ignora en el resto. Mejor aun, separar en `PUT .../role` y `PUT .../rates`.

> Claro, es que no le veo el sentido a que se envie todo el rato el rol no?? con enviar el id del usuario por ejemplo, se extrae la entity de usuario con ese id, y se consulta el rol de esa entity

**"El bloqueo excluye a los managers".** Es al reves de lo que se leia: hoy el bloqueo de tarifas en gestionada se aplica a los workers y los managers quedan libres. Quitar esa exclusion significa que el manager tambien queda bloqueado en lo suyo. Segun D2 tiene sentido que un manager no se edite sus propias tarifas.

> Un manager vamos a poner que si pueda editarse sus propias tarifas, pq sino, dependemos de que haya dos managers

**`GET /work-logs/billing-summary` y el modulo `billing`.** El modulo `billing` existe y gobierna el menu "Facturacion" del frontend, pero el endpoint **no comprueba el modulo** (`require_module` no se usa en ningun router). Es decir, hoy el modulo solo oculta la opcion; no protege los datos. Hallazgo H33. Con D6, el endpoint comprobaria `is_active` salvo para PA.

> Lo que veria bien es que se separaran dos apartados de billing, uno mas basico con una suma de lo trabajado y lo generado, y otra con algo mucho mas detallado (porcentajes, tendencias y alguna analitica) y eso es lo que se añade en el modulo

**`/modules/me`.** Tienes razon: son los modulos del usuario (personales mas los de su empresa activa). Con D6, el apartado de empresa deberia ignorarse si la empresa esta suspendida; la parte personal no tiene que ver con la empresa.

> Claro, pero si en modules me se devueleve un modulo pq tu empresa lo paga (o pagaba) no tiene sentido que pueda utilizar ese modulo si la empresa ya no esta activa

**"Feature-gating".** Es activar o bloquear una funcion segun el plan o modulos contratados. `require_module(code)` es una dependencia para proteger un endpoint de esa forma (devuelve 403 si la empresa o el usuario no tiene el modulo; PA pasa). Esta definida y no se usa. Deberia usarse en los endpoints de los modulos de pago (billing, informes, parte diario).

> Efectivamente habria que utilziarlo

### 2.8 Turnos

**"Sin validar que el destino sea miembro".** Un manager crea un turno enviando `user_id` y `company_id`. El backend comprueba que el manager gestiona esa empresa, pero **no que `user_id` pertenezca a ella**. El frontend solo ofrece miembros, asi que desde la UI no se ve, pero la API acepta cualquier UUID. Hay que validarlo en el backend.

> Efectivamente hay que validarlo, el problema que tenemos es que hay muchas cosas que no se verifican en el back, solo se condifa en el front, asique creo que lo mejor es centrarnos en el back y que luego el front no tengan logica de negocio no?? 

**`PUT /work-logs/{id}` y el `company_id`/`user_id` del cuerpo.** Hoy se toman del cuerpo; con la decision de no permitir el cambio, se ignoran o se rechazan.

**Editar y recalcular.** Hoy, al editar, se recalcula con la tarifa **actual** del miembro (`crud.py:566-616`), no con la del momento. Es decir, corregir un turno antiguo lo reprecia con la tarifa de hoy. Estoy de acuerdo contigo: si no cambian tipo, horas ni fechas, se conserva el importe; si cambian, se recalcula con las tarifas del `calculation_snapshot` de ese turno, y recalcular con la tarifa vigente seria una accion explicita. Hallazgo H31.

**Falta de tarifa y toast.** El backend responde 400 con un mensaje claro. El frontend debe mostrarlo (ver 2.12).

### 2.9 `is_managed` de true a false (D12)

Situaciones que se pueden dar:
- Los workers recuperan edicion y borrado de **todos** sus turnos, incluidos los que el manager creo en su nombre y los ya facturados.
- Recuperan la edicion de sus tarifas. Combinado con "editar reprecia con la tarifa actual", un worker podria cambiarse la tarifa y despues editar un turno antiguo para repreciarlo. El cambio de recalculo (2.8) lo evita.
- El efecto es inmediato para peticiones nuevas, pero un frontend abierto sigue mostrando el modo anterior hasta recargar.
- De false a true, los workers pierden a mitad de periodo la posibilidad de corregir sus propios turnos.

Por eso conviene auditar el cambio y que solo PA pueda hacerlo (ya es asi). Un cierre de periodo (D15) lo resolveria del todo.

> No se a que te refieres con un cierre de perido la vd

### 2.10 Frontend

**Toasts en errores HTTP.** No existe un tratamiento central: cada mutacion define su propio `onError` con un mensaje fijo y no se lee el `detail` del backend (`api.ts` no tiene interceptor de respuesta). Propuesta: un interceptor unico que mapee 401, 403, 404, 409, 422 y 5xx a una notificacion con el `detail` cuando exista. Ademas, si el backend es estricto y la UI oculta lo que no se puede hacer, un 403 por accion prohibida debe ser raro.

**Orden backend primero.** De acuerdo. Si `GET /companies` pasa a PA, el boton que lleva al listado solo se muestra a PA, y no se necesita nada mas.

### 2.11 Otras preguntas

**Rate limit.** Tienes razon en que hay que revisarlo: no hay ningun limite en la API. En `gateway/` no hay `limit_req` y no se usa `slowapi` en el backend. El login queda expuesto a fuerza bruta. Hallazgo H30. Propuesta: `limit_req_zone` en Nginx, estricto para `/api/auth/` y mas laxo para el resto.

> Perfecto

**Un manager de A con token en B.** Es el comportamiento que quieres y esta bien documentado.

**Admin de empresa "da igual".** Cierto. El unico efecto del rol hoy es que H1 permite pedir `"admin"` en `switch-scope`; con la correccion de H1 el valor desaparece de los tokens.

## 3. Cambios en el analisis principal

### Hallazgos nuevos

| ID | Sev. | Hallazgo | Conf. |
|---|---|---|---|
| H28 | Alta | `get_current_user` acepta tokens `2fa_pending`. Cuatro endpoints de empresa (`PUT members/{uid}`, `PUT members/{uid}/status`, `GET /companies/{id}`, `GET rates-v2`) lo usan en vez de `get_verified_user`. Quien conozca solo la contrasena de un usuario con 2FA podria leer tarifas o editar miembros, siempre que el token pendiente lleve `cid` y `role` (por confirmar) | V en uso de `get_current_user` (`routers/companies.py:245,270,304,327`); L en el contenido del token |
| H29 | Media | `POST /users/` es registro publico sin autenticacion y devuelve `UserCreate` (incluye `password`). Probablemente sin uso en el frontend | V (`routers/users.py:15-23`, `schemas.py:84-89`) |
| H30 | Media | Sin rate limit en el gateway ni en el backend | V (grep de `limit_req`, `slowapi`, `Limiter` sin resultados) |
| H31 | Media | Editar un turno lo recalcula con la tarifa actual del miembro, no con la del momento | L (`crud.py:566-616`) |
| H32 | Baja | El frontend da prioridad a `?companyId=` sobre la empresa del token: puede mostrar una empresa y operar sobre otra | L (`layout.tsx:81`) |
| H33 | Media | El modulo `billing` solo oculta el menu; `billing-summary` no comprueba el modulo. `require_module` no se usa en ningun router | L |

> H28 - eso hay que cambiarlo no?
> H29 - Elimina eso, ademas, la barra final?? eso es correcto?
> H32 - Eso de poner la empresa en la url era por dar la opcion de iniciar sesion en dos pestañas y poder tener seleccionado dos empresas activas distintas no?? eso es bueno tenerlo asi?? algun inconveniente?? imagino que aunque se haga caso a la url, hay que comprobar quien solicita esa informacion no?
> H33 - Habria que utilizar lo de require_modulo en los endpoint

### Cambios en hallazgos existentes

| ID | Cambio |
|---|---|
| H9 | Retirado como hallazgo medio. Con la decision de que solo PA gestiona membresias, el riesgo desaparece. Queda como nota operativa: la recuperacion es "PA anade un manager" |
| H10, D19 | Sin objeto: un manager ya no reactiva a nadie |
| H12 | Acotado por la decision D5 (respuesta publica frente a completa) |
| H13, H14 | Resueltos por las decisiones anteriores (`users/{id}/companies` acotado; datos de empresa solo PA) |
| H11 | Confirmada la direccion: bloqueo total con empresa suspendida (D6) |
| D7 | Retirada |
| Seccion 2.3 del analisis | Quitar de "Lo que falta": `plan`, `timezone`, `currency`, `slug`, `owner_id`, contacto, estado de cierre |
| Seccion 10.1 del analisis | Corregir "Quien recupera una empresa sin gestor": no hace falta cambiar de contexto, basta con que PA asigne el rol a un worker o cree un manager |
| Tabla 5.3 del analisis | Cambiar "Listar turnos" y "Billing" de PERMITE a BLOQUEA como objetivo |

## 4. Orden de trabajo propuesto

Un PR por bloque, con test que falle antes del arreglo.

1. H1 (escalada en `switch-scope`).
2. H28 (`get_current_user` aceptando `2fa_pending`).
3. H2 (usuario inactivo).
4. H3 y validacion de miembro en turnos (individual y bulk, `PUT` sin cambio de empresa/usuario).
5. Politica de permisos centralizada + las decisiones de la seccion 1 (PA solo para empresa, miembros, estado, reset; `GET /companies` solo PA; empresa suspendida bloquea todo).
6. H29 (registro publico) y H30 (rate limit).
7. Validaciones y limpieza: `name`, quitar `print`, quitar default de `tax_config`, Redis resiliente, `default_company_id`.
8. H31 (recalculo con snapshot).
9. Contratos Pydantic de los JSONB y catalogo de `settings`.
10. Frontend: ocultar lo prohibido, interceptor de errores, correcciones de `isManaged`.

Pendiente de tu confirmacion para empezar: D20 (opcion B de 2.5) y la lista de eventos de auditoria. El resto de decisiones de la seccion 1 esta cerrado.

## 5. Respuestas a las preguntas de la tabla de decisiones

**D7, "no entiendo esto" (ultimo admin).** La regla evitaba que alguien con permisos de gestion se degradara o desactivara a si mismo y dejara la empresa sin nadie que la gestione. Como ahora solo PA cambia roles y estados, nadie puede dejarse a si mismo sin acceso, y la regla no hace falta. Queda retirada.

**D8, "que es archivar".** Archivar es dar de baja sin borrar. Para la empresa ya lo hace `is_active=false`: se conservan todos los datos, pero nadie entra. Yo proponia ademas guardar fecha y autor de la baja en dos columnas nuevas; con `audit_logs` (D17) no hacen falta. Es decir, queda como dices: no se borra nada, y solo se permite borrar una empresa que no tenga absolutamente nada asociado.

**D9, "invitarlos cuando".** Ejemplo del caso futuro: un responsable de una empresa quiere que su plantilla se registre. Escribe sus emails; el sistema les envia un enlace con caducidad; cada trabajador crea su cuenta y queda unido a esa empresa. Hoy no existe porque el PA crea las cuentas. Aplazado.

**D12, "que efecto tiene" `is_managed`.** Ver 2.9 de este documento. Resumen: al pasar a no gestionada, los workers pueden editar y borrar sus turnos (tambien los ya cerrados y los creados por un manager), y cambiarse la tarifa. Al reves, pierden esa posibilidad de golpe. No se recalcula nada en automatico. Por eso interesa registrar el cambio.

**D13, RLS de PostgreSQL.** Row Level Security consiste en que la propia BD filtre las filas por `company_id`, de modo que aunque el codigo olvide un filtro, la consulta no devuelve datos de otra empresa. Es una buena segunda barrera para un SaaS multiempresa. Requisitos y cuidados:
- Cada peticion debe indicar a la BD la empresa activa (por ejemplo `SET LOCAL app.company_id = '...'` dentro de la transaccion), y el PA se exime con una politica propia.
- Con pool de conexiones hay que usar `SET LOCAL` y no `SET`, para que el valor no se filtre entre peticiones.
- Afecta a las funciones SQL como `get_billing_summary` y a las migraciones (el usuario que migra no debe estar sujeto a RLS).
- Coste: medio. Recomiendo hacerlo **despues** de centralizar los permisos (paso 5 del orden de trabajo) y con `company_id` ya NOT NULL, y empezar por `work_logs` y `company_members`.

**D15, "para que bloquear".** Un cierre evita que un turno cambie despues de haberse pagado o facturado. Si no hay nomina ni facturacion que dependa de ellos, no aporta. Descartado por ahora.

**D16, "plan o limites".** Plan: el nivel contratado por la empresa (gratis, basico, completo). Limites: topes asociados (maximo de trabajadores, de turnos al mes). Hoy el unico mecanismo es la suscripcion a modulos. Es una pregunta de producto que no hace falta resolver ahora. Queda abierta.

**D17, ver los logs desde la aplicacion.** Si: hoy `audit_logs` solo se consulta por BD. Haria falta un endpoint de lectura solo para PA (filtros por empresa, usuario, tipo y fechas) y una pantalla de administracion. Lo apunto como trabajo propio, posterior a la ampliacion de eventos.

**D19, "ahora mismo un manager puede activar o desactivar usuarios".** Si. Hoy un manager puede: activar o desactivar miembros (`PUT members/{uid}/status` y `is_active` en `PUT members/{uid}`), reactivar a quien estaba de baja con `members/add`, anadir usuarios existentes por email y resetear contrasenas. Tus decisiones lo reducen todo a PA.

**D20, "hay una inconsistencia en el codigo del back".** Si. Hay dos implementaciones de la misma logica: la que usa la API (`routers/` mas `crud.py`) y la que esta en `backend/src/` (entidades de dominio, casos de uso, repositorios), que nadie llama salvo los tests. Se parecen pero no son iguales (por ejemplo, la de `src/` exige membresia activa para crear un turno y la de `crud.py` no, H3). Hay que elegir una. Mi recomendacion es dividir `crud.py` por areas y centralizar permisos (opcion B de 2.5), y decidir el resto de `src/` mas adelante.
