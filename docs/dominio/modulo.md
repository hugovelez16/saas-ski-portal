# Modulo

Prefijo: `R-MOD`. Tablas: `app_modules` y `module_subscriptions`. Modelos: `AppModule` y
`ModuleSubscription` (`backend/models.py`).

Un [modulo](../glosario.md) es una funcionalidad de pago del catalogo de la plataforma. Una
[suscripcion](../glosario.md) lo asigna a una empresa. Este fichero sustituye a la seccion 8 de
`logica-negocio-empresa.md`, que queda como historico; donde contradiga a
[revision-base.md](../producto/revision-base.md) (P9, P10, P17, S9) manda este.

Las reglas de acceso se enlazan, no se repiten (`acceso.md`): R-ACC-19 (empresa suspendida),
R-ACC-24 (guardia de modulo) y R-ACC-78 (parte diario del worker). "Billing basico" (pagina de
facturacion y costes) no es un modulo: sus reglas estan en `R-TAR`.

## Campos

`AppModule` (catalogo):

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `id` | UUID | Si | Identificador |
| `code_name` | texto | Si | Codigo unico del modulo (`worker_daily_report`, `reports`) |
| `name` | texto | Si | Nombre para mostrar |
| `description` | texto | No | Descripcion |
| `is_active` | booleano | Si | Si es false no se puede contratar ni cuenta como valido. Por defecto true |
| `target_scope` | texto | No | **Retirada (R-MOD-18).** Se elimina |
| `price_monthly` | decimal | No | **Retirada (R-MOD-18).** Se elimina |

`ModuleSubscription`:

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `id` | UUID | Si | Identificador |
| `module_id` | UUID | Si | Modulo contratado |
| `company_id` | UUID | Si | Empresa suscrita (aislamiento) |
| `user_id`, `scope` | UUID, enum | No | **Retiradas (R-MOD-17).** Solo hay suscripciones de empresa |
| `status` | enum | Si | `active`, `trial`, `cancelled` o `expired`; por defecto `active` |
| `expires_at` | fecha y hora | No | Vencimiento; nulo = no vence |
| `notes` | texto | No | Notas del PA (por ejemplo, motivo o referencia de pago) |
| `created_at`, `updated_at` | fecha y hora | No | Alta y ultima modificacion |

## Reglas

### Catalogo

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MOD-01 | `code_name` es unico en el catalogo; crear un modulo con un `code_name` existente es un error | Cerrado | 8 | `backend/models.py:AppModule`, `backend/routers/modules.py:create_module` (responde 400) |
| R-MOD-02 | Solo el PA crea y edita modulos del catalogo; el manager y el worker reciben 403 | Cerrado | 8, matriz de revision-base.md | `backend/routers/modules.py:_require_admin` |
| R-MOD-03 | Los modulos vendidos y vigentes son dos: `worker_daily_report` (con `name` y `description` de "Cuadrante compartido" en el catalogo) e Informes (`reports`). El modulo de notificaciones push (`push_notifications`) se crea ya en el catalogo como inactivo (`is_active = false`) | Cerrado | P17, O26, Repaso 2026-11-25; `planes-y-precios.md` | `backend/migrations/versions/2314c15d1a0f_seed_default_modules.py`, `0fb22f01dd7d_seed_billing_and_reports_modules.py`; nombre y `push_notifications`: pendiente de implementar (issue de seguimiento) |
| R-MOD-04 | `billing` no es un modulo del catalogo hasta el billing avanzado (O11); se retira del catalogo y del menu | Cerrado | P17 | menu retirado en `frontend/src/app/(app)/layout.tsx`; catalogo en BD pendiente de migracion (#142): `0fb22f01dd7d_seed_billing_and_reports_modules.py` siembra `billing` |
| R-MOD-05 | Un modulo con `is_active = false` no vale como modulo contratado y no se puede suscribir | Cerrado | 8, Repaso 2026-11-25 | `backend/crud.py:user_has_module` (ignora el inactivo); pendiente de implementar (issue de seguimiento): el alta de suscripcion no lo comprueba |
| R-MOD-06 | Cualquier usuario verificado lista el catalogo activo; solo el PA ve tambien los inactivos | Cerrado | 8, Repaso 2026-11-25 | `backend/routers/modules.py:list_modules` |

### Suscripciones

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MOD-07 | Una suscripcion une una empresa y un modulo, con `status`, `expires_at` (opcional) y `notes` | Cerrado | 8, P10 | `backend/models.py:ModuleSubscription` |
| R-MOD-08 | Solo el PA crea, cambia o cancela suscripciones; el manager y el worker reciben 403 | Cerrado | 8, matriz | `backend/routers/modules.py:create_subscription`, `update_subscription` |
| R-MOD-09 | Cancelar una suscripcion es pasarla a `cancelled`; el registro se conserva | Cerrado | 8, Repaso 2026-11-25 | pendiente de implementar (issue de seguimiento): hoy existe tambien `DELETE /modules/subscriptions/{sub_id}`, que borra la fila |
| R-MOD-10 | El manager lista solo las suscripciones de su empresa activa (sin datos de usuario) y no las modifica | Cerrado | 8, matriz | `backend/routers/modules.py:list_subscriptions` |
| R-MOD-11 | Una suscripcion `active` o `trial` y no vencida es vigente; `cancelled`, `expired` o con `expires_at` pasado no valen | Cerrado | 8 | `backend/crud.py:user_has_module` |
| R-MOD-12 | Crear o reactivar una suscripcion `active` o `trial` de la misma empresa y modulo que otra vigente responde 409 | Cerrado | 8 | `backend/crud.py:_ensure_no_live_duplicate` |

### Guardia y modulos efectivos

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MOD-13 | Un endpoint de modulo responde 403 si la empresa activa no tiene el modulo vigente; el PA actuando pasa | Cerrado | 3.2 n.8, R-ACC-24 | `backend/routers/deps.py:require_module`, `deps.authorize` (`module=`); pendiente de implementar (issue de seguimiento): hoy cuenta tambien el modulo del usuario (R-MOD-17) |
| R-MOD-14 | `worker_daily_report` se exige en el backend en los endpoints del parte diario | Cerrado | P17, R-ACC-78 | `backend/routers/companies.py` (`require_company(..., module="worker_daily_report")`) |
| R-MOD-15 | `reports` se exige en el backend en los datos del modulo Informes | Cerrado | P17 | `backend/routers/work_logs.py:get_work_logs_report` (`deps.authorize(..., module="reports")`) |
| R-MOD-16 | Los modulos efectivos de una sesion son los de la empresa activa del token; si la empresa esta suspendida, no hay ninguno (R-ACC-19) | Cerrado | R-ACC-19, P10 | `backend/routers/modules.py:get_my_modules`; pendiente de implementar (issue de seguimiento): hoy suma los modulos del usuario y, sin empresa en contexto, el PA recibe todos los activos |

### Retiradas

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MOD-17 | **Retirada.** Las suscripciones de usuario (`scope = user`, `user_id`) se eliminan definitivamente: tambien en el alta publica B2C los modulos se contratan como suscripcion de la empresa del usuario (R-ACC-06) | Retirada | P10, O16, Repaso 2026-11-25 | pendiente de implementar (issue de seguimiento): `SubscriptionScope.user` y el alta de usuario siguen vivos |
| R-MOD-18 | `AppModule.target_scope` y `AppModule.price_monthly` se eliminan | Retirada | P10, S9 | pendiente de implementar (issue de seguimiento): siguen en `backend/models.py` |
| R-MOD-19 | `settings.modules` se elimina: la unica fuente de modulos contratados es `module_subscriptions` | Retirada | P9, S9 | pendiente de implementar (issue de seguimiento): `frontend/src/app/(app)/manager/daily-reports/page.tsx` aun lee `settings.modules` |

### Planes, limites y cobro

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-MOD-20 | Pista Verde paga Cuadrante compartido (5 EUR/mes) e Informes (15 EUR/mes); Azul y Roja los incluyen | Cerrado | `planes-y-precios.md` | no aplica en codigo |
| R-MOD-21 | Un modulo nuevo no queda incluido en ningun plan automaticamente: su precio por plan se decide al lanzarlo | Cerrado | `planes-y-precios.md` | no aplica en codigo |
| R-MOD-22 | Cada empresa tiene un plan asignado en el portal (en fase 0 lo fija el PA; si es personalizado, el PA escribe sus numeros); Odoo recibe el plan desde el portal para facturar y no es la fuente de verdad del plan | Cerrado | O12, O26, Repaso 2026-11-25, Cobros 2026-11-25 (C6) | pendiente de implementar (fase 0) |
| R-MOD-23 | El recuento facturable de monitores y responsables de un mes natural es el maximo de miembros activos simultaneamente en ese mes; desactivar a uno antes de activar a otro no incrementa el pico, pero activar primero y desactivar despues si suma ese mes | Cerrado | Cobros 2026-11-25 (C1) | pendiente de implementar (fase 0) |
| R-MOD-24 | Un miembro empieza a contar en el recuento del plan cuando acepta la invitacion (membresia activa), no cuando se envia la invitacion | Cerrado | Cobros 2026-11-25 (C1) | pendiente de implementar (fase 0) |
| R-MOD-25 | En planes con adicionales (Pista Verde y Pista Azul), el manager puede superar los monitores o responsables incluidos tras confirmar un aviso con el coste adicional del mes; la confirmacion queda registrada en auditoria (`audit_logs`) | Cerrado | Cobros 2026-11-25 (C2) | pendiente de implementar (fase 0) |
| R-MOD-26 | Cuando el coste de los miembros adicionales del mes supera el importe del plan superior, el aviso de superacion lo indica y ofrece subir de plan | Cerrado | Cobros 2026-11-25 (C2) | pendiente de implementar (fase 0) |
| R-MOD-27 | Pista Roja tiene un tope duro de 50 monitores activos simultaneos; intentar superarlo bloquea el alta o activacion y remite a Pista Negra (a consultar) | Cerrado | Cobros 2026-11-25 (C2) | pendiente de implementar (fase 0) |
| R-MOD-28 | El manager dispone de un panel de consumo del mes en curso con su plan, adicionales, pico alcanzado e importe previsto | Cerrado | Cobros 2026-11-25 (C2) | pendiente de implementar (fase 0) |
| R-MOD-29 | El manager puede activar o desactivar el mes natural siguiente desde el portal hasta el dia 25 del mes anterior; despues aplica la configuracion que estuviera guardada | Cerrado | Cobros 2026-11-25 (C8) | pendiente de implementar (fase 3) |
| R-MOD-30 | Ante un impago o devolucion notificado por Odoo, se avisa al manager al momento; a los 5 dias la empresa pasa a solo lectura y a los 15 dias queda suspendida conservando sus datos | Cerrado | Cobros 2026-11-25 (C5) | pendiente de implementar (fase 2) |
| R-MOD-31 | El PA puede reactivar manualmente una empresa en solo lectura o suspendida por impago en cualquier momento (por ejemplo, con justificante de pago) | Cerrado | Cobros 2026-11-25 (C5) | pendiente de implementar (fase 2) |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Manager o worker crea una suscripcion o un modulo | 403 | R-MOD-02, R-MOD-08 |
| PA crea un modulo con `code_name` repetido | Error, no se crea | R-MOD-01 |
| PA crea una suscripcion `active` si la empresa ya tiene el modulo vigente | 409 | R-MOD-12 |
| La suscripcion `active` esta vencida (`expires_at` pasado) | No es vigente: 403 en la guardia; se puede crear otra | R-MOD-11, R-MOD-12 |
| Worker sin el modulo llama a un endpoint del parte diario | 403 | R-MOD-13, R-MOD-14 |
| PA actuando sobre una empresa sin el modulo | Pasa la guardia | R-MOD-13 |
| Empresa suspendida con el modulo vigente | Sin modulos efectivos; 403 en la guardia | R-MOD-16 |
| Empresa sin `reports` pide datos de Informes | 403 | R-MOD-15 |
| Modulo desactivado (`is_active = false`) con suscripcion vigente | No cuenta como contratado | R-MOD-05 |
| Se envia una invitacion a un monitor pero aun no la acepta | No suma en el pico mensual del plan | R-MOD-24 |
| Se desactiva un monitor y despues se activa otro en el mismo mes | El pico simultaneo no aumenta | R-MOD-23 |
| Manager en Pista Verde o Azul supera los incluidos | Aviso con el coste adicional (y oferta de subida si sale mas caro); al confirmar, se audita y se permite | R-MOD-25, R-MOD-26 |
| Empresa en Pista Roja intenta activar el monitor 51 simultaneo | Bloqueo; remite a Pista Negra | R-MOD-27 |
| Manager intenta cambiar el estado del mes siguiente el dia 26 | No cambia el mes siguiente; vale lo guardado hasta el dia 25 | R-MOD-29 |
| Impago sin regularizar a los 5 y a los 15 dias | Aviso inmediato, solo lectura a los 5 dias, suspension con datos conservados a los 15 dias; el PA puede reactivar en cualquier momento | R-MOD-30, R-MOD-31 |

## Relacion con otras entidades

- Empresa (`R-EMP`): la suscripcion es de empresa; suspender la empresa invalida sus modulos (R-ACC-19).
- Acceso (`R-ACC`): R-ACC-24 define la guardia; R-ACC-78 la visibilidad del worker en el parte diario.
- Turno (`R-TUR`): el parte diario es el modulo `worker_daily_report`.
- Tarifa (`R-TAR`): la pagina de facturacion y costes es billing basico, no un modulo.
