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
- No hay minimo de meses: la puesta en marcha ya cubre el coste de arranque.
- Sin permanencia.

## Puesta en marcha

- Pago unico de 150 €, igual en todos los planes, al activar la escuela por primera vez.
- Se mantiene igual en todos los planes para no subir la barrera de entrada a los planes mas caros.
- Incluye la reunion inicial, el alta de la escuela, del responsable y de los monitores, la configuracion de tipos de clase, tarifas, suplementos y retenciones, y una formacion breve al responsable.

## Meses inactivos y mantenimiento

En cada mes no activo la escuela elige:

- **Con mantenimiento** (15, 20 o 30 € al mes segun el plan): no hay acceso a la aplicacion, pero se conservan la escuela, usuarios, tarifas e historico. Al reactivar no se paga nueva puesta en marcha.
- **Sin mantenimiento**: no tiene coste. Los datos se eliminan y al volver se aplica una nueva puesta en marcha, sin los datos anteriores.

El mantenimiento crece con el plan porque una escuela mas grande tiene mas usuarios, clases e historico que conservar. Aunque en algun caso el mantenimiento de todos los meses inactivos supere los 150 € de una nueva puesta en marcha (por ejemplo, Pista Roja con 8 meses inactivos: 240 €), no compensa dejar de mantener: la nueva puesta en marcha parte de cero, sin el historico de la temporada anterior y volviendo a configurar usuarios y tarifas. Solo interesa a una escuela que no quiera conservar sus datos.

## Precio garantizado tras el mantenimiento

Si la escuela paga el mantenimiento en todos los meses inactivos entre dos temporadas, la temporada siguiente conserva los precios que tenia, aunque la tarifa publica haya subido.

- **Alcance**: solo la temporada inmediatamente siguiente. Lo que pase despues se decide en cada off-season; la idea actual es mantener el precio la primera y la segunda temporada y aplicar la tarifa vigente desde la tercera. En la landing solo se promete la temporada siguiente.
- **Que se conserva**: la cuota del plan, el monitor adicional, el responsable adicional y los modulos ya contratados. Un modulo nuevo se contrata al precio vigente.
- **Cuando se pierde**: si algun mes inactivo queda sin mantenimiento, se aplica la tarifa vigente.
- **Cambio de plan**: el plan nuevo se factura a la tarifa vigente.

## Cambio de plan con la suscripcion activa

- **Subir de plan**: efecto inmediato. El precio nuevo se factura desde el mes siguiente; el mes en curso no se prorratea.
- **Bajar de plan**: efecto desde el mes siguiente. Lo que exceda los limites del plan nuevo se cobra aparte: monitores adicionales, responsables adicionales (50 €) y los modulos Cuadrante compartido e Informes. Si la escuela no quiere pagarlos, esos modulos se desactivan y los responsables sobrantes pierden el acceso. Los datos nunca se borran.
- **Puesta en marcha**: no se vuelve a cobrar al cambiar de plan, ni se cobra diferencia alguna.
- **Durante el mantenimiento** no hay plan activo: la escuela elige el plan al reactivarse.

## Recuento de monitores

Los monitores facturables de un mes son el maximo de monitores activos en ese mes. Esta definicion es la que determina los monitores adicionales sobre los incluidos en el plan.
