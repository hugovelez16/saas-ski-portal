# Gateway: IP real del cliente y rate limit

El gateway limita la tasa de peticiones por IP con `limit_req`. En produccion hay proxies delante, asi que sin configuracion `$remote_addr` es la IP del salto directo y el limite seria global. Este documento explica como obtiene el gateway la IP real y que se limita.

## Cadena de proxies

Cliente -> VPS (Nginx) -> tunel SSH reverso -> Nginx Proxy Manager (LXC de Proxmox) -> gateway (puerto publicado del host).

El VPS anade la IP real del cliente a `X-Forwarded-For`; Nginx Proxy Manager la conserva y anade el salto del tunel. `X-Real-IP` no sirve: Nginx Proxy Manager lo sobrescribe.

## Variable TRUSTED_PROXIES

- Lista de IP o CIDR separados por espacios (por ejemplo, `127.0.0.1 <IP del LXC de NPM>`). Se define en el stack de Komodo, no en el repo.
- Sin la variable (o vacia), no se confia en ningun proxy: `$remote_addr` es el salto directo (comportamiento anterior).
- `gateway/docker-entrypoint.d/40-real-ip.sh` valida cada entrada (IPv4 o IPv6, con CIDR opcional), rechaza `0.0.0.0/0` y `::/0`, y escribe `/etc/nginx/real-ip.d/real-ip.conf` con un `set_real_ip_from` por entrada mas `real_ip_header X-Forwarded-For` y `real_ip_recursive on`. Si una entrada no es valida, el contenedor no arranca.
- En produccion `/etc/nginx/real-ip.d` es un tmpfs (`docker-compose.prod.yml`), porque el resto del sistema de ficheros puede ir en solo lectura.
- Con `real_ip_recursive on` se descartan desde la derecha los saltos de confianza y queda la primera IP no confiable. Un `X-Forwarded-For` falsificado por el cliente queda a su izquierda y se ignora.

## Como comprobarlo tras desplegar

El log de acceso del gateway registra `$remote_addr`, `$realip_remote_addr` y `X-Forwarded-For`:

```
<IP efectiva> realip_from=<salto directo> xff="<cadena>" [fecha] "<peticion>" <estado> <bytes>
```

1. Haz una peticion desde fuera de la red y mira el log en Komodo.
2. `realip_from` es la IP con la que llega el proxy al gateway. Debe ser la del LXC de Nginx Proxy Manager y estar en `TRUSTED_PROXIES`.
3. La primera IP del log debe ser la IP publica del cliente.
4. Si `realip_from` es una 172.x (reescritura de origen de Docker o Podman), anade esa IP a `TRUSTED_PROXIES`.

## Que se limita

Zonas en `gateway/nginx.conf` (y `nginx.dev.conf`), por IP real, estado 429:

| Zona | Rutas | Tasa | Rafaga |
|---|---|---|---|
| `auth_zone` | `/api/token`, `/api/verify-2fa`, `/api/auth/dev-login`, `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/2fa/*`, `/api/admin/impersonate/*`, `/api/users/me/change-password`, `/api/users/{id}/reset-password-email` | 10 por minuto | 5 |
| `refresh_zone` | `/api/refresh-token` | 60 por minuto | 20 |
| `api_zone` | todo `/api/` | 600 por minuto | 200 |

Las tasas de `refresh_zone` y `api_zone` son holgadas por varias pestanas y NAT de escuela. Quedan por decidir y ajustar con datos reales.

Pendiente fuera de este cambio: bloqueo de `/verify-2fa` por usuario y limite por usuario en `/refresh-token`, en el backend con Redis (#93).
