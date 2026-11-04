# 07 - Permisos de work_logs (backend/routers/work_logs.py)

Alcance: solo `backend/routers/work_logs.py` (321 lineas). Los helpers (`is_manager_of_company`, `check_manager_access`, `auth.get_verified_user`, `crud.*`, `schemas.*`, `models.*`) no se han leido: las respuestas que dependen de ellos estan marcadas como NO DEFINIDO o como inferidas.

| Endpoint | Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|---|
| POST /work-logs | Puede un worker CREAR turno si company.is_managed=true? | Si, segun este fichero. El alta no consulta is_managed; solo exige user_id == current_user.id o ser manager de la empresa | work_logs.py:31-63 | Verificar que crud.create_work_log o auth no lo bloquean; no visible aqui |
| POST /work-logs | Puede un worker crear turno de otro usuario? | No, salvo que is_manager_of_company(db, user, body.company_id) sea true | work_logs.py:49-51 | Depende del helper en routers/utils.py |
| POST /work-logs | Puede un manager crear turnos a nombre de otro usuario? | Si, si is_manager_of_company sobre body.company_id es true | work_logs.py:49-51 | Sin comprobar token_scope ni membresia activa en este fichero |
| POST /work-logs | Se valida que el user_id destino pertenezca a la empresa? | No en este fichero | work_logs.py:49-54 | NO DEFINIDO en crud; un manager puede asignar turnos a un usuario ajeno a la empresa si crud no lo valida |
| POST /work-logs | Se valida company_id del body contra la empresa activa del usuario? | No. Se usa body.company_id directamente; active_company_id solo se lee en GET | work_logs.py:40, 122 | Solo se valida existencia (404, linea 40-42) y, sin platform admin, que la empresa este activa |
| POST /work-logs | Empresa inactiva: quien puede crear? | Solo platform admin. Resto 403 "Empresa inactiva o suspendida". Manager incluido | work_logs.py:44-46 | Platform admin = is_platform_admin o role == UserRole.admin |
| POST /work-logs | Se exige membresia activa (CompanyMember.is_active) para crear? | No. El alta no consulta CompanyMember | work_logs.py:31-63 | Un ex-miembro puede crear turno propio si la empresa esta activa (salvo que is_manager_of_company lo impida) |
| POST /work-logs | company_id NULL en el body | NO DEFINIDO: depende de schemas.WorkLogCreate. Si llegara None, str(None) = "None" se pasa a crud.get_company | work_logs.py:40 | Verificar schema |
| POST /work-logs | Fechas pasadas o futuras; solapamiento de turnos | No se validan fechas ni solapes aqui. Un ValueError de crud se traduce a 400 | work_logs.py:53-63 | Deteccion de solapes NO DEFINIDO (crud) |
| POST /work-logs/bulk | Puede un worker crear en bulk si is_managed=true? | No. Requiere is_manager_of_company; is_managed no se mira | work_logs.py:84-85 | Un worker sin rol de manager recibe 403 con independencia de is_managed |
| POST /work-logs/bulk | Puede un manager crear turnos para otros usuarios? | Si, para cualquier user_id del body | work_logs.py:84-88, 96 | No valida que los user_ids pertenezcan a la empresa |
| POST /work-logs/bulk | Puede un platform admin no manager crear en bulk? | NO DEFINIDO: no hay bypass explicito; depende de is_manager_of_company | work_logs.py:84 | Asimetria con DELETE/PUT, donde si hay bypass |
| POST /work-logs/bulk | Valor devuelto y auditoria | Se usa logs.extra_data como objeto unico; si crud devolviera lista, AttributeError (500) | work_logs.py:89-100 | Verificar tipo devuelto por crud.create_work_log_bulk |
| POST /work-logs/bulk | Si crud no crea nada (logs None) | Respuesta None con response_model WorkLogResponse: fallo de validacion (500), inferido | work_logs.py:89-100 | Inferido, no probado |
| GET /work-logs | Que ve un worker sin filtros? | Solo sus propios turnos, filtrados por active_company_id | work_logs.py:121-122, 177-178 | Si active_company_id es None, el filtro de empresa lo decide crud (NO DEFINIDO) |
| GET /work-logs | Worker con modulo worker_daily_report y membresia activa en company_id: que ve? | TODOS los turnos de esa empresa (target_user_id = None) | work_logs.py:142-165, 167-168 | Expone turnos de otros trabajadores; revisar si es intencionado |
| GET /work-logs | Worker sin modulo pide turnos de otro user_id | 403 "Not authorized to view other users' logs" si check_manager_access es falso | work_logs.py:172-176 | check_manager_access NO DEFINIDO aqui |
| GET /work-logs | Manager con company_id: que ve? | Todos los turnos de la empresa; user_id opcional como filtro | work_logs.py:143-147 | Membresia activa del manager depende de is_manager_of_company |
| GET /work-logs | Platform admin: que ve? | Con user_id: ese usuario. Sin filtros: solo propios. Con company_id o fechas: todos los de la empresa | work_logs.py:125-135 | Usa solo is_platform_admin, no role == admin (inconsistente con escrituras en lineas 44, 79, 251, 292) |
| GET /work-logs | Empresa inactiva o is_managed afecta al listado? | No. El GET no consulta la empresa | work_logs.py:121-189 | Lectura permitida en empresa inactiva para todos los roles |
| GET /work-logs | Fechas start_date > end_date | No se validan | work_logs.py:111-112, 186-187 | Comportamiento NO DEFINIDO (crud) |
| GET /work-logs | Paginacion (skip, limit) | Sin tope superior ni validacion de negativos; default limit 100 | work_logs.py:106-107 | Posible volcado masivo con limit alto; verificar crud |
| GET /work-logs | Turnos con company_id NULL | Solo aparecen sin filtro de empresa; con company_id no aparecen | work_logs.py:185 | Inferido del filtro; NO DEFINIDO en crud |
| GET /work-logs | Lecturas impersonadas | No se auditan | work_logs.py:105-189 | Solo escrituras generan AuditLog |
| GET /work-logs/billing-summary | Puede un worker consultar? | No: 403 | work_logs.py:204-209 | - |
| GET /work-logs/billing-summary | Puede un manager de la empresa consultar? | Si, via is_manager_of_company | work_logs.py:204-206 | No comprueba is_active ni is_managed de la empresa |
| GET /work-logs/billing-summary | Platform admin | Si (bypass por is_platform_admin) | work_logs.py:204 | Solo is_platform_admin, no role == admin |
| GET /work-logs/billing-summary | Empresa inexistente | No hay 404; devuelve lo que retorne la funcion SQL (vacio, inferido) | work_logs.py:193-238 | NO DEFINIDO get_billing_summary (SQL) |
| DELETE /work-logs/{id} | Puede un worker borrar su turno si company.is_managed=true? | No: 403 "En empresas gestionadas los trabajadores no pueden eliminar turnos directamente" | work_logs.py:262-265 | Solo manager y platform admin pasan |
| DELETE /work-logs/{id} | Worker borra su turno en empresa no gestionada y activa? | Si, si es owner (log.user_id == user) | work_logs.py:256-260 | No se comprueba membresia activa del owner |
| DELETE /work-logs/{id} | Manager borra turnos en empresa gestionada? | Si, si is_manager_of_company(log.company_id) | work_logs.py:257, 262 | Depende del helper |
| DELETE /work-logs/{id} | Empresa inactiva | 403 para todos salvo platform admin (manager incluido). Platform admin: bypass total de owner, managed e inactiva | work_logs.py:253-260 | role == admin cuenta como platform admin aqui |
| DELETE /work-logs/{id} | Turno con company_id NULL | company = None: se omiten las guardias de empresa inactiva y gestionada; owner puede borrar. is_manager_of_company(None) NO DEFINIDO | work_logs.py:250, 253, 262 | Riesgo: turnos sin empresa escapan a las guardias |
| DELETE /work-logs/{id} | UUID invalido en la ruta | UUID() lanza ValueError sin capturar: 500, inferido | work_logs.py:245 | Deberia responder 404 o 422 |
| DELETE /work-logs/{id} | Turno inexistente | 404 "Work log not found" | work_logs.py:246-248 | - |
| DELETE /work-logs/{id} | Estado aprobado/bloqueado (aplica a todos los endpoints de escritura) | No se comprueba en ningun endpoint de escritura | work_logs.py:241-321 | NO DEFINIDO en models (verificar models.WorkLog) |
| DELETE /work-logs/{id} | Auditoria y orden de operaciones | AuditLog se commitea antes de crud.delete_work_log; si el delete falla queda auditoria sin borrado | work_logs.py:267-271 | Solo con token impersonated |
| PUT /work-logs/{id} | Puede un worker editar su turno si company.is_managed=true? | No: 403 "...no pueden modificar turnos directamente" | work_logs.py:303-306 | Solo manager y platform admin pasan |
| PUT /work-logs/{id} | Owner en empresa no gestionada y activa: puede editar? | Si, si is_owner | work_logs.py:297-306 | Ver fila siguiente sobre company_id y user_id del body |
| PUT /work-logs/{id} | Body con company_id o user_id distintos al turno original | No se validan contra el destino: la autorizacion usa log.company_id (original) pero el body puede traer otra empresa o usuario | work_logs.py:280, 291-298, 312 | Riesgo cross-tenant si crud copia company_id y user_id. NO DEFINIDO crud.update_work_log |
| PUT /work-logs/{id} | apply_to_group=true | Solo manager o platform admin; worker recibe 403 | work_logs.py:309-310 | Alcance de la cascada NO DEFINIDO (crud) |
| PUT /work-logs/{id} | ValueError de crud | No se captura: 500. Inconsistente con POST y bulk, que devuelven 400 | work_logs.py:312 (sin try) | - |
| PUT /work-logs/{id} | updated_log None | Se accede a updated_log.user_id sin comprobar: AttributeError (500), inferido | work_logs.py:312-318 | Inferido de crud no leido |
| Transversal | Rol "company admin" | No existe como rol separado aqui. Solo UserRole.admin se trata como platform admin en escrituras | work_logs.py:44, 79, 251, 292 | Verificar en models.py |
| Transversal | Membresia activa (CompanyMember.is_active) | Solo se comprueba en GET sin manager (membresia para modulo worker_daily_report). En el resto depende de helpers | work_logs.py:150-157 | NO DEFINIDO en is_manager_of_company |
| Transversal | token_scope "manager" vs "full" | No se distingue en ningun endpoint; solo "impersonated" tiene efecto (auditoria) | work_logs.py:18 | Verificar auth.get_verified_user |
