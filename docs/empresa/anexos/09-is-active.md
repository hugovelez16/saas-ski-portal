# 09 - Comprobaciones de Company.is_active (empresa suspendida)

Alcance: grep de `is_active` en `backend/*.py`, `backend/routers` y `backend/src` (sin migrations ni tests). Rutas relativas a `/home/usuario/00_datos/saas-ski-portal/`.

Distincion de campos:
- `User.is_active`: `backend/models.py:54` (cuenta de login), `backend/routers/users.py:153-162`.
- `CompanyMember.is_active`: `backend/models.py:116`, membresia usuario-empresa.
- `Company.is_active`: `backend/models.py:94` (suspension de empresa). Es el campo de este analisis.

## 1) Checks de Company.is_active (backend)

Lectura: en `backend/routers/companies.py`, el check `if not is_platform_admin and not company.is_active` es el patron habitual; los platform admin lo saltan.

- `backend/routers/auth.py:329` - switch-scope (`if not company or not company.is_active`).
- `backend/routers/companies.py:36` - GET /companies (filtro de query).
- `backend/routers/companies.py:67` - PUT /companies/{id} (bloquea a no admin).
- `backend/routers/companies.py:100-101` - GET /companies/detailed, rama supervisor (filtro).
- `backend/routers/companies.py:116-117` - GET /companies/detailed, rama worker_daily_report (filtro).
- `backend/routers/companies.py:124` - GET /companies/detailed, bucle de modulos.
- `backend/routers/companies.py:133` - GET /companies/detailed, filtro final.
- `backend/routers/companies.py:156` - GET /companies/{id}/members.
- `backend/routers/companies.py:180` - PUT /companies/{id}/members/order.
- `backend/routers/companies.py:205` - POST /companies/{id}/members/add.
- `backend/routers/companies.py:255` - PUT /companies/{id}/members/{user_id}/status.
- `backend/routers/companies.py:278` - GET /companies/{id}.
- `backend/routers/companies.py:311` - GET /companies/{id}/rates-v2.
- `backend/routers/companies.py:334` - PUT /companies/{id}/members/{user_id}.
- `backend/routers/companies.py:422` - GET /companies/{id}/dashboard-summary.
- `backend/routers/work_logs.py:45` - POST /work-logs.
- `backend/routers/work_logs.py:80` - POST /work-logs/bulk.
- `backend/routers/work_logs.py:253` - DELETE /work-logs/{id}.
- `backend/routers/work_logs.py:294` - PUT /work-logs/{id}.
- `backend/crud.py:652` - get_user_companies (filtro, include_inactive=False por defecto). Usado por GET /users/me/companies (`backend/routers/users.py:80`).
- `backend/crud.py:676` - serializa `is_active` de la empresa en la respuesta (no es check).
- `backend/src/application/use_cases/work_logs/create_work_log_use_case.py:51-52` - valida solo CompanyMember, no Company.is_active. El use case no tiene usos fuera de su fichero (codigo no conectado).

No hay checks de Company.is_active en: `backend/src/` (solo CompanyMember/User), `backend/routers/modules.py`, `backend/routers/users.py` ni `backend/auth.py` (get_verified_user / get_current_user).

Nota de reactivacion: `backend/routers/companies.py:220-221` pone `CompanyMember.is_active = True` (membresia, no empresa). No reactiva la empresa.

## 2) Comportamiento con empresa suspendida (Company.is_active = false)

Tabla: ver seccion "Tabla" mas abajo.

## 3) Quien puede reactivar

- Solo platform admin (`is_platform_admin` o `role == admin`) mediante PUT /companies/{id} con `is_active`. Evidencia: `backend/routers/companies.py:58-82`; el bloque de la linea 75 impide que un manager cambie `is_active` o `is_managed` (403 "Solo administradores de plataforma pueden modificar el estado o modo de la empresa").
- Un manager de la empresa no puede reactivarla (y ademas el check de la linea 67 le bloquea antes si la empresa esta suspendida).
- Via UI: `frontend/src/app/(app)/admin/companies/CompaniesPageClient.tsx:218-223` y `:289-294` (Switch que llama a `updateCompanyMutation` con `{ isActive }`).
- Via BD directa o scripts de sembrado: no verificado en esta tarea.

## 4) Refleja el frontend el estado de la empresa?

No, salvo en la vista de administracion de plataforma.

- `frontend/src/app/(app)/admin/companies/CompaniesPageClient.tsx:138,263` y `:158,228,303` - muestra "Activa"/"Suspendida" y permite conmutar. Unico uso de `company.isActive` como estado de empresa en la UI.
- `frontend/src/lib/types.ts:45-47` - tipo Company con `isActive?` opcional; no se usa para gating.
- `frontend/src/components/auth/scope-selection-dialog.tsx:20-23` - lista empresas via GET /companies; el filtrado lo hace el backend (`companies.py:36`). No comprueba isActive.
- `frontend/src/context/AuthContext.tsx` - sin referencias a estado de empresa.
- No hay texto "Empresa inactiva o suspendida" en `frontend/src` (grep sin resultados), por lo que el 403 del backend no se traduce a un mensaje especifico.
- `frontend/src/hooks/useModules.ts:27` y `frontend/src/components/modules/ModuleCard.tsx` usan `isActive` de modulo, no de empresa.

## Tabla

Accion con empresa suspendida | Resultado | Evidencia | Nota
--- | --- | --- | ---
Login (POST /auth/token) | PERMITE | `backend/routers/auth.py:83-160` (sin check de Company.is_active) | El login valida usuario/clave, no la empresa. Se emite token aunque la empresa este suspendida.
Emision de token con empresa por defecto suspendida | PERMITE | `backend/auth.py:254-272` (filtra solo CompanyMember.is_active) | El cid de la empresa suspendida puede quedar en el JWT.
Seleccionar empresa (POST /auth/switch-scope) | BLOQUEA | `backend/routers/auth.py:328-329` | 403 "Empresa inactiva o suspendida". Solo para no platform admin.
Peticion con token ya emitido (get_verified_user) | PERMITE | `backend/auth.py:343-400` (sin Company.is_active) | Sesiones previas siguen activas hasta que cada endpoint compruebe la empresa.
Listar empresas propias (GET /companies) | BLOQUEA | `backend/routers/companies.py:36` | La empresa suspendida desaparece del listado para no admin.
Listar empresas propias (GET /users/me/companies) | BLOQUEA | `backend/routers/users.py:80`, `backend/crud.py:652` | Filtra por include_inactive=False.
Listar empresas (GET /companies/detailed) | BLOQUEA | `backend/routers/companies.py:100-133` | Para no admin, 403 "Not authorized" si no queda ninguna empresa permitida.
Ver empresa (GET /companies/{id}) | BLOQUEA | `backend/routers/companies.py:278` | 403 "Empresa inactiva o suspendida". Platform admin permitido.
Listar turnos (GET /work-logs) | PERMITE | `backend/routers/work_logs.py:105-190` (sin check de empresa) | Fuga: el company_id o active_company_id se usa sin comprobar Company.is_active.
Crear turno (POST /work-logs) | BLOQUEA | `backend/routers/work_logs.py:45` | 403 "Empresa inactiva o suspendida".
Crear turnos masivos (POST /work-logs/bulk) | BLOQUEA | `backend/routers/work_logs.py:80` | Misma comprobacion.
Editar turno (PUT /work-logs/{id}) | BLOQUEA | `backend/routers/work_logs.py:294` | Salvo platform admin.
Borrar turno (DELETE /work-logs/{id}) | BLOQUEA | `backend/routers/work_logs.py:253` | Salvo platform admin.
Ver dashboard (GET /companies/{id}/dashboard-summary) | BLOQUEA | `backend/routers/companies.py:422` | Salvo platform admin.
Ver tarifas (GET /companies/{id}/rates-v2) | BLOQUEA | `backend/routers/companies.py:311` | Salvo platform admin.
Editar tarifas/miembro (PUT /companies/{id}/members/{user_id}) | BLOQUEA | `backend/routers/companies.py:334` | Salvo platform admin.
Listar miembros (GET /companies/{id}/members) | BLOQUEA | `backend/routers/companies.py:156` | Salvo platform admin.
Anadir miembro (POST /companies/{id}/members/add) | BLOQUEA | `backend/routers/companies.py:205` | Salvo platform admin. Reactiva CompanyMember, no la empresa (linea 220).
Cambiar estado de miembro (PUT .../members/{user_id}/status) | BLOQUEA | `backend/routers/companies.py:255` | Salvo platform admin.
Ordenar miembros (PUT /companies/{id}/members/order) | BLOQUEA | `backend/routers/companies.py:180` | Salvo platform admin.
Modulos (GET /modules/me) | PERMITE | `backend/routers/modules.py:181-262` (sin check de Company.is_active) | Devuelve modulos por suscripcion de empresa suspendida. Solo valida CompanyMember si llega company_id.
Dependencia require_module | PERMITE | `backend/routers/utils.py:58-85` (solo usuario y user_has_module) | Los endpoints protegidos por require_module no comprueban la empresa.
Billing summary (GET /work-logs/billing-summary) | PERMITE | `backend/routers/work_logs.py:192-238` (solo is_manager_of_company) | Lectura de facturacion de empresa suspendida sin check de estado.
Editar empresa por manager (PUT /companies/{id}) | BLOQUEA | `backend/routers/companies.py:67` | Salvo platform admin.
Suspender o reactivar empresa (PUT /companies/{id} con is_active) | PERMITE | `backend/routers/companies.py:58-82` (bypass para platform admin) | Solo platform admin. Un manager recibe 403 por la linea 75.
Acceso de platform admin a empresa suspendida | PERMITE | `backend/routers/companies.py:67,156,278,311,334,422` y `work_logs.py:45,80,253,294` (is_platform_admin salta el check) | Diseno intencionado: el admin puede consultar y reactivar.
Perfil propio (GET /users/me) | PERMITE | `backend/routers/users.py:26-50` (solo calcula flags de membresia) | No comprueba estado de empresa.
Crear turno via use case (create_work_log_use_case) | NO DEFINIDO | `backend/src/application/use_cases/work_logs/create_work_log_use_case.py:51-52` | Codigo sin usos fuera del fichero: solo valida CompanyMember. No verificado si esta planeado.
Refresh de token (POST /auth/refresh) | NO DEFINIDO | `backend/routers/auth.py:230` | No leido en esta tarea; no se comprueba que la empresa siga activa en el codigo leido.
Frontend: bloqueo visible de empresa suspendida | NO DEFINIDO | `frontend/src/context/AuthContext.tsx`, `frontend/src/components/auth/scope-selection-dialog.tsx:20-23` | El frontend no lee el estado de empresa. Los 403 del backend no tienen mensaje especifico (sin texto "Empresa inactiva" en frontend/src).
