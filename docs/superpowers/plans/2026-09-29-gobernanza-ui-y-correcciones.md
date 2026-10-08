# Plan de Implementacion: Gobernanza UI, Seguridad Multi-Tenant y Desacoplamiento Dinamico

> **Para trabajadores agenticos:** SUB-SKILL REQUERIDA: Utilizar subagent-driven-development o executing-plans para implementar este plan tarea por tarea. Cada tarea utiliza sintaxis de casillas de verificacion (`- [ ]`) para su seguimiento.

**Meta:** Implementar la interfaz visual de gobernanza (Fase 2 UI: `isActive`, `isManaged`, proteccion de tarifas para monitores), subsanar la fuga de datos multi-tenant en gestion de miembros y desacoplar los tipos de turno hardcodeados en informes, partes diarios y liquidaciones.

**Arquitectura:** Descomposicion en 6 modulos independientes y desacoplados a nivel de archivos, permitiendo la asignacion concurrente a subagentes de desarrollo (`frontend-dev`) que editan directamente el codigo, ejecutan linteo (`npm run lint`), comprobacion estricta de tipos (`npx tsc --noEmit`) y pruebas unitarias (`npm test`) de forma aislada.

**Pila Tecnologica:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, TanStack Query v5, Date-fns v4 (locale `es`), Vitest.

**Especificacion de Referencia:**
- [docs/FASE_2_PLAN_GOBERNANZA_UI.md](file:///home/usuario/00_datos/saas-ski-portal/docs/FASE_2_PLAN_GOBERNANZA_UI.md)
- [auditoria_integral_y_estrategia_b2b.md](file:///home/usuario/.gemini/antigravity-cli/brain/cadb2f0c-fb73-4409-8300-24e85675bf67/auditoria_integral_y_estrategia_b2b.md)

## Restricciones Globales (AGENTS.md)
- Cero emojis en codigo, comentarios, respuestas o mensajes.
- Nombres de funciones, variables y codigo en TypeScript alineados con el repositorio.
- Uso exclusivo de herramientas nativas de edicion (`replace_file_content`, `write_to_file`).
- Prohibicion estricta de git commit o git push automaticos por iniciativa del subagente sin confirmacion.

---

## Modulo 1: Seguridad Multi-Tenant y Restriccion RBAC en Ficha de Miembro

**Archivos:**
- Modificar: `frontend/src/app/(app)/manager/users/[userId]/page.tsx`
- Modificar: `frontend/src/app/(app)/manager/users/page.tsx`

**Interfaces:**
- Consume: `WorkLog` (`companyId`), `CompanyResponse` (`worklogDefinitions`, `role`), `getCompanyMembers`.
- Produce: `visibleWorkLogs` estrictamente acotado a las empresas donde el usuario en sesion actua como manager/admin.

- [ ] **Paso 1.1: Eliminar fuga de datos multi-tenant en `filteredLogs`**
  - En `frontend/src/app/(app)/manager/users/[userId]/page.tsx:473`, cambiar la base del filtro de `[...workLogs]` a `[...visibleWorkLogs]`.
  - Asegurar que `visibleWorkLogs` descarte cualquier turno sin `companyId` o con un `companyId` no perteneciente a las empresas gestionadas por el usuario.

- [ ] **Paso 1.2: Restringir selector de rol a solo lectura para managers**
  - En `frontend/src/app/(app)/manager/users/[userId]/page.tsx:193-214`, sustituir el `Select` editable de rol por un componente `Badge` con texto descriptivo ("Trabajador" / "Gestor" / "Administrador").
  - Evitar que en la mutacion de guardado `onSubmit` se envie el campo `role`, manteniendo intacto el RBAC del backend.

- [ ] **Paso 1.3: Corregir bucle de renderizado y calculo NaN en tasas**
  - Memorizar `worklogDefinitions` serializado para evitar que el `useEffect` en `CompanyMemberConfigCard` ejecute `form.reset()` en cada ciclo y borre los datos introducidos.
  - Asegurar que `taxOverrides.ss` solo se divida entre 100 si es un numero valido, enviando `null` en caso contrario para evitar inyeccion de `NaN`.

- [ ] **Paso 1.4: Auto-seleccion de empresa en listado de usuarios de manager**
  - En `frontend/src/app/(app)/manager/users/page.tsx`, si `companyIdParam` no esta presente en la URL, auto-seleccionar la primera empresa gestionada disponible para evitar columnas vacias con guiones `-`.

- [ ] **Paso 1.5: Verificacion de Modulo 1**
  - Ejecutar en `frontend/`: `npm run lint && npx tsc --noEmit`.

---

## Modulo 2: Gobernanza de Tarifas de Monitor en Perfil y Endpoint Resiliente

**Archivos:**
- Modificar: `frontend/src/lib/api/settings.ts`
- Modificar: `frontend/src/app/(app)/profile/page.tsx`

**Interfaces:**
- Consume: `Company.is_managed`, `Company.settings.is_managed`, `UserRole`, `getMyCompanies()`.
- Produce: Formulario de tarifas de perfil deshabilitado con aviso visual cuando la empresa activa esta en modo gestionado (`is_managed = true`).

- [ ] **Paso 2.1: Reparar `getUserRates` en `frontend/src/lib/api/settings.ts`**
  - Eliminar la llamada no autorizada a `/companies/detailed` que devolvia HTTP 403 a monitores sin modulo de supervision.
  - Reemplazar por lectura de `getMyCompanies()` o consulta directa a `/companies/{companyId}/members/me`.
  - Asegurar que `updateUserRates` preserve `existingSettings` para no sobreescribir `member.settings` con `None`.

- [ ] **Paso 2.2: Respetar `is_managed` en `frontend/src/app/(app)/profile/page.tsx`**
  - Detectar `isCompanyManaged = Boolean(currentCompany?.settings?.is_managed || (currentCompany as any)?.is_managed)`.
  - Si el usuario es trabajador (`role === "worker"`) y la empresa es gestionada, desactivar todos los inputs de tarifas y retenciones mediante `fieldset disabled={!canEditRates}`.
  - Ocultar o deshabilitar el boton "Guardar Tarifas" y mostrar una alerta destacada: "La administracion de esta empresa gestiona directamente los convenios y tarifas. Los valores mostrados son de solo consulta."
  - Incorporar el distintivo informativo `Badge` "Modo Gestionado" en la cabecera de la tarjeta.

- [ ] **Paso 2.3: Preservar tarifas existentes al guardar**
  - En `onRateSubmit`, clonar `existingRatesConfig` previo para no perder conceptos de turnos historicos que no esten en las definiciones activas actuales.

- [ ] **Paso 2.4: Verificacion de Modulo 2**
  - Ejecutar en `frontend/`: `npm run lint && npx tsc --noEmit && npm test`.

---

## Modulo 3: Controles Visuales `isActive` e `isManaged` en Administracion de Empresas

**Archivos:**
- Modificar: `frontend/src/components/admin/company-dialog.tsx`
- Modificar: `frontend/src/app/(app)/admin/companies/CompaniesPageClient.tsx`

**Interfaces:**
- Consume: `Company.isActive`, `Company.isManaged`, `CompanyCreate`, `CompanyUpdate`.
- Produce: Switches de activacion/desactivacion y modo gestionado con badges informativos y modales de advertencia.

- [ ] **Paso 3.1: Incorporar campos en `CompanyDialog` (`company-dialog.tsx`)**
  - Anadir campos booleanos `isActive` (default `true`) e `isManaged` (default `false`) en el esquema Zod y en el formulario.
  - Anadir switch `isManaged` ("Modo Gestionado / Modo Empresa") con explicacion: "Cuando esta activo, la direccion central gestiona los turnos y fija las tarifas; los trabajadores no pueden alterar turnos ni salarios."
  - Anadir switch `isActive` ("Estado de Empresa: Activa") visible para administradores de plataforma con advertencia en rojo si se desmarca: "Suspender la empresa bloqueara el acceso operativo y la creacion de turnos para todos sus miembros."

- [ ] **Paso 3.2: Mostrar Badges de estado en `CompaniesPageClient.tsx`**
  - Anadir columna o distintivos en la tabla de empresas:
    - Badge verde "Activa" vs Badge rojo/destructivo "Suspendida" (`isActive`).
    - Badge azul "Gestionada" vs Badge gris "Autonoma" (`isManaged`).
  - Permitir conmutar rapidamente el estado de gestion o actividad mediante switch directo o menu de acciones con confirmacion previa.

- [ ] **Paso 3.3: Verificacion de Modulo 3**
  - Ejecutar en `frontend/`: `npm run lint && npx tsc --noEmit`.

---

## Modulo 4: Desacoplamiento Dinamico en Informes y Vista de Impresion

**Archivos:**
- Modificar: `frontend/src/app/(app)/reports/page.tsx`
- Modificar: `frontend/src/app/(app)/reports/print/page.tsx`
- Modificar: `frontend/src/components/reports/PrintableReport.tsx`
- Modificar: `frontend/src/components/reports/PDFReport.tsx`
- Modificar: `frontend/src/components/reports/CompanyPDFReport.tsx`

**Interfaces:**
- Consume: `WorkLog` (`netAmount`, `grossAmount`, `duration`, `durationHours`, `startDate`, `endDate`), `Company.worklogDefinitions`.
- Produce: Calculo de horas agnostico a `'particular'` / `'tutorial'`, eliminando `days * 6` y reflejando `netAmount`/`grossAmount`.

- [ ] **Paso 4.1: Eliminar multiplicador `days * 6` y filtros rigidos**
  - En `reports/page.tsx:334-340`, `PrintableReport.tsx:34-48` y `PDFReport.tsx:313-323`, reemplazar el condicional que forzaba `days * 6` en `'tutorial'`.
  - Leer la unidad desde `company.worklogDefinitions[log.type]`:
    - Si `unit === 'hours'`, sumar horas reales registradas (`log.durationHours || log.duration`).
    - Si `unit === 'days'`, contabilizar jornadas o multiplicar por la duracion configurada de jornada si existe.
    - Si `unit === 'fixed'`, sumar servicios unitarios.

- [ ] **Paso 4.2: Sustituir `log.amount` por `netAmount` / `grossAmount`**
  - Reemplazar en todas las acumulaciones de informes y graficos `log.amount` por `log.netAmount ?? log.grossAmount ?? log.amount ?? 0` para evitar que los partes modernos muestren 0 €.

- [ ] **Paso 4.3: Conectar aislamiento en `reports/print/page.tsx`**
  - En `reports/print/page.tsx`, extraer `companyId` y `userId` de `searchParams` y propagarlos en la peticion `/work-logs` para que no imprima unicamente los datos del usuario en sesion.

- [ ] **Paso 4.4: Desglose de Bruto vs Neto en `CompanyPDFReport.tsx`**
  - En `CompanyPDFReport.tsx`, separar las metricas de Total Bruto y Total Neto, calculando retenciones estimadas de IRPF y Seguridad Social segun `company.taxConfig`.

- [ ] **Paso 4.5: Verificacion de Modulo 4**
  - Ejecutar en `frontend/`: `npm run lint && npx tsc --noEmit && npm test`.

---

## Modulo 5: Partes Diarios de Manager y Eliminacion de Fugas de Permisos

**Archivos:**
- Modificar: `frontend/src/app/(app)/manager/daily-reports/page.tsx`
- Modificar: `frontend/src/app/(app)/admin/daily-reports/DailyReportPageClient.tsx`
- Modificar: `frontend/src/components/admin/daily-report-view.tsx`

**Interfaces:**
- Consume: `Company.settings.modules.worker_daily_report`, `Company.worklogDefinitions`.
- Produce: Acceso estrictamente condicionado a rol de manager Y modulo activo (`isManager && isModuleActive`), visualizacion de turnos multidia continuos sin limitacion a `'tutorial'`, y soporte para turnos fuera de la franja 8-20h.

- [ ] **Paso 5.1: Corregir fuga de acceso y disyuncion defectuosa**
  - En `manager/daily-reports/page.tsx:87-96`, sustituir `isManager || canViewReport` por `isManager && isModuleActive` con fallback seguro a `false`:
    `const isModuleActive = Boolean(settings.modules?.worker_daily_report ?? settings.features?.worker_daily_report ?? false);`

- [ ] **Paso 5.2: Corregir desaparicion de turnos multidia en dias intermedios**
  - En `getLogsForUserAndDate` (lineas 152-163), verificar si el turno cruza dias (`startDate !== endDate` o `unit === 'days'`) independientemente de si su tipo se llama `'tutorial'` o no, renderizando el chip en todos los dias del intervalo.

- [ ] **Paso 5.3: Eliminar descarte silencioso en franjas horarias y residuos de depuracion**
  - Eliminar `if (endDecimal < 8 || startDecimal > 20) return null;` para permitir visualizar turnos tempranos y nocturnos.
  - Eliminar llamadas sincronas a `alert()` y mensajes `DEBUG` en rojo en la interfaz.

- [ ] **Paso 5.4: Verificacion de Modulo 5**
  - Ejecutar en `frontend/`: `npm run lint && npx tsc --noEmit`.

---

## Modulo 6: Precision en Liquidaciones de Manager y Desbloqueo de Ajustes

**Archivos:**
- Modificar: `frontend/src/app/(app)/manager/billing/BillingPageClient.tsx`
- Modificar: `frontend/src/components/manager/billing-table.tsx`
- Modificar: `frontend/src/components/manager/billing-breakdown-dialog.tsx`
- Modificar: `frontend/src/app/(app)/manager/settings/page.tsx`

**Interfaces:**
- Consume: `worklogDefs` (`unit: 'hours' | 'days' | 'fixed'`), `CompanyConfigurationTab`.
- Produce: Conteo exacto de servicios para tarifas fijas (`logsCount`), exportacion CSV con separador `;` y BOM para Excel en espanol, y pagina de ajustes operativa para managers.

- [ ] **Paso 6.1: Soporte de tarifas fijas (`unit: 'fixed'`) en liquidacion**
  - En `BillingPageClient.tsx:90`, si `unit === 'fixed'`, asignar `quantity = item.logsCount` (en lugar de `uniqueDays`).
  - En `billing-table.tsx` y `billing-breakdown-dialog.tsx`, mostrar `X serv.` o `X ud` para turnos fijos en lugar de rotularlos como "X dias".

- [ ] **Paso 6.2: Redondeo seguro y exportacion CSV para Excel Espana**
  - Aplicar redondeo a 2 decimales para evitar derivas de coma flotante de centimos en totales.
  - En la configuracion de `mkConfig` de CSV: anadir `useBom: true`, `fieldSeparator: ';'`, `decimalSeparator: ','` e incluir la columna "Registros".

- [ ] **Paso 6.3: Desbloquear `/manager/settings/page.tsx`**
  - Reemplazar el componente stub `ForbiddenSettingsPage` por la vista funcional que renderiza `CompanyConfigurationTab` para la empresa activa seleccionada por el manager.

- [ ] **Paso 6.4: Verificacion de Modulo 6**
  - Ejecutar en `frontend/`: `npm run lint && npx tsc --noEmit && npm test`.

---

## Verificacion Integral de la Suite y Pase de Calidad

- [ ] **Paso 7.1: Ejecucion completa de calidad en Backend**
  - `~/.local/bin/ruff check backend/` (0 errores requeridos).
  - `/home/usuario/.local/bin/uv run --with-requirements backend/requirements.txt --with pytest --with pytest-asyncio --directory backend pytest test_governance.py` (8/8 tests aprobados).

- [ ] **Paso 7.2: Ejecucion completa de calidad en Frontend**
  - `npm run lint` (0 errores requeridos).
  - `npx tsc --noEmit` (0 errores de tipado requeridos).
  - `npm test` (suite completa aprobada).

- [ ] **Paso 7.3: Auditoria final de git y gobernanza**
  - Verificar que no existan archivos residuales ni emojis.
  - Presentar reporte exhaustivo con evidencia de pruebas al usuario para su revision y confirmacion previa de commit.
