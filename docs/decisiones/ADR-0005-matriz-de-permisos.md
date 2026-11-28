# ADR-0005: Matriz de permisos unica

Estado: Aceptada (2026-11-22). Pendiente de implementar entera: hoy los
permisos se reparten entre `backend/access_policy.py`, dependencias y cada
endpoint.

## Contexto

Un manager podia convertir a un worker en manager o PA porque el desplegable lo
ofrecia y el endpoint de actualizacion lo aplicaba: la regla solo se cumplia si
cada endpoint recordaba poner `require_platform_admin`. Probar la funcion de
politica no lo habria detectado, porque el endpoint no la llamaba.

## Decision

La matriz de [../producto/revision-base.md](../producto/revision-base.md)
(seccion 3) pasa a ser la unica fuente, en codigo (P16):

1. Un modulo puro junto a `backend/access_policy.py` con un `Action` por fila
   y, por rol y modo de empresa (`is_managed`, ADR-0009), permitido o no.
   `authorize_company`, `can_write_work_log` y `can_edit_member_rates` consultan
   la tabla en lugar de llevar la regla en `if`.
2. Cada endpoint declara su accion (`require(Action.MEMBER_SET_ROLE)`), no un
   rol minimo. Un endpoint sin accion declarada falla un test que recorre las
   rutas de la app.
3. Cada fila es un caso de un test parametrizado por (accion, rol, modo) que
   llama al endpoint HTTP real y espera 2xx o 403.
4. `GET /users/me` devuelve las acciones permitidas en la empresa activa. El
   frontend no deduce permisos: solo ofrece esas.
5. Regla de concesion: un rol nunca concede uno igual o superior al suyo
   (R-ACC-64, R-ACC-65).

El contenido de la matriz es de producto y dominio; este ADR solo fija donde
vive y como se prueba.

## Consecuencias

- Cambiar un permiso es editar una fila y su caso de test; el diff lo revisan
  `code-reviewer` y `security-reviewer`.
- El test recorre todas las rutas, asi que un endpoint nuevo sin accion no pasa
  CI.
- Los casos de uso declaran su `Action` y llevan sus filas en
  `tests/<contexto>/test_permissions.py`, generadas desde la matriz (ADR-0006).
- Pendiente de implementar: el modulo de la matriz, el test de rutas, el test
  parametrizado y las acciones en `GET /users/me`. Cada uno es una issue de
  seguimiento; hasta entonces mandan `access_policy.py` y los endpoints.
- Coste: una tabla mas que mantener y una lista de acciones en la respuesta de
  `/users/me`. Se acepta a cambio de no depender de la memoria de cada endpoint.
