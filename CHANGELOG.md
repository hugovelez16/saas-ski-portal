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
