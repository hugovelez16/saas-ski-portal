# Cambios a ejecutar sobre Empresa (catalogo previo al plan)

Fecha: 2026-10-16. Rama: `docs/analisis-entidad-empresa`.

## 0. Para que sirve

Lista cerrada de las tareas que el plan debe incluir para llevar el sistema al comportamiento descrito en `logica-negocio-empresa.md`. **No es el plan**: no fija orden de ejecucion ni reparto por PR. Cuando se pida el plan, se parte de este catalogo.

Cada cambio aparece una sola vez, aunque en las fuentes (`analisis-entidad-empresa.md` y `respuestas-a-comentarios.md`) se mencionara en varios sitios. Las referencias `H` y `D` son las de esas fuentes. Los hallazgos no se han reverificado en el codigo para este documento.

Columna **Estado**:
- **Listo**: la decision esta cerrada, se puede planificar.
- **Confirmar**: propuesto o derivado; planificable asumiendo la propuesta.
- **Bloqueado (Ox)**: depende de una decision abierta de la seccion 14 de este documento o de la 11.2 de `logica-negocio-empresa.md`.

Capa: BE (backend), FE (frontend), BD (migracion o datos), GW (gateway), TEST.

## 1. Resumen por area

| Area | Prefijo | Items |
|---|---|---|
| Seguridad y acceso | S | 8 |
| Politica de permisos y API | P | 8 |
| Empresa | E | 8 |
| Membresia y usuarios | M | 8 |
| Turnos | T | 11 |
| Tarifas, impuestos y settings | F | 7 |
| Modulos y billing | B | 5 |
| Auditoria | A | 3 |
| Arquitectura | X | 7 |
| Operacion e infraestructura | I | 4 |
| Frontend | U | 13 |
| Pruebas | Q | 3 |

## 2. Seguridad y acceso (S)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| S1 | `switch-scope`: validar la membresia activa y derivar el rol de la membresia; solo se emiten `manager` y `worker`; nunca aceptar el rol del cliente | H1 | BE | Listo |
| S2 | Ningun endpoint de empresa acepta tokens `2fa_pending`: pasar a `get_verified_user` los cuatro endpoints que usan `get_current_user` (`routers/companies.py:245,270,304,327`) y dejar `get_current_user` solo para la verificacion del 2FA | H28 | BE | Listo |
| S3 | Aplicar `User.is_active` en login, refresh, `get_current_user` y `get_verified_user` | H2 | BE | Confirmar |
| S4 | Emision de token (login, refresh, `switch-scope`): no poner `cid` de empresa suspendida ni de empresa sin membresia activa; el caso `cid` con `role` nulo debe ser imposible | D6, 3.3 | BE | Listo |
| S5 | Comprobaciones por peticion: empresa activa y membresia activa desde BD con cache Redis de ~60 s, y rol leido de la membresia, no del claim | D14, H4, H11 | BE | Confirmar (rol desde membresia) |
| S6 | Dejar de leer `is_admin` del token: leer `users.role` de BD | respuestas 2.1 | BE | Confirmar |
| S7 | Eliminar el registro publico `POST /users/`; dejar solo `POST /users` (PA); estandarizar las rutas sin barra final (con y sin barra son rutas distintas en FastAPI); revisar que ninguna respuesta devuelva un schema con `password` | H29 | BE | Listo |
| S8 | Verificar el `.env` de produccion respecto al bypass de login de desarrollo y hacer que la app no arranque con el bypass activo en produccion | H27 | BE | Confirmar |

## 3. Politica de permisos y API (P)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| P1 | Politica unica de permisos: una dependencia que resuelva actor, empresa, membresia, rol, bypass del PA, empresa activa y modulo, con el orden de comprobaciones de `logica-negocio-empresa.md` 3.2. Sustituye los `if not is_platform_admin and ...` repetidos en cada handler | D20, 2.1, 2.5 | BE | Listo (direccion) |
| P2 | Aplicar la matriz de permisos objetivo: pasan a **solo PA** `POST/PUT /companies` (todos los campos), `GET /companies`, `members/add`, `members/{uid}/status`, cambio de rol, `reset-password-email` | D2 a D4, D19 | BE | Listo |
| P3 | Las funciones sensibles de `crud` reciben empresa y actor y filtran por ellos, sin confiar en el router: `delete_work_log`, `update_work_log` (grupo), `get_company`, `update_company` | H8, 10.7, 2.5 | BE | Listo |
| P4 | Unificar el criterio de PA: `GET /work-logs` usa solo `is_platform_admin` y las escrituras tambien aceptan `role == admin` | H25 | BE | Listo (resuelto por P1) |
| P5 | `require_module` en los endpoints de pago: parte diario, billing avanzado, informes | H33, 2.7 | BE | Listo |
| P6 | Dividir `PUT /companies/{id}/members/{uid}` en endpoints propios: rol (solo PA), tarifas, ajustes propios, orden. El rol deja de viajar en los payloads; se identifica al usuario por id y se consulta su rol | D3, respuestas 2.7 | BE | Listo |
| P7 | Dos respuestas de empresa: reducida (worker, manager y PA) y completa (manager solo lectura y PA). Incluye corregir `GET /users/me/companies` para el PA, que omite `is_active` e `is_managed` | D5, H12, H23 | BE | Bloqueado (O5) |
| P8 | `GET /users/{id}/companies`: devolver solo las empresas que comparte con el solicitante (o dejarlo solo para PA) | H13 | BE | Confirmar |

## 4. Empresa (E)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| E1 | Validar `name`: sin espacios sobrantes, minimo 1, maximo definido; rechazar `null` y cadena vacia (hoy `null` da probablemente 500). Longitud maxima en la columna requiere migracion | H18 | BE, BD | Listo |
| E2 | `fiscal_id` obsoleto: inventariar todas las referencias (seed, dialogo de alta, tarjetas, pagina de modulos, mapper, `CompanyResponse`), retirarlas, mantener la columna nullable y borrarla en una migracion posterior | D10 | BE, FE, BD | Listo |
| E3 | Alta de empresa: exigir `tax_config` completo, sin default | respuestas 2.2 (default de `tax_config`), H19 | BE | Listo |
| E4 | Nuevo `DELETE /companies/{id}` (solo PA): permitido solo si no hay nada asociado (miembros, turnos, suscripciones, usuarios con `default_company_id`); sin cascadas; 409 con el motivo; auditado | D8 | BE | Listo |
| E5 | Suspension y reactivacion: registrar actor, fecha y motivo | D8, D17 | BE | Listo (depende de A1) |
| E6 | Cambio de `is_managed`: solo PA, auditado, sin recalculo | D12 | BE | Listo (depende de A1) |
| E7 | Documentar el procedimiento para recuperar una empresa sin manager (el PA anade un manager o cambia el rol de un worker) y corregir la seccion 10.1 del analisis original | respuestas 3 | Docs | Listo |
| E8 | Rechazar `{}` y payloads sin cambios de forma coherente en `PUT /companies/{id}` | analisis 4 | BE | Confirmar |

## 5. Membresia y usuarios (M)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| M1 | Eliminar una membresia (solo PA): solo si no tiene turnos ni nada asociado; si los tiene, queda inactiva; sin cascadas; auditado | 2.6 | BE | Listo |
| M2 | Desactivar membresia: reasignar `default_company_id` a otra membresia activa o a nulo; comprobar que ocurre en todos los caminos | 2.6, 10.2 | BE | Listo |
| M3 | Validar `default_company_id` contra membresia activa al escribirlo (`PUT /users/me` y administracion) | H24 | BE | Listo |
| M4 | `PUT /users/me` no debe sobrescribir nombres con `None` (`UserSelfUpdate(**user.dict())`) | H24 | BE | Listo |
| M5 | `get_company_member` debe filtrar membresias activas; un miembro inactivo no calcula con su tarifa | 10.2 | BE | Listo (depende de T1) |
| M6 | `members/add` solo PA; si reactiva a un miembro, definir si conserva el rol previo o vuelve a worker | H10 | BE | Bloqueado (O8) |
| M7 | `POST /users` (PA) con `company_id`: validar que la empresa existe y esta activa antes de `join_company` | analisis 4.2 | BE | Confirmar |
| M8 | Revisar `crud.create_user`, que busca la empresa "Personal" por nombre, una vez eliminado el registro publico | respuestas 2.2 | BE | Confirmar |

## 6. Turnos (T)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| T1 | Validar membresia activa del usuario del turno al crear (individual, lote y PA incluidos) | D11, H3 | BE | Listo |
| T2 | Worker no crea turnos en empresa gestionada: 403 con mensaje claro | D1, H6 | BE | Listo |
| T3 | `PUT /work-logs/{id}` no cambia `company_id` ni `user_id`: rechazar con 422 | H7 | BE | Listo |
| T4 | `group_id` generado por el servidor y `apply_to_group` acotado a la empresa del turno | H8 | BE | Confirmar |
| T5 | Recalculo al editar: conservar el importe si no cambian tipo, horas ni fechas; si cambian, recalcular con el `calculation_snapshot` del turno; la tarifa vigente solo como accion explicita | H31 | BE | Listo |
| T6 | Validaciones de dominio: `inicio <= fin`, rango razonable de fechas, UUID invalidos y estados libres devuelven 422 y no 500; `limit` con tope | 2.4, H18 | BE | Listo |
| T7 | Solapes de turnos del mismo trabajador | 2.4 | BE | Bloqueado (O3) |
| T8 | `company_id` NOT NULL en `work_logs`: comprobar los turnos sin empresa en BD, asignar empresa o resolverlos, migracion reversible con backfill | D13 | BD, BE | Listo (precondicion de datos, ver seccion 15) |
| T9 | Con empresa suspendida, bloquear listado de turnos y billing (hoy permitidos) | D6, 5.3 | BE | Listo (resuelto por P1 y S5) |
| T10 | Endpoint propio para el parte diario que devuelva solo lo que necesita; deja de usarse `/companies/detailed` y el listado con modulo por parte de un worker | 2.7 | BE | Listo |
| T11 | Dashboard de empresa: la lectura de Redis queda dentro del `try` y el endpoint funciona sin cache si Redis falla (hoy da 500); misma forma de respuesta en cache y en fallo de cache. Los totales frente al desglose con miembros inactivos (H21) quedan por decidir | H22, H21 | BE | Confirmar (H21: O6) |

## 7. Tarifas, impuestos y settings (F)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| F1 | Modelo `TaxConfig` en backend: claves `social_security`, `irpf_base`, `extra`, valores entre 0 y 1, **0 valido**, clave ausente o tipo incorrecto rechazado al escribir, sin defaults de modelo, schema ni UI; manejar `tax_overrides: null` | H19, D18 | BE | Listo (nombre de clave IRPF: O9) |
| F2 | Modelo `CompanySettings` en backend con defaults, tipos y `extra="forbid"`; el frontend deja de tener defaults (`use-company-settings.ts`) | 2.2 | BE, FE | Listo |
| F3 | Retirar `allow_tutorial`, `allow_coordination` y `settings.is_managed` del catalogo, e inspeccionar y migrar los `settings` reales de la BD antes de activar `extra="forbid"` | 2.2 | BE, BD | Listo (depende de F2 y de la seccion 15) |
| F4 | Contrato de `worklog_definitions` (`unit`, `is_range`, `label`, `fields`) y de `rates_config` | 2.2 | BE | Confirmar |
| F5 | Defaults mutables de `Column(JSONB, default={...})`: pasar a callables | H20 | BE | Confirmar |
| F6 | Analizar si los `settings` de membresia aportan algo y como usarlos | 2.2 | Analisis | Bloqueado (O10) |
| F7 | Ajustar el catalogo de settings al borrar claves; el dato de empresa solo lo edita el PA (ver P2) | D4 | BE | Listo |

## 8. Modulos y billing (B)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| B1 | Separar billing en dos niveles: basico (suma de lo trabajado y generado, sin modulo) y avanzado (porcentajes, tendencias, analitica, tras el modulo) | 2.7 | BE, FE | Bloqueado (O11) |
| B2 | `GET /modules/me` y `require_module` ignoran los modulos de la empresa si esta suspendida | D6, 2.7 | BE | Listo |
| B3 | Validar `scope`, `target_scope` y `status` en suscripciones (un `PUT` con estado invalido da 500); decidir si se impiden duplicados empresa+modulo | analisis 4.1 | BE | Confirmar |
| B4 | Eliminar `crud.get_subscriptions` (sin uso) | analisis 2.2 | BE | Listo |
| B5 | Definir el modulo y el endpoint del parte diario junto con T10 | 2.7 | BE | Listo |

## 9. Auditoria (A)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| A1 | Ampliar `audit_logs` (quien, cuando, accion, empresa, valor anterior y nuevo, motivo) y registrar: alta, suspension y reactivacion de empresa; cambio de `is_managed`; alta, baja y reactivacion de membresia; cambio de rol; cambio de tarifa; cambios de `tax_config` y `settings`; borrado de empresa y de membresia | D17 | BE, BD | Listo |
| A2 | Endpoint de lectura de logs solo para PA, con filtros (empresa, usuario, tipo, fechas), y pantalla de administracion | D17 | BE, FE | Listo (posterior a A1) |
| A3 | Trigger de `updated_at` en PostgreSQL | respuestas 2.2 | BD | Confirmar (no prioritario) |

## 10. Arquitectura (X)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| X1 | Completar `backend/src/` como API v2 en paralelo, manteniendo `crud.py` y su API mientras se prueba la nueva. Incluye alinear el dominio con la BD (la entidad `Company` no tiene `is_active`, `is_managed` ni `updated_at`) y tests de paridad entre v1 y v2 | D20 | BE | Bloqueado (O4) |
| X2 | La politica central de permisos (P1) debe poder usarse desde v1 y v2 para que las reglas no se dupliquen | P1 | BE | Listo |
| X3 | Renombrados de la API que rompen contrato (`/companies/detailed` a `?include=members`, `rates-v2` a un nombre sin sufijo, solape de `/members` con `detailed`): hacerlos en v2, no en v1 | 2.7 | BE | Confirmar |
| X4 | Dividir `crud.py` (1257 lineas) por areas (opcion B). Decidir si se hace o se limita a lo necesario, dado que v2 lo sustituira | D20 | BE | Bloqueado (O4) |
| X5 | Valorar si Python es el mejor lenguaje del backend (ver seccion 14) | respuestas 2.5 | Analisis | Bloqueado (O4) |
| X6 | RLS de PostgreSQL por `company_id` con el PA exento: `SET LOCAL app.company_id` por transaccion, `work_logs` y `company_members` primero, revisar funciones SQL como `get_billing_summary` y el usuario de migraciones | D13 | BD, BE | Bloqueado (O1; despues de P1 y T8) |
| X7 | La API v2 serializa en `snake_case` (sin `alias_generator=to_camel`), de modo que BD, dominio, JSON y tipos del frontend usan los mismos nombres. v1 sigue en `camelCase` mientras exista. El cliente del frontend para v2 se tipa con `snake_case`; migrar pantallas a v2 de una en una | conversacion 2026-10-16 | BE, FE | Confirmar |

## 11. Operacion e infraestructura (I)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| I1 | Seed: quitarlo del arranque (`main.py:102-108`); solo al crear la BD y solo si no hay usuarios (o ningun PA), por `./bin/seed`. Unificar el rol que asignan `seed` (`manager`) y `dev_seed` (`CompanyRole.admin`) | 2.3, 10.1 | BE | Listo |
| I2 | Sustituir los `print` de depuracion por `logging` con nivel y sin datos sensibles (`routers/companies.py:70,340-343,348`, `crud.py:841,848`); los 403 no devuelven `is_manager`, `is_self` ni ids de usuario | H16 | BE | Listo (Confirmar el alcance de los 403) |
| I3 | Rate limit: `limit_req_zone` en Nginx, estricto para `/api/auth/` y mas laxo para el resto de la API; valorar limites por endpoint | H30 | GW | Listo |
| I4 | Unificar las respuestas 404 y 403 para no permitir enumerar ids de empresa (varios endpoints devuelven 404 antes de autorizar y los 403 distinguen la empresa suspendida) | H17 | BE | Confirmar |

## 12. Frontend (U)

Solo despues de que el backend este definido y probado (P5), con la salvedad de la seccion 14 (restricciones transversales).

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| U1 | Interceptor unico de errores en `api.ts` que mapee 401, 403, 404, 409, 422 y 5xx a una notificacion con el `detail` del backend; los toasts por mutacion dejan de usar mensajes fijos | 2.10, H26 | FE | Confirmar |
| U2 | Ocultar todo lo que el backend ya prohibe segun la matriz: guarda de rol en la pagina de administracion y en `/manager/*`, switches, acciones de alta, edicion y borrado en `/list` segun `is_managed` y rol | analisis 8 | FE | Listo |
| U3 | Boton al listado de empresas solo para PA; los demas usan `/users/me/companies` | respuestas 2.10 | FE | Listo |
| U4 | Empresa suspendida: mensaje especifico, el selector no la ofrece, un 403 al listar no se muestra como lista vacia | analisis 8 | FE | Listo |
| U5 | Confirmacion al suspender, reactivar y cambiar `is_managed` | analisis 8 | FE | Listo |
| U6 | Retirar lo obsoleto: `settings.is_managed` y `(currentCompany as any)?.is_managed` (`CompaniesPageClient.tsx:137,262`, `profile/page.tsx:94-95`), `company-settings-dialog.tsx` sin uso, defaults de settings, `allow_tutorial` y `allow_coordination` | analisis 2.2 | FE | Listo (depende de F2 y F3) |
| U7 | `profile/page.tsx`: las tarifas pasan a editables solo si se confirma que la empresa es autonoma (hoy falla abierto si la empresa no esta en la lista) y se lee `is_managed` | analisis 8 | FE | Listo |
| U8 | Empresa en la URL (`?companyId=`) segun la decision tomada | H32 | FE, BE | Bloqueado (O2) |
| U9 | Quitar `fiscal_id` de formularios, tarjetas y paginas; permitir editar el `name` | D10 | FE | Listo (ver nota de la seccion 14) |
| U10 | Toasts del alta en espanol; sacar del JSX el correo de contacto fijo; tipar `updateCompany` (hoy `any`) y `tax_config`; validar NaN en el editor de JSON | analisis 8 | FE | Confirmar |
| U11 | El manager deja de ver los editores de `tax_config`, `worklog_definitions` y `settings` (hoy los edita); solo PA | D4, H14 | FE | Listo |
| U12 | Validaciones de negocio del frontend (fechas, etc.) quedan como aviso previo; la fuente es el backend | respuestas 2.4 | FE | Listo |
| U13 | Consumir el endpoint propio del parte diario (T10) y la pantalla de logs de PA (A2) | 2.7, D17 | FE | Listo (depende de T10 y A2) |

## 13. Pruebas (Q)

| ID | Cambio | Origen | Capa | Estado |
|---|---|---|---|---|
| Q1 | Casos que hoy no existen, cada uno con un test que falle antes del arreglo: aislamiento entre empresas (dashboard, billing, turnos, miembros, modulos); escalada por `switch-scope`; worker crea turno en gestionada y en autonoma; PA sobre empresa suspendida; manager cambia `is_active` o `is_managed` (ahora 403); manager desactiva miembros (ahora 403); `is_managed` de true a false; tokens `2fa_pending`, `impersonated` y caducado; usuario o membresia desactivados con token vigente | H15, analisis 11 | TEST | Listo |
| Q2 | Entorno de test: `cd backend && pytest tests/` no ejecuta los ocho ficheros de la raiz; moverlos a `tests/` o configurar `pytest.ini`, actualizar el comando en `CLAUDE.md`; `test_governance.py` fuerza SQLite al importarse y hace `commit` sin rollback; `test_rates.py` no es un test (consulta la BD al importarse) | analisis 11 | TEST | Listo |
| Q3 | Pruebas de paridad entre `crud.py` y `src/` para la API v2 | D20 | TEST | Bloqueado (O4) |

## 14. Notas para el plan

### Decisiones abiertas que bloquean items

| Id | Bloquea |
|---|---|
| O1 (RLS) | X6 |
| O2 (empresa en la URL) | U8 |
| O3 (solapes) | T7 |
| O4 (capa `src/`, lenguaje) | X1, X3, X4, X5, Q3 |
| O5 (vista reducida del worker) | P7 |
| O8 (reactivar membresia) | M6 |
| O10 (settings de membresia) | F6 |
| O11 (billing avanzado) | B1 |
| O9 (clave IRPF) | F1 (detalle) |
| O6 (totales del dashboard con miembros inactivos, H21) | Parte de T11 |

El detalle de cada una esta en `logica-negocio-empresa.md`, seccion 11.2.

### Contradiccion que hay que resolver antes de planificar

En `respuestas-a-comentarios.md` la seccion 1 dice "Editar `name` y `fiscal_id` en la UI: OK", pero D10 dice que `fiscal_id` es obsoleto y se quita de formularios. Este catalogo asume que **solo se edita el `name`** (U9). Hay que confirmarlo.

### Valoracion de Python como lenguaje del backend (X5)

Pregunta del usuario en las respuestas. Valoracion para decidir, no una decision.

| Ventajas de Python | Desventajas |
|---|---|
| FastAPI, Pydantic, SQLAlchemy y Alembic cubren este tipo de aplicacion (CRUD multiempresa con reglas de negocio) y ya estan en uso | Tipado dinamico: errores que otros lenguajes detectan al compilar aparecen en ejecucion. Se mitiga con tipado estricto y `pyright` o `mypy` en CI |
| La carga es de E/S (BD, Redis), donde Python rinde bien; no hay calculo intensivo | Peor rendimiento en tareas de CPU y el GIL limitan el paralelismo dentro de un proceso |
| Ecosistema amplio, contratacion sencilla, el codigo existente ya esta escrito | Dos lenguajes en el proyecto (Python y TypeScript) impiden compartir tipos con el frontend |
| Reescribir tendria un coste alto y sin valor visible para el usuario | Los problemas detectados en este analisis (validaciones ausentes, reglas repartidas, permisos duplicados) son de arquitectura y no del lenguaje: un cambio de lenguaje no los resolveria |

Recomendacion: mantener Python y resolver los problemas con P1, X1 y el tipado en CI. Una migracion de lenguaje solo compensaria si hubiera un requisito concreto de rendimiento o de compartir codigo con el frontend, y hoy no lo hay.

### Restricciones transversales para el plan

- **Orden:** backend primero y frontend despues (P5). Las restricciones del backend que rompen flujos que la UI actual ofrece al manager (`members/add`, estado de membresia, `reset-password-email`, editores de configuracion) deben salir en la misma entrega que su ocultacion en el frontend, o la UI mostraria errores.
- **Dependencias:** P1 antes de S5, T9 y X6; A1 antes de E5, E6 y A2; T1 antes de M5; T8 antes de X6; F2 antes de F3 y U6.
- **Contrato de API:** los cambios que rompen contrato (renombrados, nuevas respuestas) van en v2; en v1 se mantienen las rutas porque el frontend actual depende de ellas.
- **Un PR por bloque**, con un test que falle antes del arreglo (regla del analisis original).
- **Versionado SemVer** (regla 8 de `CLAUDE.md`) al final, sobre `develop` actualizado: los cambios con funcionalidad o correccion incrementan version en `package.json`, `frontend/package.json` y `CHANGELOG.md`.
- **Revision:** `code-reviewer` siempre; `security-reviewer` para S y P; `database-reviewer` para migraciones (T8, E1, E2, A1, A3, X6, F3); migraciones Alembic reversibles.
- **Datos de produccion:** nunca lanzar `./scripts/sync_db.sh` por iniciativa propia; las comprobaciones de la seccion 15 las ejecuta quien tenga acceso.

## 15. Comprobaciones de datos previas (solo lectura)

Consultas a ejecutar sobre la BD antes de planificar las migraciones. Ninguna modifica datos.

| Para | Que comprobar |
|---|---|
| T8 | Numero de `work_logs` con `company_id` nulo y a que usuarios pertenecen |
| T1, M5 | Turnos cuyo usuario no tiene membresia en la empresa del turno |
| P1, S1 | Membresias con rol `admin`: cuantas hay y de quien |
| E7 | Empresas sin ningun manager |
| M3 | Usuarios cuyo `default_company_id` no corresponde a una membresia activa |
| M8 | Si existe una empresa llamada "Personal" y cuantos usuarios tiene |
| F1, F3 | Contenido real de `tax_config` y `settings`: claves ausentes, `irpf` frente a `irpf_base`, `allow_tutorial`, `allow_coordination`, `is_managed` |
| B3 | Suscripciones duplicadas por empresa y modulo, y con `status` fuera de los valores validos |
| E2 | Empresas con `fiscal_id` informado (para decidir el borrado de la columna) |
