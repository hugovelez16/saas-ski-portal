---
name: smart-flow
description: "Orquesta el ciclo completo de entrega en Git: audita y propone commits atomicos (smart-commit), sube los cambios de forma segura (smart-push) y redacta y abre el Pull Request (smart-pr), solicitando confirmacion paso a paso o en bloque."
disable-model-invocation: true
---

# Skill: Smart Flow - Orquestador Integral de Entrega Git

## Rol y Objetivo

Actuas como el guardian de calidad y orquestador integral del ciclo de entrega en Git para saas-ski-portal. Tu objetivo es integrar en una sola experiencia fluida y segura las tres etapas clave de publicacion:

1. **Smart Commit:** Auditoria de cambios locales, limpieza de temporales y propuesta de commits atomicos en espanol.
2. **Smart Push:** Verificacion de sincronizacion y subida segura de commits al repositorio remoto.
3. **Smart PR:** Redaccion tecnica estructurada (sin prefijo WIP) y apertura del Pull Request hacia la rama base `develop`.

---

## Reglas Obligatorias de Gobernanza (CLAUDE.md)

- **Cero automatismos sin confirmacion:** NUNCA ejecutar commits, pushes ni abrir PRs sin que el usuario haya revisado y aprobado explicitamente el plan.
- **Idioma estrictamente en espanol:** Nombres de ramas, mensajes de commit, titulos y descripciones de PRs deben estar redactados en espanol.
- **Prohibicion estricta de emojis:** Redaccion 100% tecnica, sobria y profesional en texto plano y markdown estandar.
- **Titulos de PR sin prefijo WIP:** El titulo del Pull Request debe seguir la convencion de commits en espanol (`<tipo>(<ambito>): <descripcion>` o `<tipo>: <descripcion>`) directamente sin `WIP:`.
- **Proteccion de ramas:** Prohibido commitear o pushear directamente sobre `main` o `develop`.
- **Incremento de Version SemVer (cuando aplique):** Verificar si el cambio requiere bump de version (`package.json`, `frontend/package.json`, `CHANGELOG.md`) o si aplica la excepcion (infraestructura local, contenedores dev, tooling o tareas *chore*).

---

## Flujo de Trabajo Obligatorio

### Fase 1: Diagnostico Integral y Auditoria (Solo Lectura)

Ejecuta unicamente comandos de inspeccion para recopilar el estado completo:

1. **Rama de trabajo:**
   - `git branch --show-current`.
   - Si la rama es `main` o `develop`, detiene el flujo y advierte de que se debe crear una rama de caracteristica (`<tipo>/<descripcion-en-espanol>`).

2. **Estado local y limpieza:**
   - `git status -s`.
   - Detecta archivos temporales, logs, caches o ficheros no deseados para sugerir su eliminacion o exclusion en `.gitignore`.

3. **Analisis de diff y commits atomicos:**
   - `git diff` y `git diff --cached`.
   - Agrupa los cambios por contexto funcional en commits atomicos independientes siguiendo Conventional Commits en espanol (`feat:`, `fix:`, `refactor:`, `chore:`, `ci:`, `docs:`).

4. **Verificacion de sincronizacion remota:**
   - `git status -sb` y comprobacion de upstream (`git rev-parse --abbrev-ref @{u}` si existe).

5. **Evaluacion de Version SemVer:**
   - Determina si los cambios requieren incremento de version segun las reglas de `CLAUDE.md` (`package.json`, `frontend/package.json`, `CHANGELOG.md`).

---

### Fase 2: Presentacion del Plan Integral (ESPERA CONFIRMACION)

**NO ejecutes ningun comando de escritura (`git add`, `git commit`, `git push`, creacion de PR) todavia.**
Muestra al usuario el plan unificado de entrega:

```markdown
### Plan Integral de Entrega (Smart Flow)

#### 1. Limpieza y Commits Atomicos Propuestos:
- [ ] Limpieza: (ej. anadir temp a .gitignore / sin temporales detectados)
- **Commit 1:** `<tipo>(<ambito>): <descripcion concisa en espanol>`
  - Archivos: `<lista de archivos>`
- **Commit 2:** `<tipo>(<ambito>): <descripcion concisa en espanol>`
  - Archivos: `<lista de archivos>`

#### 2. Sincronizacion y Push Remoto:
- **Rama local:** `<rama_actual>`
- **Destino remoto:** `origin/<rama_actual>` (Crear nueva upstream / Actualizar existente)

#### 3. Propuesta de Pull Request:
- **Rama Base:** `develop`
- **Titulo:** `<tipo>(<ambito>): <descripcion>`
- **Incremento SemVer:** `<version>` (o "No requerido por tratarse de tarea interna/chore")
- **Resumen:** <1-2 frases del proposito>
- **Detalle de cambios:** <puntos principales>
- **Validaciones:** <evidencia de tests/builds ejecutados>
```

> **Pregunta de confirmacion:**
> - `Completo` / `Adelante` -> Ejecuta el flujo integro en secuencia (Commit -> Push -> Creacion de PR).
> - `Paso a paso` -> Ejecuta el commit primero y pide confirmacion antes del push y la PR.
> - O indica si deseas ajustar commits, titulo o descripcion.

---

### Fase 3: Ejecucion Secuencial (Tras Aprobacion)

Tras recibir el consentimiento explicito:

1. **Etapa A - Limpieza y Commits:**
   - Aplica limpiezas o exclusiones acordadas.
   - Realiza `git add` especifico por cada bloque y ejecuta `git commit -m "<mensaje-en-espanol>"`.

2. **Etapa B - Push Seguro:**
   - Ejecuta `git push -u origin <rama_actual>`.

3. **Etapa C - Creacion Directa del Pull Request via GitHub CLI:**
   ```bash
   gh pr create --base develop --head <rama_actual> --title "<tipo>(<ambito>): <descripcion>" --body "<cuerpo_markdown_estructurado>"
   ```

---

### Fase 4: Resumen Final de Entrega

Finaliza mostrando un resumen claro con:
- Estado del arbol de trabajo (`git status -s`).
- Commits confirmados y subidos al remoto.
- Numero y enlace navegable directo del Pull Request creado en GitHub.
