# ADR-0003: Autenticacion

Estado: Aceptada (2026-11-22). Parte pendiente de implementar: quitar la cache
Redis de acceso.

## Contexto

El acceso a la API depende de un token y de un rol. Antes de la revision de
base el rol se cacheaba 60 s en Redis con invalidacion en cada cambio de
membresia o empresa (`backend/routers/deps.py`), y el token se discutia entre
llevar el rol o leerlo de BD (O7). La cache anade un segundo sitio donde el
rol puede estar desfasado y dos mecanismos de invalidacion que mantener.

## Decision

- JWT firmado con RS256 en cookie HttpOnly `access_token`; la cabecera
  `Authorization: Bearer` es el respaldo (R-ACC-01, R-ACC-05).
- Token minimo: solo `sub`, `cid`, `scope` y `exp`, mas `admin_user_id` al
  suplantar (O7, R-ACC-02). Si un token
  trae `role` o `is_admin`, se ignoran (R-ACC-03).
- El rol de plataforma y el de empresa se leen de BD en cada peticion. No hay
  cache de acceso: se quita la cache Redis y con ella R-ACC-21 y R-ACC-22
  (P11, R-ACC-79). Un cambio de rol o de estado surte efecto en la siguiente
  peticion.
- Entrada de desarrollo (`dev-login`): solo con `ENVIRONMENT=development` y
  `DEV_LOGIN_BYPASS`; si no se cumplen las dos, el arranque aborta (P-9 de la
  tabla 4.1 del plan de empresa, historico).
- El rol de PA no lo concede ningun endpoint: solo seed o comando de servidor,
  auditado (R-ACC-65, P5).

Las reglas completas estan en [../dominio/acceso.md](../dominio/acceso.md); este
ADR no las repite.

## Consecuencias

- Una consulta de membresia mas por peticion. Se acepta a cambio de no
  mantener la invalidacion; si algun dia pesa, se mide antes de reintroducir una
  cache.
- Redis deja de formar parte del camino de autorizacion. Sigue en el stack para
  el limite por cuenta (ADR-0011, #93).
- Pendiente de implementar: hoy `backend/routers/deps.py` todavia cachea el
  rol. La retirada es una issue de seguimiento aparte; hasta que se cierre, las
  reglas R-ACC-21 y R-ACC-22 describen el comportamiento real y R-ACC-79 el
  objetivo.
- Revocar sesiones o cambiar roles no necesita invalidar nada: basta el cambio
  en BD.
