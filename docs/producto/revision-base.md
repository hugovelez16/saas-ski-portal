# Revision de base del producto

Estado: **Propuesta**. Fecha: 2026-11-22. Issue: #102.

Diagnostico y propuesta antes del dominio (#66-#72) y la migracion hexagonal
(O4). No cambia reglas `R-*` ni codigo; lo que hay que decidir esta en la
seccion 7 (cuestionario para Docmost). Mediciones con `wc -l` y `grep`.

## 1. Producto en una pagina

**Problema.** Una escuela de esqui trabaja con monitores temporales o
autonomos, cada uno con su precio por tipo de clase y sus retenciones. Hoy
lleva las jornadas en hojas de calculo y calcula a mano lo que debe a cada
monitor. La plataforma registra las jornadas (turnos), calcula el importe con
la tarifa y los impuestos de cada monitor y da al responsable el parte del dia
y los informes de la temporada.

**Para quien.**

- **B2B, la escuela (lo que se vende hoy).** El responsable (manager) organiza
  y paga; los monitores (worker) consultan o registran sus jornadas. Se cobra
  por plan y meses activos (`docs/planes-y-precios.md`): Pista Verde, Azul y
  Roja, con limites de monitores y responsables y dos modulos de pago
  (Cuadrante compartido e Informes).
- **B2C, el monitor (futuro, O16).** Un monitor que trabaja para varias
  escuelas apunta sus jornadas en una empresa propia, gratis o con un plan
  personal. No existe hoy y no hay nada vendido.

**v1 frente a futuro.**

| Entra en v1 | Futuro (no se construye hasta que haya cliente o decision) |
|---|---|
| Alta de escuela, responsables y monitores (la hace hoy el PA en la puesta en marcha) | Registro publico y empresa propia B2C (O16) |
| Turnos, tipos de turno, tarifas por monitor, impuestos, creacion en lote | Billing avanzado (O11) |
| Empresa gestionada o autonoma | Aprobacion de turnos, cierre de periodo |
| Parte diario (Cuadrante compartido) e Informes como modulos de empresa | Invitaciones por email |
| Billing basico, auditoria, soporte del PA | Limites del plan aplicados en codigo (O12) |
| 2FA, sesiones, multiempresa por usuario | Admin de empresa, RLS (ver seccion 5) |

## 2. Modelo minimo

Entidades necesarias para la v1 y su relacion:

```
User 1-n CompanyMember (rol, estado, rates_config) n-1 Company (impuestos, tipos, settings, modos)
User 1-n WorkLog n-1 Company        AppModule 1-n ModuleSubscription n-1 Company
AuditLog (actor, empresa, objetivo, antes, despues)   UserSession (refresh por dispositivo)
```

Siete tablas bastan. Lo que sigue es cada concepto actual con la propuesta.

| Concepto | Hoy | Propuesta | Motivo |
|---|---|---|---|
| Empresa personal | Restos: la propiedad `is_personal` de la entidad de dominio (`backend/src/domain/entities/company.py`) compara el nombre con "personal" y nadie lo llama; `work_logs.company_id` es nullable y `crud.py` aun filtra `company_id IS NULL`; el alta de usuario del PA ofrece "No company (Personal)" | **Se elimina** de v1. `work_logs.company_id` pasa a NOT NULL tras comprobar que no hay filas nulas | Un turno sin empresa no tiene tarifa, impuestos ni aislamiento. Es requisito de RLS (O1). Si llega el B2C, su empresa propia es una empresa normal con un campo de tipo, nunca por nombre (P2) |
| Gestionada / autonoma (`is_managed`) | Un booleano en la empresa, solo lo cambia el PA | **Se queda** | Es la diferencia real entre escuelas: la que apunta por el monitor y la que deja que el monitor apunte. Un solo sitio y una sola regla en `access_policy` |
| `owner` | Retirado (O13) | **Eliminado**, no se reintroduce | La responsabilidad la tienen los managers y el PA. Un owner pide reglas de traspaso y de ultimo owner |
| `rates_config` por miembro | Tarifa por tipo de turno, con `is_gross`, `tax_overrides` y `extras` | **Se queda** | La tarifa depende del monitor. Es el unico sitio de la tarifa. Que la edite el worker en autonoma es decision (P7) |
| `CompanyMember.settings` | O10 lo aparca, pero hay caso de uso (`set_member_settings`), validador, permiso `can_edit_member_settings` y mezcla al leer la empresa | **Se elimina** (codigo y despues columna) | Nadie lo usa y obliga a mantener una capa de configuracion, un permiso y sus tests (P8) |
| `worklog_definitions` | Catalogo de tipos de turno por empresa (`unit`, `label`, `fields` libre) | **Se queda; se simplifica** `fields` | Es necesario. `fields` es `list[dict[str, Any]]` sin contrato: se tipa o se quita cuando se migre Turnos |
| `tax_config` | Claves libres `nombre: fraccion` | **Se queda** | Cada escuela nombra sus retenciones. Ya tiene contrato y tests |
| Modulos y suscripciones | Catalogo con `target_scope` (`company`, `user`, `both`), `price_monthly` sin uso, suscripciones de empresa y de usuario, y ademas `CompanySettings.modules` | **Se simplifica**: solo suscripciones de empresa en v1; se quitan `price_monthly` y `settings.modules` | Se venden dos modulos de empresa. La suscripcion de usuario solo sirve al B2C (O16). `settings.modules` es una segunda fuente para lo mismo (P9, P10) |
| "Ver como" | Claim `view_as`, solo PA, solo lectura, 48 referencias en backend y frontend | **Se simplifica** o se fusiona con la suplantacion (P4) | Dos mecanismos de soporte con reglas propias (R-ACC-44 a 53). En "ver como" worker el PA ve sus propios turnos, que no es lo que ve ningun monitor real |
| Suplantacion | Token `impersonated` de 10 min que puede escribir; 43 referencias; hallazgo #79 (el refresh la prolonga) | **Se queda**, idealmente de solo lectura (P4) | Es lo que responde a "veo lo que ve este usuario". Escribir como otro es el caso de mayor riesgo |
| Admin de empresa | `CompanyRole.admin` reservado; el backend lo trata como manager | **Se elimina** del enum (P3) | Un rol sin efecto confunde a agentes y revisores y amplia la matriz. Se anade cuando haya una necesidad concreta |
| `allowed_rates` en `settings` | Validado y guardado; el backend no lo entrega y el frontend no lo usa | **Se elimina** (P9) | Codigo muerto con contrato y migracion propios |

## 3. Matriz de permisos

Roles: PA actuando, manager y worker. El admin de empresa no aparece porque se
propone eliminarlo (P3). "A" es empresa autonoma y "G" gestionada; si no se
indica, vale para las dos. Toda accion sobre una empresa exige ademas membresia
activa, empresa activa y empresa del token (R-ACC-18 a 23, 41).

| Accion | PA | Manager | Worker |
|---|---|---|---|
| Crear empresa | SI | NO | NO |
| Editar empresa (`name`, `tax_config`, `worklog_definitions`, `settings`) | SI | NO | NO |
| Suspender o reactivar, cambiar `is_managed` | SI | NO | NO |
| Borrar empresa sin datos asociados | SI | NO | NO |
| Ver empresa completa / reducida | SI / SI | NO / SI | NO / SI |
| Anadir o desactivar un worker | SI | NO hoy; SI propuesto (P6) | NO |
| Anadir o desactivar un manager | SI | NO | NO |
| Cambiar el rol de una membresia | SI | NO | NO |
| Conceder o quitar el rol de PA | Fuera de la app (P5) | NO | NO |
| Ver la lista de miembros | SI | SI | NO |
| Reordenar miembros | SI | SI | NO |
| Ver tarifas de todos | SI | SI | NO |
| Editar tarifas ajenas | SI | SI | NO |
| Editar tarifas propias | SI | SI | A: SI hoy (P7); G: NO |
| Crear, editar, borrar turnos propios | SI | SI | A: SI; G: NO |
| Crear, editar, borrar turnos ajenos y en lote | SI | SI | NO |
| Ver turnos propios / ajenos | SI / SI | SI / SI | SI / NO |
| Billing basico | SI | SI | NO |
| Parte diario (modulo) | SI | SI, con importes | SI, sin importes |
| Informes (modulo) | SI | SI, de equipo | Propios (hoy solo en el menu, ver seccion 5) |
| Gestionar modulos y suscripciones | SI | NO | NO |
| Crear usuarios, resetear contrasena o 2FA ajeno | SI | NO | NO |
| Consultar auditoria | SI | NO | NO |
| Suplantar o "ver como" | SI | NO | NO |

**Regla de concesion.** Un rol nunca concede un rol igual o superior al suyo:
el worker no concede nada, el manager como mucho da de alta workers (si se
aprueba P6) y nunca toca el rol de nadie, y el rol de PA no lo concede ningun
PA desde la aplicacion. El fallo ya ocurrido (un manager convertia a un worker
en manager o PA porque el desplegable lo ofrecia y el update lo aplicaba) es
exactamente la violacion de esta regla, y hoy solo la evita que cada endpoint
recuerde poner `require_platform_admin`.

**Propuesta de implementacion.**

1. La matriz vive en un solo sitio del codigo: un modulo puro junto a
   `backend/access_policy.py` con un `Action` por fila y, por rol y modo,
   permitido o no. `authorize_company`, `can_write_work_log` y
   `can_edit_member_rates` pasan a consultar la tabla en lugar de llevar la
   regla escrita en `if`.
2. Cada endpoint declara su accion (`require(Action.MEMBER_SET_ROLE)`), no un
   rol minimo. Un endpoint sin accion declarada falla un test que recorre las
   rutas de la app.
3. Cada fila es un caso de un test parametrizado por (accion, rol, modo) que
   llama al endpoint HTTP real y espera 2xx o 403. Probar solo la funcion de
   politica no habria detectado el fallo: el endpoint de actualizacion no la
   llamaba.
4. El frontend no deduce permisos: `GET /users/me` devuelve las acciones
   permitidas en la empresa activa y la UI solo ofrece esas (P1, P16).

## 4. Configuracion por capas

Regla: cada ajuste vive en un solo sitio. Solo hay una herencia, la del
impuesto: el `tax_overrides` del miembro manda sobre el `tax_config` de la
empresa para la misma clave.

| Capa | Ajuste | Quien lo cambia | Nota |
|---|---|---|---|
| Plataforma (codigo) | Catalogo de `settings` y sus defaults (`backend/contracts.py`) | Despliegue | No es tabla (4.4 de `logica-negocio-empresa.md`) |
| Plataforma (BD) | Catalogo de modulos (`app_modules`) | PA | Sin `price_monthly` ni `target_scope` en v1 (P10) |
| Plataforma (futuro) | Limites del plan (monitores, responsables) | PA | O12. Se modelan con suscripciones cuando haya facturacion |
| Empresa | `name`, `is_active`, `is_managed` | PA | Columnas |
| Empresa | `tax_config`, `worklog_definitions` | PA | JSONB con contrato |
| Empresa | `settings.business_logic.price_type` | PA | Solo afecta a la vista del dashboard |
| Empresa | `settings.worker_experience` (modo de entrada, importe a mano) | PA | |
| Empresa | `settings.ui_customization.labels` | PA | |
| Empresa | Modulos contratados (`module_subscriptions`) | PA | Unica fuente de modulos |
| Miembro | Rol, `is_active`, `sort_order` | PA (alta de worker: P6) | |
| Miembro | `rates_config` (tarifa, bruto o neto, `tax_overrides`, `extras`) | PA, manager; worker en autonoma (P7) | |
| Navegador | Ultima empresa (`lastCompanyId`) | El propio usuario | Nada en servidor (R-ACC-43) |

**Se elimina:** `CompanyMember.settings` (capa miembro de ajustes de interfaz),
`settings.modules` (duplica `module_subscriptions`), `settings.allowed_rates`
(sin consumidor), `AppModule.price_monthly` (sin uso) y las suscripciones con
`scope = user` mientras no exista el B2C.

## 5. Sobreingenieria

Ordenado por coste de mantenerlo frente a lo que aporta hoy. El coste se mide
en lo que obliga a tocar en cada cambio y en lo que un agente tiene que leer
para no romperlo.

| # | Que | Coste de mantenerlo | Propuesta |
|---|---|---|---|
| 1 | **API v1 y v2 a la vez** (`/api/` en `camelCase`, `/api/v2/` en `snake_case`) | Cada endpoint de empresa existe dos veces, con dos clientes en el frontend y pruebas de paridad. 63 rutas en `backend/routers`. Los agentes dudan de cual tocar | Mantener O4, pero cada contexto migrado borra su v1 en la misma serie de PR, con fecha. Ningun endpoint nuevo en v1 (P13) |
| 2 | **RLS de PostgreSQL** (O1, decidida para despues de O4) | `SET LOCAL app.company_id` en cada transaccion, PA exento, politicas por tabla, migraciones y tests solo en PostgreSQL. Con un unico usuario de BD y el filtro por `company_id` ya probado, protege sobre todo de un fallo de consulta | Aplazar hasta tener la matriz de permisos probada por HTTP y `company_id` NOT NULL. Revisar con mas de 10 escuelas (P12) |
| 3 | **Dos mecanismos de soporte** ("ver como" y suplantacion) | 91 referencias en codigo, 11 reglas R-ACC (42 y 44 a 53), claims propios, banner, lista de escrituras permitidas, hallazgo #79 | Uno solo: suplantacion de solo lectura de un usuario concreto (P4) |
| 4 | **Cache Redis de acceso** (60 s con invalidacion) | `access_cache.py`, invalidacion en dos repositorios y en `crud.join_company`, tests de backoff. Un fallo de invalidacion deja permisos viejos 60 s | Quitarla: con decenas de usuarios, leer la membresia por peticion es una consulta por clave primaria (P11) |
| 5 | **Modulos con alcance de usuario** y `target_scope` | Union de suscripciones personales y de empresa en `GET /modules/me` y `require_module`, con su caso de empresa suspendida | Solo empresa en v1; el alcance usuario vuelve con O16 (P10) |
| 6 | **Modulo `billing` sembrado** sin billing avanzado (O11) | Aparece en el catalogo y en el menu sin funcionalidad de pago detras | Retirarlo del catalogo hasta O11 (P17) |
| 7 | **Admin de empresa reservado** | Rama en `normalize_member_role`, valor en el enum, texto en glosario y logica | Eliminarlo (P3) |
| 8 | **`CompanyMember.settings`** | Caso de uso, validador, permiso y mezcla al leer | Eliminarlo (P8) |
| 9 | **Restos de empresa personal** | `company_id` nullable, filtro `IS NULL`, opcion en el alta | Eliminarlos (P2) |
| 10 | **`settings.modules`, `allowed_rates`, `price_monthly`** | Contratos, migracion de normalizacion y tipos del frontend sin uso real | Eliminarlos (P9) |

**Hallazgo (no se arregla aqui).** `reports` y `billing` solo ocultan entradas
del menu (`frontend/src/app/(app)/layout.tsx`); en el backend solo el parte
diario usa la guardia de modulo. Informes se vende en Pista Verde y su pagina
se alimenta de `/work-logs`, que no exige el modulo. Registrado como issue
aparte en #103.

## 6. Estructura para agentes de IA

**Medicion actual** (`wc -l`, 2026-11-22).

| Fichero | Lineas | Nota |
|---|---|---|
| `backend/crud.py` | 1553 | 46 funciones de todos los contextos |
| `backend/schemas.py` | 686 | Esquemas v1 de todos los contextos |
| `backend/routers/auth.py` | 657 | Login, 2FA, switch-scope, suplantacion, sesiones |
| `backend/auth.py` | 578 | Tokens, contexto, resolucion de empresa activa |
| `backend/routers/work_logs.py` | 383 | Con logica de alcance y auditoria dentro del router |
| `backend/contracts.py` | 318 | Contratos JSON de empresa y miembro |
| `backend/routers/v2/schemas.py` | 282 | |
| `backend/routers/modules.py` | 278 | Calculo de modulos efectivos en el router |
| `backend/models.py` | 275 | |
| Total `backend/*.py` y `backend/routers/*.py` | 6622 | |
| `backend/src/` | 2138 en 41 ficheros | Mayor: `company_repository.py` con 267; casos de uso de 14 a 120 |
| Frontend, paginas mayores | 552 a 727 | `manager/users/[userId]`, `reports`, `list`, `admin/companies/[companyId]` |

`backend/src/` ya cumple casi todo; el problema es lo de fuera: un cambio de
turnos obliga a leer `crud.py`, `schemas.py` y `routers/work_logs.py` (2622).

**Reglas propuestas para la migracion hexagonal.**

1. **Un contexto por carpeta.** `backend/src/<contexto>/` con `domain/`,
   `application/` e `infrastructure/` dentro (vertical), en lugar de un
   `use_cases/<contexto>/` dentro de cada capa (P14). Contextos: `company`,
   `membership`, `work_log`, `access`, `module`, `audit`.
2. **README por contexto** de 60 lineas como maximo: responsabilidad, reglas
   `R-*` que implementa, puertos que expone y consume, endpoints y comando de
   tests. Es lo unico que un agente lee antes de abrir codigo.
3. **Limite de lineas**: 300 por fichero y 120 por caso de uso. Un test de CI
   lista los ficheros que lo superan; los existentes entran en una lista de
   excepciones que solo puede encoger (P15).
4. **Casos de uso pequenos**: una clase con un `execute` por fichero, que recibe
   un comando tipado y el actor, y lanza excepciones de dominio, nunca
   `HTTPException`.
5. **Puertos**: el caso de uso solo conoce interfaces de `domain/ports`; la
   implementacion SQLAlchemy vive en `infrastructure` y se inyecta en el router.
6. **Permisos junto al caso de uso**: cada caso de uso declara su `Action` de
   la matriz y su carpeta de tests incluye las filas de esa accion
   (`tests/<contexto>/test_permissions.py`), generadas desde la matriz.
7. **Nada de logica en routers**: el router valida la entrada, llama a un caso
   de uso y traduce excepciones. Un test de imports (como el de pureza de
   `access_policy`) prohibe importar `models`, `crud` o `sqlalchemy` desde
   `backend/routers/v2/`.
8. **Orden de migracion** (O4): Turnos, luego Usuarios y Membresias, luego
   Modulos y billing. Cada contexto termina borrando su parte de `crud.py`,
   `schemas.py` y v1.

## 7. Preguntas para el usuario

### P1. Alcance de la v1

La v1 vendida es B2B (escuela). El B2C (monitor con empresa propia, O16) no
tiene nada construido ni vendido.

- [ ] Solo B2B en v1; el B2C se disena cuando haya un caso real (Recomendada)
- [ ] B2B y B2C gratuito en v1
- [ ] B2B y B2C con plan personal de pago en v1
- Otra:
- Notas:

### P2. Empresa personal y turnos sin empresa

Quedan restos de la "empresa personal" y `work_logs.company_id` admite nulos.

- [ ] Eliminar los restos y hacer `work_logs.company_id` NOT NULL (Recomendada)
- [ ] Eliminar los restos pero dejar la columna nullable
- [ ] Mantenerlo hasta decidir el B2C
- Otra:
- Notas:

### P3. Admin de empresa

Rol reservado que hoy se trata como manager y no se asigna.

- [ ] Eliminarlo del enum y de la documentacion; se anade si hace falta (Recomendada)
- [ ] Mantenerlo reservado como hoy
- [ ] Activarlo ya (crea tipos de turno y anade usuarios)
- Otra:
- Notas:

### P4. "Ver como" y suplantacion

Dos mecanismos de soporte del PA con reglas propias. La suplantacion puede
escribir como el usuario.

- [ ] Uno solo: suplantacion de solo lectura; se elimina "ver como" (Recomendada)
- [ ] Mantener los dos, con la suplantacion de solo lectura
- [ ] Mantener los dos como hoy
- Otra:
- Notas:

### P5. Quien concede el rol de PA

Con la regla "nadie concede un rol igual o superior al suyo", ningun PA
nombra a otro PA desde la aplicacion.

- [ ] Solo por seed o comando de servidor, auditado (Recomendada)
- [ ] Un PA puede nombrar a otro PA desde la aplicacion, auditado
- Otra:
- Notas:

### P6. Alta de monitores por el manager

Hoy solo el PA anade y desactiva miembros. Durante la temporada la escuela
incorpora monitores y depende del soporte.

- [ ] El manager anade y desactiva workers, nunca cambia roles (Recomendada)
- [ ] Solo el PA, como hoy
- [ ] El manager gestiona workers y otros managers
- Otra:
- Notas:

### P7. Tarifas propias del worker en empresa autonoma

Hoy el worker de una empresa autonoma edita su propia tarifa.

- [ ] Solo PA y manager editan tarifas en cualquier modo (Recomendada)
- [ ] Mantenerlo: el worker edita las suyas en autonoma
- Otra:
- Notas:

### P8. Ajustes por miembro (`CompanyMember.settings`)

Aparcado en O10, pero con caso de uso, permiso y validador activos.

- [ ] Eliminar el codigo y despues la columna (Recomendada)
- [ ] Mantener el campo reservado sin codigo
- [ ] Usarlo ya para preferencias de interfaz del monitor
- Otra:
- Notas:

### P9. Ajustes duplicados o sin uso

`settings.modules` duplica las suscripciones y `settings.allowed_rates` no lo
usa nadie.

- [ ] Eliminar los dos (Recomendada)
- [ ] Eliminar solo `settings.modules`
- [ ] Mantenerlos
- Otra:
- Notas:

### P10. Suscripciones de usuario

El catalogo admite modulos de empresa y de usuario. Solo se venden de empresa.

- [ ] Solo suscripciones de empresa en v1; quitar `target_scope` y `price_monthly` (Recomendada)
- [ ] Mantener las de usuario para el B2C futuro
- Otra:
- Notas:

### P11. Cache Redis de acceso

El rol se cachea 60 s con invalidacion en cada cambio de membresia o empresa.

- [ ] Quitar la cache y leer la membresia de BD en cada peticion (Recomendada)
- [ ] Mantenerla
- Otra:
- Notas:

### P12. RLS de PostgreSQL

O1 decidio aplicarla despues de migrar Turnos y Membresias.

- [ ] Aplazarla hasta tener la matriz probada por HTTP, `company_id` NOT NULL y mas de 10 escuelas (Recomendada)
- [ ] Mantener O1 tal cual
- [ ] Descartarla
- Otra:
- Notas:

### P13. Convivencia de v1 y v2

Hoy los endpoints de empresa existen en las dos versiones.

- [ ] Cada contexto migrado borra su v1 en la misma serie de PR; nada nuevo en v1 (Recomendada)
- [ ] Mantener v1 hasta migrar todos los contextos
- Otra:
- Notas:

### P14. Estructura de `backend/src/`

Hoy es por capas (`domain`, `application`, `infrastructure`) con el contexto
dentro de cada una.

- [ ] Por contexto: `backend/src/<contexto>/{domain,application,infrastructure}` con README (Recomendada)
- [ ] Por capas, como hoy, con README por contexto en `application/use_cases/<contexto>/`
- Otra:
- Notas:

### P15. Limite de lineas por fichero

Hay ficheros de 1553, 686 y 657 lineas.

- [ ] 300 por fichero y 120 por caso de uso, con test de CI y lista de excepciones que solo encoge (Recomendada)
- [ ] Limite solo para ficheros nuevos, sin test
- [ ] Sin limite
- Otra:
- Notas:

### P16. Matriz de permisos como fuente unica

Hoy los permisos se reparten entre `access_policy`, dependencias y cada
endpoint.

- [ ] Matriz unica en codigo, accion declarada por endpoint, test HTTP por fila y acciones permitidas en `GET /users/me` (Recomendada)
- [ ] Matriz unica y tests, sin exponerla al frontend
- [ ] Solo documentarla
- Otra:
- Notas:

### P17. Modulos Informes y billing

Informes se vende pero el backend no lo exige; `billing` esta en el catalogo
sin billing avanzado (O11).

- [ ] Exigir `reports` en el backend y retirar `billing` del catalogo hasta O11 (Recomendada)
- [ ] Exigir los dos en el backend
- [ ] Dejarlo como esta
- Otra:
- Notas:
