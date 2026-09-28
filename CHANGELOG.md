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
