# ADR-0004: Aislamiento multiempresa

Estado: Aceptada (2026-11-22). Parte pendiente de implementar: `work_logs.company_id`
NOT NULL (hoy `nullable=True` en `backend/models.py`) y el punto unico del
bypass del PA.

## Contexto

La plataforma es multiempresa: un usuario puede pertenecer a varias empresas y
el administrador de plataforma (PA) opera sobre todas. Los riesgos son que una
empresa vea datos de otra, que se pueda enumerar empresas ajenas por la
diferencia entre errores, y que cada handler repita su propia comprobacion.

## Decision

- La empresa activa es solo la del claim `cid` del token, validada contra la
  membresia activa; nunca se toma de la URL (R-ACC-33, O2).
- Una empresa inexistente, ajena o sin membresia responde el mismo 403: no se
  puede distinguir si existe (anti-enumeracion, P-5 del plan de empresa). Solo
  el PA recibe 404. La membresia se comprueba antes que la suspension
  (R-ACC-18 a 20).
- El PA no queda bloqueado por una empresa suspendida (P-4 del plan de empresa);
  worker y manager si (R-ACC-19).
- El bypass del PA vive en un solo punto, `authorize_company`
  (`backend/access_policy.py`); ningun handler repite `if not is_platform_admin`
  (R-ACC-25).
- No hay empresa "personal" ni turnos sin empresa: `work_logs.company_id` pasa
  a NOT NULL (P2).
- No hay empresa por defecto en servidor (`default_company_id` eliminado): el
  navegador recuerda la ultima en `localStorage` (`lastCompanyId`) y la envia en
  el login; el backend la valida.
- RLS de PostgreSQL aplazada (P12, O1): se retoma cuando la matriz de permisos
  (ADR-0005) este probada por HTTP, `company_id` sea NOT NULL y haya mas de 10
  escuelas. Cuando se aplique, pedira `SET LOCAL app.company_id` por
  transaccion, con el PA exento.

Reglas en [../dominio/acceso.md](../dominio/acceso.md).

## Consecuencias

- El aislamiento depende de la capa de aplicacion, sin red de seguridad en BD
  hasta que llegue la RLS. Por eso el test HTTP por fila de ADR-0005 es
  condicion y no opcion.
- Cada consulta de un contexto filtra por `company_id`; el revisor
  (`code-reviewer`) lo comprueba en cada PR.
- Pendiente de implementar: la migracion de `work_logs.company_id` necesita el
  paso previo de ADR-0010 (script de reparacion con los turnos sin empresa).
- Aplazar la RLS acepta el riesgo de un fallo de filtro en una consulta nueva
  mientras no exista.
