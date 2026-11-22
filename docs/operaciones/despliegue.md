# Despliegue de produccion

Produccion corre siempre una version fija y conocida. `deploy-prod` ya no despliega por webhook: publica las imagenes y el tag git, y el despliegue y el rollback se hacen cambiando `IMAGE_TAG` en el stack de produccion de Komodo. En dev no cambia nada: cada merge a `develop` despliega `X.Y.Z-dev.N` (ADR-0001).

## Como funciona

- `docker-compose.prod.yml` exige `IMAGE_TAG` en `migrate`, `backend`, `frontend` y `gateway`. Sin la variable, el stack no arranca y el error indica que falta (`required variable IMAGE_TAG is missing a value`). No existe valor por defecto ni se usa `latest`.
- `IMAGE_TAG` es una version con prefijo `v`, por ejemplo `v0.28.0`. Se define en las variables del stack de produccion en Komodo, no en el repositorio.
- `deploy-prod.yml` se ejecuta con cada push a `main` (y `workflow_dispatch`): construye y publica `backend`, `frontend` y `gateway` con los tags `vX.Y.Z` y `latest`, y crea el tag git `vX.Y.Z` si no existe. `latest` se sigue publicando por compatibilidad, pero produccion no debe usarlo.

## Desplegar una version

1. Haz la release (skill `release`): el PR de `develop` a `main` lo fusiona el usuario.
2. Espera a que `deploy-prod` termine en verde y comprueba que existen las imagenes y el tag:

   ```bash
   gh run list --repo hugovelez16/saas-ski-portal --workflow deploy-prod.yml --limit 1
   git ls-remote --tags origin 'refs/tags/vX.Y.Z'
   ```

3. Antes de desplegar, si la version lleva una migracion con paso previo (backup o script de reparacion), sigue `backups.md` y la seccion 10 de `empresa/plan-implementacion-empresa.md`.
4. En Komodo, abre el stack de produccion y cambia `IMAGE_TAG` a `vX.Y.Z`.
5. Despliega el stack (Deploy). El servicio `migrate` aplica las migraciones y `backend` arranca cuando termina bien.
6. Verifica:
   - Logs del gateway: cada linea debe mostrar la IP real del cliente y `realip_from=<IP del proxy de confianza>` (ver `gateway-ip-real.md`). Si `realip_from` sale vacio o con la IP del cliente, revisa `TRUSTED_PROXIES`.
   - Salud: la ruta `/health` del gateway responde 200 (`curl -fsS https://<dominio>/health`).
   - Los contenedores `migrate` (terminado con exito), `backend`, `frontend` y `gateway` estan en la version esperada.

## Rollback

1. En Komodo, pon `IMAGE_TAG` a la version anterior (por ejemplo `v0.27.0`) y redespliega. Las imagenes anteriores siguen en GHCR; no se borran.
2. Si la version nueva aplico una migracion, decide antes de cambiar la imagen:
   - Si el `downgrade` es completo: ejecuta `alembic downgrade -1` con la imagen NUEVA (es la que contiene los ficheros de migracion) y despues cambia `IMAGE_TAG`. El orden importa.
   - Si el `downgrade` no es completo: restaura el backup previo (`backups.md`) y despues cambia `IMAGE_TAG`.
   El detalle esta en la seccion 10 de `empresa/plan-implementacion-empresa.md`.
3. Verifica igual que tras un despliegue.

## Ver las versiones publicadas

- Tags git: `git ls-remote --tags origin 'refs/tags/v*'` o la lista de tags del repositorio en GitHub. Los de produccion son `vX.Y.Z`; los de dev, `vX.Y.Z-dev.N`.
- Imagenes en GHCR: en GitHub, `Packages` del repositorio (`backend`, `frontend`, `gateway`). Los tags de produccion son `vX.Y.Z` y `latest`; los de dev, `dev-vX.Y.Z-dev.N` y `dev-latest`.
- Version desplegada hoy: el valor actual de `IMAGE_TAG` en el stack de produccion de Komodo.
