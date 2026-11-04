# 16. Inventario de tests backend relacionados con empresa

Alcance: `backend/test_governance.py`, `backend/test_modules.py`, `backend/test_work_logs_supervisor.py`, `backend/test_rates.py`, `backend/test_dashboard_summary.py`, `backend/test_billing_summary.py`, `backend/tests/`. Analisis de solo lectura. No se han ejecutado tests.

## Cubierto

Rutas relativas a `backend/`. Los asserts citados son los clave.

| Fichero::test | Garantiza |
|---|---|
| test_governance.py::TestCompanyGovernance::test_manager_cannot_change_member_role | Un manager de empresa no puede cambiar el rol de un miembro a admin (403, "Solo los administradores"). |
| test_governance.py::test_platform_admin_can_change_member_role | Un admin de plataforma puede cambiar el rol de un miembro. |
| test_governance.py::test_worker_cannot_edit_rates_in_managed_company | En empresa `is_managed=True`, un worker recibe 403 al tocar sus tarifas. |
| test_governance.py::test_worker_can_edit_rates_in_autonomous_company | En empresa `is_managed=False`, el worker puede editar sus tarifas. |
| test_governance.py::test_inactive_company_blocks_access_to_non_admin | `read_company` devuelve 403 "Empresa inactiva o suspendida" a no plataforma si `is_active=False`. |
| test_governance.py::test_inactive_company_allows_access_to_platform_admin | Admin de plataforma accede a empresa inactiva. |
| test_governance.py::test_cannot_create_work_log_in_inactive_company | `create_work_log` rechaza con 403 en empresa inactiva. |
| test_governance.py::test_worker_cannot_edit_or_delete_shifts_in_managed_company | En empresa gestionada, worker recibe 403 al borrar o editar turnos. |
| test_modules.py::test_regular_user_no_company_context | Usuario sin contexto de empresa ve solo sus suscripciones personales. |
| test_modules.py::test_regular_user_active_company_id_context | Con `active_company_id`, ve personales + modulos de la empresa activa. |
| test_modules.py::test_regular_user_explicit_company_id_context | Con `company_id` explicito, ve personales + modulos de esa empresa. |
| test_modules.py::test_regular_user_explicit_company_id_not_member | Pedir modulos de empresa sin membresia da 403 "No autorizado.". |
| test_modules.py::test_regular_user_explicit_company_id_inactive_member | Membresia inactiva da 403 al pedir modulos de esa empresa. |
| test_modules.py::test_platform_admin_no_company_context | Admin de plataforma sin contexto ve el catalogo activo; excluye modulos inactivos. |
| test_modules.py::test_platform_admin_with_active_company_id_context | Admin con `active_company_id` ve solo modulos de esa empresa. |
| test_modules.py::test_platform_admin_with_explicit_company_id_context | Admin con `company_id` explicito ve solo modulos de esa empresa. |
| test_work_logs_supervisor.py::test_supervisor_with_explicit_company_id | Manager con `company_id` explicito lista turnos de todos los miembros. |
| test_work_logs_supervisor.py::test_supervisor_with_implicit_company_id | Manager sin `company_id` ve solo sus propios turnos. |
| test_work_logs_supervisor.py::test_worker_with_daily_report_module_explicit_company_id | Worker con modulo `worker_daily_report` ve turnos de la empresa solo con `company_id` explicito. |
| test_dashboard_summary.py::test_get_dashboard_summary_metrics | Metricas del dashboard (horas, net/gross de periodo, miembros activos) y lista de workers. |
| test_dashboard_summary.py::test_unauthorized_access_denied | Acceso al dashboard sin autorizacion devuelve 403. |
| test_billing_summary.py::test_manager_can_access_billing_summary | Manager accede al resumen de facturacion; calcula net/gross y horas por worker. |
| test_billing_summary.py::test_worker_cannot_access_billing_summary | Worker recibe 403 en el resumen de facturacion. |
| test_billing_summary.py::test_admin_can_access_billing_summary | Admin de plataforma accede al resumen de cualquier empresa. |
| tests/application/test_create_work_log_use_case.py::test_create_work_log_success | Alta de turno con membresia activa; calcula net 60 y gross 75 (repos en memoria). |
| tests/application/test_create_work_log_use_case.py::test_create_work_log_inactive_member_raises | Membresia inactiva impide crear turno (repos en memoria). |
| tests/application/test_two_factor_totp.py::test_reset_is_forbidden_for_non_platform_admin | Admin de empresa sin `is_platform_admin` recibe 403 al resetear 2FA de otro usuario y no se modifica nada. |
| tests/application/test_two_factor_totp.py::test_verify_2fa_rejects_full_scope_token | Un token con scope `full` no sirve para completar el 2FA (403). |
| tests/domain/test_work_log_calculation_service.py (3 tests) | Calculo de tarifas hora/dia (net a gross, extras, override manual). No depende de empresa en el dominio. |
| tests/infrastructure/test_sqlalchemy_mappers.py::test_company_mapper_bidirectional | Mapeo ida y vuelta de Company. Solo verifica mapper, no reglas. |

Nota: `backend/test_rates.py` no es un test. No tiene `def test_` y ejecuta una consulta a BD a nivel de modulo (lista miembros y `rates_config`). Al colectarse con pytest abre conexion real y no aserta nada.

## Casos que faltan

Columna "Existe?": Si, Parcial o No. "Parcial" indica que el caso solo esta cubierto en otro sentido o en otro nivel.

| Caso | Existe? | Evidencia |
|---|---|---|
| Worker crea turno propio en empresa gestionada (`is_managed=True`) | No | `routers/work_logs.py`: `is_managed` solo aparece en delete/update (lineas 262, 303). El alta no tiene guard. Regla esperada sin definir. |
| Worker crea turno en empresa autonoma | No | Sin test; `test_governance.py` solo prueba tarifas en autonoma. |
| Worker crea turno en empresa inactiva | Parcial | `test_governance.py::test_cannot_create_work_log_in_inactive_company` (solo worker, solo router). |
| Platform admin crea turno en empresa inactiva (debe permitirse) | No | Solo se prueba acceso de admin a lectura (`test_inactive_company_allows_access_to_platform_admin`). |
| Manager de empresa inactiva lee dashboard o billing | No | `test_dashboard_summary.py` y `test_billing_summary.py` no fijan `is_active`. |
| Worker lee sus turnos en empresa inactiva | No | Sin test sobre `read_work_logs` con empresa inactiva. |
| Modulos de empresa inactiva (`get_my_modules`) | No | `test_modules.py` no usa `is_active` de Company. |
| Manager actualiza empresa en PUT y cambia `is_active` o `is_managed` | No | `routers/companies.py:73-75` bloquea a no plataforma. Sin test. |
| Empresa inactiva: `update_company` de manager | No | `routers/companies.py:67` lanza 403 si inactiva. Sin test. |
| Aislamiento: manager de A pide dashboard de B | No | Solo hay tests de la empresa propia en `test_dashboard_summary.py`. |
| Aislamiento: manager de A pide billing de B | No | `test_billing_summary.py` solo usa la empresa de su setup. |
| Aislamiento: `read_work_logs(company_id=B)` como miembro de A | No | Solo se prueban empresa propia y `company_id=None`. |
| Aislamiento: `create_work_log` en B con membresia solo en A | No | Solo `test_create_work_log_inactive_member_raises` (misma empresa). |
| Aislamiento: `update_company_member` cruzado (manager de A sobre miembro de B) | No | `test_governance.py` solo usa `managed_company`. |
| Aislamiento: `update_member_status` cruzado | No | `routers/companies.py:239`. Sin test. |
| Aislamiento: modulos de empresa B con `company_id` de A | Parcial | `test_modules.py::test_regular_user_explicit_company_id_not_member` cubre usuario sin membresia, no el caso de contexto mixto. |
| Manager escala a admin de empresa (cambio de rol) | Si | `test_governance.py::test_manager_cannot_change_member_role`. |
| Manager escala a admin via `auth/switch-scope` sin membresia manager | No | `routers/auth.py:348` lanza 403. Sin test. |
| Worker cambia su propio rol | No | Solo se prueba manager y admin de plataforma. |
| Admin de empresa (`CompanyRole.admin`, no plataforma) cambia rol de miembro | No | `routers/companies.py` permite `is_company_admin`. Sin test. |
| Admin de empresa cambia `is_managed` o `is_active` | No | `routers/companies.py:73-75`. Sin test. |
| Ultimo admin de empresa: no se puede quitar o degradar | No | Grep en `routers/` y `src/` no encuentra la regla. Falta en codigo y en tests. |
| Manager desactiva miembro (`PUT .../members/{id}/status`) | No | `routers/companies.py:239`. Sin test. |
| Miembro desactivado no aparece en listado de empresas | Parcial | `test_modules.py` solo prueba `membership.is_active=False` en modulos. |
| Manager de gestionada modifica tarifas de un worker | No | `routers/companies.py:381-395`. Sin test. |
| Worker en gestionada: tarifas inmutables, pero `rates_config` ignorado al actualizar | Parcial | `test_governance.py::test_worker_cannot_edit_rates_in_managed_company` cubre el 403; no el caso de admin. |
| Cambio de `is_managed` a False reabre la edicion de tarifas | No | Sin test. |
| Manager o admin edita o borra turnos de worker en gestionada | No | Solo se prueba el 403 para worker. |
| Worker borra su propio turno en empresa autonoma | No | `routers/work_logs.py:262` solo aplica a gestionadas. |
| Platform admin crea turno en nombre de un worker | No | Sin test. |
| Usuario no miembro crea turno en empresa | No | Solo se prueba membresia inactiva. |
| Scope `impersonated` no puede crear/borrar turnos | No | `routers/work_logs.py:18` (check). Sin test. |
| Token `2fa_pending` no sirve como sesion completa | No | `routers/auth.py:111-113, 175`. Solo se prueba el rechazo de `full`. |
| Token caducado o manipulado en endpoint de empresa | No | Solo `tests/domain/test_reset_token_security.py` cubre tokens de reset. |
| `switch-scope` a empresa inactiva | No | `routers/auth.py` lanza 403 (linea de "Empresa inactiva"). Sin test. |
| `switch-scope` a empresa sin membresia | No | `routers/auth.py` lanza 403 "You are not a member". Sin test. |
| Auditoria de impersonacion al borrar turno | No | `routers/work_logs.py` llama `record_impersonation_audit`. Sin test. |
| Suscripcion de modulo `expired` o `cancelled` no devuelve el modulo | No | `test_modules.py` solo usa `status=active`. |
| Supervisor: manager de A con `company_id` de B | No | `test_work_logs_supervisor.py` solo usa su empresa. |
| Worker con `company_id` explicito sin modulo `worker_daily_report` | No | Solo se prueba el caso con modulo suscrito. |
| Dashboard: usuario con `is_active=False` | No | Sin test. |
| `test_rates.py` como test real con asserts | No | Es un script sin `def test_` y sin asserts. |

## Entorno de test

1. Runner y configuracion: `backend/pytest.ini` define `pythonpath = src .`, `testpaths = tests .`, `python_files = test_*.py` y `asyncio_mode = auto`. No hay `conftest.py` en el repo.
2. Dos estilos:
   - Los ficheros raiz `backend/test_*.py` son `unittest.TestCase`. Hacen setUp con `SessionLocal()` y datos creados a mano. No usan fixtures de pytest.
   - `backend/tests/` usa funciones pytest con fixtures locales: `fake_redis`, `stub_token_issuing` (`test_two_factor_totp.py`) y repos en memoria (`test_create_work_log_use_case.py`). `test_create_work_log_use_case` no toca BD.
3. Base de datos:
   - `database.py` lee `DATABASE_URL` al importarse. Si no existe, usa `postgresql://postgres@postgres:5432/postgres` (host `postgres`, nombre del servicio de compose).
   - `test_governance.py` fija `os.environ["DATABASE_URL"] = "sqlite:///:memory:"` al importarse y compila `JSONB` a `JSON` para SQLite. Solo surte efecto si `database.py` no se ha importado antes.
   - `pytest` colecciona en orden alfabetico. `test_auth_dev_bypass.py` importa `database` antes que `test_governance.py`. Por tanto, en una ejecucion completa de `backend/` la sqlite del governance es probablemente inefectiva y todo corre contra la BD del entorno. Esto es inferencia del codigo; no se ha ejecutado.
   - `test_modules`, `test_work_logs_supervisor`, `test_dashboard_summary` y `test_billing_summary` usan la BD real a traves de `SessionLocal`.
4. Aislamiento de datos:
   - `test_governance.py` hace `commit` en setUp y solo cierra la sesion en tearDown. No hay rollback, y los datos persisten entre ejecuciones. Usa emails con uuid para evitar colisiones.
   - `test_modules.py` hace rollback en tearDown.
   - `test_dashboard_summary.py` borra a mano en tearDown.
   - `test_billing_summary.py` y `test_work_logs_supervisor.py` no se han revisado en tearDown, solo en su setUp.
5. Comando documentado: `CLAUDE.md` indica `cd backend && pytest tests/`. Con esa ruta solo se colectan los tests de `backend/tests/`. Los ocho ficheros raiz relacionados con empresa no se ejecutan con ese comando. Para incluirlos hay que ejecutar `pytest` sin argumentos o listar los ficheros explicitamente.
6. Requisitos: los tests de BD requieren PostgreSQL 16 accesible (o `DATABASE_URL` apuntando a SQLite). No se ha verificado si el compose de dev arranca la BD para tests.
7. Verificacion: no se han ejecutado tests, como pedia la tarea. Lo afirmado sobre el orden de colecion y la BD efectiva es inferencia del codigo.
