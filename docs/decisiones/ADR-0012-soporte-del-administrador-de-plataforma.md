# ADR-0012: Soporte del administrador de plataforma

Estado: Aceptada (2026-11-22). Pendiente de implementar: hoy la suplantacion
puede escribir como el usuario y sigue existiendo `view_as`.

## Contexto

El administrador de plataforma (PA) tenia dos mecanismos de soporte con reglas
propias: `view_as` (entrar como worker o manager de una empresa, de solo
lectura) y la suplantacion de un usuario concreto, que puede escribir como el.
El segundo es el riesgo mayor: una escritura suplantada pierde la autoria real y
obliga a un registro de auditoria especial (R-ACC-53).

## Decision

- Un solo mecanismo: suplantacion de solo lectura (P4). Dura 10 minutos, esta
  auditada (inicio y fin en `audit_logs`, con el PA y el usuario suplantado) y
  el frontend muestra un banner con el usuario suplantado y la salida
  (R-ACC-66 a 68).
- Se elimina `view_as` y las reglas que lo regulan (R-ACC-44 a 49 y R-ACC-53,
  retiradas).
- Para ver lo que ve cada rol sin suplantar a nadie, cada empresa de prueba
  tiene un usuario demo manager y uno worker que el PA usa (R-ACC-69).
- Durante la suplantacion toda peticion distinta de GET, HEAD u OPTIONS
  responde 403, salvo salir de la suplantacion y cerrar sesion (R-ACC-66).

El texto de las reglas esta en [../dominio/acceso.md](../dominio/acceso.md).

## Consecuencias

- Desaparece la categoria de errores "una accion hecha por el PA con la
  identidad de otro": solo se lee.
- Soporte que necesite escribir lo hace con su propia identidad o con el usuario
  demo, que queda en la auditoria con su nombre.
- Pendiente de implementar: bloquear las escrituras durante la suplantacion,
  auditar inicio y fin, el banner, crear los usuarios demo en el seed y retirar
  `view_as` de `backend/access_policy.py`, `backend/schemas.py` y del frontend.
  Cada punto es una issue de seguimiento.
- Mientras tanto el codigo sigue como describian R-ACC-47 y R-ACC-53 (ya
  retiradas como objetivo en `acceso.md`).
