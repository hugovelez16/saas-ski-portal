# Contexto y Reglas para Agentes (AGENTS.md)

Este repositorio contiene la plataforma SaaS de gestion de escuelas de esqui, reservas y jornadas laborales (saas_ski_vesotel).

## Reglas Obligatorias para Agentes

1. PROHIBICION ESTRICTA DE COMMITS, PUSHES Y PRs AUTOMATICOS (ALCANCE PUNTUAL):
   - El agente NUNCA debe ejecutar git commit, git push ni crear un Pull Request por iniciativa propia, incluso tras resolver errores o implementar correcciones tecnicas.
   - Alcance puntual de las ordenes: Si el usuario indica en un mensaje especifico ejecutar un commit, push o PR (o invoca las skills /smart-commit, /smart-push), dicha autorizacion tiene validez unica y exclusiva para esa accion y ese momento puntual.
   - Prohibicion de arrastre de permisos: Una autorizacion previa NUNCA otorga permiso implicito o permanente para iteraciones o turnos posteriores.
   - En cada cambio posterior, el agente debe limitarse a modificar archivos locales o reportar la solucion y esperar la confirmacion explicita del usuario.

2. IDIOMA DE LOS COMMITS Y RAMAS: ESPANOL:
   - TODOS los mensajes de commit y nombres de ramas en este repositorio deben redactarse obligatoriamente en ESPANOL.
   - Nombres de ramas: <tipo>/<descripcion-en-espanol> (ej: feature/reportes-diarios, fix/validador-tarifa).
   - Mensajes de commit: <tipo>: <descripcion concisa en espanol> (ej: feat: anadir filtro por empresa en dashboard).

3. PROHIBICION ESTRICTA DE EMOJIS (NO EMOJIS):
   - NUNCA utilizar emojis en ningun contexto del repositorio:
     - No usar emojis en codigo fuente (Python, TypeScript, HTML, CSS, Bash).
     - No usar emojis en comentarios de codigo.
     - No usar emojis en mensajes de commit de Git.
     - No usar emojis en titulos ni descripciones de Pull Requests.
     - No usar emojis en respuestas o resumenes dirigidos al usuario.
   - El estilo debe ser 100% sobrio, tecnico y profesional en texto plano y markdown estandar.

4. CREACION DE PULL REQUESTS CON PREFIJO WIP:
   - Cada vez que el agente cree o proponga un Pull Request a peticion del usuario, el titulo debe comenzar obligatoriamente con el prefijo WIP: (ejemplo: WIP: feat(backend): implementar calculo de tarifas).

5. VERIFICACION OBLIGATORIA DE RAMA ANTES DE MODIFICAR CODIGO:
   - Antes de iniciar cambios o desarrollos, el agente DEBE verificar obligatoriamente en que rama se encuentra (git branch --show-current).

6. PROTECCION ESTRICTA DE RAMAS MAIN Y DEVELOP:
   - Las ramas `main` y `develop` estan protegidas y tienen deshabilitado el push directo.
   - NUNCA intentar hacer push directo a `develop` o `main`.
   - Todos los cambios deben realizarse en ramas de caracteristica con nomenclatura en espanol (<tipo>/<descripcion-en-espanol>) y fusionarse mediante Pull Request tras pasar las validaciones de CI.

7. USO EXCLUSIVO DE HERRAMIENTAS NATIVAS DE EDICION (PROHIBIDO CAT / SED / REDIRECCIONES BASH):
   - Para editar o crear archivos de texto plano, codigo fuente, workflows YAML, configuraciones o documentacion, el agente DEBE utilizar EXCLUSIVAMENTE las herramientas de edicion nativas (`replace_file_content`, `write_to_file`).
   - Queda TERMINANTEMENTE PROHIBIDO usar comandos de consola bash (`cat << 'EOF'`, `echo >`, `sed -i` o similares) para inyectar o modificar contenido en archivos del repositorio. La consola bash solo debe utilizarse para ejecutar tests, linters, git o comandos del sistema.

8. ENTORNO DE DESARROLLO LOCAL BASADO EN GATEWAY UNIFICADO:
   - El desarrollo en local se ejecuta a traves de `docker-compose.dev.yml` con el servicio `gateway` (Nginx) expuesto en el puerto `8080:80`.
   - El frontend atiende en `/` y el backend en `/api/`.
   - Todo montaje de volumen debe utilizar el sufijo `:z` para compatibilidad con SELinux y Podman rootless.

9. INCREMENTO OBLIGATORIO DE VERSION SEMVER POR PULL REQUEST:
   - Cada Pull Request que introduzca nuevas funcionalidades (minor), correcciones de errores (patch) o cambios estructurales (major) debe incluir obligatoriamente un incremento de version SemVer (siguiendo PRINCIPAL.MENOR.PARCHE, ej: 0.1.0 -> 0.1.1 o 0.2.0).
   - Excepcion: No es obligatorio incrementar la version si el Pull Request corresponde a cambios puramente internos de configuracion de desarrollo local o tooling menor que no afecte al despliegue o a la aplicacion.
   - Justificacion tecnica y operativa: Cada merge a `develop` o `main` desencadena la compilacion y publicacion automatica de imagenes en GitHub Container Registry (GHCR) etiquetadas con la version SemVer canonica (`dev-vX.Y.Z` o `vX.Y.Z`). Sin este incremento, se perderia la trazabilidad, la capacidad de auditoria y la posibilidad de rollback en Komodo.
   - Archivos obligatorios a actualizar cuando aplique incremento de version:
     1. `package.json` (campo `version` en raiz, fuente de verdad principal).
     2. `frontend/package.json` (campo `version`).
     3. `CHANGELOG.md` (nueva seccion con version, fecha y resumen de cambios bajo el estandar Keep a Changelog).
   - Los mensajes de commit NO deben llevar el numero de version en su titulo; los commits deben describir concisamente el cambio tecnico realizado.

