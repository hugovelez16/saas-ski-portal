# Turno

Prefijo: `R-TUR`. Tabla: `work_logs`. Modelo: `WorkLog` (`backend/models.py`).
Entidad de dominio: `backend/src/domain/entities/work_log.py`.

Un turno (work log, ver [glosario](../glosario.md)) es el trabajo de un usuario
en una empresa: tipo, fechas, horas e importes. De el salen el parte diario, el
panel y la billing basica. Las reglas de quien escribe segun el modo de empresa
estan en `acceso.md` (R-ACC-70 y R-ACC-71) y no se repiten. El calculo del
importe, las tarifas, los impuestos y la billing basica (pagina de facturacion y
costes) son de `tarifa.md` (`R-TAR`, #69). Lo historico esta en la seccion 6 de
[logica-negocio-empresa.md](../empresa/logica-negocio-empresa.md); donde
contradiga a [revision-base.md](../producto/revision-base.md) manda este
fichero. Las reglas con origen S, T o P vienen de las decisiones de la revision de base
(2026-11-22).

## Campos

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `id` | UUID | Si | Identificador |
| `user_id` | UUID | Si | Usuario del turno. No cambia al editar (R-TUR-02) |
| `company_id` | UUID | Si | Empresa del turno (aislamiento). NOT NULL; no cambia al editar (R-TUR-01, R-TUR-02) |
| `type` | texto | Si | Clave de `worklog_definitions` de la empresa (R-TUR-13) |
| `start_date`, `end_date` | fecha | Si | `inicio <= fin` y dentro del rango de R-TUR-11 |
| `start_time`, `end_time` | hora | No | Horas del turno; sin ellas el turno cubre el dia completo a efectos de solape |
| `duration` | numerico | No | Duracion en la unidad del tipo (horas, dias o fija) |
| `gross_amount`, `net_amount` | numerico | Si (R-TUR-16) | Importes guardados del turno, calculados al crear y al recalcular |
| `extra_data` | JSON | No | Extras dinamicos (`has_night`...) y `group_id` del grupo |
| `description` | texto | No | Texto libre |
| `calculation_snapshot` | JSON | No | Copia de tarifas, definiciones e impuestos usados (R-TUR-19) |
| `created_at`, `updated_at` | fecha y hora | Si | Control |

## Reglas

### Empresa y escritura

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-01 | Todo turno tiene `company_id` (NOT NULL). No existen turnos sin empresa: un turno que llega sin empresa responde 422 | Cerrado | 6.2, P2 |
| R-TUR-02 | Editar no cambia `company_id` ni `user_id` del turno: un valor distinto responde 422 | Cerrado | 6.2 |
| R-TUR-03 | Crear un turno exige membresia activa del usuario del turno en la empresa, tambien en turno propio, ajeno y en lote; si no la tiene responde 400 | Cerrado | 6.2 |
| R-TUR-04 | Crear, editar y borrar turnos propios: lo que dicen R-ACC-70 (gestionada: el worker es espectador, 403) y R-ACC-71 (autonoma: el worker escribe los suyos) | Cerrado | S7, T1 |
| R-TUR-05 | Crear, editar y borrar turnos ajenos y crear en lote solo lo hacen PA y manager, de su empresa activa. El worker recibe 403 en ambos modos | Cerrado | 6.1, matriz |
| R-TUR-06 | `apply_to_group` solo lo usan PA y manager y actua solo sobre turnos de la misma empresa | Confirmar | 6.2 |
| R-TUR-07 | El `group_id` lo genera el servidor al crear un turno para varios usuarios; el valor que mande el cliente se ignora | Confirmar | 6.2 |
| R-TUR-08 | Durante una suplantacion no hay escrituras de turnos (403, R-ACC-66). R-ACC-53 esta retirada | Cerrado | P4 |
| R-TUR-09 | En una empresa suspendida todo lo de turnos esta bloqueado (403) salvo para el PA (R-ACC-19) | Cerrado | 6.1, 3.2 |

### Validaciones

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-10 | Las fechas cumplen `inicio <= fin`, con error 422 si no. La validacion vive primero en el backend; el frontend la replica para avisar antes de enviar | Cerrado | 6.2 |
| R-TUR-11 | Las fechas estan entre 2000-01-01 y hoy + 730 dias (el manager planifica), con error 422 fuera de ese rango | Cerrado | 6.2, P-12 |
| R-TUR-12 | Un tipo con unidad `days` exige fecha de inicio y de fin. Si faltan responde 422, no se guarda un importe 0 en silencio | Cerrado | revision-base, turnos por dias |
| R-TUR-13 | El tipo del turno existe en `worklog_definitions` de la empresa (#66). Un tipo inexistente responde 400 | Cerrado | 4.4, 6.2 |
| R-TUR-14 | Un turno sin tarifa aplicable (tarifa 0 o ausente) responde 400 con mensaje claro, que el frontend muestra. Ya no hay importe manual que lo evite | Cerrado | 6.2, S6, T2 |
| R-TUR-15 | Un identificador mal formado (UUID) responde 422, nunca 500 | Confirmar | 6.2 |

### Importes

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-16 | Cada turno guarda `gross_amount` y `net_amount`. No existe `price_type`. El calculo de ambos es de `R-TAR-*` (#69) y no se repite aqui | Cerrado | S3, T5 |
| R-TUR-17 | Los importes los fija el motor de calculo del servidor, nunca el cliente | Cerrado | S6 |
| R-TUR-18 | **Retirada (S6, T2).** El importe manual y `allow_manual_amount` desaparecen: no se crea ni se edita un turno con importe manual. Los turnos antiguos con `calculation_snapshot.type = manual_override` se siguen leyendo sin migrar | Retirada | S6, T2 |
| R-TUR-19 | Editar un turno sin cambiar tipo, horas ni fechas conserva el importe. Si cambian, se recalcula con las tarifas del `calculation_snapshot` del propio turno | Cerrado | 6.2, T3 |
| R-TUR-20 | "Recalcular" con la tarifa vigente es una accion explicita propia, no un efecto de editar | Cerrado | T3 |
| R-TUR-21 | Al cambiar de tipo o recalcular, el sistema avisa antes de guardar con el importe actual frente al nuevo, y exige confirmacion | Cerrado | T3 |
| R-TUR-22 | Unidad "libre" (precio obligatorio, fecha de inicio obligatoria con fin = inicio, horas opcionales): el precio se trata segun el bruto/neto del miembro y solo lo crea quien puede escribir turnos. Futura, issue aparte; ver R-EMP-44 | Abierto (O18) | S6 |

### Solapes

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-23 | Dos turnos del mismo trabajador que se solapan estan permitidos: el backend crea el turno (201) y devuelve `warnings`, que el frontend muestra. Sin hora de inicio el turno empieza a las 00:00; sin hora de fin acaba al final del dia; los contiguos (fin == inicio) no solapan; editar un turno no lo solapa consigo mismo | Cerrado | 6.2, O3 |

### Listados, agregados y visibilidad

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-24 | `limit` de un listado de filas tiene un maximo de 2000, con 422 si se supera. El limite solo aplica a listados de filas | Cerrado | 6.2, P-12 |
| R-TUR-25 | Toda suma o metrica la calcula el backend sobre el rango completo, nunca el frontend sumando filas. Las sumas son por columna: `gross_amount` y `net_amount` por separado | Cerrado | 6.2, S3 |
| R-TUR-26 | Los listados de filas devuelven el total de filas que cumplen el filtro (sin `skip` ni `limit`) en la cabecera `X-Total-Count` | Cerrado | 6.2 |
| R-TUR-27 | Los totales y el desglose incluyen a los miembros inactivos, marcados como inactivos | Cerrado | O6 |
| R-TUR-28 | El worker ve todos sus turnos. PA y manager ven los de toda su empresa activa. El worker no ve turnos ajenos salvo en el parte diario (R-TUR-31) | Cerrado | matriz, S8 |
| R-TUR-29 | El panel muestra siempre importe bruto y neto, sin elegir tipo de precio | Cerrado | S3 |
| R-TUR-30 | La billing basica (pagina de facturacion y costes) no se rige por este fichero: ver `R-TAR` (#69) | Cerrado | P17 |

### Parte diario

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-31 | El parte diario (modulo `worker_daily_report`) lista los miembros activos (y los inactivos con turno ese dia) y los turnos del dia de toda la empresa. El modulo se exige en backend (#70) | Cerrado | 8 (parte diario) |
| R-TUR-32 | PA y manager reciben los importes. El worker recibe descripcion, horas y tipo de los turnos ajenos, sin claves de importe y sin poder abrir el detalle (R-ACC-62, R-ACC-78) | Cerrado | S8 |

### Aplazado

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-TUR-33 | Aprobacion de turnos y cierre de periodo: aplazados a un modulo futuro | Abierto (O24) | 6.2, 10 |
| R-TUR-34 | En empresa gestionada el worker acepta la asignacion de turnos, y el plus admite cantidad editable por turno (nocturnidad = dias - 1, "2 festivos"). Futuro | Abierto (O24) | S7, S5 |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Crear turno para un usuario sin membresia activa en la empresa | 400 | R-TUR-03 |
| Worker de empresa gestionada crea su propio turno | 403 | R-TUR-04 |
| Manager edita un turno de otra empresa | 403 | R-TUR-05 |
| PUT con `company_id` o `user_id` distinto del guardado | 422 | R-TUR-02 |
| Turno por dias sin fecha de fin | 422, no un importe 0 | R-TUR-12 |
| `end_date` anterior a `start_date`, o fecha en el ano 2062 | 422 | R-TUR-10, R-TUR-11 |
| Tipo con `base_rate` 0 | 400 | R-TUR-14 |
| Editar solo la descripcion de un turno | El importe no cambia | R-TUR-19 |
| Turno que solapa con otro del mismo trabajador | 201 con `warnings` | R-TUR-23 |
| `limit=5000` en un listado | 422 | R-TUR-24 |
| Turno antiguo con `manual_override` | Se lee con su importe; no se migra | R-TUR-18 |
| Worker con el modulo abre el detalle de un turno ajeno | No hay detalle, solo descripcion, horas y tipo | R-TUR-32 |
| PA suplantando a un worker crea un turno | 403 de solo lectura | R-TUR-08 |

## Relacion con otras entidades

- Acceso (`R-ACC`): R-ACC-19, 62, 66, 70, 71 y 78 se enlazan, no se repiten.
- Empresa (`R-EMP`): `worklog_definitions` define los tipos (R-EMP-43, R-EMP-44).
- Membresia (`R-MEM`): la membresia activa condiciona crear (R-TUR-03).
- Tarifa (`R-TAR`): importes, impuestos y billing basica.
- Modulo (`R-MOD`): `worker_daily_report`.
- Auditoria (`R-AUD`): O21 decide si se audita toda escritura de turnos.

## Codigo

Diferencias con el codigo actual, cada una con issue de seguimiento:

| Regla | Hoy en el codigo | Codigo |
|---|---|---|
| R-TUR-01 | `work_logs.company_id` es `nullable=True` en `backend/models.py`; el schema `WorkLogInput` ya exige empresa, pero `_authorize_work_log_write` aun tiene la rama de turno sin empresa | pendiente de implementar (issue de seguimiento) |
| R-TUR-12 | No se exige la fecha en unidad `days`; el importe sale 0 | pendiente de implementar (issue de seguimiento) |
| R-TUR-14, R-TUR-18 | `amount` y `net_amount` de `WorkLogInput`, `keep_manual_amount` y el 409 `manual_amount_choice` siguen en `crud.py` y `routers/work_logs.py` | pendiente de implementar (issue de seguimiento) |
| R-TUR-16 | `gross_amount` y `net_amount` existen en `WorkLog`; `settings.price_type` sigue en la vista del dashboard | pendiente de implementar (issue de seguimiento) |
| R-TUR-20, R-TUR-21 | Recalcular con tarifa vigente existe solo dentro del dialogo de importe manual; no hay aviso con importe actual frente a nuevo | pendiente de implementar (issue de seguimiento) |
| R-TUR-13 | Un tipo que no esta en `worklog_definitions` no se rechaza: `crud.create_work_log` usa la unidad `hours` por defecto | pendiente de implementar (issue de seguimiento) |
| R-TUR-12 | La rama `duration_hours` de `calculate_dynamic_work_log` no se alcanza desde la API | pendiente de implementar (issue de seguimiento) |
| R-TUR-08 | La suplantacion escribe y `record_impersonation_audit` registra las escrituras | pendiente de implementar (issue de seguimiento) |
| R-TUR-23 | `crud.py:_overlap_warnings` y `work_log_rules.py:find_overlaps` | Implementado |
| R-TUR-24, R-TUR-26 | `Query(100, ge=1, le=2000)` y `X-Total-Count` en `read_work_logs` | Implementado |
| R-TUR-32 | `routers/companies.py:read_daily_report` con `DailyReportFullResponse` y `DailyReportWorkerResponse` | Implementado |
