# Auditoria de la propuesta Iliberis contra el codigo

Fecha de la auditoria: 2026-10-15. Rama de trabajo: `develop`. Version del producto: 0.8.1.
Documento de referencia: `docs/propuesta-iliberis.md`.

Este fichero es la fuente de verdad de lo que el producto hace HOY frente a lo que la propuesta promete. Se actualiza cuando cambie el codigo o la propuesta. Nada de lo que figura como NO o PARCIAL debe prometerse sin reformular o implementar.

## Metodo y limites

- Lectura del codigo de backend, frontend e infraestructura, con comprobacion de los puntos criticos a mano (reset de contrasena y alta de work logs).
- Estados: OK (implementado, verificado por lectura o test), PARCIAL (existe con limites), NO (no existe), NO VERIFICADO (no se pudo comprobar).
- Tests ejecutados: `pytest tests -q` en backend, 34 passed (solo dominio). Los tests de backend que usan Postgres no se pudieron ejecutar (no hay base de datos en el entorno de auditoria). En frontend, `npx vitest run`: 85 tests pasan, 6 ficheros no cargan porque faltan `posthog-js` y `qrcode.react` en el `node_modules` local; `npx tsc --noEmit` da 7 errores por esas mismas dependencias.
- Por tanto, las conclusiones sobre roles, `is_managed`, layout, dashboard del responsable y 2FA se basan en lectura de codigo, no en tests.
- No se ha accedido a produccion: copias de seguridad, SMTP y configuracion real quedan sin verificar.

## Resumen para decidir

Funciona y se puede prometer: tipos de turno por horas, dias o importe fijo con cruce de medianoche; tarifas por monitor en bruto o neto; suplementos; retenciones SS, IRPF y "otros" con desglose; totales por monitor y tipo; calendario con vistas mes, semana, dia y agenda; alta individual y masiva (un registro para varios monitores); listado filtrable; informes PDF; CSV; 2FA.

No se puede prometer tal cual:

1. Arrastrar una clase en el calendario: es solo visual, no se guarda.
2. Alta y baja de monitores por el responsable: solo activar, desactivar y ordenar. El alta de usuarios es del administrador de plataforma.
3. "El monitor no puede modificar turnos ni tarifas": solo si la empresa tiene `is_managed=true`, que por defecto es false.
4. Recuperacion de contrasena por correo: el correo se envia pero la nueva contrasena no se guarda (falta `db.commit()` en `backend/routers/auth.py`, confirmado por lectura; `get_db` no hace commit).
5. Cambiar el correo desde el perfil del monitor.
6. Exportacion completa y gratuita de los datos de la escuela.
7. "La ve al momento": no hay avisos ni refresco automatico.
8. Cuota base, tramos de monitores y responsable adicional: no estan en el producto, se facturan fuera.
9. Eliminar la escuela en la opcion "sin mantenimiento": no existe borrado de empresa.

## Seguridad (prioridad alta)

- **S1. Aislamiento entre empresas en work logs (leer y confirmar).** `POST /work-logs` (`backend/routers/work_logs.py:31-64`) solo exige que `user_id` sea el del usuario autenticado; no comprueba que ese usuario pertenezca a `company_id`. Segun la auditoria, `PUT /work-logs` permite ademas cambiar `company_id` y `amount`. Contradice "datos separados por escuela". Pendiente de reproducir con un test.
- **S2. Reset de contrasena** no persiste (ver arriba). Ademas, impide recuperar cuentas.
- **S3. `POST /work-logs` no comprueba `is_managed`**: en una empresa gestionada, el monitor puede crearse clases propias aunque no pueda editarlas ni borrarlas.
- **S4. `/auth/dev-login`** existe; confirmar que esta deshabilitado en produccion.
- **S5. Rutas de gestion** (`/manager/*`) sin guardas por ruta en el frontend: un monitor que teclee la URL ve la interfaz. Los datos los protege el backend.
- **S6. `require_module` no se usa en ningun endpoint**: el control de modulos esta en el frontend (y en backend solo para `worker_daily_report`).

## Tabla de verificacion: backend e infraestructura

| ID | Afirmacion | Estado | Evidencia | Notas |
| --- | --- | --- | --- | --- |
| B1 | Responsable gestiona; monitor solo ve lo suyo y no modifica turnos ni tarifas | PARCIAL | `routers/work_logs.py:44-51,256-265,297-306`, `routers/companies.py:337-397`, `models.py:95` | Solo con `is_managed=true`. Con false, el monitor edita y borra sus turnos y su propia tarifa. Ver S1 y S3. |
| B2 | Alta, baja y activacion de monitores; orden de plantilla | PARCIAL | `routers/companies.py:165,190,239`, `routers/users.py:114-118` | Activar/desactivar y `sort_order`: si. Crear usuario nuevo: solo admin de plataforma. El responsable solo puede anadir a un usuario existente por correo. No hay borrado de miembro. |
| B3 | Alta individual, masiva, edicion y borrado | PARCIAL | `routers/work_logs.py:31,66,241,277` | Funciona. El bulk es solo del responsable. El trabajador gestiona sus logs mientras la empresa no sea `is_managed`. |
| B4 | Tipos de turno por horas, dias o fijo; cruce de medianoche | OK | `crud.py:104,161-186,382-386,591-595` | Si `end_time < start_time`, `end_date = start_date + 1`. Test de dominio pasa (el servicio probado no es el que usa `crud.py`). |
| B5 | Tarifas por monitor y tipo, bruto o neto | OK | `models.py:120`, `crud.py:142-143,212-222` | `rates_config[tipo]`. Sin tarifa y sin importe manual, falla. |
| B6 | Suplementos fijos o por unidad | OK | `crud.py:188-207` | Se definen por monitor, no por la escuela. |
| B7 | Retenciones configurables con desglose | PARCIAL | `crud.py:145-156,250-280`, `models.py:88` | Solo 3: Seguridad Social, IRPF y "otros". Valores de empresa con override por monitor. No hay lista libre de deducciones. |
| B8 | Cambio de tarifa no altera lo registrado | PARCIAL | `crud.py:283-296,566-613` | Cierto al crear. Editar una clase (incluido arrastrar, si se conectara) recalcula con tarifas vigentes y sobrescribe el snapshot. |
| B9 | Totales por monitor, tipo y periodo | OK | `routers/work_logs.py:192-238` | `/work-logs/billing-summary`, solo responsable o admin. |
| B10 | Recuperacion de contrasena por correo; cambio de nombre y correo | PARCIAL | `routers/auth.py:582-620`, `email_utils.py`, `schemas.py:122-125` | Envio real con `fastapi_mail` (no verificado SMTP en produccion). Reset no persiste (S2). El monitor solo cambia nombre, apellido y empresa por defecto, no el correo. |
| B11 | Modulos Informes y Parte diario del equipo | PARCIAL | `crud.py:977`, `routers/utils.py:57`, migraciones `0fb22f01dd7d`, `2314c15d1a0f` | `code_name` reales: `worker_daily_report`, `reports`, `billing`. Se activan por `ModuleSubscription`, solo por admin de plataforma. Informes es solo frontend. `billing` no se menciona en la propuesta. |
| B12 | Cuenta de responsable adicional | PARCIAL | `models.py:28-31`, `routers/companies.py:365-378` | Roles `manager` y `admin`, varios por empresa posibles. Sin limite ni logica de cobro. |
| B13 | Exportacion de datos gratuita | NO | `export-dialog.tsx`, `reports/page.tsx` | Solo CSV de listados desde el frontend. No hay exportacion completa de empresa. |
| B14 | Copias de seguridad fuera del servidor | PARCIAL | `docker-compose.prod.yml:152-172`, `.env.example:84` | Servicio `pgbackups` diario (retencion 7 dias, 4 semanas, 3 meses) en `${BACKUP_DIR:-/mnt/nas_backups/clases-vesotel}`. Que el NAS este fuera del servidor es una suposicion. Sin prueba de restauracion. |
| B15 | Cuota, tramos, mantenimiento / sin mantenimiento | NO | sin resultados en backend ni scripts | No hay calculo de tramos, ni informe de cuentas por mes, ni `DELETE /companies`. Desactivar empresa (`is_active`) la bloquea sin borrar datos. |
| B16 | Cuenta segura, 2FA | PARCIAL | `auth.py:28,409-418`, `routers/auth.py:505-556` | JWT RS256, TOTP, secreto cifrado con Fernet, reset de 2FA con auditoria. 2FA opcional, no forzado. |

## Tabla de verificacion: frontend

| ID | Afirmacion | Estado | Evidencia | Notas |
| --- | --- | --- | --- | --- |
| F1 | Panel de equipo: alta, baja, activacion, orden | PARCIAL | `app/(app)/manager/users/page.tsx:155-185,235-262` | Activar/desactivar y reordenar (con "Guardar orden"). `AddMemberDialog` solo en el panel de admin. |
| F2 | Calendario mes, semana, dia, agenda; mover arrastrando | PARCIAL | `manager/calendar/page.tsx:213-219`, `event-calendar/event-calendar.tsx:261-268,386-446` | Vistas OK con filtro por monitor. El arrastre no persiste: sin `onEventUpdate`, el evento vuelve y sale un toast en ingles. |
| F3 | Registro individual, masivo, edicion, borrado | OK | `components/work-log/manager-add-log-dialog.tsx:184-196` | "Masivo" = un mismo registro para varios monitores, no un rango de fechas. |
| F4 | Listado filtrable con CSV | PARCIAL | `manager/shifts/page.tsx:81-125`, `export-dialog.tsx`, `company-dashboard.tsx:305-335` | `/manager/shifts` filtra por monitor, fecha y tipo pero no tiene boton CSV. El CSV completo esta en el dashboard del responsable. El del monitor exporta solo lo visible y muestra el id de empresa. |
| F5 | Panel de control | PARCIAL | `dashboard-kpis.tsx`, `dashboard-charts.tsx`, `company-dashboard.tsx` | Horas, partes, monitores activos, coste bruto y neto con selector de periodo. Evolucion diaria (no semanal). No hay "coste mensual estimado" fijo ni "ultimos registros". |
| F6 | Partes diarios | OK | `manager/daily-reports/page.tsx:236-350` | Matriz por horas. El boton editar es un TODO sin accion. Los tipos "tutorial" se dibujan de 9 a 16 h. |
| F7 | Informes para imprimir o archivar | OK | `reports/page.tsx`, `PDFReport.tsx`, `CompanyPDFReport.tsx` | PDF individual y de empresa, texto copiable y CSV. `/reports/print` existe pero ningun enlace apunta a el. |
| F8 | Configuracion de tipos de turno, tarifas, suplementos y retenciones | PARCIAL | `manager/settings/page.tsx`, `manager/users/[userId]/page.tsx:672-745` | Hay UI. `/manager/settings` no esta enlazada en el menu. Suplementos en el builder: no verificado. |
| F9 | Vista del monitor: calendario, listado, resumenes, movil | PARCIAL | `calendar/page.tsx`, `dashboard/page.tsx`, `overview-v2.tsx` | Calendario, listado y dashboard por mes. El desglose esta en cada registro, no en el resumen. Sin PWA (no manifest ni service worker). Uso real en movil no verificado. |
| F10 | Perfil del monitor, recuperar contrasena, 2FA | PARCIAL | `profile/page.tsx`, `auth/forgot-password`, `auth/reset-password` | Nombre y apellidos si, correo no. Flujo forgot/reset en UI existe pero no persiste (S2). 2FA en perfil. |
| F11 | Parte diario del equipo y sus informes para el monitor | PARCIAL | `layout.tsx:35-39,128-137`, `manager/daily-reports/page.tsx` | El menu lo gobiernan las suscripciones. El monitor ve la pagina del responsable, con botones de gestion que el backend debera rechazar. |
| F12 | Comportamiento cuando el modulo no esta contratado | PARCIAL | `layout.tsx:44-79`, `reports/page.tsx:179-196` | El menu lo oculta. `/reports` avisa; `/manager/daily-reports` no. Dos fuentes distintas: suscripciones en el menu, `settings.modules` en las paginas. |
| F13 | El monitor no modifica turnos ni tarifas desde la UI | PARCIAL | `layout.tsx:151-170`, `routers/work_logs.py:262,303` | Menu por rol, sin guardas por ruta. Ver S3 y S5. |
| F14 | Aviso o refresco al asignar una clase | NO | `email_utils.py` (solo bienvenida y reset), `providers.tsx:89` | Sin correo, push ni polling. `staleTime` de 60 s. |

## Cambios de redaccion necesarios en la propuesta

Aplicar solo cuando se decida; no se han editado.

- "mover una clase arrastrandola": quitar o implementar antes.
- "alta, baja y activacion de monitores": cambiar por "activacion, baja logica y orden de la plantilla; el alta de usuarios la hace Vesotel en la puesta en marcha".
- "no puede modificar turnos ni tarifas": mantener solo si Iliberis se configura como `is_managed=true`.
- "puede cambiar su nombre y su correo": quitar "correo".
- "la ve en su calendario al momento": cambiar por "la ve en su calendario al abrir la aplicacion".
- "exportacion gratuita": mantener solo si se implementa una exportacion completa; hoy es CSV de listados.
- "4 a 5 horas al mes": indicar de donde sale o formularlo como estimacion.
- "Cuenta de responsable adicional" y "Informes 15 EUR": coherentes como oferta comercial, pero se facturan fuera del producto.
- "copias de seguridad fuera del servidor": confirmar ubicacion real del NAS y hacer una prueba de restauracion antes de prometerlo.
- Dashboard: no prometer "ultimos registros", "evolucion semanal" ni "coste mensual estimado" tal cual.

## Trabajo pendiente en producto (sin priorizar con el usuario)

Cada punto se hara en rama propia con plan previo, segun `CLAUDE.md`.

1. Corregir S1, S2 y S3 (seguridad, con tests).
2. Conectar el arrastre del calendario a `PUT /work-logs/{id}` y decidir si debe recalcular.
3. Permitir al monitor cambiar su correo (con verificacion).
4. Enlazar `/manager/settings` en el menu del responsable.
5. Exportacion completa de la empresa (usuarios, tarifas, tipos de turno, registros) para el responsable.
6. Informe de administracion: cuentas de monitor activas por empresa y mes, con tramos marginales y cuota base.
7. Eliminacion de empresa para la opcion "sin mantenimiento", con copia previa.
8. Unificar la fuente de modulos (suscripciones) y usar `require_module` en backend.
9. Avisos al asignar o cambiar una clase.
10. Unificar el nombre del producto (no prioritario; cuando la app este estable). Nombre: "Clases Vesotel", siempre con el descriptor "Gestion de escuelas de esqui" (titulo: "Clases Vesotel · Gestion de escuelas de esqui"). Vesotel es la empresa; esto es un producto suyo. Variantes actuales a sustituir:
    - "Vesotel Jornadas": landing (`frontend/src/app/page.tsx`) y mensajes de contacto (`frontend/src/lib/landing-contact.ts`).
    - "Clases Vesotel" sin descriptor: pestana (`frontend/src/app/layout.tsx`) y `login/page.tsx`.
    - "Ski Vesotel": menu lateral (`components/ui/sidebar.tsx`) e informes (`components/reports/PrintableReport.tsx`, `PDFReport.tsx`).
    - "Vesotel Work": `login/page.tsx` y `reset-password/page.tsx`.
    - "Vesotel Gestor" y "Vesotel Team": correos (`backend/email_utils.py`) y `backend/main.py`.
    - "Vesotel System": `backend/auth.py`. Comprobar antes si es un identificador interno (emisor del token); si lo es, cambiarlo invalidaria las sesiones abiertas.
    - No tocar "Vesotel Ski" de `backend/seed.py` y `backend/dev_seed.py`: es el nombre de la escuela de prueba.

## Decisiones abiertas

- Definir "cuentas existentes en cada mes" para facturar: cuenta activa a fin de mes o cualquier cuenta con actividad en el mes.
- Confirmar `is_managed=true` para Iliberis y verificarlo con una prueba real.
- Confirmar si el NAS de copias esta fuera del servidor y probar una restauracion.
