---
name: smart-pr
description: "Revisa la rama actual, analiza los diffs frente a la rama base (develop), redacta titulo y descripcion estructurada y crea el Pull Request tras confirmacion."
disable-model-invocation: true
---

# Skill: Smart PR & Review Requester

## Rol y Objetivo

Actuas como un especialista en integracion y control de calidad de Git para saas-ski-portal. Tu objetivo es inspeccionar los commits y cambios funcionales de la rama actual frente a la rama base (`develop`), redactar un titulo descriptivo en espanol siguiendo Conventional Commits (sin prefijo WIP), estructurar una documentacion exhaustiva de la PR, verificar el cumplimiento de las reglas de gobernanza de `CLAUDE.md` (incremento de version si aplica, cero emojis) y solicitar la confirmacion del usuario antes de abrir el Pull Request a traves de la CLI (`gh pr create`) o interfaz web.

---

## Flujo de Trabajo Obligatorio

### Fase 1: Diagnostico e Inspeccion Previa (Solo Lectura)

1. **Verificar rama actual y rama base:**
   - Rama actual: `git branch --show-current`.
   - Si la rama es `main` o `develop`, advierte al usuario de que no se debe abrir una PR de la rama principal sobre si misma.
   - En este repositorio, la rama base destino por defecto es `develop`.

2. **Verificar estado del arbol local:**
   - `git status -s`.
   - Si hay cambios no commiteados, avisa al usuario y recomienda guardar el trabajo (`smart-commit`) antes de abrir la PR.

3. **Verificar sincronizacion con el remoto:**
   - Comprueba si la rama tiene upstream configurado y si todos los commits locales han sido subidos (`git status -sb`).
   - Si hay commits pendientes de subir al remoto, recomienda ejecutar `smart-push` antes de continuar.

4. **Analizar el contenido y diff de la PR:**
   - Listar commits incluidos: `git log origin/develop..HEAD --oneline`.
   - Analizar cambios en archivos: `git diff --stat origin/develop...HEAD`.
   - Identificar los cambios funcionales y de logica (ignorando formateos o comentarios triviales).

5. **Verificar regla de incremento de version SemVer:**
   - Comprueba si los cambios introducen nuevas funcionalidades, correcciones o cambios visibles en la plataforma.
   - Si aplica incremento de version, verifica que se hayan actualizado:
     1. `package.json` (raiz)
     2. `frontend/package.json`
     3. `CHANGELOG.md`
   - Si el cambio es puramente de infraestructura local, configuracion de contenedores de desarrollo o tareas de mantenimiento (*chore*) sin impacto en la API o interfaz, confirma que no es necesario el incremento de version.

---

### Fase 2: Redaccion y Preparacion de la PR

1. **Estructura del Titulo:**
   - Seguir formato Conventional Commits en espanol: `<tipo>(<ambito>): <descripcion concisa en espanol>` o `<tipo>: <descripcion concisa en espanol>` (ejemplo: `feat(backend): implementar calculo de tarifas`).
   - No usar prefijo `WIP:`.

2. **Estructura de la Descripcion (Body):**
   - **Resumen:** Proposito principal del cambio en 1-2 frases.
   - **Cambios funcionales:** Lista detallada de las modificaciones tecnicas reales agrupadas por modulo/componente.
   - **Verificacion / Pruebas:** Evidencia de ejecucion de tests (`npm test`, `pytest`), linters o validaciones previas.
   - **Cero emojis:** Redaccion sobria, tecnica y profesional en texto plano y markdown.

---

### Fase 3: Propuesta y Confirmacion (ESPERA CONFIRMACION)

**NO ejecutes la creacion de la PR todavia.**
Muestra un resumen estructurado:

```markdown
### Plan de Pull Request Propuesto

- **Rama Origen:** `<rama_actual>`
- **Rama Destino:** `develop`
- **Titulo:** `<tipo>(<ambito>): <descripcion>`
- **Incremento SemVer:** `<version_anterior> -> <nueva_version>` (o "No requerido por tratarse de tarea interna de infraestructura/chore")

#### Descripcion propuesta:

## Resumen de Cambios
...

### Cambios Detallados
...

### Verificacion
...
```

> **Pregunta de confirmacion:**
> Solicita al usuario confirmacion explicita (`Si` / `Adelante`) antes de crear el Pull Request.

---

### Fase 4: Creacion Automatizada de la PR

Una vez que el usuario otorgue confirmacion explicita (`Si` / `Adelante` / `Completo`):

1. **Creacion con GitHub CLI (`gh`):**
   ```bash
   gh pr create --base develop --head <rama_actual> --title "<tipo>(<ambito>): <descripcion>" --body "<cuerpo_en_markdown>"
   ```

2. **Informe del Resultado:**
   - Mostrar el numero de Pull Request generado (`#X`).
   - Mostrar el enlace navegable directo al Pull Request creado.
   - Confirmar el estado de la entrega y el seguimiento de checks de CI.
