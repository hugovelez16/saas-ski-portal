# ADR-0011: Rate limit

Estado: Aceptada (2026-11-22). Limite por IP en el gateway: implementado (#61).
Limite por cuenta en el backend: pendiente de implementar (#93).

## Contexto

La autenticacion no tenia ninguna defensa contra fuerza bruta ni abuso. El plan
de empresa lo recogia como PR-22 (rate limit en el gateway). En produccion hay
proxies delante del gateway (VPS, tunel SSH, Nginx Proxy Manager), asi que sin
configuracion `$remote_addr` es el salto directo y un limite por IP seria
global.

## Decision

- Dos niveles con responsabilidades distintas:
  1. **Por IP real, en el gateway** (Nginx `limit_req`, estado 429), con zonas
     por tipo de ruta: autenticacion, refresco de token y resto de `/api/`.
     Implementado en #61.
  2. **Por cuenta, en el backend con Redis**: bloqueo de `/verify-2fa` por
     usuario y limite por usuario en `/refresh-token`. Pendiente (#93).
- La IP real se obtiene de `X-Forwarded-For` descartando los saltos de
  confianza. Los saltos de confianza se definen con la variable de entorno
  `TRUSTED_PROXIES` del stack de despliegue; el repo no contiene IPs. Sin la
  variable no se confia en ningun proxy. Se rechazan `0.0.0.0/0` y `::/0`.
- Las tasas concretas, las rutas de cada zona y como comprobarlo tras desplegar
  estan en [../operaciones/gateway-ip-real.md](../operaciones/gateway-ip-real.md),
  no en este ADR.

## Consecuencias

- PR-22 del plan de empresa queda resuelto por #61; ya no esta aparcado.
- El limite por IP no protege una cuenta atacada desde muchas IP ni distingue
  usuarios tras un mismo NAT de escuela. Para eso existe el nivel por cuenta.
- Pendiente de implementar: #93 (limite por cuenta con Redis). Redis se queda en
  el stack para eso aunque deje de cachear el acceso (ADR-0003).
- Las tasas de `refresh_zone` y `api_zone` son holgadas y quedan por ajustar con
  datos reales.
- Una `TRUSTED_PROXIES` mal configurada degrada el limite a global o lo hace
  eludible: se verifica con el log del gateway tras cada cambio de proxies.
