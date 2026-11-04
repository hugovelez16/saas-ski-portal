# 03 - Router CRUD de empresas (backend/routers/companies.py, lineas 1-140)

Rutas base: `/companies`. Dependencia comun: `auth.get_verified_user` (auth.py:343-402).
`is_platform_admin` se calcula en cada handler como `token.is_admin` o `user.role == admin` de BD (companies.py:27, 47, 60, 87; auth.py:247, 283).
Ninguno de los 4 endpoints consulta `token_scope`. Solo se rechaza `scope == "2fa_pending"` (auth.py:377-378).

| Endpoint | Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|---|
| GET /companies | Dependencia de auth | `get_verified_user` | companies.py:24; auth.py:343-402 | Rechaza token vacio (401), token 2fa_pending (403), JWT invalido o en blacklist (401) |
| GET /companies | Roles que pueden | Cualquier usuario autenticado: platform admin, admin, manager, worker o sin membresia | companies.py:26-37 | Usuario sin membresia recibe lista vacia, no 403 |
| GET /companies | Platform admin | Ve todas las empresas, sin filtrar is_active | companies.py:27-28, 37 | |
| GET /companies | Empresas visibles para no admin | Solo membresias con CompanyMember.is_active=True y Company.is_active=True | companies.py:30-36 | No filtra por rol de membresia |
| GET /companies | Token scope | No comprobado. Cualquier scope distinto de 2fa_pending pasa | auth.py:343-402 | Valores de scope validos fuera de full: NO DEFINIDO (no se leyeron los emisores de token) |
| GET /companies | Usuario inactivo (User.is_active) | NO DEFINIDO | auth.py:391-393 | get_verified_user no lo comprueba; crud.get_user no se leyo |
| GET /companies | Validacion de skip/limit | Sin limite maximo ni minimo (limit=100 por defecto) | companies.py:21-22 | Un usuario puede pedir limit muy alto; skip negativo no se valida en el router |
| POST /companies | Dependencia de auth | `get_verified_user` | companies.py:45 | |
| POST /companies | Roles que pueden | Solo platform admin o usuario con role=admin en BD. Admin de empresa, manager, worker y sin membresia reciben 403 "Not authorized" | companies.py:47-49 | El chequeo es global, no por membresia |
| POST /companies | Token scope | No comprobado | companies.py:44-50 | |
| POST /companies | Campos que acepta | name, fiscal_id, tax_config, worklog_definitions, is_active, is_managed, settings | schemas.py:165-180 | Se persiste company.dict() sin filtrar |
| POST /companies | Se comprueba is_active al crear | No aplica. Se acepta is_active=false e is_managed=true en la creacion | schemas.py:173-174; crud.py:816-821 | Solo un platform admin puede llegar aqui, riesgo bajo |
| POST /companies | Validacion nombre vacio | No. `name: str` sin min_length ni strip | schemas.py:166 | "" se acepta. models.py:83 solo exige NOT NULL |
| POST /companies | Duplicado de nombre | No comprobado | companies.py:41-50; crud.py:816-821 | |
| POST /companies | Validacion/duplicado de fiscal_id | Ninguna. Columna sin unique | schemas.py:167; models.py:84 | Dos empresas pueden tener el mismo NIF/CIF |
| POST /companies | Se crea membresia admin para el creador | No. crud.create_company solo inserta Company | crud.py:816-821; companies.py:50 | El platform admin creador no queda como miembro; solo ve la empresa por ser platform admin |
| PUT /companies/{company_id} | Dependencia de auth | `get_verified_user` | companies.py:58 | |
| PUT /companies/{company_id} | company_id inexistente | 404 "Company not found" | companies.py:62-64 | |
| PUT /companies/{company_id} | company_id con UUID invalido | 404 (no 422). get_company devuelve None | crud.py:824-828; companies.py:62-64 | |
| PUT /companies/{company_id} | Empresa de otro tenant, usuario no manager | 403 si la empresa existe y esta activa. 404 si no existe | companies.py:62-71 | Filtracion de existencia: 404 vs 403 distingue empresas existentes |
| PUT /companies/{company_id} | Empresa inactiva, usuario no admin | 403 "Empresa inactiva o suspendida" antes de comprobar membresia | companies.py:66-68 | Cualquier autenticado sabe que la empresa existe y esta suspendida |
| PUT /companies/{company_id} | Empresa inactiva, platform admin | Puede actualizarla | companies.py:66 | El bloque de chequeos solo aplica a no admin |
| PUT /companies/{company_id} | Roles que pueden (no platform admin) | Manager o admin de la empresa activa del token. Worker y sin membresia: 403 | companies.py:66-69; routers/utils.py:41-53 | Admin de empresa (CompanyRole.admin) puede si el token tiene active_role admin |
| PUT /companies/{company_id} | Se comprueba membresia activa (CompanyMember.is_active) | No en BD. Solo los claims cid y role del token. Manager de A con token activo en B recibe 403 | routers/utils.py:48-52; auth.py:261-278 | El rol sale del token emitido al login. Una membresia desactivada sigue valiendo hasta expirar el token. Otra comprobacion en crud.get_user: NO DEFINIDO |
| PUT /companies/{company_id} | Campos modificables por no admin | name, fiscal_id, tax_config, worklog_definitions, settings | companies.py:73-82; schemas.py:183-190; crud.py:840-846 | |
| PUT /companies/{company_id} | Campos modificables por platform admin | Todos los de CompanyUpdate, incluidos is_active e is_managed | companies.py:66-82; schemas.py:183-190 | |
| PUT /companies/{company_id} | is_active o is_managed siendo company admin | 403 "Solo administradores de plataforma pueden modificar el estado o modo de la empresa" | companies.py:74-79 | El chequeo mira la presencia de la clave (exclude_unset). Enviar el mismo valor o null tambien da 403 |
| PUT /companies/{company_id} | Body vacio {} | 200. Devuelve la empresa sin cambios. No hay 400 | companies.py:74, 81-82; crud.py:840-851 | Para no admin el chequeo no bloquea. Solo se hace commit sin cambios |
| PUT /companies/{company_id} | name a null explicito | No se valida. setattr a None sobre columna NOT NULL: error de BD, probablemente 500 no controlado | schemas.py:184; models.py:83; crud.py:842-844 | Probable, no ejecutado |
| PUT /companies/{company_id} | name vacio "" | Aceptado | schemas.py:184 | Sin validacion |
| PUT /companies/{company_id} | Duplicados (nombre o fiscal_id) | No comprobado | companies.py:81-82; crud.py:832-851 | |
| PUT /companies/{company_id} | Log de datos personales | `print` con email del usuario y company_id en stdout | companies.py:70 | Revisar si es aceptable en logs de produccion |
| PUT /companies/{company_id} | Se comprueba company.is_active | Si, para no admin (db_company.is_active). No para platform admin | companies.py:66-68 | |
| GET /companies/detailed | Dependencia de auth | `get_verified_user` | companies.py:86 | |
| GET /companies/detailed | Platform admin | Recibe todas las empresas con todos los miembros, sin filtrar is_active | companies.py:89-90 | |
| GET /companies/detailed | Admin o manager de empresa | Empresas con membresia activa con rol manager o admin y empresa activa | companies.py:94-104, 129-136 | |
| GET /companies/detailed | Worker | Solo si tiene membresia activa y el modulo worker_daily_report activo en la empresa | companies.py:110-127 | Detalle de crud.user_has_module: NO DEFINIDO (no leido) |
| GET /companies/detailed | Filtrado por membresia | Si. CompanyMember.is_active y Company.is_active | companies.py:94-120, 129-135 | |
| GET /companies/detailed | Miembros devueltos | Todos los miembros de la empresa (joinedload sin filtrar is_active ni rol) | companies.py:132 | Un worker con el modulo ve datos de compañeros, incluidos inactivos. Filtro de CompanyWithMembers: NO DEFINIDO |
| GET /companies/detailed | Usuario sin membresia o sin modulo | 403 "Not authorized", no lista vacia | companies.py:129-138 | Inconsistente con GET /companies, que devuelve lista vacia |
| GET /companies/detailed | Token scope | No comprobado | companies.py:85-138 | Campos modificables: no aplica (solo lectura) |
