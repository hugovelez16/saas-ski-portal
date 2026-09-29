# Estado de la Plataforma y Plan de Implementacion - Fase 2

Este documento resume el trabajo completado en las Fases 1 y 3, el estado de los Pull Requests y la guia detallada paso a paso para ejecutar la **Fase 2 (Interfaz Visual de Gobernanza y RBAC)** en una conversacion posterior.

---

## 1. Contexto y Estado Actual

Se han completado y validado en CI dos fases en ramas independientes partiendo de `develop`:

### Pull Request #3: Rediseño Data-Driven del Dashboard (Fase 3)
- **Rama**: `feat/dashboard-usuario-dinamico`
- **Version**: `0.2.0`
- **Estado**: PR abierto en GitHub ([PR #3](https://github.com/hugovelez16/saas-ski-portal/pull/3)), CI 100% superado.
- **Alcance completado**:
  - Eliminadas formulas rigidas heredadas (`days * 6` para tutoriales) y filtros binarios (`particular` / `tutorial`).
  - Panel 100% dinamico basado en `company.worklogDefinitions`.
  - Agrupacion por unidades reales (`hours`, `days`, turnos fijos o combinaciones).
  - Grafico responsivo Recharts y soporte de localizacion en espanol (`date-fns/locale/es`).

### Pull Request #4: Gobernanza de Empresas y Blindaje RBAC Backend (Fase 1)
- **Rama**: `feat/gobernanza-modo-empresa`
- **Version**: `0.3.0`
- **Estado**: PR abierto en GitHub ([PR #4](https://github.com/hugovelez16/saas-ski-portal/pull/4)), CI 100% superado.
- **Alcance completado**:
  - Migracion Alembic `8f10a2b3c4d5_anadir_is_active_e_is_managed_a_companies.py`:
    - `is_active` (Boolean, default `true`, server_default `'true'`).
    - `is_managed` (Boolean, default `false`, server_default `'false'`).
  - Modelos SQLAlchemy y esquemas Pydantic con soporte camelCase (`isActive`, `isManaged`).
  - Restriccion estricta de cambio de roles: `manager` no puede modificar roles de miembros; unicamente `admin` de empresa o `is_platform_admin`.
  - Modo empresa gestionada (`is_managed = True`): tarifas (`rates_config`) y modificacion/borrado de turnos en solo lectura para trabajadores.
  - Desactivacion de empresas (`is_active = False`): bloqueo estricto de accesos, turnos y conmutacion de ambito para no administradores.
  - Suite de pruebas de gobernanza (`backend/test_governance.py`) con 8/8 tests superados.

---

## 2. Tareas Previas al Iniciar la Fase 2

Antes de comenzar el desarrollo de la Fase 2:

1. **Merge de PRs a develop**:
   - Merge de PR #3 (`feat/dashboard-usuario-dinamico`).
   - Merge de PR #4 (`feat/gobernanza-modo-empresa`).
2. **Actualizacion local de develop**:
   ```bash
   git checkout develop
   git pull origin develop
   ```
3. **Limpieza de worktrees temporales**:
   ```bash
   git worktree remove /home/usuario/00_datos/saas-ski-portal-wt-dashboard
   git worktree remove /home/usuario/00_datos/saas-ski-portal-wt-backend
   git branch -d feat/dashboard-usuario-dinamico
   git branch -d feat/gobernanza-modo-empresa
   ```
4. **Creacion de rama para Fase 2**:
   - Nombre de rama: `feat/gobernanza-empresas-ui`
   - Opcionalmente trabajar en worktree o directamente en workspace principal una vez integrado `develop`.

---

## 3. Plan Detallado para la Fase 2 (Frontend UI)

### 3.1. Administracion de Empresas (`frontend/src/app/(app)/admin/companies`)
- **Archivos involucrados**:
  - `frontend/src/app/(app)/admin/companies/CompaniesPageClient.tsx`
  - `frontend/src/app/(app)/admin/companies/[companyId]/page.tsx`
  - `frontend/src/components/admin/company-dialog.tsx` (o modal de edicion)
  - `frontend/src/lib/api/companies.ts`
- **Requerimientos UI**:
  1. **Interruptor `isActive` (Estado de la Empresa)**:
     - Toggle switch para activar/desactivar la empresa.
     - Indicador visual claro (badge verde "Activa" vs badge gris/rojo "Inactiva/Suspendida").
     - Modal de confirmacion al desactivar: avisar que trabajadores y managers perderan acceso inmediato a turnos y gestion.
  2. **Interruptor `isManaged` (Modo Empresa)**:
     - Toggle switch para alternar entre:
       - **Modo Autonomo** (`isManaged = false`): trabajadores autogestionan tarifas y turnos.
       - **Modo Gestionado / Corporativo** (`isManaged = true`): las tarifas y turnos son controlados exclusivamente por los administradores de la empresa.
     - Texto de ayuda contextual bajo el interruptor explicando el impacto.

### 3.2. Detalle y Edicion de Usuarios (`frontend/src/app/(app)/manager/users/[userId]`)
- **Archivos involucrados**:
  - `frontend/src/app/(app)/manager/users/[userId]/page.tsx`
  - `frontend/src/app/(app)/admin/users/[userId]/page.tsx`
- **Requerimientos UI**:
  1. **Restriccion visual de cambio de rol**:
     - Si el usuario autenticado tiene rol `manager` (y no `admin` ni `is_platform_admin`):
       - El selector de rol debe sustituirse por un `Badge` no editable o un desplegable bloqueado (`disabled`).
       - Tooltip o mensaje discreto: *"Solo los administradores de la empresa o de la plataforma pueden modificar el rol del miembro."*
     - Si el usuario autenticado es `admin` de empresa o plataforma, el selector de rol permanece activo.
  2. **Proteccion de tarifas segun `isManaged`**:
     - En el perfil del trabajador (`/profile`) o en la edicion de tarifas:
       - Si la empresa activa tiene `isManaged == true`, ocultar o deshabilitar los campos de edicion de tarifas contractuales con aviso informativo.

### 3.3. Selector de Empresas en Navegacion
- **Archivos involucrados**:
  - `frontend/src/components/layout/company-switcher.tsx` (o componente equivalente)
- **Requerimientos**:
  - Las empresas con `isActive == false` no deben listarse para usuarios regulares ni managers.
  - Unicamente deben ser visibles para administradores de plataforma (`isPlatformAdmin == true`).

---

## 4. Validaciones de Calidad Obligatorias para la Fase 2

Al finalizar la implementacion de la Fase 2:
1. `npm run lint` en `frontend/` (0 errores).
2. `npx tsc --noEmit` en `frontend/` (0 errores de tipado).
3. `npm test` en `frontend/` (pruebas pasando).
4. `~/.local/bin/ruff check backend/` (si se tocan endpoints o esquemas).
5. Incremento de version SemVer en `package.json`, `frontend/package.json` y `CHANGELOG.md` (ej: `0.4.0`).
6. Solicitud de confirmacion previa al usuario antes de commits o pushes, de acuerdo con `AGENTS.md`.
