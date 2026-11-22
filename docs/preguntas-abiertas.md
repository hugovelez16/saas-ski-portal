# Preguntas abiertas

Decisiones de negocio sin cerrar. Las reglas de [dominio/](dominio/README.md)
con estado `Abierto` citan aqui su ID.

## Formato

- **ID**: `O<n>`. Se conservan los IDs de la seccion 11.2 de
  [empresa/logica-negocio-empresa.md](empresa/logica-negocio-empresa.md)
  (`O1` a `O11`). `O12` y `O13` salen de los temas "sin decision" de la
  seccion 11.1; las preguntas nuevas siguen la numeracion (`O14` a `O22`; la siguiente es `O23`).
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
| O17 | Convivencia de `is_gross` durante su migracion | S2 pasa `is_gross` de cada `RateEntry` (por tipo de turno) a un unico `is_gross` por miembro, con `default_is_gross` en `companies.settings`. Sin decidir: que valor toma un miembro con tipos mezclados (bruto en unos, neto en otros), si el codigo lee ambos formatos durante la migracion y cuando se borra el campo de `RateEntry`. Issue de seguimiento: #116 | #66 (S2); `producto/revision-base.md` seccion 8 | R-EMP-45, R-EMP-46; `R-TAR` (#69) |
| O18 | `fields` y unidad "libre" de los tipos de turno | `fields` de `worklog_definitions` se tipa o se quita al migrar Turnos, y la unidad "libre" (S6) se define en #68. Sin decidir ninguna de las dos | #66 (S6); 4.4 de `logica-negocio-empresa.md` | R-EMP-43, R-EMP-44; #68 |
| O19 | Contenido de la vista reducida de la empresa | R-ACC-55 dice que la vista reducida lleva "los ajustes de interfaz", pero S9 elimina `worker_experience` y `ui_customization` y `settings` solo guarda `default_is_gross`. Sin decidir si la vista reducida lleva `settings` y que parte | #66 (S9) | R-ACC-55, R-EMP-49 |
| O20 | Retencion de la auditoria | `audit_logs` no tiene politica de retencion ni tarea que purgue: los eventos se acumulan sin limite. Sin decidir durante cuanto se conservan, si se archivan o se borran, y quien lo ejecuta | #71; seccion 10 de `logica-negocio-empresa.md` | R-AUD-28 |
| O21 | Auditoria general de turnos | Hoy los turnos solo se auditan durante la suplantacion (R-ACC-53, retirada con la suplantacion de solo lectura). Sin decidir si se audita toda creacion, edicion o borrado de turnos, con que campos y con que volumen asumible | #71; P4 | R-AUD-26, R-AUD-27 |
| O22 | Nombre de las acciones nuevas de auditoria | Sin fijar el nombre de la accion de inicio y de fin de suplantacion (R-ACC-67) ni el de la concesion del rol de PA (R-ACC-65). Se propone el patron `<entidad>.<verbo>` de `AuditAction` | #71; P4, P5 | R-AUD-23, R-AUD-24, R-AUD-25 |
| O23 | Turnos antiguos con `manual_override` al editar o recalcular | S6 y T2 retiran el importe manual y los turnos antiguos se leen sin migrar, pero no esta decidido que pasa al editar uno de ellos (conservar su importe, forzar el recalculo con la tarifa vigente o bloquear la edicion de datos de calculo) | #68; S6, T2 | R-TUR-18 |
| O24 | Aceptacion de turnos, aprobacion, cierre de periodo y plus por turno | Futuro, sin diseno: en empresa gestionada el worker acepta la asignacion de turnos; aprobacion de turnos y cierre de periodo en un modulo futuro; plus con cantidad editable por turno (S5). Sin decidir estados, quien aprueba ni como afectan a los importes | #68; S5, S7; seccion 10 de `logica-negocio-empresa.md` | R-TUR-33, R-TUR-34 |

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
