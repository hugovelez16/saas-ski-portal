# Registro de Cambios (CHANGELOG)

Todos los cambios notables en este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y se rige por las directivas de **Versionado Semantico (SemVer)**.

---

## Estandar de Versionado Semantico

El formato sigue el estandar Semantic Versioning utilizando 3 numeros separados por un punto:
`PRINCIPAL.MENOR.PARCHE` (o `MAJOR.MINOR.PATCH`)

- **MAJOR (Principal)**: Cambios incompatibles con versiones anteriores (rompe la API o modelo de datos no migrado).
- **MINOR (Menor)**: Nuevas funcionalidades compatibles con versiones anteriores.
- **PATCH (Parche)**: Correcciones de errores y bugs compatibles.
- **Desarrollo Inicial**: El desarrollo inicial utiliza una version principal `0` (ej: `0.y.z`).
- **Reinicio de contadores**: Al aumentar MINOR, PATCH se restablece a 0; al aumentar MAJOR, MINOR y PATCH se restablecen a 0.

---

## [0.7.0] - 2026-10-05

### Tipo de Cambio SemVer

- **MINOR**: Integracion de analitica de producto con PostHog: inyeccion en build-time, inicializacion condicionada a la clave e identificacion de usuario sin datos personales.

### Funcionalidades y Mejoras

- **Analitica (`frontend/src/components/providers.tsx`)**:
  - Inicializacion de `posthog-js` solo si `NEXT_PUBLIC_POSTHOG_KEY` esta definida; sin clave no hace nada (desarrollo y tests).
  - Host por defecto `https://eu.i.posthog.com`, perfiles solo para usuarios identificados y grabacion de sesion con enmascarado de campos.
  - **Pageviews en SPA**: `capture_pageview: "history_change"` para capturar cambios de ruta en App Router sin reloads.
  - **Sanitizacion de URLs**: helper `sanitizeEvent` elimina query string y fragmentos en `$current_url`, `$referrer`, `$initial_current_url`, `$initial_referrer` (con tolerancia a valores no-URL) para evitar filtrar tokens en URLs como `/reset-password?token=...`.
  - **Proteccion en pagina de reset**: `disable_session_recording` desactiva la grabacion en `/reset-password` para no capturar el token en la sesion.
  - **Privacidad**: `persistence: "memory"` (sin almacenamiento entre sesiones) y `maskTextSelector: "*"` (enmascarado total de texto en replay).
- **Ciclo de vida de autenticacion (`frontend/src/context/AuthContext.tsx`)**:
  - `posthog.identify` con el id de usuario, el rol y el id de empresa; no se envia email ni nombre.
  - `posthog.reset` al cerrar sesion.
- **CI/CD**:
  - `frontend/Dockerfile` y workflows `deploy-dev.yml` y `deploy-prod.yml` pasan `NEXT_PUBLIC_POSTHOG_KEY` y `NEXT_PUBLIC_POSTHOG_HOST` como `build-args`.
- **Pruebas**: tests de vitest para `Providers` y `AuthProvider` (caso sin clave, identify y reset).

---

## [0.6.0] - 2026-09-29

### Tipo de Cambio SemVer

- **MINOR**: Renovacion integral del Dashboard de Gestores con operativa en tiempo real, KPIs adaptativos, cache Redis e implementacion de bypass de autenticacion para desarrollo local.

### Funcionalidades y Mejoras

- **Dashboard de Gestores Modular (`frontend/src/components/manager/`)**:
  - `DashboardTodayCard`: Panel de operativa en tiempo real con conteo de monitores activos, horas programadas, resumen de tipos de turnos y listado cronologico de la jornada.
  - `DashboardKpis`: Selector de periodo (Hoy, Semana, Mes, Mes Anterior, Temporada, Personalizado) y tarjetas de KPIs adaptativas. Si la empresa no distingue bruto y neto, presenta una metrica unificada de liquidacion sin duplicar cifras.
  - `DashboardCharts`: Graficos dinamicos con Recharts y selector de metrica (Horas vs Coste). Muestra distribucion por servicios si hay 2+ tipos de turnos activos, o carga semanal acumulada por dias si hay 1 solo tipo.
  - `DashboardTeamTable`: Resumen de plantilla respetando el orden definido por el gestor (`sort_order`), eliminando clasificaciones de tipo ranking.
  - `DashboardHeaderActions`: Barra de acciones con boton principal para añadir partes de trabajo y exportacion en formato CSV.
- **Gestion y Administracion de Empresas**:
  - Ordenacion inteligente de empresas: activas primero y suspendidas al final, con ordenacion alfabetica secundaria.
  - Creacion de funcion de utilidad `formatPercentage` para evitar artefactos de punto flotante IEEE-754 en tipos de Seguridad Social.
  - Traduccion al espanol de todos los dialogos y componentes de administracion.
- **Backend y Rendimiento**:
  - Nuevo endpoint analitico `GET /companies/{company_id}/dashboard-summary` con agregacion optimizada de metricas del periodo, jornada actual y desglose por trabajador.
  - Integracion de cache Redis con TTL de 300 segundos e invalidacion reactiva ante mutaciones de partes de trabajo y cambios en ordenacion de miembros.
  - Manejo robusto de claves RSA no encriptadas en entornos locales de desarrollo.
- **Bypass de Desarrollo y Auto-Login**:
  - Creacion del modulo `dev_seed.py` para sembrado y garantia de existencia del usuario administrador (`admin@vesotel.com`) y empresa predeterminada.
  - Endpoints dedicados `GET /api/auth/dev-status` y `POST /api/auth/dev-login` para emision directa de cookies de sesion HttpOnly sin credenciales en entorno local.
  - Integracion en frontend (`AuthContext.tsx` y `LoginPage`) para detectar modo desarrollo, iniciar sesion automaticamente y auto-recuperar la sesion ante reinicios del backend (error 401).
- **Seguridad**:
  - Variable `ENCRYPTION_KEY` eliminada de la plantilla `env.example`; se documenta como comentario el comando para generarla.
- **Suite de Pruebas**:
  - Nuevos tests frontend en `manager-dashboard.test.tsx`, `companies.test.ts` y `utils.test.ts` (85 pruebas unitarias passing).
  - Nuevos tests backend en `test_dashboard_summary.py` (calculo de metricas, control de acceso y RBAC).
  - Pruebas de bypass de desarrollo y optimizaciones de compilacion frontend.

---

## [0.5.0] - 2026-09-29

### Tipo de Cambio SemVer

- **MINOR**: Transicion estructural a Arquitectura Hexagonal (Puertos y Adaptadores) y Clean Architecture, desacoplamiento del motor de calculo salarial y fiscal en capas de dominio puras, proteccion de endpoints y saneamiento contra replay attacks.

### Funcionalidades y Mejoras

- **Arquitectura Hexagonal en Backend (`backend/src/`)**:
  - Implementadas entidades de dominio puras (`User`, `Company`, `CompanyMember`, `WorkLog`) y Value Objects inmutables (`Money`, `WorkDuration`, `TaxConfiguration`, `RateDefinition`, `CalculationSnapshot`).
  - Creado `WorkLogCalculationService` para liquidacion de jornadas y retenciones impositivas, 100% aislado de SQLAlchemy, FastAPI y Redis.
  - Definidos puertos abstractos de repositorio (`UserRepositoryPort`, `CompanyRepositoryPort`, `WorkLogRepositoryPort`).
  - Desarrollados casos de uso de aplicacion (`CreateWorkLogUseCase`).
  - Implementados adaptadores y mappers de persistencia bidireccionales (`SqlAlchemyUserMapper`, `SqlAlchemyCompanyMapper`, `SqlAlchemyWorkLogMapper`, `SqlAlchemyWorkLogRepository`, `SqlAlchemyUserRepository`, `SqlAlchemyCompanyRepository`).
- **Seguridad, Autenticacion y Endpoints**:
  - Protegido el endpoint `GET /companies` requiriendo autenticacion obligatoria con `auth.get_verified_user` y filtrado multi-tenant por rol.
  - Subsanada vulnerabilidad de replay attack en reseteo de contrasenas mediante un solo uso de `jti` en tokens criptograficos.
  - Prevenido bypass de 2FA en incorporacion de miembros de empresa (`add_company_member`).
- **Clean Architecture en Frontend (`frontend/src/`)**:
  - Implementados Value Objects (`Money.ts`), entidades de dominio (`WorkLog.ts`) y servicios de calculo mensuales desacoplados (`WorkLogCalculationService.ts`).
  - Creado cliente HTTP tipado (`AxiosHttpClient.ts`) implementando el puerto `IHttpClient.ts`.
  - Desarrollados mappers (`WorkLogMapper.ts`) y repositorios API (`ApiWorkLogRepository.ts`).
- **Aseguramiento de Calidad**:
  - 100% de aprobacion en las suites de pruebas automatizadas en Pytest (backend) y Vitest (frontend).

---

## [0.4.0] - 2026-09-29

### Tipo de Cambio SemVer

- **MINOR**: Gobernanza visual de empresas (Fase 2 UI), aislamiento multi-tenant en supervision de miembros, desacoplamiento dinamico de turnos en partes, liquidaciones e informes PDF/impresion.

### Funcionalidades y Mejoras

- **Gobernanza de Empresas en UI**:
  - Incorporados switches y distintivos visuales de estado (Activa vs Suspendida, Gestionada vs Autonoma) en el panel de administracion de empresas (`CompaniesPageClient.tsx`) y dialogo de alta (`CompanyDialog.tsx`).
  - Incorporado alternador entre vista de tarjetas y vista de lista compacta con persistencia permanente en `localStorage` (`admin_companies_view_mode`).
  - Posibilidad de conmutar directamente el estado operativo y de gestion con persistencia inmediata.
- **Seguridad Multi-Tenant y Restriccion RBAC**:
  - Corregida fuga de datos en la vista de detalle de trabajador (`manager/users/[userId]/page.tsx`), garantizando que los registros filtrados pertenezcan estrictamente al conjunto de empresas visibles.
  - Bloqueada la alteracion no autorizada de roles en la edicion de miembros por parte de managers mediante conversion del selector a distintivo informativo de solo lectura.
  - Subsanado error de tipo en base de datos al activar/desactivar miembros con normalizacion booleana estricta y soporte para administradores de plataforma con contexto activo.
  - Protegida la configuracion de tasas contra valores invalidos (NaN) y solventado el bucle de renderizado en `CompanyMemberConfigCard`.
  - Auto-seleccion de la primera empresa gestionada en el panel de supervision de miembros (`manager/users/page.tsx`).
- **Gobernanza de Tarifas en Perfil**:
  - Resuelto error 403 Forbidden para trabajadores en la consulta de tarifas mediante eliminacion de dependencia con `/companies/detailed`.
  - Deteccion de modo gestionado en perfil de usuario con desactivacion de formulario, aviso informativo destacado y preservacion de configuraciones existentes.
- **Liquidaciones y Partes Diarios**:
  - Correccion en el conteo de servicios fijos (`unit === 'fixed'`) usando `logsCount` en lugar de `uniqueDays` en el resumen mensual de facturacion.
  - Formato de exportacion CSV compatible con hojas de calculo en Espana (separador punto y coma, coma decimal y codificacion BOM UTF-8).
  - Sustitucion de la pagina bloqueante de ajustes de manager por el panel completo de configuracion de escuela (`CompanyConfigurationTab`).
  - Soporte de turnos por rango de fechas (multidia) en partes diarios diarios para cualquier tipo configurado, sin restriccion estatica a turnos 'tutorial'.
  - Eliminacion de texto de depuracion y limites rigidos que descartaban franjas horarias tempranas o nocturnas.
- **Informes, Impresion y Exportacion**:
  - Erradicado el multiplicador fijo de 6 horas para tutoriales en informes visuales e impresion.
  - Calculo financiero basado en los campos efectivos de importes netos y brutos (`netAmount`, `grossAmount`).
  - Habilitado el filtrado por empresa y trabajador en la vista de impresion `/reports/print`.
  - Redisenado el informe PDF corporativo (`CompanyPDFReport.tsx`) con desglose de retenciones estimadas de IRPF y Seguridad Social segun `taxConfig`.

---

## [0.3.0] - 2026-09-28

### Tipo de Cambio SemVer

- **MINOR**: Gobernanza de empresas, modo empresa gestionada vs autonoma, control de actividad y restricciones estrictas RBAC.

### Funcionalidades y Mejoras

- **Base de Datos y Modelos**:
  - Migracion Alembic reversible \`8f10a2b3c4d5_anadir_is_active_e_is_managed_a_companies\` que anade columnas \`is_active\` e \`is_managed\` a la tabla \`companies\`.
  - Actualizados modelos SQLAlchemy y esquemas Pydantic con soporte camelCase (\`isActive\`, \`isManaged\`).
- **Gobernanza y RBAC**:
  - Restriccion estricta en cambio de roles: Se elimina la posibilidad de que un manager altere el rol de un usuario. Solo los administradores de empresa o administradores de plataforma pueden modificar roles.
  - Modo Empresa Gestionada (\`is_managed = True\`): Los trabajadores tienen sus tarifas (\`rates_config\`) en solo lectura y no pueden alterar turnos directamente.
  - Desactivacion de Empresa (\`is_active = False\`): Bloqueo total de operaciones, conmutacion de ambito y registro de turnos para usuarios regulares, permitiendo acceso administrativo unicamente a la administracion de plataforma.
- **Suite de Pruebas**:
  - Cobertura completa de politicas de gobernanza con \`test_governance.py\` (8/8 pruebas unitarias superadas).

---

## [0.2.0] - 2026-09-28

### Tipo de Cambio SemVer

- **MINOR**: Rediseño data-driven completo del dashboard de usuario y calculo dinamico de turnos laborales.

### Funcionalidades y Mejoras

- **Dashboard de Usuario Data-Driven**:
  - Eliminado el calculo estatico obsoleto de 6 horas por dia para turnos tutoriales (`days * 6`).
  - Agrupacion automatica y dinamica de metricas segun las unidades configuradas en la empresa (`hours`, `days`, turnos fijos o combinaciones hibridas) leyendo de `company.worklogDefinitions`.
  - Sustitucion de la tarta binaria rigida por tarjetas de ingresos y actividad real desglosada por tipo de turno.
  - Grafico de area interactivo y responsivo con Recharts adaptado a la tendencia mensual.
  - Internacionalizacion completa de fechas con soporte regional en espanol (`date-fns/locale/es`).

---

## [0.1.0] - 2026-09-24

### Tipo de Cambio SemVer

- **MINOR**: Version inicial del portal SaaS Ski (saas_ski_vesotel) con autenticacion, gestion de monitores, clases, jornadas y despliegue CI/CD en Komodo.

### Funcionalidades Iniciales

- **Arquitectura Monorepo y Gateway**:
  - Pasarela Nginx (gateway) unificando frontend Next.js en `/` y backend FastAPI en `/api/`.
  - Configurado entorno de desarrollo y produccion con Docker Compose.
- **Backend (FastAPI)**:
  - Modulos de autenticacion JWT y gestion de sesiones.
  - CRUD de usuarios, empresas, partes de trabajo (work logs) y modulos.
  - Base de datos PostgreSQL con migraciones Alembic y cache Redis.
- **Frontend (Next.js 16 / React 19)**:
  - Panel administrativo, planificador interactivo, gestion de monitores y partes.
  - Componentes de diseno accesibles con Tailwind CSS y Radix UI.
- **Pipelines CI/CD (GitHub Actions)**:
  - Flujo de integracion continua con linters, pruebas unitarias y comprobacion de tipos.
  - Workflows de despliegue continuo para desarrollo (`deploy-dev.yml`) y produccion (`deploy-prod.yml`) hacia Komodo con publicacion de imagenes en GHCR etiquetadas mediante SemVer.
