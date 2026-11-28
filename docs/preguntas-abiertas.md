# Preguntas abiertas

Decisiones de negocio sin cerrar. Las reglas de [dominio/](dominio/README.md)
con estado `Abierto` citan aqui su ID.

## Formato

- **ID**: `O<n>`. Se conservan los IDs de la seccion 11.2 de
  `logica-negocio-empresa.md` (eliminado, ver historial de git)
  (`O1` a `O11`). `O12` y `O13` salen de los temas "sin decision" de la
  seccion 11.1; las preguntas nuevas siguen la numeracion (`O14` a `O30`; la siguiente es `O31`).
  Un ID no se reutiliza.
- **Alta**: una fila en "Abiertas" con tema, detalle, origen y las reglas o
  issues que bloquea.
- **Cierre**: solo lo decide el usuario. La fila pasa a "Cerradas" con la
  decision y donde quedo escrita (regla `R-<ENT>-nn`, seccion o ADR). Las
  reglas que la citaban cambian su estado a `Cerrado`.

## Abiertas

| ID | Tema | Detalle | Origen | Bloquea |
|---|---|---|---|---|
| O16 | Cobro a particulares B2C (aplazado) | Cerrado en el repaso 2026-11-25 (R-ACC-06, R-ACC-75 a 77, R-ACC-80): el usuario gratuito tiene su empresa autonoma ("Empresa de `<Nombre> <Apellido>`") y sus turnos propios sin modulos de pago; los modulos se contratan despues como suscripcion de su empresa y recibe rol de `manager` al contratar un plan de pago (por rol, no por modo). Sigue abierto (aplazado, sin decidir): el cobro a particulares (B2C). Issue de idea: #89 | Cuestionario de dominio 2026-11-21; FRD 1.2 (eliminado, ver historial de git); P1; Repaso 2026-11-25 | R-ACC-06 (solo cobro B2C, aplazado) |
| O29 | Esquema SEPA Core o B2B (C4) | Depende de Vesotel. SEPA Core permite al cliente devolver un cargo en 8 semanas sin motivo; SEPA B2B no admite devoluciones, pero obliga a la escuela a registrar el mandato en su banco, lo que choca con el alta autonoma (C11) | Cobros 2026-11-25 (#130) | Fase 3 de `docs/producto/cobros.md` (alta autonoma y mandatos SEPA) |
| O30 | Acceso a la API y capacidades del Odoo de Vesotel | En Odoo Online la API externa solo esta disponible en el plan Custom. Confirmar el plan contratado de Odoo Online 19.0 Enterprise, si el modulo SEPA Direct Debit esta activo, si permite firmar el mandato online en 19.0 y si Odoo puede notificar a un sistema externo (webhook) al pagarse o devolverse una factura | Cobros 2026-11-25 (#130) | Fases 1 a 3 de `docs/producto/cobros.md` |

## Cerradas

Se conservan para trazar el ID. Las secciones citadas sin fichero provienen de
`logica-negocio-empresa.md` (eliminado, ver historial de git); las decisiones
vigentes estan en `dominio/`.

| ID | Tema | Decision | Donde esta |
|---|---|---|---|
| O1 | RLS de PostgreSQL por `company_id` (D13) | Si, despues de la migracion hexagonal de Turnos y Membresias (O4), empezando por `work_logs` y `company_members`. Pide `SET LOCAL app.company_id` en cada transaccion, con el PA exento. Sin implementar. Revisada 2026-11-22: RLS aplazada (P12) | 11.2 (principio P4); cuestionario 2026-11-21; `producto/revision-base.md` P12 |
| O2 | Empresa en la URL (`?companyId=`) | Se quita de la URL. El backend nunca se fia de lo que muestre la URL; la empresa activa es la del token, validada contra la membresia | 3.3 y 11.2 |
| O3 | Solapes de turnos del mismo trabajador | Permitidos con aviso: el backend crea el turno (201) y devuelve `warnings`; el frontend lo muestra | 6.2 |
| O4 | Capa `backend/src/` y API v2 (D20) | Reabierta y cerrada con decision nueva (2026-11-21): se migra el backend por contextos a `backend/src/` (Turnos, luego Usuarios y Membresias, luego Modulos y billing), se exponen en `/api/v2/` en `snake_case` y `crud.py` se vacia poco a poco. Sustituye a "v2 solo del area empresa y `crud.py` no se divide". Python se mantiene. Precisada 2026-11-22: cada contexto migrado borra su v1 (P13), estructura `backend/src/<contexto>/{domain,application,infrastructure}` con README (P14) y limite de 300 lineas por fichero y 120 por caso de uso (P15) | `CLAUDE.md` (Stack); 11.2 y `cambios-empresa.md` 14 (eliminados, ver historial de git); `producto/revision-base.md` P13 a P15 |
| O5 | Vista reducida del worker (D5) | Se le da lo que necesita su frontend: `id`, `name`, `is_managed`, ajustes de interfaz y, en solo lectura, `worklog_definitions` y `tax_config` | 9 |
| O6 | Totales del dashboard | Los totales incluyen a los miembros inactivos y el desglose tambien, marcados como inactivos | 11.2 |
| O7 | Confirmaciones pendientes de acceso | Opcion A: el token lleva solo `sub`, `cid`, `scope` y `exp`; rol e `is_admin` se leen de BD | 3.1 y 3.2 |
| O8 | Reactivar una membresia | Vuelve siempre como worker. Cambiada 2026-11-22 y confirmada 2026-11-25: un worker desactivado lo reactivan el manager y el PA, un manager desactivado solo el PA, y la reactivacion no cambia el rol | R-MEM-11, R-MEM-12 |
| O9 | Nombre de la clave de IRPF | Claves libres de impuestos: el override usa la misma clave que `tax_config` | 4.4 |
| O10 | `CompanyMember.settings` | Aparcado: no se usa hasta que haya un caso concreto. El campo queda reservado. Cerrada de nuevo 2026-11-22: `CompanyMember.settings` se elimina, con su endpoint, caso de uso y validador, sin migracion de datos (P8, S9) | R-MEM-22; `producto/revision-base.md` P8 y S9 |
| O11 | Billing avanzado | Aplazado hasta que lo pida un cliente. No se vende hoy: `planes-y-precios.md` no lo incluye | `planes-y-precios.md`; glosario (Billing avanzado) |
| O12 | Plan o limites por empresa (D16) | Si, modelados con `module_subscriptions` y limites por modulo, cuando exista facturacion por plan. Actualizada 2026-11-25: los limites de monitores y responsables se aplican ya bloqueando el alta y la invitacion | R-MOD-22 |
| O13 | `owner_id` de la empresa | No se retoma: la responsabilidad la tienen los managers y el administrador de plataforma | Este fichero |
| O14 | Que ve el manager de la empresa y de otros usuarios | Se cambia la regla, no el codigo: el manager solo ve su empresa activa y no ve `is_active` de la empresa ni otras empresas del usuario | R-ACC-56, R-ACC-60 |
| O15 | Vigencia del FRD (eliminado, ver historial de git) | Eliminado (#131); manda `dominio/`. Su registro publico no se descarta: abre la O16 | `docs/README.md`; O16 |
| O17 | Convivencia de `is_gross` durante su migracion | Si un miembro tiene tipos con bruto/neto mezclado pasa al valor por defecto de la empresa (`default_is_gross`) y se avisa al manager; ambos formatos se leen solo durante la migracion y el antiguo se borra al terminar (Repaso 2026-11-25) | R-TAR-07 (#116) |
| O18 | `fields` y unidad "libre" de los tipos de turno | Se quita `fields` de los tipos de turno (solo se usan las opciones/pluses). La unidad "libre" queda aplazada hasta que un cliente la pida (Repaso 2026-11-25) | R-EMP-39, R-EMP-43, R-EMP-44, R-TUR-22 |
| O19 | Contenido de la vista reducida de la empresa | La vista reducida no lleva `settings` (Repaso 2026-11-25) | R-ACC-55, R-EMP-49 |
| O20 | Retencion de la auditoria | La auditoria se conserva siempre, sin purga automatica. El PA puede purgar a mano eligiendo una fecha tras ver el recuento y confirmar; la purga se audita y ese apunte no se borra (Repaso 2026-11-25, ronda 2 7.4) | R-AUD-28 |
| O21 | Auditoria general de turnos | No se auditan los turnos en general; basta el `calculation_snapshot` guardado en cada turno (Repaso 2026-11-25) | R-AUD-27 |
| O22 | Nombre de las acciones nuevas de auditoria | `impersonation.started`, `impersonation.ended` y `user.platform_admin_granted` (Repaso 2026-11-25) | R-AUD-23, R-AUD-24, R-AUD-25 |
| O23 | Turnos antiguos con `manual_override` al editar o recalcular | Consulta en produccion (2026-11-25): `count = 0`. No hay turnos con `manual_override`; se elimina todo lo de importe manual sin mas (Repaso 2026-11-25, ronda 2 4.3) | R-TUR-18, R-TAR-21 |
| O24 | Aceptacion de turnos, aprobacion, cierre de periodo y plus por turno | Aceptacion de turnos, aprobacion, cierre de periodo y cantidad editable de cada plus por turno quedan aplazados hasta que un cliente lo pida, sin estados nuevos (Repaso 2026-11-25) | R-TUR-33, R-TUR-34, R-TAR-20 |
| O25 | Tabla 5 de `logica-negocio-empresa.md` desactualizada | Manda `docs/dominio/membresia.md`; la tabla 5 de `logica-negocio-empresa.md` (eliminado, ver historial de git) queda como historico (Repaso 2026-11-25) | `docs/dominio/membresia.md` |
| O26 | Lo vendido frente a lo implementado en modulos y planes | Los limites de monitores y responsables se aplican ya bloqueando el alta; "Cuadrante compartido" es `name` y `description` de `worker_daily_report` en el catalogo; `push_notifications` se crea ya en el catalogo como inactivo (Repaso 2026-11-25, ronda 2 6.1) | R-MOD-03, R-MOD-22 |
| O27 | Miembros inactivos en la billing basica | La facturacion basica incluye a los miembros inactivos, marcados como tales (Repaso 2026-11-25) | R-TAR-29 |
| O28 | Suma de impuestos mayor que 100 % con tarifa bruta | Se rechaza guardar impuestos (de empresa o de miembro) si la suma supera el 100 %; el editor muestra la suma y avisa si pasa del 100 % (Repaso 2026-11-25, ronda 2 5.3) | R-TAR-16 |
