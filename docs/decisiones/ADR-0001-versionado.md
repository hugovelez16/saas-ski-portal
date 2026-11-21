# ADR-0001: Versionado

Estado: Aceptada (2026-11-21)

## Contexto

Hasta la 0.27.0 cada PR subia la version SemVer en `package.json`,
`frontend/package.json` y `CHANGELOG.md` (antigua regla 8 de `CLAUDE.md`).
Tenia dos problemas:

- Con varios agentes en paralelo (un worktree por issue), todos los PR chocaban
  en esos tres ficheros.
- Un merge a `develop` que no subia la version volvia a publicar la misma
  imagen `dev-vX.Y.Z` en GHCR y Komodo perdia el punto de rollback anterior.

## Decision

Se usa SemVer con prereleases en dev, como en portal-pisos:

1. En `develop`, `package.json` (raiz) y `frontend/package.json` guardan la
   **proxima** version (por ejemplo `0.28.0`). El raiz es la fuente de verdad.
2. Cada push a `develop` hace que `deploy-dev` calcule
   `0.28.0-dev.<github.run_number>`, etiquete con ella las imagenes
   (`dev-v0.28.0-dev.N` y `dev-latest`), cree el tag git `v0.28.0-dev.N` y
   despliegue el stack dev en Komodo.
3. Los PR normales no tocan la version. Solo anaden su linea en
   `## [Unreleased]` del `CHANGELOG.md` con `(#<n>)`.
4. Release (skill `release`):
   - Un PR `chore(release): prepara vX.Y.Z` a `develop` pasa `[Unreleased]` a
     `## [X.Y.Z] - <fecha>`.
   - Despues se abre el PR de `develop` a `main`. El merge lo hace el usuario.
   - `deploy-prod` publica `vX.Y.Z` y `latest`.
5. Tras la release, un PR a `develop` sube `package.json` y
   `frontend/package.json` a la siguiente version (minor por defecto).

## Consecuencias

- `0.28.0-dev.5` es anterior a `0.28.0` segun SemVer: el orden es correcto.
- Los numeros `N` pueden saltar (ejecuciones fallidas). No importa.
- Solo chocan las lineas de `[Unreleased]`, y el conflicto se resuelve
  conservando ambas.
- El tipo de cambio (MAJOR, MINOR, PATCH) se decide en la release a partir de
  `[Unreleased]`, no en cada PR.
- `deploy-prod` no crea tag git; la version de produccion queda en la imagen
  `vX.Y.Z` y en el CHANGELOG.
