---
name: daily-sync
description: "Comprueba actualizaciones remotas al inicio del día, audita cambios locales no guardados antes de hacer pull/rebase y sincroniza el repositorio de forma segura."
triggers:
  - "sync"
  - "actualizar repo"
  - "pull"
  - "hay cambios"
  - "inicio del dia"
  - "buenos dias"
---

# Skill: Daily Sync & Remote Checker

## Rol y Objetivo
Actúas como un guardián de sincronización de Git. Tu función es verificar si el repositorio local está al día con la rama remota al comenzar la jornada, asegurando que el usuario no trabaje sobre una versión desactualizada ni pierda trabajo local por sobrescrituras accidentales.

---

## Flujo de Trabajo Obligatorio

### Fase 1: Diagnóstico e Inspección Remota
1. Descarga el estado más reciente del servidor remoto **sin alterar tu área de trabajo local**:
   ```bash
   git fetch --all --prune
   ```
2. Revisa el estado de la rama actual y la diferencia con su *upstream*:
   ```bash
   git status -sb
   ```
3. Comprueba si hay commits en el remoto que no tienes en local:
   ```bash
   git log HEAD..@{u} --oneline
   ```

---

### Fase 2: Análisis de Escenarios y Respuesta

Analiza el resultado y actúa según el estado detectado:

####  Escenario A: Todo actualizado (*Up to date*)
Si el repositorio local y el remoto están en el mismo commit y no hay cambios pendientes:
- Confirma al usuario con un mensaje claro y corto:
  > *"¡Todo al día! Tu repositorio local está alineado con el remoto y no hay cambios pendientes. Listo para empezar a trabajar."*

####  Escenario B: Hay cambios en el remoto y tu local está LIMPIO
Si el servidor remoto tiene commits nuevos y tú no tienes cambios locales pendientes:
- Muestra los commits que se van a descargar (autor, fecha/mensaje corto).
- Aplica directamente el pull (preferiblemente con `--ff-only` o rebase limpio):
  ```bash
  git pull --ff-only
  ```
- Confirma que la actualización fue exitosa y muestra el nuevo commit en el que te encuentras.

####  Escenario C: Hay cambios en el remoto Y ADEMÁS tienes cambios locales sin commitear
Si hay novedades en el remoto pero el usuario ya estuvo tocando código en local:
1. **NO hagas `git pull` directo** (evitarás ensuciar el código con conflictos no deseados).
2. Muestra un resumen claro:
   * Commits pendientes de bajar desde el remoto.
   * Archivos locales que están modificados actualmente.
3. Propón las opciones seguras para proceder:
   * **Opción 1:** Hacer un `git stash`, aplicar `git pull` y luego `git stash pop`.
   * **Opción 2:** Usar la skill `smart-commit` para guardar primero lo local antes de traer lo remoto.

---

### Fase 3: Resumen Final
Termina siempre mostrando un breve estado final (`git status -s`) para que el usuario sepa exactamente en qué punto se queda su entorno de trabajo.