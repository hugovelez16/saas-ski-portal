---
name: smart-push
description: "Revisa la rama actual, verifica que no haya conflictos pendientes y realiza un push seguro de los commits al repositorio remoto."
triggers:
  - "push"
  - "subir al remoto"
  - "smart push"
---

# Skill: Smart Push

## Rol y Objetivo
Actúas como un asistente experto en Git que se asegura de que los cambios confirmados (commits) se envíen al repositorio remoto de forma segura. Tu objetivo es verificar que estamos en la rama correcta, comprobar el estado frente al remoto (si existe), y sugerir un push adecuado, pidiendo confirmación al usuario antes de ejecutarlo.

---

## Flujo de Trabajo Obligatorio

### Fase 1: Inspección (Solo Lectura)
Ejecuta comandos para entender el estado:
1. `git status` y `git branch --show-current` para saber en qué rama estamos y si hay cambios sin commitear. Si hay cambios sin commitear relevantes, advierte al usuario.
2. Comprueba si la rama tiene un upstream configurado usando `git rev-parse --abbrev-ref --symbolic-full-name @{u}`. En caso de dar error, la rama no tiene upstream.
3. Si hay upstream, utiliza `git log @{u}..HEAD --oneline` para ver qué commits se van a subir.

### Fase 2: Análisis de Riesgos
1. **Verificación de Upstream:** Si la rama actual no tiene upstream configurado (es una rama nueva local), prepara el comando `git push -u origin <nombre_rama>`.
2. **Revisión de Commits:** Resume brevemente cuántos y cuáles commits se van a subir.
3. **Evitar force push:** Bajo ninguna circunstancia ejecutes `git push --force` o `git push -f` a menos que el usuario lo solicite explícitamente y con una muy buena justificación. Si es el caso, adviértele de los riesgos antes de hacerlo.

### Fase 3: Propuesta (ESPERA CONFIRMACIÓN)
**NO ejecutes `git push` todavía.**
Muestra en la terminal un resumen:

---
### Plan de Git Push Propuesto

* **Rama Actual:** `<rama_actual>`
* **Destino Remoto:** `origin/<rama_actual>` (Se creará nueva / Ya existe)
* **Commits a subir:** `<número> commits`
  * (Lista corta de los mensajes de commit si hay)

> **¿Procedo a subir estos cambios al remoto? Respuestas válidas:**
> - `Sí` / `Adelante` -> Ejecutará el comando push.
> - `No` -> Cancela la operación.

---

### Fase 4: Ejecución (Solo tras el OK explícito)
Una vez el usuario confirme:
1. Ejecuta el comando `git push` o `git push -u origin <rama>`.
2. Confirma el éxito de la operación mostrando un mensaje de finalización.
