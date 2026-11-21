# Documentacion

No hace falta leerlo todo. Busca tu tarea en la tabla y lee solo lo que indica.
Las reglas generales estan en [../CLAUDE.md](../CLAUDE.md).

| Fichero o carpeta | Contenido | Cuando leerlo |
|---|---|---|
| [flujo/git.md](flujo/git.md) | Ramas, commits, PR, merge, versionado y proteccion local | Antes del primer commit o PR |
| [flujo/issues.md](flujo/issues.md) | Plantillas, labels, Project y criterio de "listo" | Al crear o refinar issues |
| [flujo/orca.md](flujo/orca.md) | Ciclo con Orca y sin Orca, con los comandos | Al lanzar, reanudar o limpiar un worktree |
| [decisiones/](decisiones/) | ADRs: el porque de cada decision (versionado, ramas y merge) | Si dudas de una decision o vas a cambiarla |
| [empresa/logica-negocio-empresa.md](empresa/logica-negocio-empresa.md) | Comportamiento objetivo de empresa, roles, acceso, membresia y turnos | Dominio provisional: cualquier tarea de empresa, permisos o turnos. Lee solo la seccion que cite la issue |
| [functional_requirements_document.md](functional_requirements_document.md) | Requisitos funcionales de la plataforma | Para entender una funcionalidad existente fuera de empresa |
| [planes-y-precios.md](planes-y-precios.md) | Planes comerciales y cambio de plan | Tareas de landing, planes o modulos de pago |
| [auditoria-propuesta-iliberis.md](auditoria-propuesta-iliberis.md) | Lo prometido al cliente frente a lo que hace el codigo | Antes de prometer o priorizar funcionalidades |
| [operaciones/backups.md](operaciones/backups.md) | Backups de produccion y restauracion | Tareas de infra, migraciones destructivas o despliegue |
| [legal/](legal/) | Textos legales y contrato de encargado del tratamiento | Tareas de paginas legales, RGPD o datos personales |
| [empresa/tareas-manuales-release.md](empresa/tareas-manuales-release.md) | Variables, secretos y pasos manuales por entorno | Antes de una release |
| [empresa/plan-implementacion-empresa.md](empresa/plan-implementacion-empresa.md) | Plan PR-00 a PR-23, ya ejecutado (salvo PR-22) | Solo como historico, o para el paso previo de despliegue de migraciones (secciones 9 y 10) |

Pendiente (fase 2): `docs/dominio/` por entidad con reglas con ID, glosario,
preguntas abiertas y paso de los planes ya ejecutados a `docs/historico/`.
