---
name: smart-flow
description: "Orquesta el ciclo completo de entrega en Git: audita y propone commits atomicos (smart-commit), sube los cambios de forma segura (smart-push) y redacta y abre el Pull Request en Forgejo con prefijo WIP (smart-pr), solicitando confirmacion paso a paso o en bloque."
triggers:
  - "smart-flow"
  - "/smart-flow"
  - "smart flow"
  - "smart ship"
  - "entregar cambios"
  - "flujo completo git"
  - "publicar cambios"
  - "commit push pr"
---

# Skill: Smart Flow - Orquestador Integral de Entrega Git

## Rol y Objetivo

Actuas como el guardián de calidad y orquestador integral del ciclo de entrega en Git para poc-portal. Tu objetivo es integrar en una sola experiencia fluida y segura las tres etapas clave de publicacion:

1. **Smart Commit:** Auditoria de cambios locales, limpieza de temporales y propuesta de commits atomicos en espanol.
2. **Smart Push:** Verificacion de sincronizacion y subida segura de commits al repositorio remoto (Forgejo).
3. **Smart PR:** Redaccion tecnica estructurada con prefijo `WIP:` y apertura del Pull Request hacia la rama base `develop`.

---

## Reglas Obligatorias de Gobernanza (AGENTS.md)

- **Cero automatismos sin confirmacion:** NUNCA ejecutar commits, pushes ni abrir PRs sin que el usuario haya revisado y aprobado explicitamente el plan.
- **Idioma estrictamente en espanol:** Nombres de ramas, mensajes de commit, titulos y descripciones de PRs deben estar redactados en espanol.
- **Prohibicion estricta de emojis:** Redaccion 100% tecnica, sobria y profesional en texto plano y markdown estandar.
- **Prefijo WIP obligatorio en PRs:** El titulo del Pull Request debe iniciar con `WIP:`.
- **Proteccion de ramas:** Prohibido commitear o pushear directamente sobre `main` o `develop`.
- **Incremento de Version SemVer (cuando aplique):** Verificar si el cambio requiere bump de version (funcionalidades o correcciones visibles) o si aplica la excepcion (infraestructura local, contenedores dev, tooling o tareas *chore*).

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
   - Determina si los cambios requieren incremento de version segun `AGENTS.md`. Si aplica, comprueba que se hayan actualizado los 5 archivos requeridos (`shared/package.json`, `shared/src/version.ts`, `backend/package.json`, `frontend/package.json`, `CHANGELOG.md`).

---

### Fase 2: Presentacion del Plan Integral (ESPERA CONFIRMACION)

**NO ejecutes ningun comando de escritura (`git add`, `git commit`, `git push`, peticion de PR) todavia.**
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
- **Titulo:** `WIP: <tipo>(<ambito>): <descripcion>`
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
   - Ejecuta `git push -u origin <rama_actual>` hacia Forgejo.

3. **Etapa C - Creacion Directa del Pull Request via API:**
   - Obtener el token de acceso personal de Forgejo:
     ```bash
     TOKEN=$(printf "protocol=https\nhost=git.civica-soft.com\n\n" | git credential fill | grep '^password=' | cut -d= -f2)
     ```
   - Extraer la ruta del repositorio:
     ```bash
     REPO_PATH=$(git config --get remote.origin.url | sed -E 's/.*git\.civica-soft\.com[:\/](.+)\.git/\1/')
     ```
   - Realizar la llamada `POST /api/v1/repos/{owner}/{repo}/pulls` en la API de Forgejo:
     ```bash
     curl -s -X POST \
       -H "Authorization: token $TOKEN" \
       -H "Content-Type: application/json" \
       -d '{
         "head": "<rama_actual>",
         "base": "develop",
         "title": "WIP: <tipo>(<ambito>): <descripcion>",
         "body": "<cuerpo_markdown_estructurado>"
       }' \
       "https://git.civica-soft.com/api/v1/repos/${REPO_PATH}/pulls"
     ```
   - Extrae el `html_url` y el numero de PR retornado por Forgejo.

---

### Fase 4: Resumen Final de Entrega

Finaliza mostrando un resumen claro con:
- Estado del arbol de trabajo (`git status -s`).
- Commits confirmados y subidos al remoto.
- Numero y enlace navegable directo del Pull Request creado en Forgejo (`https://git.civica-soft.com/<owner>/<repo>/pulls/<id>`).
