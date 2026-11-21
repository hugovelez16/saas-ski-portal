# Preguntas abiertas

Decisiones de negocio sin cerrar. Las reglas de [dominio/](dominio/README.md)
con estado `Abierto` citan aqui su ID.

## Formato

- **ID**: `O<n>`. Se conservan los IDs de la seccion 11.2 de
  [empresa/logica-negocio-empresa.md](empresa/logica-negocio-empresa.md)
  (`O1` a `O11`). `O12` y `O13` salen de los temas "sin decision" de la
  seccion 11.1; las preguntas nuevas siguen la numeracion (`O14`, `O15`...).
  Un ID no se reutiliza.
- **Alta**: una fila en "Abiertas" con tema, detalle, origen y las reglas o
  issues que bloquea.
- **Cierre**: solo lo decide el usuario. La fila pasa a "Cerradas" con la
  decision y donde quedo escrita (regla `R-<ENT>-nn`, seccion o ADR). Las
  reglas que la citaban cambian su estado a `Cerrado`.

## Abiertas

| ID | Tema | Detalle | Origen | Bloquea |
|---|---|---|---|---|
| O1 | RLS de PostgreSQL por `company_id` (D13) | Segunda barrera de aislamiento, con el PA exento. Recomendado despues de centralizar permisos y con `company_id` NOT NULL, empezando por `work_logs` y `company_members`. Pide `SET LOCAL app.company_id` en cada transaccion y afecta a funciones SQL y migraciones | 11.2; principio P4 | Reglas de aislamiento de `R-ACC` |
| O10 | `CompanyMember.settings` | Analizar que aportaria usar los ajustes por usuario y cuando | 11.2 | Reglas de ajustes de `R-MEM` |
| O11 | Billing avanzado | Que incluye exactamente y como se llama el modulo | 11.2; seccion 8 | Reglas de billing de `R-MOD` |
| O12 | Plan o limites por empresa (D16) | Si cada empresa tiene un plan con limites (usuarios, turnos, modulos). Sin decision, no urgente | 11.1 | Ninguna por ahora |
| O13 | `owner_id` de la empresa | Si se retoma, decidir a que se vincula: a un usuario de la plataforma o a la empresa | 11.1 | Ninguna por ahora |
| O14 | Que ve el manager de la empresa y de otros usuarios | La seccion 9 dice que el manager ve `is_active` de la empresa y las empresas que comparte con otro usuario. El codigo no expone `is_active` al manager: la vista reducida no lo lleva (`backend/routers/v2/schemas.py:CompanyReduced`) y `read_user_companies` limita al manager a la empresa del token. Decidir si se cambia la regla o el codigo | 9; codigo 2026-11-21 | R-ACC-56, R-ACC-60 |
| O15 | Vigencia de `functional_requirements_document.md` | El FRD contradice a `logica-negocio-empresa.md` y al codigo: dice que existe registro publico (`POST /users`, hoy solo PA), que el manager da de alta y promueve personal (hoy solo el PA), que el worker gestiona sus turnos sin distinguir empresa gestionada y que el admin de empresa equivale al manager en todo. Decidir si se actualiza o se marca como historico | FRD 1.2 y 2.1 | Ninguna (manda `dominio/`) |

## Cerradas

Se conservan para trazar el ID. La decision completa esta en la seccion citada
de `logica-negocio-empresa.md` hasta que pase a su fichero de `dominio/`.

| ID | Tema | Decision | Donde esta |
|---|---|---|---|
| O2 | Empresa en la URL (`?companyId=`) | Se quita de la URL. El backend nunca se fia de lo que muestre la URL; la empresa activa es la del token, validada contra la membresia | 3.3 y 11.2 |
| O3 | Solapes de turnos del mismo trabajador | Permitidos con aviso: el backend crea el turno (201) y devuelve `warnings`; el frontend lo muestra | 6.2 |
| O4 | Capa `backend/src/` y API v2 (D20) | v2 solo del area empresa, en `/api/v2/` y `snake_case`. Python se mantiene y `crud.py` no se divide | 11.2; `cambios-empresa.md` 14 |
| O5 | Vista reducida del worker (D5) | Se le da lo que necesita su frontend: `id`, `name`, `is_managed`, ajustes de interfaz y, en solo lectura, `worklog_definitions` y `tax_config` | 9 |
| O6 | Totales del dashboard | Los totales incluyen a los miembros inactivos y el desglose tambien, marcados como inactivos | 11.2 |
| O7 | Confirmaciones pendientes de acceso | Opcion A: el token lleva solo `sub`, `cid`, `scope` y `exp`; rol e `is_admin` se leen de BD | 3.1 y 3.2 |
| O8 | Reactivar una membresia | Vuelve siempre como worker | 5 |
| O9 | Nombre de la clave de IRPF | Claves libres de impuestos: el override usa la misma clave que `tax_config` | 4.4 |
