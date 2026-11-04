**Plantilla base para adaptar a cada cliente. Debe revisarla y validarla un abogado o delegado de protección de datos (DPO) antes de utilizarla.**

# Contrato de encargo del tratamiento

De conformidad con el artículo 28 del Reglamento (UE) 2016/679 (RGPD)

## 1. Partes

De una parte, **[PENDIENTE_DE_RELLENAR: denominación social de la escuela de esquí]**, con NIF **[PENDIENTE_DE_RELLENAR: NIF de la escuela de esquí]**, domicilio en **[PENDIENTE_DE_RELLENAR: domicilio social de la escuela de esquí]**, inscrita en **[PENDIENTE_DE_RELLENAR: registro y datos registrales de la escuela de esquí, si procede]**, representada por **[PENDIENTE_DE_RELLENAR: nombre, apellidos y cargo de quien representa a la escuela de esquí]**, en adelante, la **Responsable**.

Y de otra parte, **[PENDIENTE_DE_RELLENAR: denominación social del prestador del servicio SaaS]**, con NIF **[PENDIENTE_DE_RELLENAR: NIF del prestador]**, domicilio en **[PENDIENTE_DE_RELLENAR: domicilio social del prestador]**, inscrita en **[PENDIENTE_DE_RELLENAR: registro y datos registrales del prestador, si procede]**, representada por **[PENDIENTE_DE_RELLENAR: nombre, apellidos y cargo de quien representa al prestador]**, en adelante, el **Encargado**.

Ambas partes, reconociéndose capacidad suficiente, acuerdan este contrato de encargo del tratamiento. La Responsable determina los fines y medios del tratamiento de los datos personales tratados en el servicio; el Encargado los trata por cuenta de la Responsable conforme a sus instrucciones documentadas.

## 2. Objeto y duración

Este contrato regula el acceso y tratamiento de datos personales por el Encargado para prestar a la Responsable el servicio SaaS de gestión de escuelas de esquí descrito en el contrato de servicios **[PENDIENTE_DE_RELLENAR: identificación y fecha del contrato de servicios]**.

El encargo comienza en la fecha de entrada en vigor del contrato de servicios y dura mientras este permanezca vigente. Las obligaciones que por su naturaleza deban subsistir, incluidas las relativas a confidencialidad, seguridad, devolución, supresión y conservación bloqueada, seguirán vigentes durante el tiempo que corresponda.

## 3. Naturaleza, finalidad y operaciones del tratamiento

La naturaleza del tratamiento comprende la recogida, registro, organización, conservación, consulta, utilización, modificación, comunicación por transmisión cuando sea necesaria para prestar el servicio, y supresión de los datos introducidos o generados en la plataforma.

La finalidad es permitir a la Responsable gestionar las cuentas y funciones de su escuela, incluidos sus responsables, empleados y monitores, así como la configuración de tarifas, clases, jornadas, informes y auditoría asociados al servicio.

El Encargado no utilizará los datos para fines propios ni para otros fines distintos de la prestación del servicio y de las instrucciones documentadas de la Responsable.

## 4. Interesados y categorías de datos

### 4.1 Categorías de interesados

- Empleados y monitores de la escuela.
- Responsables de la escuela.
- Clientes finales de la escuela, únicamente si la Responsable introduce sus datos en campos de texto libre de la plataforma.

### 4.2 Categorías de datos personales

- **Identificación y contacto:** nombre, apellidos y correo electrónico.
- **Credenciales y autenticación:** contraseña almacenada mediante hash y secreto de verificación en dos pasos. El uso de la verificación en dos pasos es opcional.
- **Datos laborales y de actividad:** membresía en la escuela, rol, tarifas, registros de clases y jornadas con fechas, horas, duración, importes brutos y netos, retenciones configuradas y descripciones.
- **Datos técnicos y de seguridad:** sesiones con dirección IP y nombre del dispositivo, y registro de auditoría de acciones.

No se prevé el tratamiento de categorías especiales de datos personales. La Responsable no debe introducirlas en el servicio.

## 5. Instrucciones documentadas

La Responsable instruye al Encargado para que trate los datos únicamente con la finalidad, alcance, categorías de interesados y categorías de datos descritos en este contrato y en el contrato de servicios. Las instrucciones adicionales deberán quedar documentadas, incluso por medios electrónicos.

El Encargado informará a la Responsable si, a su juicio, una instrucción infringe la normativa aplicable en materia de protección de datos. El Encargado no vendrá obligado a ejecutar la instrucción cuestionada hasta que las partes la revisen, salvo que la ley aplicable disponga otra cosa.

Si una norma de la Unión Europea o de un Estado miembro obliga al Encargado a tratar los datos al margen de las instrucciones, informará previamente a la Responsable, salvo que la norma lo prohíba por razones importantes de interés público.

## 6. Deber de confidencialidad

El Encargado garantizará que las personas autorizadas para tratar datos personales se hayan comprometido a respetar la confidencialidad o estén sujetas a una obligación legal equivalente, y que reciban instrucciones adecuadas sobre sus obligaciones. El deber de confidencialidad continuará después de finalizar su relación con el Encargado.

## 7. Medidas de seguridad

El Encargado aplicará medidas técnicas y organizativas apropiadas al riesgo conforme al artículo 32 del RGPD. Entre las medidas implantadas en el servicio se encuentran:

- Almacenamiento de contraseñas mediante hash.
- Tokens JWT firmados con RSA en cookies con atributos `HttpOnly`, `Secure` y `SameSite=Lax`.
- Verificación en dos pasos opcional.
- Separación de los datos por empresa.
- Registro de auditoría de acciones.
- Copias de seguridad diarias de la base de datos.
- Cifrado de las comunicaciones mediante HTTPS.

La Responsable reconoce que la configuración y el mantenimiento de estas medidas deben revisarse periódicamente en función de los riesgos, las características del tratamiento y la evolución del servicio.

## 8. Subencargados del tratamiento

La Responsable otorga una autorización general para que el Encargado recurra a subencargados necesarios para prestar el servicio, con la obligación de informar previamente de cualquier alta o sustitución. La Responsable podrá oponerse por motivos relacionados con la protección de datos dentro de **[PENDIENTE_DE_RELLENAR: plazo de preaviso para comunicar nuevos subencargados y plazo para formular oposición]** desde la notificación. Las partes tratarán de resolver la oposición de buena fe; si no fuera posible, la Responsable podrá resolver la parte del servicio afectada conforme al contrato de servicios.

El Encargado impondrá a cada subencargado obligaciones de protección de datos sustancialmente equivalentes a las de este contrato y seguirá siendo responsable ante la Responsable del cumplimiento de las obligaciones del subencargado.

| Subencargado y servicio | Entidad y datos de contacto |
| --- | --- |
| Proveedor de hosting y servidores para alojar y operar la plataforma | **[PENDIENTE_DE_RELLENAR: nombre, domicilio y contacto del proveedor de hosting y servidores]** |
| Proveedor de correo SMTP para el envío de correos transaccionales | **[PENDIENTE_DE_RELLENAR: nombre, domicilio y contacto del proveedor de correo SMTP]** |
| PostHog Inc., analítica de uso y grabación de sesiones, con servidor en la Unión Europea; la grabación enmascara textos y campos si esta función está activada | **[PENDIENTE_DE_RELLENAR: datos de contacto y entidad contractual de PostHog aplicables al servicio]** |

## 9. Transferencias internacionales

El Encargado no realizará transferencias de datos personales fuera del Espacio Económico Europeo salvo que la Responsable lo autorice o que exista una obligación legal. Antes de cualquier transferencia, informará a la Responsable del destino, los datos afectados, el mecanismo de transferencia y las garantías aplicables.

**[PENDIENTE_DE_RELLENAR: países de destino, mecanismo de transferencia y garantías aplicables, o confirmación de que no existen transferencias internacionales]**

## 10. Asistencia en el ejercicio de derechos

Teniendo en cuenta la naturaleza del tratamiento, el Encargado asistirá a la Responsable mediante medidas técnicas y organizativas apropiadas para que esta pueda responder a las solicitudes de ejercicio de derechos de los interesados. Si el Encargado recibe directamente una solicitud, la remitirá a la Responsable sin demora y no responderá por cuenta de esta, salvo instrucción documentada o exigencia legal.

## 11. Violaciones de seguridad de los datos personales

El Encargado notificará a la Responsable, sin dilación indebida, cualquier violación de seguridad de los datos personales de la que tenga conocimiento, aportando la información disponible para que la Responsable pueda cumplir sus obligaciones legales. La notificación se realizará en un máximo de **[PENDIENTE_DE_RELLENAR: plazo contractual de notificación]** desde que el Encargado tenga conocimiento de la violación. Como propuesta inicial, se recomienda fijar un máximo de 48 horas.

En la medida de lo posible, la notificación describirá la naturaleza de la violación, las categorías y el número aproximado de interesados y registros afectados, sus posibles consecuencias, las medidas adoptadas o propuestas y un punto de contacto.

## 12. Evaluaciones de impacto y consultas previas

El Encargado asistirá a la Responsable, teniendo en cuenta la naturaleza del tratamiento y la información a su disposición, en la realización de evaluaciones de impacto relativas a la protección de datos y en las consultas previas a la autoridad de control, cuando procedan.

## 13. Devolución y supresión de los datos

Al finalizar el servicio, la Responsable podrá solicitar la devolución de los datos personales en un formato razonablemente disponible o su supresión. El Encargado cumplirá la opción indicada en un plazo de **[PENDIENTE_DE_RELLENAR: plazo para devolver o suprimir los datos tras la terminación]**, salvo que una norma aplicable exija su conservación.

Cuando exista obligación legal de conservar datos, el Encargado los mantendrá bloqueados, con acceso restringido y únicamente durante el plazo exigido, y los suprimirá cuando dicha obligación termine. A solicitud de la Responsable, el Encargado confirmará la devolución o supresión realizada, sin perjuicio de los ciclos ordinarios de eliminación de copias de seguridad.

## 14. Auditorías e inspecciones

El Encargado pondrá a disposición de la Responsable la información razonablemente necesaria para demostrar el cumplimiento de las obligaciones de este contrato y permitirá auditorías e inspecciones realizadas por la Responsable o por un auditor independiente sujeto a confidencialidad. Las auditorías se coordinarán con antelación razonable, durante horario laboral y de forma que no afecten indebidamente a la seguridad ni a la continuidad del servicio, salvo que una incidencia o norma exija otra cosa.

Las partes acordarán **[PENDIENTE_DE_RELLENAR: preaviso, frecuencia y condiciones operativas de las auditorías, si se desean concretar]**. La Responsable asumirá los costes de sus auditorías, excepto cuando se detecte un incumplimiento imputable al Encargado o la ley disponga otra cosa.

## 15. Responsabilidad

Cada parte responderá de las obligaciones que le correspondan conforme al RGPD, este contrato y la normativa aplicable. La responsabilidad entre las partes se regirá por el RGPD y por las cláusulas de responsabilidad del contrato de servicios, sin limitar los derechos de los interesados ni las competencias de las autoridades de control.

## 16. Ley aplicable y jurisdicción

Este contrato se regirá por **[PENDIENTE_DE_RELLENAR: ley aplicable]**. Para las controversias derivadas del contrato, las partes se someten a **[PENDIENTE_DE_RELLENAR: jurisdicción y tribunales competentes]**, sin perjuicio de las normas imperativas aplicables.

## 17. Firma

Firmado en **[PENDIENTE_DE_RELLENAR: lugar de firma]**, a **[PENDIENTE_DE_RELLENAR: fecha de firma]**.

| Por la Responsable | Por el Encargado |
| --- | --- |
| Nombre: **[PENDIENTE_DE_RELLENAR: nombre de quien firma por la escuela]** | Nombre: **[PENDIENTE_DE_RELLENAR: nombre de quien firma por el prestador]** |
| Cargo: **[PENDIENTE_DE_RELLENAR: cargo de quien firma por la escuela]** | Cargo: **[PENDIENTE_DE_RELLENAR: cargo de quien firma por el prestador]** |
| Firma: | Firma: |
