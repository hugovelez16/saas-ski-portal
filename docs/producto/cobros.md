# Modelo de cobro, planes y limites

Estado: **Decidido** (2026-11-25, issue #130). Las condiciones comerciales publicas estan en [../planes-y-precios.md](../planes-y-precios.md) y las reglas de dominio de plan y limites en [../dominio/modulo.md](../dominio/modulo.md) (`R-MOD-20` a `R-MOD-31`).

Objetivo a futuro: que una escuela pueda darse de alta, elegir plan, pagar y cambiar de plan sin intervencion de Vesotel. Este documento fija el reparto con Odoo, el flujo de cobro mensual y las fases de implantacion.

## Reparto entre el portal y Odoo

| Responsabilidad | Dueno | Detalle |
|---|---|---|
| Cliente y datos fiscales | Odoo de Vesotel | El portal no guarda datos fiscales (`R-ACC-57`) |
| Facturacion, Verifactu y factura electronica B2B | Odoo de Vesotel | El portal nunca emite facturas |
| Mandatos SEPA, remesas, cobros, impagos y devoluciones | Odoo de Vesotel | Gestion bancaria y contable completa en Odoo |
| Plan de cada escuela | Portal | El plan vive en el portal (`C6`, `R-MOD-22`); Odoo lo recibe para facturar |
| Meses activos e inactivos | Portal | Configurados por el PA (fase 0) o por el manager (fase 3, `C8`) |
| Limites, avisos y recuento de uso | Portal | El portal aplica los limites por codigo y calcula el pico mensual (`C1`, `C2`) |
| Efectos de impago en el acceso | Portal | Aplica aviso, solo lectura y suspension segun lo notificado por Odoo (`C5`) |

**Integracion prevista:**

- **Portal -> Odoo:** el portal informa a Odoo de lo que hay que cobrar (plan, mes activo o mantenimiento, y adicionales segun el pico del mes anterior).
- **Odoo -> Portal:** Odoo informa al portal de pagos confirmados, devoluciones e impagos para aplicar o levantar las restricciones de `C5`.

## Datos conocidos del Odoo de Vesotel

Segun la informacion disponible hasta la fecha (pendiente de verificar en `O30`):

- Entorno probable: **Odoo Online**, version **19.0 Enterprise**.
- Modulo **Suscripciones** actualmente en uso.
- Sin confirmar si esta activo el modulo de domiciliacion **SEPA Direct Debit**; a la mayoria de clientes periodicos se les carga actualmente en banco.

## Flujo de cobro mensual y decisiones (C1 a C12)

### Recuento y limites (C1, C2, C6)

- **C1 (pico simultaneo):** se cobra por el maximo de monitores y de responsables activos simultaneamente en el mes natural. Desactivar a uno y activar a otro despues no cuesta nada; activar primero y desactivar despues si suma ese mes. Un monitor cuenta desde que acepta la invitacion (membresia activa), no desde que se envia (`R-MOD-23`, `R-MOD-24`).
- **C2 (superacion y panel de consumo):** en Pista Verde y Pista Azul, el manager puede superar lo incluido tras confirmar un aviso con el coste ("Superas los N monitores de tu plan. Este mes se cobrara X EUR por cada monitor adicional"); la confirmacion se audita. Si los adicionales cuestan mas que subir de plan, el aviso lo indica y ofrece subir. Misma logica para responsables adicionales (50 EUR/mes). Tope duro solo en Pista Roja (50 monitores; por encima es Pista Negra). El manager ve un panel de consumo del mes (plan, adicionales, pico, importe previsto) (`R-MOD-25` a `R-MOD-28`).
- **C6 (fuente de verdad):** el plan vive en el portal y Odoo lo recibe para facturar (`R-MOD-22`).

### Calendario, remesa e impagos (C3, C5, C8)

- **C8 (cierre del mes siguiente):** el manager activa o desactiva el mes siguiente desde el portal hasta el dia 25 del mes anterior; a partir del dia 26 vale la configuracion guardada (`R-MOD-29`).
- **C3 (cobro mensual):** el dia 1 de cada mes se cobra en una sola remesa la cuota del mes que empieza por adelantado (o el mantenimiento si es mes inactivo) mas los adicionales del mes anterior a mes vencido, segun su pico real. El primer mes se cobra el dia del alta y cubre ese mes natural entero. Nota: el usuario acepta el dia fijo 1 aunque no le convence del todo.
- **C5 (impago o devolucion):**
  1. **Dia 0:** aviso inmediato al manager.
  2. **Dia 5:** la escuela pasa a modo solo lectura.
  3. **Dia 15:** la escuela queda suspendida conservando todos sus datos.
  4. **Reactivacion manual:** el PA puede reactivar la escuela a mano en cualquier momento (por ejemplo, tras recibir un justificante de pago) (`R-MOD-30`, `R-MOD-31`).

### Puesta en marcha, alta autonoma y pasarela (C7, C11, C12)

- **C7 (puesta en marcha opcional):** los 150 EUR dejan de ser obligatorios y se cobran solo si la escuela los pide. Pasan a ser una jornada de formacion donde tambien se ensena al manager a configurar la escuela; no incluye importacion de datos ni historico. Cuando exista el pago automatico sera un servicio opcional en el alta.
- **C11 (alta autonoma y prueba gratuita):** prueba gratuita de 14 dias con un manager, sin pedir pago. La escuela crea su empresa real e invita a su equipo (lo configurado se conserva). Opcionalmente se le crea aparte una "Empresa de ejemplo" con workers y turnos ficticios (seed) para practicar, que se borra al acabar la prueba. Para seguir tras la prueba, paga el primer mes con tarjeta o Bizum y firma la domiciliacion SEPA en el mismo paso.
- **C12 (pasarela del primer pago):** se decide en la fase 3, comparando el TPV de Redsys del banco de Vesotel con Stripe o Mollie integrados en Odoo.

### Temas aplazados o abiertos (C4, C9)

- **C4 (esquema SEPA Core frente a B2B):** abierto en `O29` (`docs/preguntas-abiertas.md`).
- **C9 (cobro a particulares B2C):** aplazado sin decidir; sigue en `O16` (`docs/preguntas-abiertas.md`).

## Fases de implantacion (C10)

| Fase | Alcance | Dependencias y bloqueos |
|---|---|---|
| **Fase 0** | Plan asignado por el PA, limites aplicados en codigo (C1, C2) e informe mensual de uso por escuela (pico de monitores y responsables, meses activos) para facturar a mano en Odoo (#147) | Migracion del contexto Modulos y billing (`O4`) |
| **Fase 1** | El portal envia automaticamente el uso mensual a Odoo | Fase 0 y acceso a la API de Odoo (`O30`) |
| **Fase 2** | Odoo notifica al portal pagos, devoluciones e impagos y el portal aplica `C5` | Fase 1 y webhooks/notificaciones desde Odoo (`O30`) |
| **Fase 3** | Alta autonoma completa (`C11`), cambios de plan y meses activos/inactivos desde el portal (`C8`), y eleccion de pasarela del primer pago (`C12`) | Fase 2, esquema SEPA (`O29`) y capacidades de Odoo (`O30`) |
| **Fase 4** | Cobro a particulares B2C (`C9`) | Decision de `O16` |

## Preguntas abiertas relacionadas

Ver [../preguntas-abiertas.md](../preguntas-abiertas.md):

- **O16:** cobro a particulares (B2C), aplazado.
- **O29:** eleccion del esquema SEPA (Core frente a B2B).
- **O30:** plan de Odoo Online (API externa solo en Custom), estado de SEPA Direct Debit, firma de mandato online en 19.0 y notificaciones salientes (webhooks) al pagarse o devolverse una factura.
