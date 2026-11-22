# Preguntas abiertas

Decisiones de negocio sin cerrar. Las reglas de [dominio/](dominio/README.md)
con estado `Abierto` citan aqui su ID.

## Formato

- **ID**: `O<n>`. Se conservan los IDs de la seccion 11.2 de
  [empresa/logica-negocio-empresa.md](empresa/logica-negocio-empresa.md)
  (`O1` a `O11`). `O12` y `O13` salen de los temas "sin decision" de la
  seccion 11.1; las preguntas nuevas siguen la numeracion (`O14` a `O16`; la siguiente es `O17`).
  Un ID no se reutiliza.
- **Alta**: una fila en "Abiertas" con tema, detalle, origen y las reglas o
  issues que bloquea.
- **Cierre**: solo lo decide el usuario. La fila pasa a "Cerradas" con la
  decision y donde quedo escrita (regla `R-<ENT>-nn`, seccion o ADR). Las
  reglas que la citaban cambian su estado a `Cerrado`.

## Abiertas

| ID | Tema | Detalle | Origen | Bloquea |
|---|---|---|---|---|
| O16 | Registro publico B2C gratuito y capa freemium | Decidido en P1 de `producto/revision-base.md` (2026-11-22): el alta publica es un alta automatica que crea una empresa con el nombre del usuario, con el como unico worker y sin manager, con impuestos y tipos de turno prefijados y, al principio, sin acceso de manager (R-ACC-75 a 77). Se disena ya y se implementa tras migrar Usuarios y Membresias. Sigue abierto: que puede y que no puede hacer el usuario gratuito (limites, modulos, paso a un plan de pago) y si pasa a manager de su empresa (se resolveria por rol, no por modo). Issue de idea: #89 | Cuestionario de dominio 2026-11-21; FRD 1.2; P1 | R-ACC-06 (cuenta gratuita) |

## Cerradas

Se conservan para trazar el ID. La decision completa esta en la seccion citada
de `logica-negocio-empresa.md` hasta que pase a su fichero de `dominio/`.

| ID | Tema | Decision | Donde esta |
|---|---|---|---|
| O1 | RLS de PostgreSQL por `company_id` (D13) | Si, despues de la migracion hexagonal de Turnos y Membresias (O4), empezando por `work_logs` y `company_members`. Pide `SET LOCAL app.company_id` en cada transaccion, con el PA exento. Sin implementar. Revisada 2026-11-22: RLS aplazada (P12) | 11.2 (principio P4); cuestionario 2026-11-21; `producto/revision-base.md` P12 |
| O2 | Empresa en la URL (`?companyId=`) | Se quita de la URL. El backend nunca se fia de lo que muestre la URL; la empresa activa es la del token, validada contra la membresia | 3.3 y 11.2 |
| O3 | Solapes de turnos del mismo trabajador | Permitidos con aviso: el backend crea el turno (201) y devuelve `warnings`; el frontend lo muestra | 6.2 |
| O4 | Capa `backend/src/` y API v2 (D20) | Reabierta y cerrada con decision nueva (2026-11-21): se migra el backend por contextos a `backend/src/` (Turnos, luego Usuarios y Membresias, luego Modulos y billing), se exponen en `/api/v2/` en `snake_case` y `crud.py` se vacia poco a poco. Sustituye a "v2 solo del area empresa y `crud.py` no se divide". Python se mantiene. Precisada 2026-11-22: cada contexto migrado borra su v1 (P13), estructura `backend/src/<contexto>/{domain,application,infrastructure}` con README (P14) y limite de 300 lineas por fichero y 120 por caso de uso (P15) | `CLAUDE.md` (Stack); 11.2 y `cambios-empresa.md` 14 son historico; `producto/revision-base.md` P13 a P15 |
| O5 | Vista reducida del worker (D5) | Se le da lo que necesita su frontend: `id`, `name`, `is_managed`, ajustes de interfaz y, en solo lectura, `worklog_definitions` y `tax_config` | 9 |
| O6 | Totales del dashboard | Los totales incluyen a los miembros inactivos y el desglose tambien, marcados como inactivos | 11.2 |
| O7 | Confirmaciones pendientes de acceso | Opcion A: el token lleva solo `sub`, `cid`, `scope` y `exp`; rol e `is_admin` se leen de BD | 3.1 y 3.2 |
| O8 | Reactivar una membresia | Vuelve siempre como worker | 5 |
| O9 | Nombre de la clave de IRPF | Claves libres de impuestos: el override usa la misma clave que `tax_config` | 4.4 |
| O10 | `CompanyMember.settings` | Aparcado: no se usa hasta que haya un caso concreto. El campo queda reservado. Cerrada de nuevo 2026-11-22: `CompanyMember.settings` se elimina, con su endpoint, caso de uso y validador, sin migracion de datos (P8, S9) | Este fichero; sin regla `R-MEM` que lo use; `producto/revision-base.md` P8 y S9 |
| O11 | Billing avanzado | Aplazado hasta que lo pida un cliente. No se vende hoy: `planes-y-precios.md` no lo incluye | `planes-y-precios.md`; glosario (Billing avanzado) |
| O12 | Plan o limites por empresa (D16) | Si, modelados con `module_subscriptions` y limites por modulo, cuando exista facturacion por plan | Este fichero; sin implementar |
| O13 | `owner_id` de la empresa | No se retoma: la responsabilidad la tienen los managers y el administrador de plataforma | Este fichero |
| O14 | Que ve el manager de la empresa y de otros usuarios | Se cambia la regla, no el codigo: el manager solo ve su empresa activa y no ve `is_active` de la empresa ni otras empresas del usuario | R-ACC-56, R-ACC-60 |
| O15 | Vigencia de `functional_requirements_document.md` | Pasa a historico (lo mueve #73); manda `dominio/`. Su registro publico no se descarta: abre la O16 | `docs/README.md`; O16 |
