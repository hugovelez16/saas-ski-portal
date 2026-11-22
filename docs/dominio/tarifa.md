# Tarifa

Prefijo: `R-TAR`. Tabla: `company_members` (columna `rates_config`). Modelo: `CompanyMember` (`backend/models.py`).
Valores de dominio: `backend/src/domain/value_objects/rate_definition.py`, `tax_configuration.py` y
`calculation_snapshot.py`; motor: `backend/src/domain/services/work_log_calculation_service.py`.

La tarifa ([glosario](../glosario.md)) es el precio de un miembro por tipo de turno. Con los impuestos de la
empresa y el bruto o neto del miembro da el importe de cada turno (liquidacion). Este fichero recoge tambien la
billing basica (la pagina de facturacion y costes), que solo suma esos importes. El contrato de `tax_config`, de
`worklog_definitions` y de `settings` es de [empresa.md](empresa.md) (R-EMP-34 a R-EMP-36, R-EMP-40 y R-EMP-45 a
R-EMP-47) y no se copia. Quien escribe turnos y tarifas segun el modo de empresa esta en
[acceso.md](acceso.md) y se enlaza.

## Campos

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `company_members.rates_config` | JSONB | No | Tipo de turno -> tarifa (R-TAR-01) |
| `base_rate` | numerico | Si | Precio por hora, por dia o fijo, segun la unidad del tipo; >= 0 y finito |
| `is_gross` | bool | No | Hoy por tipo, dentro de cada entrada; objetivo: uno por miembro (R-TAR-05) |
| `tax_overrides` | JSON | No | Nombre de impuesto -> tasa 0 a 1, o `null` (no sustituye); hoy por tipo, dentro de cada entrada |
| `extras` | JSON | No | Plus -> `value` (>= 0) y `per_unit` (bool), solo para `options` del tipo; hoy por tipo, dentro de cada entrada |
| `companies.settings.default_is_gross` | bool | No | Valor de `is_gross` que se copia a los miembros nuevos (R-EMP-46) |
| `work_logs.gross_amount`, `net_amount` | numerico | Si | Importes guardados de cada turno (R-TUR-16) |
| `work_logs.calculation_snapshot` | JSON | No | Tarifas, extras e impuestos usados al calcular (R-TAR-15) |

## Reglas

### Tarifa por miembro y tipo

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-01 | La tarifa vive solo en `company_members.rates_config`, por miembro y tipo de turno. No hay otra tabla ni otro sitio de tarifa | Cerrado | revision-base 2; 7 | `backend/models.py:CompanyMember` |
| R-TAR-02 | `base_rate` es >= 0 y finito (sin NaN ni infinito). Su unidad la da el tipo: por hora, por dia o fijo | Cerrado | 4.4 | `backend/contracts.py:RateEntry` |
| R-TAR-03 | `rates_config` admite como maximo 50 tipos y 65536 bytes de JSON; si se supera, el servidor rechaza el cambio | Cerrado | 4.4 | `backend/contracts.py:RatesConfig` |
| R-TAR-04 | Una tarifa nueva solo se guarda para una clave que exista en `worklog_definitions` de la empresa (R-EMP-40); las claves que el miembro ya tenia se conservan | Cerrado | 4.4, #66 | `set_member_rates.py` (`MSG_UNKNOWN_SHIFT_TYPE`) |

### Bruto o neto

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-05 | Cada miembro tiene un unico ajuste bruto o neto (`is_gross`), igual para todos sus tipos de turno | Cerrado | S2 | pendiente de implementar (issue de seguimiento): hoy `is_gross` es por tipo en `RateEntry` |
| R-TAR-06 | Al dar de alta un miembro se le copia `companies.settings.default_is_gross`. Cambiar ese valor despues no modifica a los miembros que ya existen | Confirmar | S2, R-EMP-46 | pendiente de implementar (issue de seguimiento) |
| R-TAR-07 | Durante la migracion conviven `is_gross` por tipo y por miembro: que valor toma un miembro con tipos mezclados, si el codigo lee ambos formatos y cuando se borra el campo de `RateEntry` | Abierto (O17) | S2; issue #116 | `backend/src/domain/value_objects/rate_definition.py` lee `is_gross` de cada tipo |

### Impuestos del miembro

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-08 | Los impuestos propios del miembro se eligen de la lista de impuestos de la empresa, con valor de 0 a 1 o `null` (sin sustituir). El rechazo de nombres inexistentes y la limpieza de huerfanos son R-ACC-74 y no se repiten | Cerrado | S4, O9 | valor: `backend/contracts.py:validate_tax_overrides`; nombres: pendiente de implementar (issue de seguimiento), hoy se acepta cualquier nombre |
| R-TAR-09 | Los impuestos efectivos son los de la empresa mas los overrides del miembro con valor. Para la misma clave manda el miembro, tambien con 0 | Cerrado | O9, S4 | `backend/contracts.py:resolve_taxes` |
| R-TAR-10 | Una empresa sin impuestos (`tax_config: {}`, R-EMP-36) liquida sin deducciones: bruto y neto salen iguales. El seed no trae impuestos (R-EMP-37) | Cerrado | revision-base 8 ("Seed") | `backend/src/domain/value_objects/tax_configuration.py` |

### Liquidacion de un turno

Sea `S` la suma de las tasas efectivas (R-TAR-09). Duracion: horas o dias del turno.

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-11 | Importe base: con unidad por hora o por dia, duracion x `base_rate`; con unidad fija, `base_rate` | Cerrado | 7 | `work_log_calculation_service.py:calculate` |
| R-TAR-12 | Con tarifa bruta: bruto = base + extras; neto = bruto x (1 - S) | Cerrado | S2, S3 | `work_log_calculation_service.py:calculate` |
| R-TAR-13 | Con tarifa neta no se deduce nada: neto = base + extras; bruto = neto / (1 - S) si `S` < 1, y bruto = neto si `S` >= 1 | Cerrado | S2, S3 | `work_log_calculation_service.py:calculate` |
| R-TAR-14 | Cada importe se redondea a 2 decimales, con la mitad hacia arriba | Cerrado | 7 | `work_log_calculation_service.py` (`ROUND_HALF_UP`) |
| R-TAR-15 | Cada turno guarda `gross_amount` y `net_amount` (R-TUR-16) y un `calculation_snapshot` con la tarifa, los extras y los impuestos usados | Cerrado | S3, T5 | `backend/src/domain/value_objects/calculation_snapshot.py` |
| R-TAR-16 | Con tarifa bruta y `S` > 1 el neto saldria negativo. Sin decidir si se rechaza al guardar impuestos o tarifas | Abierto (O28) | R-TAR-12 | sin validar: `backend/contracts.py:TaxConfig` solo acota cada tasa |

### Pluses

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-17 | Un plus es una opcion (`options`) del tipo de turno con valor en `extras` de la tarifa del miembro: importe fijo, o por unidad (valor x duracion) si `per_unit` es true | Cerrado | S5 | `work_log_calculation_service.py:calculate` |
| R-TAR-18 | Solo se suman los pluses que el turno tiene activados en sus opciones | Cerrado | S5 | `crud.py:calculate_dynamic_work_log` (`opciones`) |
| R-TAR-19 | Guardar tarifas nunca borra lo que la pantalla de edicion no toca (extras y overrides de otros tipos); la pantalla lleva valor y "fijo / por unidad" | Cerrado | S5 | pendiente de implementar (issue de seguimiento): `set_member_rates.py` guarda el `rates_config` recibido completo |
| R-TAR-20 | Futuro: la cantidad de cada plus se edita en el turno (nocturnidad = dias - 1, "2 festivos") | Abierto (O24) | S5 | sin implementar |

### Retiradas

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-21 | **Retirada.** El importe manual (y `allow_manual_amount`) desaparece: la liquidacion sale siempre de tarifa e impuestos. Los turnos antiguos con `manual_override` se leen sin migrar (R-TUR-18) | Retirada | S6, T2 | pendiente de implementar (issue de seguimiento): rama `manual_override` de `crud.py` y del motor de dominio |
| R-TAR-22 | **Retirada.** `price_type` ya no existe: el panel muestra siempre bruto y neto, sustituida por R-TAR-15 | Retirada | S3, T5 | pendiente de implementar (issue de seguimiento): `backend/contracts.py:BusinessLogic` |

### Acceso y trazabilidad

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-23 | Quien edita tarifa, bruto o neto e impuestos propios y quien las ve: R-ACC-70 y R-ACC-71 (edicion segun el modo de empresa) y R-ACC-58 (lectura de las de todos). No se repiten | Cerrado | P7, S7 | `backend/access_policy.py:can_edit_member_rates` |
| R-TAR-24 | No hay historial de tarifas: cada cambio queda en `audit_logs` con valor anterior y nuevo (R-AUD), y cada turno conserva su `calculation_snapshot` | Cerrado | 7 | `set_member_rates.py` (`AuditAction.MEMBER_RATES_CHANGED`) |

### Billing basica

| ID | Regla | Estado | Origen | Codigo |
|---|---|---|---|---|
| R-TAR-25 | La billing basica (pagina de facturacion y costes) no es un modulo: la ven PA y manager de la empresa activa; el worker no. La retirada del modulo `billing` es de #70 | Cerrado | P17, matriz de permisos | `backend/routers/work_logs.py:get_billing_summary` (manager); modulo `billing`: pendiente de implementar (issue de seguimiento) |
| R-TAR-26 | Muestra, por miembro y tipo de turno, en un rango de fechas: horas, dias distintos, numero de turnos, total bruto y total neto | Cerrado | S3, T5 | `backend/migrations/versions/7d19bd7c379c_add_get_billing_summary_function.py` |
| R-TAR-27 | Cada importe es la suma por columna de `gross_amount` y `net_amount` guardados en los turnos; no se recalcula con la tarifa vigente ni se elige un tipo de precio | Cerrado | S3, T5, R-TUR-25 | `get_billing_summary` (`SUM(net_amount)`, `SUM(gross_amount)`) |
| R-TAR-28 | Entran los turnos cuyo rango de fechas solapa con el rango consultado, con su importe completo (no se reparte por dias) | Confirmar | 7 | `get_billing_summary` (`end_date >= s_date AND start_date <= e_date`) |
| R-TAR-29 | Los miembros inactivos: R-TUR-27 y O6 los incluyen y marcados; el codigo solo lista miembros activos. Sin decidir cual vale para la billing basica | Abierto (O27) | O6, R-TUR-27 | `get_billing_summary` (`cm.is_active = true`) |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| Empresa sin impuestos, tarifa bruta | Bruto y neto iguales | R-TAR-10 |
| Tarifa neta con impuestos que suman 100 % o mas | Bruto igual al neto | R-TAR-13 |
| Override con la clave de un impuesto de empresa y valor 0 | Ese impuesto no se deduce a ese miembro | R-TAR-09 |
| Override `null` | No sustituye al de la empresa | R-TAR-09 |
| Override con un nombre que no esta en la empresa | Rechazado (R-ACC-74); hoy se acepta | R-TAR-08 |
| Tarifa para un tipo que no existe en la empresa | Rechazada | R-TAR-04 |
| Mas de 50 tipos en `rates_config` | Rechazado | R-TAR-03 |
| Turno antiguo con `manual_override` | Se lee con su importe; no se migra | R-TAR-21 |
| Worker pide la billing basica | Sin acceso | R-TAR-25 |
| Empresa suspendida (`is_active = false`) | Manager y worker reciben 403 tambien en billing (R-EMP-24) | R-TAR-25 |

## Ejemplos de liquidacion

Verificados con `cd backend && pytest tests/domain/test_work_log_calculation_service.py -q`: 8 passed.

| Caso | Calculo | Test |
|---|---|---|
| 2 h x 20 EUR neto, IRPF 15 % | Neto 40,00; bruto 40 / (1 - 0,15) = 47,06 | `test_calculate_hourly_rate_net_to_gross` |
| 3 dias x 100 EUR bruto, transporte 10 EUR por dia, dietas 15 EUR fijo, IRPF 10 % y Seguridad Social 5 % | Base 300 + extras 45 = bruto 345,00; neto 345 x (1 - 0,15) = 293,25 | `test_calculate_daily_rate_gross_to_net_with_extras` |
| Override de IRPF a 30 % sobre empresa al 15 %, 2 h x 100 EUR bruto | Bruto 200; neto 200 x 0,70 = 140 | `backend/tests/routers/test_tax_calculation.py:test_member_override_with_same_key_wins_over_company` |

## Relacion con otras entidades

- Empresa ([empresa.md](empresa.md)): aporta `tax_config`, `worklog_definitions` y `default_is_gross`.
- Membresia ([membresia.md](membresia.md)): `rates_config` es una columna de `company_members`.
- Turno ([turno.md](turno.md)): guarda los importes (R-TUR-16) y decide cuando se recalcula (R-TUR-19 a R-TUR-21). La unidad "libre" y su precio estan en R-TUR-22 y R-EMP-44 (O18): se tratan segun el bruto o neto del miembro y no se redefinen aqui.
- Acceso ([acceso.md](acceso.md)): R-ACC-58, R-ACC-70, R-ACC-71 y R-ACC-74.
- Auditoria ([auditoria.md](auditoria.md)): el evento `member.rates_changed`.
