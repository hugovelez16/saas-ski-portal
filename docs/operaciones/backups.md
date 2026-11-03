# Backups de la base de datos de produccion

Referencia para entender como se generan las copias de seguridad de PostgreSQL en produccion, donde se guardan, como comprobarlas y como restaurarlas. Esta pensado para que una persona o una sesion de Claude, sin contexto previo, sepa que hacer si hay que recuperar datos.

Este documento no contiene secretos ni valores de `.env`. Los datos de acceso al servidor (direccion, usuario) no se incluyen: se indican como `<SERVIDOR_PRODUCCION>` y `<USUARIO>`.

---

## 1. Como funciona

- El stack de produccion (proyecto Compose `ski-saas-prod`, fichero `docker-compose.prod.yml`) incluye el servicio `pgbackups`, contenedor `ski-saas-prod-pgbackups`, con la imagen `prodrigestivill/postgres-backup-local`.
- Se conecta al servicio `postgres` (PostgreSQL 16) y ejecuta `pg_dump` de la base `postgres` con el usuario `postgres`.
- Programacion: `@daily` (00:00 UTC). Configurable con `BACKUP_SCHEDULE`.
- Retencion: 7 diarios, 4 semanales y 3 mensuales (`BACKUP_KEEP_DAYS`, `BACKUP_KEEP_WEEKS`, `BACKUP_KEEP_MONTHS`). Tras cada copia borra los ficheros mas antiguos de su carpeta.
- Formato: SQL plano comprimido con gzip (`pg_dump -Z1`). **No** incluye `DROP` ni `CREATE DATABASE`, y si incluye `OWNER TO postgres`. Por eso restaurar exige partir de un esquema vacio (seccion 4).

## 2. Donde se guardan

- Carpeta del host: `/mnt/nas_backups/clases-vesotel`, montada en el contenedor como `/backups`. El host la monta por NFS desde la NAS (`<NAS>:/Backup_docker`).
- Se configura con la variable `BACKUP_DIR` (por defecto `/mnt/nas_backups/clases-vesotel` en `docker-compose.prod.yml`).
- Subcarpetas: `daily/`, `weekly/`, `monthly/` y `last/`, cada una con un enlace `postgres-latest.sql.gz` a la copia mas reciente.
- Nombres: `postgres-AAAAMMDD.sql.gz` (diario), `postgres-AAAASS.sql.gz` (semanal), `postgres-AAAAMM.sql.gz` (mensual) y `postgres-AAAAMMDD-HHMMSS.sql.gz` (`last/`).
- Los nombres no incluyen el nombre del stack ni de la base. **Dos stacks que escriban en la misma carpeta se pisan los ficheros** y no se puede saber de cual es cada copia. Cada stack debe tener su propia carpeta.
- Carpeta `clases-vesotel-antiguo`: copias de la aplicacion anterior (`saas_ski_vesotel`) y de la base nueva anteriores a la separacion de carpetas. Pueden estar mezcladas: antes de usar una, ver la seccion 3.3. No borrar: son la unica copia de los datos de la aplicacion antigua.
- El stack antiguo (proyecto `ski_prod`) tiene su propio `pgbackups`, `ski_prod-pgbackups-1`, parado a proposito. Si ese stack se redespliega, se recrea y vuelve a montar `BACKUP_DIR`: fijar en su `.env` `BACKUP_DIR=/mnt/nas_backups/clases-vesotel-antiguo` o quitar el servicio de su compose.
- Copias manuales: `~/backups-manual/` en `<SERVIDOR_PRODUCCION>`, con permisos 700. **Solo existen en ese servidor**: copiarlas tambien a la NAS.

## 3. Comprobar que los backups funcionan

Acceso: `ssh <USUARIO>@<SERVIDOR_PRODUCCION>`.

### 3.1 El contenedor y su carpeta

```bash
docker ps --filter name=pgbackups --format '{{.Names}}\t{{.Status}}'
docker inspect -f '{{range .Mounts}}{{if eq .Destination "/backups"}}{{.Source}}{{end}}{{end}}' ski-saas-prod-pgbackups
docker logs --tail 15 ski-saas-prod-pgbackups
```

El `Source` debe ser `/mnt/nas_backups/clases-vesotel`. El log debe terminar en `SQL backup created successfully` tras cada ejecucion.

### 3.2 Los ficheros

```bash
ls -l /mnt/nas_backups/clases-vesotel/daily
gzip -t /mnt/nas_backups/clases-vesotel/daily/postgres-AAAAMMDD.sql.gz && echo OK
```

Debe haber un fichero por dia. Si el ultimo no es de hoy o de ayer, el backup ha fallado.

### 3.3 De que base es una copia

```bash
zcat FICHERO.sql.gz | awk '/^COPY public.alembic_version/{getline; print $1; exit}'
```

Imprime la revision de Alembic. Comparala con la de la base viva:

```bash
docker exec ski-saas-prod-postgres sh -c 'psql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-postgres}" -At -c "select version_num from alembic_version"'
```

Una revision que no pertenece a la cadena de migraciones del repo actual (`backend/migrations/versions/`) indica que el fichero es de la base antigua.

## 4. Restaurar

### 4.1 Antes de empezar

1. Elegir la copia y comprobarla: `gzip -t` y revision de Alembic (3.3).
2. Hacer una copia de seguridad del estado actual (seccion 5), aunque este danado.
3. Decidir el destino: una base limpia de pruebas (4.2) o la base de produccion (4.3).

### 4.2 Restaurar en una base temporal (sin tocar produccion)

Sirve para comprobar que una copia es valida o para inspeccionar datos.

```bash
docker run -d --rm --name tmp-restore-test -e POSTGRES_PASSWORD=test postgres:16-alpine
# esperar a que responda: docker exec tmp-restore-test pg_isready -U postgres
zcat FICHERO.sql.gz | docker exec -i tmp-restore-test psql -U postgres -d postgres -q -v ON_ERROR_STOP=1
docker exec tmp-restore-test psql -U postgres -d postgres -c 'select count(*) from users'
docker stop tmp-restore-test
```

Debe terminar sin errores. Es el procedimiento que se ha ensayado.

### 4.3 Restaurar en la base de produccion

La base de produccion se llama `postgres` y no se puede eliminar estando conectado a ella, asi que se vacia el esquema `public` y se carga la copia.

1. Parar la aplicacion para que nadie escriba: `docker stop ski-saas-prod-backend`.
2. Vaciar el esquema:

```bash
docker exec -i ski-saas-prod-postgres sh -c 'psql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-postgres}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
```

3. Cargar la copia:

```bash
zcat FICHERO.sql.gz | docker exec -i ski-saas-prod-postgres sh -c 'psql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-postgres}" -v ON_ERROR_STOP=1 -q'
```

4. Comprobar `alembic_version` y el numero de filas de las tablas principales (`users`, `companies`, `work_logs`) frente a lo esperado.
5. Arrancar el backend: `docker start ski-saas-prod-backend`, o redeploy desde Komodo. Si la copia es de una version anterior del codigo, el servicio `migrate` aplica las migraciones pendientes al arrancar el stack.

**No verificado:** los pasos 2 y 3 sobre la base viva de produccion no se han ensayado. Lo ensayado es la restauracion en una base limpia (4.2). Conviene probar 4.3 sobre una copia antes de necesitarlo de verdad.

## 5. Copia manual

Para hacer una copia puntual antes de un cambio delicado:

```bash
mkdir -p ~/backups-manual && chmod 700 ~/backups-manual
F=~/backups-manual/ski-saas-prod-$(date +%Y%m%d-%H%M%S).sql.gz
docker exec ski-saas-prod-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "${POSTGRES_DB:-postgres}" --no-owner --no-privileges' | gzip > "$F"
gzip -t "$F" && echo "OK $F"
```

Despues, comprobarla con 4.2 y copiarla a la NAS.

Tambien se puede forzar una copia del mecanismo normal, que escribe en la carpeta del stack y rota las anteriores: `docker exec ski-saas-prod-pgbackups /backup.sh`.

## 6. Si el backup se para

- Contenedor parado o reiniciando: `docker logs ski-saas-prod-pgbackups`, y `docker start ski-saas-prod-pgbackups`.
- Carpeta vacia o sin permisos: comprobar que la NAS esta montada (`findmnt /mnt/nas_backups`) y que la carpeta existe y es escribible.
- Si se mueve o renombra la carpeta del host, el contenedor monta la ruta de nuevo al arrancar. No hace falta recrearlo, pero hay que comprobar la seccion 3.1.
- Fallo de conexion a la base: el servicio depende de `postgres` sano. Ver `docker ps` y los logs de `ski-saas-prod-postgres`.

## 7. Historial relevante

- **2026-11-03:** se detecto que los `pgbackups` de los dos stacks escribian en la misma carpeta con los mismos nombres de fichero. Se paro el del stack antiguo, se renombro la carpeta a `clases-vesotel-antiguo` y se creo `clases-vesotel` vacia para el stack nuevo. Se comprobo con un backup manual que escribe en la carpeta nueva. Los dumps con revisiones de Alembic de la rama de desarrollo hacen sospechar de un tercer escritor (el entorno de desarrollo); **no verificado**.

## 8. Pendiente

- Copiar `~/backups-manual/` a la NAS.
- Fijar `BACKUP_DIR` en el `.env` del stack antiguo (seccion 2).
- Ensayar 4.3 sobre una copia.
- Valorar nombres de fichero con el nombre del stack, para evitar colisiones.
