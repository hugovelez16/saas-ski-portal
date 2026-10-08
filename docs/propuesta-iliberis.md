# Propuesta para Iliberis: gestión de clases y monitores

## Índice

1. [Introducción](#introducción)
2. [El problema: asignar clases y contar horas a mano](#el-problema-asignar-clases-y-contar-horas-a-mano)
3. [La solución para el responsable de la escuela](#la-solución-para-el-responsable-de-la-escuela)
4. [La solución para los monitores](#la-solución-para-los-monitores)
5. [Antes y después](#antes-y-después)
6. [Cómo empezar](#cómo-empezar)
7. [Precios](#precios)
   - [Cuota mensual](#cuota-mensual)
   - [Módulos adicionales](#módulos-adicionales)
   - [Puesta en marcha](#puesta-en-marcha)
   - [Ejemplos de cálculo](#ejemplos-de-cálculo)
   - [Fuera de temporada: qué pasa con los datos](#fuera-de-temporada-qué-pasa-con-los-datos)
   - [Copias de seguridad](#copias-de-seguridad)
8. [Preguntas frecuentes](#preguntas-frecuentes)
9. [Contacto y validez](#contacto-y-validez)

## Introducción

Que el cierre de mes y los avisos dejen de ocupar al responsable de la escuela. Esa es la idea de esta propuesta: una aplicación web donde el responsable asigna las clases a cada monitor y los totales de horas e importes se calculan solos.

Contar las horas de cada monitor y calcular lo que le corresponde supone, de media, entre 4 y 5 horas cada mes, a las que hay que sumar el trabajo diario de apuntar las clases y de modificarlas cada vez que hay un cambio. Con la aplicación, el recuento mensual pasa a ser consultar un resumen ya calculado.

Los monitores acceden con su propio usuario y consultan en cualquier momento qué clases tienen. Desaparecen el recuento manual a final de mes y los avisos uno a uno.

Lo que gana la escuela es tiempo, comodidad y flexibilidad: información siempre a mano para el responsable y para cada monitor, y un cálculo que se adapta a cómo se paga cada tipo de clase (por horas, por días o importe fijo, en bruto o en neto).

La aplicación tiene dos tipos de usuario: el **responsable**, que gestiona turnos, tarifas y la liquidación de importes de cada monitor, y el **monitor**, que consulta lo suyo.

## El problema: asignar clases y contar horas a mano

Asignar clases a los monitores es una tarea que se repite cada día y que consume mucho tiempo. En temporada hay que decidir quién da cada clase, avisar a cada monitor, rehacerlo todo cuando hay una baja o un cambio de última hora, y a final de mes sentarse a contar cuántas horas ha trabajado cada uno y cuánto le corresponde.

Es un trabajo pesado, repetitivo y fácil de equivocar:

- **Tiempo del responsable:** asignar, avisar, corregir y, al cierre de mes, sumar horas y calcular importes de cada monitor.
- **Cálculos manuales:** horas, días, suplementos y retenciones se calculan a mano, y cada tipo de clase se paga de una forma distinta.
- **Errores que no se ven:** un dato mal anotado o una cuenta mal hecha cambia lo que cobra un monitor sin que nadie lo detecte.
- **Cuadrar al cierre:** si hay dudas, reconstruir qué clases se dieron y cuáles se pagan lleva tiempo y genera desconfianza.
- **Poca visibilidad para el monitor:** depende de que le avisen de cada cambio para saber qué clases tiene.
- **Difícil de crecer:** cada monitor o cada curso nuevo multiplica el trabajo y las posibilidades de error.

## La solución para el responsable de la escuela

El responsable gestiona toda la escuela desde un panel único. Puede editar los turnos, asignarlos a los monitores y configurar las tarifas y la liquidación de importes de cada monitor.

- **Equipo:** alta, baja y activación de monitores, con el orden de la plantilla que prefiera la escuela.
- **Calendario:** vista de mes, semana, día y agenda con las clases de cada monitor, y posibilidad de mover una clase arrastrándola.
- **Registro de clases:** alta individual o masiva, edición y borrado de lo que se ha asignado.
- **Listado filtrable:** consulta por monitor, fecha o tipo, con exportación a CSV.
- **Tipos de turno a medida:** la escuela define sus propios tipos de clase y elige cómo se calcula cada uno: por horas, por días o por importe fijo. Los turnos que cruzan la medianoche se contemplan.
- **Tarifas por monitor:** cada monitor puede tener su propia tarifa para cada tipo de turno, indicada en bruto o en neto.
- **Suplementos:** importes adicionales por turno (por ejemplo, nocturnidad u otros pluses), de importe fijo o por unidad trabajada, que se activan al registrar la clase.
- **Retenciones configurables:** Seguridad Social, IRPF y otras deducciones, con el desglose de cada importe (base, retenciones y neto). La aplicación calcula con los porcentajes que configura la escuela; no sustituye a la gestoría ni emite nóminas oficiales.
- **Totales automáticos:** resumen de facturación por monitor, por tipo de turno y por periodo, calculado al momento. Cada clase guarda el desglose con el que se calculó, de modo que un cambio posterior de tarifa no altera lo ya registrado.
- **Panel de control:** horas totales, coste mensual estimado, monitores activos, últimos registros y evolución semanal del coste.
- **Partes diarios:** vista del día con las clases de cada monitor.
- **Informes (módulo adicional):** generación de informes para imprimir o archivar.

## La solución para los monitores

Cada monitor entra con su usuario y solo ve lo suyo. No puede modificar turnos ni tarifas.

- **Su calendario:** las clases asignadas, por día, semana o mes, desde el móvil o el ordenador, sin instalar nada.
- **Su listado:** el detalle de lo trabajado, siempre actualizado.
- **Sus resúmenes:** horas trabajadas e importe generado en el periodo que elija, con el desglose de cada cálculo.
- **Su perfil:** puede cambiar su nombre y su correo, y recuperar su contraseña por correo si la olvida.
- **Parte diario del equipo (módulo adicional):** vista del día con las clases de todos los monitores.
- **Sus informes (módulo adicional):** puede consultar y descargar su propio resumen, sin pedirlo a nadie.
- **Cuenta segura:** acceso personal con contraseña y datos separados por escuela.

## Antes y después

| Aspecto | Hoy, a mano | Con la aplicación |
| --- | --- | --- |
| Asignar una clase | Anotarla y avisar al monitor | Registrar la clase en la app, de forma individual o masiva |
| Aviso al monitor | Manual, uno a uno | El monitor la ve en su calendario al momento |
| Total por monitor | Suma de horas y cuentas al cierre del mes (4 a 5 horas al mes) | Calculado solo, por monitor y por periodo |
| Tarifas y tipos de clase | Cada caso se calcula por separado | Tipos de turno y tarifas por monitor, por horas, días o importe fijo, en bruto o en neto |
| Suplementos y retenciones | Se calculan a mano | Configurados una vez y aplicados con su desglose |
| Acceso del monitor | Depende de que le informen | Usuario propio, desde el móvil o el ordenador |

Registrar la clase sigue siendo un paso; lo que desaparece es el recuento final, los cálculos manuales y el aviso uno a uno al monitor.

## Cómo empezar

1. Reunión corta para ver cómo se organizan hoy las clases, qué tipos hay y cómo se calcula lo que cobra cada monitor.
2. Alta de la escuela Iliberis, del responsable y de los monitores. La escuela nos facilita la lista de monitores, los tipos de clase y las tarifas.
3. Ayuda con la configuración inicial: tipos de clase, tarifas, suplementos y retenciones.
4. Formación breve al responsable y acceso para los monitores.
5. Un periodo en paralelo con el método actual para comprobar que los totales coinciden, con acompañamiento en el uso de la plataforma.

Si se acepta la propuesta con antelación, los pasos anteriores se hacen en noviembre, antes de que arranque la temporada. Ese mes sirve para la puesta en marcha y no lleva cuota mensual: se paga la puesta en marcha y la mensualidad empieza en diciembre.

## Precios

Todos los importes son por mes de temporada y no incluyen IVA. La temporada va de diciembre a abril (5 meses). Fuera de temporada no se factura la cuota mensual de uso.

### Cuota mensual

| Concepto | Precio |
| --- | --- |
| Cuota base de la escuela (incluye una cuenta de responsable) | 150 € |
| Cuenta de responsable adicional | 50 € |
| Monitores | Según tramos (ver tabla siguiente) |

Se factura por las cuentas de monitor existentes en cada mes. Cada mes pueden entrar o salir monitores, y el importe se ajusta al número de cuentas de ese mes.

Los tramos de monitores son marginales: cada precio se aplica solo a los monitores que caen en ese tramo.

| Tramo de monitores | Precio por monitor y mes |
| --- | --- |
| 1 a 10 | 5,00 € |
| 11 a 20 | 4,75 € |
| 21 a 30 | 4,50 € |
| 31 a 40 | 4,25 € |
| 41 a 50 | 4,00 € |
| Más de 50 | A consultar |

Las cuentas de usuario son personales e intransferibles: cada cuenta de responsable o de monitor corresponde a una única persona y no puede compartirse.

Sin permanencia: la escuela puede cancelar el servicio cuando quiera.

### Módulos adicionales

- **Informes:** 15 € al mes.
- **Parte diario del equipo para los monitores:** 5 € al mes. Incluido sin coste para Iliberis durante la primera temporada (valor de 25 € en la temporada).

Al terminar la primera temporada se consultará a la escuela si quiere mantener el parte diario del equipo, con su coste, o desactivarlo. No se cobra sin confirmación previa.

### Puesta en marcha

Cuota única de 150 €, que incluye el alta de la escuela, el alta del responsable y de los monitores, y la ayuda con la configuración inicial.

### Ejemplos de cálculo

Los ejemplos suponen una cuenta de responsable y ningún módulo adicional. Cada módulo se suma a la cuota mensual según su precio (por ejemplo, Informes supone 15 € más al mes).

Los tramos son progresivos: con 15 monitores, los 10 primeros se cobran a 5,00 € (50,00 €) y los 5 siguientes a 4,75 € (23,75 €), lo que da 73,75 €.

| Concepto | 15 monitores | 20 monitores | 30 monitores |
| --- | --- | --- | --- |
| Cuota base de la escuela | 150,00 € | 150,00 € | 150,00 € |
| Monitores | 73,75 € | 97,50 € | 142,50 € |
| **Total al mes** | **223,75 €** | **247,50 €** | **292,50 €** |
| Temporada (5 meses) | 1.118,75 € | 1.237,50 € | 1.462,50 € |
| Puesta en marcha única | 150,00 € | 150,00 € | 150,00 € |
| **Primera temporada** | **1.268,75 €** | **1.387,50 €** | **1.612,50 €** |

### Fuera de temporada: qué pasa con los datos

Al terminar la temporada, la escuela elige entre estas opciones:

**Opción 1: mantenimiento.** La escuela, sus usuarios, tarifas y datos se conservan tal cual y están listos al empezar la siguiente temporada, sin repetir la puesta en marcha. Cuesta 20 € al mes fuera de temporada (mayo a noviembre, 7 meses: 140 € al año).

**Opción 2: sin mantenimiento.** La escuela se elimina de la aplicación al terminar la temporada y no tiene coste fuera de temporada. Sus datos se conservan en una copia de seguridad interna hasta el inicio de la siguiente temporada y después se eliminan. Esa copia es una protección del servicio; para recuperar los datos en la aplicación se necesita la exportación descargada por la escuela.

Los meses de mantenimiento son de mayo a noviembre. En 2026, el mes de noviembre es de puesta en marcha y no lleva cuota.

Si una escuela sin mantenimiento retoma el servicio en una temporada posterior, se aplica una nueva puesta en marcha (150 €). Si además quiere recuperar los datos de la temporada anterior en la aplicación, la importación tiene un coste adicional de 100 €, que cubre el trabajo de carga y verificación de los datos. Para ello, la escuela debe haber descargado la exportación de sus datos mientras tenía acceso.

En resumen, mantener la escuela fuera de temporada cuesta 140 € al año; no mantenerla y volver a empezar cuesta 150 € (250 € si se quieren recuperar los datos).

La exportación es gratuita, con independencia de la opción elegida. Recomendamos descargarla antes de que termine la temporada.

### Copias de seguridad

El servicio incluye copias de seguridad periódicas de la base de datos, almacenadas fuera del servidor donde se ejecuta la aplicación.

## Preguntas frecuentes

**¿Quién puede ver los datos de la escuela?** Cada escuela tiene sus datos separados de las demás. Dentro de la escuela, el acceso depende del rol: el responsable gestiona turnos y tarifas, y cada monitor solo ve lo suyo. Las condiciones del tratamiento de datos personales se recogen en el presupuesto formal.

**¿Qué pasa si la aplicación falla en plena temporada?** El servicio incluye copias de seguridad periódicas fuera del servidor. Las condiciones de soporte y el canal de contacto en temporada se detallan en el presupuesto formal.

**¿Puedo cambiar una tarifa a mitad de temporada?** Sí. Cada clase guarda el desglose con el que se calculó, por lo que el cambio solo afecta a las clases que se registren a partir de ese momento y no altera lo ya registrado.

**¿Se mantienen los precios la temporada siguiente?** Los precios de esta propuesta son los de la temporada 2026-2027. Cualquier cambio para la temporada siguiente se comunicará a la escuela con antelación.

**¿Hay permanencia?** No. La escuela puede cancelar cuando quiera. Si más adelante vuelve, se aplica una nueva puesta en marcha.

**¿Los monitores tienen que instalar algo?** No. Se accede desde el navegador del móvil o del ordenador con el usuario personal de cada monitor.

## Contacto y validez

Esta propuesta es válida hasta el 1 de noviembre de 2026, para poder tener la escuela configurada antes del inicio de la temporada el 1 de diciembre.

Contacto: Hugo Vélez, hugo@vesotel.com. Para cualquier duda sobre la propuesta, el correo es el canal preferido.

Una vez aceptada la propuesta se elaborará un presupuesto formal, que recogerá las condiciones de soporte, los métodos y condiciones de pago, el calendario de puesta en marcha y el tratamiento de datos personales.
