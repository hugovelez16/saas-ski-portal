# 18 - Seeds, arranque y get_billing_summary

Repo: /home/usuario/00_datos/saas-ski-portal (solo lectura). Sin valores de .env.

| Pregunta | Respuesta | Evidencia | Nota |
|---|---|---|---|
| 1. Como se crea la primera empresa y el primer admin | Solo si INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD estan definidos y el email no existe: crea Company (nombre INITIAL_COMPANY_NAME, por defecto "Vesotel Ski School"), User role=admin, CompanyMember role=manager y ModuleSubscription para cada AppModule activo | backend/seed.py:24-28, 46-98, 100-126 | Si la empresa ya existe por nombre se reutiliza sin tocar su configuracion |
| 1a. Defaults de la empresa: is_managed / is_active | is_managed False y is_active True (defaults de modelo; seed.py no los fija) | backend/models.py:94-95 | |
| 1b. Defaults de la empresa: tax_config | {"social_security": 0.0648} | backend/seed.py:54 | Igual que default de modelo (models.py:87) |
| 1c. Defaults de la empresa: worklog_definitions | "particular" y "colectiva", unit hours, label Clase Particular / Clase Colectiva, fields [] | backend/seed.py:55-58 | Solo se aplica al crear la empresa |
| 1d. Defaults de la empresa: settings | {"features": {"worker_daily_report": true}} | backend/seed.py:59 | dev_seed.py:40 usa settings {} y definiciones {} |
| 1e. Admin creado: flags | role admin, is_active True, is_2fa_enabled False, must_change_password False, default_company_id = empresa | backend/seed.py:67-76 | Admin de plataforma (UserRole.admin) |
| 1f. Membresia del admin | CompanyRole.manager, is_active True, sort_order 1 | backend/seed.py:90-96 | Difiere de dev_seed, que usa admin (fila 3b) |
| 2. Es idempotente | Parcialmente. Si el email ya existe retorna False sin cambios | backend/seed.py:41-44 | Riesgo: el usuario se confirma en seed.py:79 y la membresia en seed.py:98 en commits separados. Si falla la membresia, el reintento sale porque el usuario ya existe y la membresia nunca se completa |
| 2a. Se ejecuta en cada arranque | Si. lifespan llama seed_initial_data() sin condicion; sin variables imprime "Omitiendo" | backend/main.py:102-108 | Los errores se registran y no paran el arranque |
| 2b. Ejecucion manual | ./bin/seed ejecuta seed.seed_initial_data() en el compose de dev | bin/seed:10; backend/seed.py:145-146 | Tras ./bin/migrate |
| 3. dev_seed: empresas de ejemplo | No hay empresas de ejemplo. Crea una sola (DEV_ADMIN_COMPANY, por defecto "Vesotel Ski School") | backend/dev_seed.py:23-45 | Si no existe esa empresa por nombre, usa la primera de la BD (dev_seed.py:33) |
| 3a. dev_seed: roles | Admin de plataforma (UserRole.admin) y CompanyRole.admin en la empresa | backend/dev_seed.py:56, 93-100 | seed.py asigna manager a nivel de empresa |
| 3b. dev_seed: credenciales por defecto | admin@vesotel.com y password "admin" si no hay variables | backend/dev_seed.py:23-24 | Password fija en el codigo |
| 3c. dev_seed: usuario existente | Fuerza role admin, is_active True y desactiva 2FA sin avisar | backend/dev_seed.py:66-84 | Modifica cuentas existentes con ese email |
| 3d. Se puede ejecutar por error en produccion | Si el flag de dev esta activo. No hay guarda aparte del entorno | backend/dev_seed.py:11-16 (is_dev_mode: ENVIRONMENT=development, NODE_ENV=development o DEV_LOGIN_BYPASS=true/1/yes) | docker-compose.prod.yml no fija ENVIRONMENT ni DEV_LOGIN_BYPASS; depende del .env de produccion, no leido. NO DEFINIDO sin verificar |
| 3e. Vias de ejecucion de dev_seed | lifespan crea el admin de dev al arrancar; /auth/dev-login y el login usan ensure_dev_admin_user | backend/main.py:84-89; backend/routers/auth.py:40-46, 95-96 | Todas dependen solo de is_dev_mode() |
| 3f. Bypass de contrasena en login | Con is_dev activo, un login con username igual a DEV_ADMIN_EMAIL entra como admin sin verificar contrasena | backend/routers/auth.py:100-101 | Riesgo critico si el flag llega a produccion |
| 4. get_billing_summary filtra por company_id | Si: membresias y work_logs filtran por company_id | backend/migrations/versions/7d19bd7c379c_add_get_billing_summary_function.py:40, 45 | |
| 4a. Filtra por is_active de membresia | Si: cm.is_active = true | migration 7d19bd7c379c:41 | No filtra users.is_active |
| 4b. Filtra por is_active de empresa | No: la funcion no consulta companies | migration 7d19bd7c379c:36-42 | El router solo comprueba permisos (routers/work_logs.py:204-212) |
| 4c. Usa is_managed | No | migration 7d19bd7c379c (fichero completo) | is_managed si se usa en routers/work_logs.py:262 y 303, fuera de billing |
| 4d. Usa tax_config | No: la funcion no lee tax_config | migration 7d19bd7c379c (fichero completo) | Los impuestos se aplican al crear el work log (create_work_log_use_case.py:83) |
| 4e. Rango de fechas y dias unicos | Solapamiento: end_date >= s_date AND start_date <= e_date; dias unicos con generate_series por dia | migration 7d19bd7c379c:46, 49-51 | |
| 4f. Miembro sin logs | LEFT JOIN produce una fila con type NULL y totales 0 | migration 7d19bd7c379c:63-76 | Comprobar que el consumidor filtra type NULL |
| 4g. Autorizacion | No esta en SQL: el router exige platform admin o manager de la empresa | routers/work_logs.py:204-212; routers/utils.py:41-58 | is_manager_of_company devuelve True para role admin (utils.py:45) |
| 5. main.py: middlewares o handlers dependientes de empresa | Ninguno. No hay logica ni cabecera de empresa | backend/main.py:138-159 | |
| 5a. CORS | origins desde ALLOWED_ORIGINS (vacio = sin origenes), allow_credentials True, methods y headers "*" | backend/main.py:149-159 | No depende de empresa |
| 5b. Middleware log_requests | Solo registra metodo, ruta y origin; reenvia excepciones | backend/main.py:138-146 | No modifica respuestas |
