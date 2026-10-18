# PR-22 - Rate limit en el gateway: estado y pendientes

Rama `chore/rate-limit-gateway`. Aparcada el 2026-10-18: no se mergea. Sirve como referencia para retomar el bloque I3 del plan (`plan-implementacion-empresa.md`, seccion PR-22).

## Que contiene la rama

- `gateway/nginx.conf` y `gateway/nginx.dev.conf`:
  - `limit_req_zone` `auth_zone` (10r/m) y `api_zone` (20r/s), `limit_req_status 429` y `limit_req_log_level warn`.
  - `location ~ ^/api/(token|verify-2fa|refresh-token|logout|auth)(/|$)` con `limit_req zone=auth_zone burst=10 nodelay`.
  - `location /api/` con `limit_req zone=api_zone burst=40 nodelay`.
- Desviacion respecto al plan: Nginx no admite URI en `proxy_pass` dentro de una location regex, asi que la location de autenticacion usa `rewrite ^/api/(.*)$ /$1 break;` y `proxy_pass http://backend_upstream;` (sin barra final). La URL que recibe el backend es la misma que con `location /api/`.

## Verificado

- `nginx -t` correcto con ambos ficheros.
- 15 POST a `/api/token` con credenciales falsas: 401 las 11 primeras y 429 las 4 ultimas.
- `/api/health`: 200, tambien en 60 peticiones seguidas.

## Motivo del aparcado

En produccion hay uno o varios proxies delante del gateway. `$binary_remote_addr` seria la IP del ultimo proxy, asi que los limites por IP serian globales: 10 r/m en `auth_zone` impediria el login de todos los usuarios. No se conocen las IPs de los proxies.

## Pendiente

- Decidir estrategia:
  - A) `set_real_ip_from` con las IPs o redes de los proxies, `real_ip_header X-Forwarded-For` y `real_ip_recursive on`. Nunca `0.0.0.0/0`, porque la cabecera se podria falsificar.
  - B) Limite por cuenta e IP real en el backend, con Redis.
- Identificar la cadena de proxies de produccion.
- Probar que `api_zone` devuelve 429 con una rafaga paralela (no se probo: con curl secuencial no se alcanza).
- Rutas sensibles fuera de la regex, hoy solo bajo `api_zone`: `/2fa/*`, `/users/me/change-password`, `/users/{id}/reset-password-email`, `/admin/impersonate/*`.
- Decidir si `refresh-token` va a una zona mas laxa: varias pestanas o usuarios tras una misma NAT (escuelas) pueden agotar el limite.
- Revisar el bloqueo por usuario de `/verify-2fa` en el backend (no verificado).
- Si se retoma como PR: incremento PATCH en `package.json`, `frontend/package.json` y `CHANGELOG.md`, al final y sobre `develop` actualizado.
- Arreglar el symlink roto de `frontend/node_modules` en este worktree: el frontend dev no arranca aqui.
