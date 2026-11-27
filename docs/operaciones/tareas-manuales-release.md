# Tareas manuales de release (fuera del repositorio)

Lista viva de lo que NO se despliega con el codigo y hay que hacer a mano antes o despues de llevar los PRs del plan de empresa a `develop`, `main` y produccion. Cada bloque que anada una tarea de este tipo la apunta aqui en el mismo PR. Las acciones sobre produccion de los bloques con migracion (backup y script de reparacion con `--apply`) estan detalladas en las secciones 9 y 10 de `plan-implementacion-empresa.md`; aqui solo se enlazan.

Al terminar un despliegue, marcar la casilla con la fecha.

## Variables y secretos

| Variable | Donde se define | Bloque | Obligatoria | Efecto si falta |
|---|---|---|---|---|
| `NEXT_PUBLIC_CONTACT_EMAIL` | Variable (no secreto) de GitHub Actions del repositorio (Settings > Secrets and variables > Actions > Variables); la usan `deploy-dev.yml` y `deploy-prod.yml` como `build-arg` del frontend. No va en Komodo: se incrusta en el build, que ocurre en GitHub. Para desarrollo local, `.env`/entorno del contenedor de frontend. | PR-19 | No, pero conviene | El correo del administrador no se muestra en la pantalla "No estas vinculado a ninguna empresa" ni en el dialogo "Request Access" del login. No hay valor por defecto en el codigo. |

Notas:
- Las variables `NEXT_PUBLIC_*` de Next.js se incrustan en el build: cambiar el secreto exige volver a construir y publicar la imagen del frontend (merge a `develop` o `main`), no basta con reiniciar el contenedor.
- Una variable de GitHub no definida se pasa como cadena vacia: el build no falla.
- Si dev y produccion deben mostrar correos distintos, definir la variable por entorno de GitHub (Environments) en vez de a nivel de repositorio.

## Checklist por entorno

### develop (dev)
- [ ] Crear la variable `NEXT_PUBLIC_CONTACT_EMAIL` en GitHub (Settings > Secrets and variables > Actions > Variables) antes del merge de PR-19 a `develop`.

### main (produccion)
- [ ] Comprobar que la variable `NEXT_PUBLIC_CONTACT_EMAIL` existe antes del merge a `main` (es la misma variable de repositorio).
- [ ] Bloques con migracion y script de reparacion (PR-06, PR-09, PR-10, PR-11, PR-23): backup y `--apply` previos, segun las secciones 9 y 10 del plan.

## Cambios de comportamiento a comunicar

- PR-19: la empresa activa ya no va en la URL (`?companyId=`). Cambiar de empresa en una pestana la cambia en todas las pestanas abiertas (cookie compartida). Los marcadores o enlaces antiguos con `?companyId=` dejan de filtrar.
- PR-19: el informe de impresion (`/reports/print`) se genera sobre la empresa activa; un administrador de plataforma sin empresa activa ve todas.
