# 05 - Router de tarifas y dashboard (backend/routers/companies.py, lineas 300-453)

Alcance: solo las lineas 300-453 de `backend/routers/companies.py`. Las funciones `is_manager_of_company`, `crud.get_company_rates`, `crud.update_company_member`, `crud.get_company_member`, `crud.get_dashboard_summary`, `schemas.CompanyMemberUpdate` y `auth.get_verified_user` estan fuera de rango. Las respuestas que dependen de ellas se marcan NO DEFINIDO.

Roles de referencia: "platform admin" = `is_platform_admin` o `role == UserRole.admin`; "company admin" = membresia activa con `role == CompanyRole.admin`; "manager" = `is_manager_of_company` (NO DEFINIDO en rango).

| Endpoint | Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|---|
| GET rates-v2 | Roles permitidos | Platform admin, manager y company admin (este ultimo segun `is_manager_of_company`). Worker recibe 403 | companies.py:306, 315-316 | El comentario de L314 dice "Admin or Manager"; la funcion es NO DEFINIDO |
| GET rates-v2 | Efecto de is_managed | Ninguno. El endpoint no lee `company.is_managed` | companies.py:302-318 | - |
| GET rates-v2 | Worker | 403 "Not authorized" | companies.py:315-316 | No puede leer tarifas ajenas. Tampoco las propias por este endpoint |
| GET rates-v2 | Manager | Devuelve la lista completa de `CompanyMemberResponse` de la empresa, con tarifas de todos los miembros | companies.py:318 | Sin filtrado de campos en el router. Esperable para un gestor |
| GET rates-v2 | Company admin | Igual que manager | companies.py:315-318 | - |
| GET rates-v2 | Platform admin | Hace bypass de `is_active` (L311) pero NO de `is_manager_of_company` (L315). Si no es miembro, 403 salvo que la funcion lo contemple | companies.py:311, 315 | HALLAZGO medio: inconsistente con dashboard-summary (L425), que si hace bypass explicito. Comprobar `is_manager_of_company` |
| GET rates-v2 | Valida company.is_active | Si, salvo platform admin. Responde 403 "Empresa inactiva" antes de comprobar membresia | companies.py:311-312 | Revela a no miembros que la empresa esta suspendida. Riesgo bajo |
| GET rates-v2 | Miembro inexistente | No aplica al endpoint. Devuelve lista (vacia si no hay miembros) | companies.py:318 | - |
| GET rates-v2 | Empresa inexistente | 404 "Company not found" antes de autorizar | companies.py:307-309 | HALLAZGO bajo: cualquier usuario autenticado puede enumerar IDs de empresa existentes (404 vs 403) |
| GET rates-v2 | Dependencia de autenticacion | `auth.get_current_user` (no exige verificacion) | companies.py:304 | HALLAZGO bajo: el dashboard usa `get_verified_user` (L411). Confirmar si la diferencia es intencionada |
| PUT members | Roles permitidos | Platform admin, company admin, manager, y el propio miembro (`is_self`). Cualquier otro: 403 | companies.py:337-349 | El 403 de L345 se evalua antes del 404 de L351 |
| PUT members | Worker editando a otro miembro | 403 | companies.py:345 | Correcto |
| PUT members | Worker: efecto de is_managed | Si `is_managed` y el worker es self: `rates_config` no nulo da 403 (L383-386); `role` no nulo da 403 (L387-390) | companies.py:382-390 | Motivo: en gestionadas las tarifas las fijan los administradores |
| PUT members | Manager: efecto de is_managed | Ninguno. El bloque L382 excluye a managers | companies.py:382 | HALLAZGO medio: un manager en empresa gestionada puede fijar sus propias tarifas y las de cualquier miembro. Contradice "tarifas fijadas por administradores" si el manager no es admin. Intencion NO DEFINIDO |
| PUT members | Company admin / platform admin: efecto de is_managed | Ninguno. Excluidos por `not is_company_admin` | companies.py:365-367, 382 | Esperado |
| PUT members | Worker en empresa NO gestionada: editar propias tarifas | Si. `ratesConfig=member_data.rates_config` pasa sin cambios | companies.py:393-395 | Confirmado a nivel router. Sin validacion de estructura |
| PUT members | Worker en empresa gestionada: ratesConfig | Si el valor es no nulo, 403 (L383-386). Si es nulo, L395 fuerza `ratesConfig=None` | companies.py:383-386, 395 | Motivo: la gestion de tarifas es de administradores. Forzar None es redundante con el 403 previo, salvo que el worker no envie ratesConfig |
| PUT members | Riesgo de ratesConfig=None en crud | Si `crud.update_company_member` asigna `rates_config` incondicionalmente, un worker que solo cambia `settings` borraria sus tarifas. Aplica a empresas gestionadas y no gestionadas | companies.py:395, 399 | HALLAZGO medio potencial. Depende de crud (NO DEFINIDO). Verificar que None se trate como "sin cambio" |
| PUT members | Worker: campos modificables | `settings` siempre (L396). `ratesConfig` segun reglas. `role` solo si coincide con el actual (L371-374). `is_active` y `sort_order` se descartan al reconstruir (L394-397) | companies.py:371-374, 393-397 | Confirmado a nivel router |
| PUT members | Worker en gestionada: role igual al actual | 403 aunque el valor no cambie | companies.py:387-390 | Incoherencia menor frente a L371-374, que solo bloquea cambios reales |
| PUT members | Manager: campos modificables | `rates_config`, `settings`, `is_active` y `sort_order` sin filtro. `role` solo si no cambia | companies.py:371-374, 393 (no aplica a managers) | HALLAZGO medio: mass assignment sin lista blanca. Un manager puede poner `is_active=false` a un company admin |
| PUT members | Company admin / platform admin: campos modificables | Todos, incluidos `role` (incluido admin), `is_active`, `sort_order` | companies.py:365-374 | Diseno: el admin puede promover a admin. Esperado |
| PUT members | Manager puede cambiar rol de alguien a admin | No. Si el rol enviado difiere del actual y el requester no es company admin, 403 | companies.py:371-378 | Confirmado. Tampoco puede cambiar el rol de un admin ni degradarlo |
| PUT members | Manager puede cambiar rol a worker o manager | No (mismo bloque) | companies.py:371-378 | - |
| PUT members | Comparacion de tipos del rol | `member_data.role` se compara con `target_role_str` (string). Si el schema usa Enum no-str, la comparacion siempre difiere. Validacion de valores validos de role NO DEFINIDO | companies.py:372-373 | NO DEFINIDO (schemas). Riesgo de falsos 403 o de valores no validos |
| PUT members | Valida estructura de rates_config | No. El router no valida. Depende de `schemas.CompanyMemberUpdate` | companies.py:325 | NO DEFINIDO. HALLAZGO medio si el schema no valida la forma del JSON |
| PUT members | Valida company.is_active | Si, para no platform admin, tambien para self. Responde 403 antes de autorizar | companies.py:334-335 | Correcto |
| PUT members | Miembro inexistente, caller autorizado | 404 "Member not found" | companies.py:351-353 | Solo se alcanza tras pasar la autorizacion |
| PUT members | Miembro inexistente, worker que no es self | 403 antes de llegar al 404 | companies.py:345, 351 | No hay oracle de existencia para workers |
| PUT members | IDOR entre empresas | `target_member` se busca con `company_id` (L351) y `crud.update_company_member` recibe `company_id` (L399). El aislamiento depende de crud | companies.py:351, 399 | NO DEFINIDO (crud). Verificar que la query filtre por empresa |
| PUT members | user_id no UUID | Sin validacion en el router. `is_self` compara strings (L338) | companies.py:338, 351 | Menor. Un valor malformado produce 404 o error de crud |
| PUT members | Fuga de informacion | `print` DEBUG en cada PUT (ids, is_manager, is_self). El 403 devuelve `is_manager`, `is_self`, `user_id` y `current_user_id` en `detail` | companies.py:340-343, 348 | HALLAZGO medio: codigo de depuracion en produccion y datos internos en la respuesta |
| PUT members | Membresia del requester | Solo cuenta membresias activas (`is_active == True`). Company admin se calcula por membresia de la empresa, no por rol global (salvo platform admin) | companies.py:356-367 | Correcto |
| PUT members | Respuesta | Devuelve `CompanyMemberResponse` del miembro actualizado, incluido su `ratesConfig` | companies.py:399-402 | - |
| GET dashboard-summary | Roles permitidos | Platform admin y manager/company admin (`is_manager_of_company`). Worker recibe 403 | companies.py:421-426 | Usa `get_verified_user` (L411) |
| GET dashboard-summary | Que ve cada rol | Worker: nada (403). Manager/company admin: agregado de la empresa completa. Platform admin: cualquier empresa | companies.py:425-426, 438-443 | Si el agregado se filtra por gestor es NO DEFINIDO (crud) |
| GET dashboard-summary | Efecto de is_managed | Ninguno | companies.py:417-450 | - |
| GET dashboard-summary | Valida company.is_active | Si, salvo platform admin. Se comprueba antes del rol | companies.py:421-423 | Correcto |
| GET dashboard-summary | Empresa inexistente | 404 antes de autorizar | companies.py:417-419 | HALLAZGO bajo: mismo oracle de existencia de empresa que rates-v2 |
| GET dashboard-summary | Aislamiento de la cache Redis | Clave `dashboard_summary:{company_id}:{start}:{end}`, sin usuario. Es seguro porque la autorizacion (L425) se ejecuta antes de leer la cache (L430) | companies.py:425, 429-431 | OK. El company_id va sin validar en la clave (riesgo minimo) |
| GET dashboard-summary | Redis caido | `redis_manager.get` (L430) queda fuera del `try`. Una excepcion da 500 | companies.py:430, 437 | HALLAZGO bajo, depende de `redis_manager` (NO DEFINIDO) |
| GET dashboard-summary | Forma de respuesta cache vs. miss | Cache devuelve JSON serializado `by_alias`. Miss devuelve `summary_data` crudo | companies.py:433, 445-446, 450 | HALLAZGO bajo: formas potencialmente distintas. FastAPI aplica `response_model` en ambos casos |
| GET dashboard-summary | Validacion de rango de fechas | El router no valida `start_date <= end_date`. `ValueError` de crud devuelve 400 | companies.py:408-409, 451-452 | NO DEFINIDO (crud) |
| GET dashboard-summary | Errores de serializacion | Los fallos de `DashboardSummaryResponse` se ignoran en silencio (except pass). Solo se pierde la cache | companies.py:444-448 | Diseno aceptable, pero oculta errores de esquema |

## Hallazgos resumidos

- HALLAZGO medio: manager puede fijar tarifas propias y ajenas en empresa gestionada (L382).
- HALLAZGO medio: mass assignment en PUT para managers. Pueden poner `is_active=false` a un company admin (L393, L399).
- HALLAZGO medio potencial: `ratesConfig=None` (L395) puede borrar tarifas si crud no lo trata como "sin cambio" (L399). NO DEFINIDO.
- HALLAZGO medio: `print` DEBUG y `detail` con datos internos (L340-343, L348).
- HALLAZGO medio: platform admin sin bypass de `is_manager_of_company` en GET rates-v2 (L315).
- HALLAZGO bajo: 404 antes de autorizar en rates-v2 y dashboard (L307-309, L417-419).
- HALLAZGO bajo: rates-v2 usa `get_current_user` y dashboard usa `get_verified_user` (L304, L411).
- HALLAZGO bajo: Redis caido da 500 en dashboard (L430).
- HALLAZGO bajo: forma de respuesta distinta entre cache y miss (L433, L450).
- NO DEFINIDO: validacion de `rates_config` y de valores de `role` (schemas, fuera de rango).
- NO DEFINIDO: aislamiento por empresa en crud (L351, L399) y filtrado del agregado por gestor (L438).
