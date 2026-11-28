# Planes y precios publicos

Condiciones comerciales de los planes que se publican en la landing (`/`). Precios de la temporada 2026-2027, sin IVA. La fuente de los importes en el codigo es `frontend/src/lib/landing-pricing.ts`; si cambia una cifra, se cambia alli y en este documento.

## Planes

Los planes llevan el nombre del color de las pistas de esqui, de menor a mayor tamano de escuela. Se descarto usar nombres de pistas concretas (por ejemplo, de Sierra Nevada): la landing se dirige a escuelas de toda Espana y una escuela de otra estacion lo veria como un producto ajeno.

| | Pista Verde | Pista Azul | Pista Roja |
|---|---|---|---|
| Cuota por mes activo | 129 € | 249 € | 399 € |
| Monitores incluidos | 10 | 25 | 50 |
| Monitor adicional | 9 €/mes | 7 €/mes | - |
| Responsables incluidos | 1 | 2 | Ilimitados |
| Responsable adicional | 50 €/mes | 50 €/mes | - |
| Cuadrante compartido | 5 €/mes | Incluido | Incluido |
| Informes | 15 €/mes | Incluido | Incluido |
| Mantenimiento por mes inactivo | 15 € | 20 € | 30 € |

- Mas de 50 monitores: Pista Negra, a consultar.
- Informes a medida: bajo consulta.
- Los planes Azul y Roja incluyen solo los modulos que nombran (Cuadrante compartido e Informes). Un modulo nuevo no queda incluido automaticamente: se decide su precio por plan al lanzarlo.

## Meses activos

- La escuela elige que meses activa. No hay temporada fija: puede activar de diciembre a marzo, de febrero a mayo o cualquier otro periodo.
- Se factura por mes natural completo. Activar a mitad de mes cuenta como mes entero.
- No hay minimo de meses ni permanencia.
- El responsable puede activar o desactivar el mes siguiente desde el portal hasta el dia 25 del mes anterior; a partir del dia 26 se aplica la configuracion que estuviera guardada.

## Puesta en marcha

- Servicio opcional de pago unico (150 €), igual en todos los planes: no es obligatoria y solo se cobra si la escuela la pide.
- Consiste en una jornada de formacion en la que tambien se ensena al responsable a configurar la escuela (alta de monitores, tipos de clase, tarifas, suplementos y retenciones).
- No incluye importacion de datos ni migracion de historico.
- Cuando exista el alta autonoma con pago automatico, se ofrecera como servicio opcional al darse de alta.

## Meses inactivos y mantenimiento

En cada mes no activo la escuela elige:

- **Con mantenimiento** (15, 20 o 30 € al mes segun el plan): no hay acceso a la aplicacion, pero se conservan la escuela, usuarios, tarifas e historico.
- **Sin mantenimiento**: no tiene coste. Los datos se eliminan y, si la escuela vuelve mas adelante, parte de cero sin los datos ni la configuracion de la temporada anterior (y puede contratar de nuevo la puesta en marcha opcional si quiere formacion).

El mantenimiento crece con el plan porque una escuela mas grande tiene mas usuarios, clases e historico que conservar. Conservar el mantenimiento en todos los meses inactivos evita reconfigurar usuarios y tarifas al volver, preserva el historico de la temporada anterior y mantiene el precio garantizado la temporada siguiente. Solo interesa dejar de mantener a una escuela que no quiera conservar sus datos.

## Precio garantizado tras el mantenimiento

Si la escuela paga el mantenimiento en todos los meses inactivos entre dos temporadas, la temporada siguiente conserva los precios que tenia, aunque la tarifa publica haya subido.

- **Alcance**: solo la temporada inmediatamente siguiente. Lo que pase despues se decide en cada off-season; la idea actual es mantener el precio la primera y la segunda temporada y aplicar la tarifa vigente desde la tercera. En la landing solo se promete la temporada siguiente.
- **Que se conserva**: la cuota del plan, el monitor adicional, el responsable adicional y los modulos ya contratados. Un modulo nuevo se contrata al precio vigente.
- **Cuando se pierde**: si algun mes inactivo queda sin mantenimiento, se aplica la tarifa vigente.
- **Cambio de plan**: el plan nuevo se factura a la tarifa vigente.

## Cambio de plan con la suscripcion activa

- **Subir de plan**: efecto inmediato. El precio nuevo se factura desde el mes siguiente; el mes en curso no se prorratea.
- **Bajar de plan**: efecto desde el mes siguiente. Lo que exceda los limites del plan nuevo se cobra aparte: monitores adicionales, responsables adicionales (50 €) y los modulos Cuadrante compartido e Informes. Si la escuela no quiere pagarlos, esos modulos se desactivan y los responsables sobrantes pierden el acceso. Los datos nunca se borran.
- **Puesta en marcha**: cambiar de plan no implica contratar ni pagar puesta en marcha.
- **Durante el mantenimiento** no hay plan activo: la escuela elige el plan al reactivarse.

## Recuento de monitores y limites del plan

- **Pico simultaneo**: se cobra por el maximo de monitores (y responsables) activos simultaneamente en el mes natural. Desactivar a un miembro y activar a otro despues no cuesta nada; activar primero y desactivar despues si suma ese mes.
- **Cuando cuenta un miembro**: un monitor cuenta desde que acepta la invitacion (membresia activa), no desde que se envia la invitacion.
- **Superar lo incluido con aviso**: en Pista Verde y Pista Azul, el responsable puede superar los monitores incluidos tras confirmar un aviso con el coste ("Superas los N monitores de tu plan. Este mes se cobrara X EUR por cada monitor adicional"); la confirmacion queda auditada. Si los adicionales cuestan mas que subir de plan, el aviso lo indica y ofrece subir. Con los responsables adicionales (50 €/mes) se aplica la misma dinamica.
- **Tope duro**: solo existe en Pista Roja (50 monitores activos simultaneos); por encima corresponde Pista Negra, a consultar.
- **Panel de consumo**: el responsable ve en el portal el consumo del mes en curso (plan, adicionales, pico alcanzado e importe previsto).

## Alta y prueba gratuita

- **Prueba gratuita de 14 dias**: una escuela nueva empieza con 14 dias gratis y un responsable, sin pedir datos de pago.
- **Empresa real y empresa de ejemplo**: la escuela crea su empresa real e invita a su gente (todo lo que configure se conserva). Opcionalmente se le crea aparte una "Empresa de ejemplo" con monitores y turnos ficticios (seed) para practicar, que se elimina al acabar la prueba.
- **Paso a pago**: para continuar tras la prueba, la escuela paga el primer mes con tarjeta o Bizum y firma la domiciliacion SEPA en el mismo paso.

## Cobro mensual e impagos

- **Cobro mensual**: el dia 1 de cada mes se cobra en una sola remesa la cuota del mes que empieza por adelantado (o la cuota de mantenimiento si es mes inactivo) y los adicionales del mes anterior a mes vencido, segun el pico real alcanzado. El primer mes se cobra el dia del alta y cubre ese mes natural entero.
- **Impagos y devoluciones**: ante un impago o devolucion bancaria se avisa al responsable al momento. A los 5 dias sin regularizar, la escuela pasa a solo lectura; a los 15 dias queda suspendida conservando todos sus datos. El administrador de plataforma puede reactivarla a mano en cualquier momento (por ejemplo, con justificante de pago).
