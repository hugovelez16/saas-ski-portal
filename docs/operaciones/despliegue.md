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

3. Antes de desplegar, si la version lleva una migracion con paso previo (backup o script de reparacion), sigue `backups.md` y la seccion "Migraciones con paso previo" de este documento.
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
   El detalle operativo esta en la seccion "Migraciones con paso previo" y la decision en `docs/decisiones/ADR-0010-migraciones-con-paso-previo.md`.
3. Verifica igual que tras un despliegue.

## Migraciones con paso previo

Aplica a toda version con migracion Alembic que altere o borre columnas o pueda chocar con datos existentes (ADR-0010). Todo comando de produccion lo ejecuta el usuario, nunca un agente.

1. **Backup manual previo**: ademas del diario de `pgbackups`, haz un `pg_dump -Fc` inmediatamente antes de desplegar (`backups.md`), verifica el volcado con `pg_restore --list <fichero> | head` y anota el `IMAGE_TAG` actual para rollback.
2. **Inventario de vistas manuales (solo lectura)**: si la migracion altera o borra columnas, revisa las vistas del esquema `public` (`pg_views`) y sus dependencias sobre las columnas afectadas (`pg_depend` y `pg_rewrite`), porque bloquean `ALTER`/`DROP`. Las migraciones que usan `backend/migration_helpers.py` guardan y restauran propietario, definicion y privilegios (`GRANT`) al recrear vistas; si aparece una vista no prevista, adaptarla es decision manual antes de migrar.
3. **Ensayo previo con copia anonimizada (recomendado)**: levanta un Postgres 16 desechable en `127.0.0.1` sin volumenes, restaura el volcado, anonimiza antes de cualquier consulta los datos personales (`users`: `email`, `hashed_password`, `first_name`, `last_name`, `otp_secret`; `user_sessions`: `refresh_token`, `ip_address`, `device_name`) y ensaya `alembic upgrade head`, el script en `--dry-run` y la migracion. Al terminar, destruye el contenedor y el volcado temporal.
4. **Script de reparacion de datos (`backend/scripts/`)**:
   - Se ejecuta desde la imagen publicada del backend (`python3 -m scripts.<nombre>`) montando `${BACKUP_DIR}:/backups:z` para guardar los ficheros JSON fuera del repo (permisos `0600`, sin secretos).
   - `--dry-run` es el modo por defecto (no escribe). `--apply --backup-dir /backups/repairs` aplica los cambios en una unica transaccion tras escribir el backup.
   - Codigos de salida: `0` limpio, `2` pendientes de decision manual (no se tocan automaticamente), `1` error.
   - Repite `--dry-run` tras resolver los pendientes manuales y aplicar `--apply` hasta obtener codigo `0`, y vuelve a comprobarlo justo antes de desplegar.
5. **Si `migrate` falla**: PostgreSQL revierte la transaccion DDL y `backend` no arranca (`service_completed_successfully`). Lee el log de `migrate` (indica el script a ejecutar), corrige los datos y relanza el despliegue.
6. **Si falla tras aplicar la migracion**:
   - Con `downgrade` completo: ejecuta `docker compose -f docker-compose.prod.yml run --rm migrate python3 -m alembic downgrade -1` con la imagen NUEVA y despues cambia `IMAGE_TAG` a la version anterior.
   - Con `downgrade` incompleto (perdida de datos): para `backend` y `frontend`, restaura el backup del paso 1 (`backups.md`), cambia `IMAGE_TAG` a la version anterior y redespliega. Los ficheros de `${BACKUP_DIR}/repairs/` permiten recuperacion parcial si procede.

## Ver las versiones publicadas

- Tags git: `git ls-remote --tags origin 'refs/tags/v*'` o la lista de tags del repositorio en GitHub. Los de produccion son `vX.Y.Z`; los de dev, `vX.Y.Z-dev.N`.
- Imagenes en GHCR: en GitHub, `Packages` del repositorio (`backend`, `frontend`, `gateway`). Los tags de produccion son `vX.Y.Z` y `latest`; los de dev, `dev-vX.Y.Z-dev.N` y `dev-latest`.
- Version desplegada hoy: el valor actual de `IMAGE_TAG` en el stack de produccion de Komodo.
