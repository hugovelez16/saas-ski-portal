# Evaluacion de librerias de calendario frente al componente propio

Fecha: 2026-11-27
Issue: #144
Reglas relacionadas: `R-ACC-62`, `R-ACC-78` ([../dominio/acceso.md](../dominio/acceso.md)), `R-TUR-19` a `R-TUR-23`, `R-TUR-31`, `R-TUR-32` ([../dominio/turno.md](../dominio/turno.md))
Estado: Propuesta pendiente de decision del usuario (sin cambios en codigo de aplicacion)

## 1. Objetivo y contexto de dominio

Evaluar si conviene adoptar **FullCalendar**, **Schedule-X** o **`@event-calendar/core` (vkurko)** frente a mantener y evolucionar el componente propio `frontend/src/components/event-calendar/` para cubrir la separacion de pantallas fijada en `R-ACC-78` (decision D8 y ronda 2, punto 1.4 de #129; S8 de [../producto/revision-base.md](../producto/revision-base.md)):

- **`/manager/calendar`**: calendario del manager para su empresa activa, con **vista de dia por defecto que actua como parte diario** (cuadrante del equipo con importes, alta en hueco horario, detalle, edicion y borrado de turnos, sin depender del modulo `worker_daily_report`) y posibilidad de cambiar a semana, mes o agenda para planificar.
- **`/daily-report`**: pantalla exclusiva del modulo de pago `worker_daily_report` ("Cuadrante compartido"), donde el worker consulta los turnos del dia de toda la empresa mostrando solo descripcion, horas y tipo, sin claves de importe y sin abrir el dialogo de detalle de turnos ajenos (`R-ACC-62`, `R-TUR-31`, `R-TUR-32`).

### Restricciones reales del producto que condicionan la eleccion

1. **Escala acotada por empresa**: los planes comerciales cubren 10 monitores (Pista Verde), 25 (Pista Azul) y hasta 50 monitores activos simultaneos (Pista Roja) ([../planes-y-precios.md](../planes-y-precios.md)), con jornadas visibles tipicas de 8 a 14 horas por dia.
2. **Modelo de turnos propio**: un turno puede tener unidad `hours` (con o sin cruce de medianoche), `days` (rango `start_date..end_date`) o `fixed` (`worklog_definitions`). No se usan reglas de recurrencia iCalendar (RFC 5545).
3. **Solapes permitidos**: dos turnos del mismo trabajador pueden solaparse (`R-TUR-23`); el cuadrante diario debe mostrarlos sin ocultarse mutuamente.
4. **Edicion con reglas de liquidacion**: cambiar horas, fechas o tipo exige respetar el `calculation_snapshot` o pedir confirmacion explicita comparando importe actual frente a nuevo (`R-TUR-19` a `R-TUR-21`). Por ello, arrastrar y soltar en el calendario se retiro de la promesa comercial en v0.26.0 (auditoria de la promesa comercial eliminada en #131, F2) y no es requisito de esta entrega.
5. **Stack del frontend**: Next.js `16.0.7` (App Router), React `19.2.0`, TypeScript 5, Tailwind CSS v4, primitivos Radix / `shadcn/ui`, `date-fns` `^3.6.0` y `@dnd-kit/core` `^6.3.1` (`frontend/package.json`).

---

## 2. Diagnostico del estado actual en el repositorio

Hoy conviven en el frontend **dos implementaciones distintas** para representar turnos en el tiempo: el calendario general (`event-calendar/`) y tres matrices horizontales de parte diario casi identicas entre si.

### 2.1. Componente `frontend/src/components/event-calendar/`

Suma **3.498 lineas** en 18 ficheros mas **137 lineas** de tests (`__tests__/calendar-config.test.tsx`), derivado de una plantilla React + Tailwind + `@dnd-kit`:

| Pieza | Ficheros y lineas | Uso real y estado |
|---|---|---|
| Contenedor y barra superior | `event-calendar.tsx` (518), `use-calendar-config.tsx` (57), `constants.ts` (15), `types.ts` (20), `index.ts` (24) | Usado en `/calendar` (159 lineas, worker) y `/manager/calendar` (283 lineas, manager), ambos con `initialView="month"`. Selector horario `Desde/Hasta` persistido en `localStorage` y callback `onRangeChange` conectado a React Query |
| Vistas mes, semana, dia y agenda | `week-view.tsx` (418), `day-view.tsx` (336), `month-view.tsx` (279), `agenda-view.tsx` (90) | Funcionales para un calendario individual. **`DayView` no agrupa por monitor/recurso**: dibuja una unica columna temporal y escalona los solapes con sangria del 10 % (`left = columnIndex * 0.1`), lo que resulta ilegible con mas de 4-5 turnos simultaneos y no deja ver que monitores estan libres |
| Eventos y utilidades | `event-item.tsx` (264), `utils.ts` (156), `use-event-visibility.ts` (85), `use-current-time-indicator.ts` (58) | Estilado nativo en Tailwind v4 con modo oscuro. `use-current-time-indicator.ts` calcula la semana con `weekStartsOn: 0` mientras `week-view` y `month-view` usan `weekStartsOn: 1`. `manager/calendar/page.tsx` asigna `color = "purple"`, no declarado en `EventColor` |
| Arrastrar y soltar (`@dnd-kit`) | `calendar-dnd-context.tsx` (376), `draggable-event.tsx` (141), `droppable-cell.tsx` (57) | **Desconectado en produccion** (574 lineas): ni `/calendar` ni `/manager/calendar` pasan `onEventUpdate`. Arrastrar lanza un toast en ingles (`Event "..." moved`) sin guardar cambios. Monta 96 `DroppableCell` en vista dia y 672 en vista semana, y aplica `touch-none` sobre los eventos, bloqueando el scroll vertical tactil cuando el gesto empieza encima de un turno |
| Dialogo y popup internos | `event-dialog.tsx` (465), `events-popup.tsx` (139) | **Codigo sin uso efectivo** (604 lineas): ambas paginas pasan `showAddButton={false}`, `onEventClick` y `onDateClick` para abrir `WorkLogDetailsDialog`, `UserCreateWorkLogDialog` y `ManagerAddWorkLogDialog` |
| Internacionalizacion y limpieza | Varios ficheros | Textos fijos en ingles (`Today`, `Month`, `Week`, `Day`, `Agenda`, `All day`, `No events found`, formatos `MMM d, yyyy` sin locale `es`) y `console.log` de depuracion activos |

### 2.2. Matrices de parte diario existentes fuera de `event-calendar/`

El repositorio **ya dispone de una vista diaria de recursos (monitores en filas x horas en columnas)** escrita en React y Tailwind, pero triplicada en tres pantallas que suman **927 lineas**:

- `frontend/src/app/(app)/manager/daily-reports/page.tsx` (401 lineas): usa `useCalendarConfig`, columna izquierda fija (`sticky left-0`) con avatar de iniciales en movil y nombre/rol/estado en escritorio, clic en celda vacia que abre `ManagerAddWorkLogDialog` precargado con usuario, fecha y tramo de 1 hora, y clic en bloque que abre `WorkLogDetailsDialog`.
- `frontend/src/app/(app)/admin/daily-reports/DailyReportPageClient.tsx` (299 lineas): variante para el PA con selector de empresa y rango fijo 8:00-20:00.
- `frontend/src/components/admin/daily-report-view.tsx` (227 lineas): tercera variante incrustada en la ficha de empresa del PA (`admin/companies/[companyId]`).

Limitaciones actuales de esas tres matrices:
1. Los turnos solapados de un mismo monitor se posicionan con `top-1 bottom-1` absoluto en la misma fila de `h-12`, tapandose entre si.
2. El tipo `tutorial` tiene horas `9..16` cableadas en cliente en lugar de apoyarse solo en `unit === "days"` / fechas del turno.
3. Las celdas de creacion son `<div>` con `onClick`, sin foco de teclado ni atributos ARIA de rejilla.

---

## 3. Comparativa objetiva de alternativas

| Criterio | FullCalendar (`@fullcalendar/*` v6.1) | Schedule-X (`@schedule-x/*` v2/v3) | `@event-calendar/core` (vkurko) | Componente propio (`event-calendar/` + cuadrante unificado) |
|---|---|---|---|---|
| **Licencia vistas basicas (dia/semana/mes)** | MIT | MIT | MIT | Propia del repositorio (sin dependencia externa) |
| **Licencia vista de recursos / monitores en SaaS comercial** | **Comercial de pago** (FullCalendar Premium / Scheduler; la licencia gratuita solo cubre entidades sin animo de lucro o evaluacion) | **Comercial de pago** (Schedule-X Premium; codigo cerrado en paquetes privados) | **MIT** (`resource-time-grid` y `resource-timeline` incluidos gratis para uso comercial) | **Sin coste de licencia** (`date-fns` y Radix son MIT) |
| **Coste economico e impacto en CI/CD** | Desde **480 USD por desarrollador** (720 USD para 2, pago unico con 1 ano de actualizaciones) + gestion de `schedulerLicenseKey` | **~479 EUR/ano** (2-3 devs) o **~999 EUR perpetua** + **token de registro npm privado** obligatorio en GitHub Actions y builds Docker | **0 EUR**, paquetes publicos en npm estandar | **0 EUR**, sin paquetes ni secretos adicionales en CI ni Docker |
| **Tamano de bundle adicional (min + gzip estimado)** | **~65-95 KB gzipped** (`core` + `react` + `daygrid` + `timegrid` + `interaction` + `resource-timeline` / `resource-timegrid`) | **~35-55 KB gzipped** (+ ~15-20 KB gzipped si requiere `temporal-polyfill` segun version) | **~35-39 KB comprimido** (cero dependencias; incluye runtime compilado de Svelte) | **0 KB de dependencias nuevas** (~10-14 KB gzipped de codigo propio tras podar ~600 lineas muertas) |
| **Compatibilidad React 19.2 y Next.js 16 (App Router / SSR)** | Buena: `@fullcalendar/react` declara soporte React 19 en `peerDependencies`. Exige `"use client"` y `next/dynamic(..., { ssr: false })` | Media: wrapper `@schedule-x/react` ligero con `"use client"` y `ssr: false`; puede requerir `overrides` o `--legacy-peer-deps` con React 19 | Media-baja en React: escrito en **Svelte**, sin paquete React oficial. Exige wrapper imperativo (`useRef` + `createCalendar` / `destroyCalendar`) y `ssr: false` | **Nativa**: Client Components en React 19.2 y TypeScript 5, sin puentes imperativos ni errores de hidratacion |
| **Integracion con Tailwind v4, `shadcn/ui` y modo oscuro** | Baja: CSS propio y variables `--fc-*`; exige hoja de adaptacion para igualar bordes, tipografia y tema oscuro | Baja: estetica Material Design 3 (`--sx-*`) distante del estilo `shadcn/ui` del portal | Media-baja: CSS propio (`.ec-*`) a sobreescribir; eventos personalizados devuelven strings HTML o nodos DOM, **no JSX** | **Total**: usa directamente las clases Tailwind, tokens CSS, `Badge`, `Popover`, `Tooltip` y dialogos del proyecto |
| **Vista de dia para cuadrante de monitores (`R-ACC-78`)** | Completa en Premium (`resourceTimelineDay` horizontal y `resourceTimeGridDay` vertical, apilado automatico de solapes) | Completa solo en Premium (`Resource Scheduler`) | Completa en MIT (`resourceTimelineDay` y `resourceTimeGridDay` con apilado de solapes) | **Ya existe base funcional** en `daily-reports` (filas x horas con cabecera fija); falta apilar solapes en subfilas e integrarla en `EventCalendar` |
| **Reutilizacion para `/daily-report` de worker (`R-ACC-62`, `R-TUR-32`)** | Posible pasando eventos sin importes y desactivando clic/edicion | Posible en Premium con configuracion de solo lectura | Posible con `editable: false` y `eventClick` condicionado | **Directa**: un mismo subcomponente React acepta `readOnly` / `onEventClick` opcional y sustituye las 3 matrices duplicadas |
| **Soporte movil y tactil** | Maduro: scroll fluido, `longPressDelay` para arrastre tactil y vistas adaptables | Correcto en vistas estandar; gestos avanzados limitados | Bueno: CSS Grid y `longPressDelay` / `eventLongPressDelay`. Sin virtualizacion de DOM (aceptable hasta 50 monitores/dia) | Responsive ya resuelto en la matriz actual (columna compacta con iniciales en movil); quitar `touch-none` del DnD inactivo restaura el scroll tactil limpio |
| **Accesibilidad (teclado y ARIA)** | **Alta**: WAI-ARIA integrado, `eventInteractive={true}`, `aria-label` automaticos | Media: navegacion por teclado basica; ARIA avanzado requiere ajustes | Media: cabeceras con `dayHeaderAriaLabelFormat`; eventos y celdas requieren `eventDidMount` manual para ARIA completo | Media hoy (botones accesibles en eventos y barra; celdas vacias sin teclado). Facil de completar con `<button>` / `role="gridcell"` en el componente propio |
| **Esfuerzo inicial** | Medio-alto (integrar plugins, licencias, CSS y adaptar formularios propios) | Alto (compra, registro npm privado en CI/Docker/worktrees y reestilado completo) | Medio (crear wrapper React imperativo, traducir renderizado de eventos a DOM/HTML y adaptar CSS) | **Bajo-medio** (unificar las 3 matrices actuales en un subcomponente de `event-calendar/`, apilar solapes, traducir a espanol y borrar codigo muerto) |
| **Mantenimiento y riesgo a medio plazo** | Bajo mantenimiento funcional; coste por asiento al crecer el equipo | Riesgo operativo en CI/builds por registro privado y coste recurrente anual | Dependencia de un unico autor principal (`vkurko`) y friccion permanente React vs DOM imperativo Svelte | Control total en el repo; al eliminar codigo muerto y triplicado, la superficie neta de codigo **disminuye** respecto a hoy |

---

## 4. Analisis detallado por opcion

### 4.1. FullCalendar (`@fullcalendar/react` + Scheduler)

**Pros:**
- Es el estandar de facto del sector: resuelve de fabrica `resourceTimelineDay` (monitores en filas) y `resourceTimeGridDay` (monitores en columnas), calculo de solapes, cruce de medianoche, zonas horarias, impresion y accesibilidad WAI-ARIA.
- Wrapper oficial `@fullcalendar/react` compatible con React 19 que permite pasar JSX dentro de `eventContent`.

**Contras:**
- La funcion que motiva esta evaluacion (cuadrante de monitores por dia para `R-ACC-78` y `/daily-report`) **no entra en la licencia MIT**: requiere FullCalendar Premium (desde 480 USD por desarrollador).
- Es la opcion mas pesada en cliente (~65-95 KB gzipped incluso cargando solo los plugins necesarios con `next/dynamic`).
- Sustituye solo la rejilla visual: todos los dialogos de negocio (`ManagerAddWorkLogDialog`, `WorkLogDetailsDialog`, avisos de recalculo `R-TUR-21` y solapes `R-TUR-23`) siguen siendo propios en `shadcn/ui`, y hay que mantener una capa de sobreescritura CSS (`--fc-*`) para no romper la coherencia visual en claro y oscuro.

### 4.2. Schedule-X (`@schedule-x/react` + Premium)

**Pros:**
- Arquitectura modular moderna y mas ligera que FullCalendar en sus vistas basicas MIT.

**Contras:**
- Al igual que FullCalendar, la vista de recursos/monitores es de pago (~479 EUR/ano o ~999 EUR perpetua).
- A diferencia de FullCalendar (cuyos paquetes npm son publicos y validan una clave), los plugins Premium de Schedule-X se distribuyen desde un **registro npm privado con token**. En este proyecto eso obligaria a inyectar secretos de autenticacion npm en `.github/workflows/ci.yml`, `deploy-dev.yml`, `deploy-prod.yml`, `frontend/Dockerfile` y en cada worktree local de Orca (`./bin/orca-setup`), rompiendo el principio de builds autonomos sin secretos externos.
- Su diseno base (Material Design 3) choca con el sistema visual `shadcn/ui` + Tailwind v4 del portal.

### 4.3. `@event-calendar/core` (vkurko Event Calendar)

**Pros:**
- **Unica libreria externa evaluada 100 % MIT** que incluye `resource-timeline` y `resource-time-grid` sin coste comercial ni restricciones para SaaS.
- Ligera (~35-39 KB comprimida), rapida en navegador y con una API de opciones inspirada en FullCalendar muy sencilla de configurar.

**Contras:**
- **Friccion arquitectonica con React 19**: esta compilada desde Svelte y no ofrece adaptador React declarativo. Cualquier contenido rico dentro de un turno o cabecera de monitor (insignia de monitor inactivo `R-TUR-27`, rol, indicador de pluses o tooltip de `shadcn/ui`) tiene que generarse concatenando strings HTML o nodos DOM manuales en `eventContent` / `resourceLabelContent`, duplicando estilos fuera de los componentes React del proyecto y exigiendo cuidado explicito contra XSS si se interpola `description` con `{ html }` en vez de `{ domNodes }`.
- Factor bus concentrado en un unico mantenedor y necesidad de mantener nosotros el wrapper imperativo de sincronizacion de opciones/ciclo de vida en Next.js (`ssr: false`).

### 4.4. Mantener y evolucionar el componente propio (`event-calendar/` + cuadrante unificado)

**Pros:**
- **Coste cero y cero dependencias nuevas**: ni licencias por desarrollador, ni suscripciones anuales, ni registros privados en CI, ni aumento del bundle de cliente.
- **Reduccion neta de deuda tecnica**: hoy existen ~3.498 lineas en `event-calendar/` (de las cuales ~604 son dialogos/popups sin uso y ~574 son un contexto DnD desconectado) mas ~927 lineas repartidas en **tres copias** de la matriz diaria (`manager/daily-reports`, `admin/daily-reports` y `daily-report-view`). Extraer una unica vista `ResourceDayView` (cuadrante horizontal monitor x hora con apilado de subfilas en solapes y banda para turnos de dia completo) dentro de `event-calendar/` y podar lo muerto deja **menos codigo total que mantener hoy** y unifica las cuatro pantallas (`/manager/calendar`, `/daily-report`, `/calendar` y la vista del PA).
- **Alineacion exacta con las reglas del dominio**: renderizado 100 % JSX con componentes `shadcn/ui`, control directo de que datos recibe y puede clicar cada rol (`R-ACC-62`, `R-ACC-78`, `R-TUR-32`), soporte natural de miembros inactivos con insignia (`R-TUR-27`) y cumplimiento sencillo del limite de 300 lineas por fichero (ADR-0007).
- **Escala perfectamente suficiente**: para 10-50 monitores y 10-24 columnas horarias (100 a 1.200 celdas ligeras en una vista de 1 dia), React 19 renderiza en pocos milisegundos sin necesidad de motores externos de virtualizacion.

**Contras:**
- La responsabilidad de corregir el apilado visual de solapes en la matriz horizontal, la localizacion al espanol y las mejoras de accesibilidad por teclado recae en el propio equipo/agentes del repositorio.
- Si en el futuro se quisiera permitir **arrastrar y redimensionar turnos entre monitores y cuartos de hora en movil y escritorio**, construir y mantener esa interaccion sobre una matriz de recursos propia seria mas costoso que activar el plugin `Interaction` de una libreria dedicada.

---

## 5. Recomendacion

### Decision recomendada: mantener y refactorizar el componente propio unificando el cuadrante diario

Se recomienda **no incorporar ninguna libreria externa ahora** y resolver `R-ACC-78` evolucionando `frontend/src/components/event-calendar/` junto con la consolidacion de la matriz diaria que ya existe en el repositorio:

1. **Integrar la vista de cuadrante por monitor en `event-calendar/`**: convertir la matriz horizontal `monitores x horas` (hoy triplicada en `manager/daily-reports`, `admin/daily-reports` y `daily-report-view`) en un componente reutilizable (dividido en ficheros de menos de 300 lineas segun ADR-0007) que calcule subfilas automaticas cuando un mismo monitor tenga turnos solapados (`R-TUR-23`) y represente de forma diferenciada los turnos de unidad `days` / cruce de medianoche sin valores fijos para `tutorial`.
2. **Cubrir `R-ACC-78` con una sola pieza**:
   - En `/manager/calendar`: `EventCalendar` arranca en `initialView="day"` mostrando el cuadrante de todos los monitores de la empresa activa (con importes, alta al pulsar hueco horario y apertura de `WorkLogDetailsDialog`), permitiendo conmutar a `week`, `month` y `agenda` para consulta/planificacion temporal.
   - En `/daily-report` (modulo `worker_daily_report`): reutiliza el mismo cuadrante diario en modo solo lectura (`readOnly`), alimentado por `GET /companies/{id}/daily-report`, sin importes y sin accion de apertura de detalle en turnos ajenos (`R-ACC-62`, `R-TUR-32`).
   - En `/calendar` (calendario individual del worker): conserva `DayView` unipersonal, `WeekView`, `MonthView` y `AgendaView`.
3. **Saneamiento incluido al tocar `event-calendar/`**:
   - Eliminar `event-dialog.tsx` (465 lineas) y `events-popup.tsx` (139 lineas) sin uso real, asi como los `console.log` residuales.
   - Desactivar o retirar `CalendarDndProvider` mientras no exista persistencia de arrastre en backend, eliminando cientos de nodos `useDroppable` innecesarios y el `touch-none` que penaliza el scroll tactil en movil.
   - Traducir controles y formatos `date-fns` a espanol (`locale: es`), unificar `weekStartsOn: 1` en `use-current-time-indicator.ts` y convertir las celdas horarias clicables en controles accesibles por teclado (`<button>` o `role="gridcell"` con `tabIndex` y `aria-label`).

### Cuando reconsiderar una libreria externa (criterio de salida)

- Si un cliente o una fase futura del producto convierte en requisito firme **mover turnos entre monitores y redimensionar su duracion arrastrando en el cuadrante** (con soporte tactil `long-press`), la primera candidata a evaluar mediante prototipo acotado es **`@event-calendar/core` (vkurko)** por su licencia MIT y bajo peso (~39 KB), asumiendo un wrapper React controlado con `domNodes`.
- **FullCalendar Premium** solo tendria sentido si mas adelante se buscase soporte comercial externo con WAI-ARIA completo y vistas multi-recurso complejas en React nativo asumiendo el coste de licencia por desarrollador (480+ USD).
- **Schedule-X** queda descartada mientras su vista de recursos exija licencia de pago distribuida por registro npm privado.
