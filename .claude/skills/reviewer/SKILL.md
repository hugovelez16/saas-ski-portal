---
name: reviewer
description: Auditoria integral de codigo, revision de directivas de gobernanza de CLAUDE.md (cero emojis, espanol, formato convencional de PR), buenas practicas y cobertura de pruebas. Usar al realizar revisiones de codigo antes de solicitar confirmacion para merge o PR.
---

# Checklists complementarios de revision

La revision completa la define el agente `reviewer` (`.claude/agents/reviewer.md`). Esta skill solo aporta checklists y comandos de apoyo; no encadena otros agentes ni skills.

## Checklist de gobernanza (reglas de CLAUDE.md)

- [ ] Sin emojis en codigo, comentarios, commits ni descripciones de PR.
- [ ] Commits y ramas en espanol (`<tipo>(<ambito>): <descripcion>`, `<tipo>/<descripcion-en-espanol>`).
- [ ] Titulo de PR en espanol y sin prefijo `WIP:`.
- [ ] Incremento SemVer coherente en `package.json`, `frontend/package.json` y `CHANGELOG.md` (si aplica).
- [ ] Trabajo en rama de caracteristica, nunca directo sobre `main` o `develop`.

## Checklist tecnico

- [ ] `ruff check backend/` y `cd backend && pytest tests/` limpios.
- [ ] Desde `frontend/`: `npm run lint`, `npx tsc --noEmit`, `npm test` y `npm run build` limpios.
- [ ] Endpoints protegidos con las dependencias de auth/roles existentes y filtrado por empresa.
- [ ] Cambios de modelo con migracion Alembic reversible.
- [ ] Sin secretos en el repositorio.

## Busqueda de emojis (solo lectura)

```bash
git diff --name-only origin/develop...HEAD | xargs -r grep -nP '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]'
```

Sin salida significa que no se detectaron emojis en los ficheros modificados.
