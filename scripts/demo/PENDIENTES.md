# Video de presentacion: estado y mejoras pendientes

Registro para retomar el trabajo sobre el video de demo. Rama: `feature/video-presentacion-demo`.

## Estado actual

- Datos de demo: `backend/demo_seed.py` y `./bin/seed-demo` (empresa "Escuela de Esqui Nieve Sur", 1 manager, 6 monitores, unas 250 jornadas semialeatorias con semilla fija).
- Grabacion: `scripts/demo/grabar-demo.mjs` (Playwright). Genera `videos/demo-presentacion.webm` y `videos/demo-presentacion.zoom.json`.
- Edicion: `scripts/demo/editar-zoom.mjs` (ffmpeg). Aplica zoom suave a los dialogos y exporta `videos/demo-presentacion-zoom.webm`. Para la exportacion final: `FORMATO=mp4 npm run editar`.
- Comandos, desde `scripts/demo` y con el entorno levantado (`npm run docker:dev`, `./bin/migrate`, `./bin/seed-demo`):
  - `BASE_URL=http://localhost:<GATEWAY_PORT> npm run grabar`
  - `npm run editar`
- Cuenta del manager: `demo@nievesur.es` / `Demo2026!`. Los monitores usan la misma clave, con email `nombre.apellido@nievesur.es` (por ejemplo `javier.molina@nievesur.es`).
- El zoom se sincroniza con un marcador magenta de 4x4 px que el script pinta en la esquina mientras hay un dialogo abierto; `editar-zoom.mjs` lo lee del propio video.

## Mejoras pendientes

### Movimiento del raton

1. Eliminar los movimientos cortos de relleno cuando la pantalla esta quieta. Hoy `vagar()` mueve el cursor unos pixeles mientras no pasa nada, y se nota artificial. Aplica sobre todo a la pantalla de login y a la ficha de usuario. Opciones: dejar el cursor quieto, o sustituir el relleno por una accion real (scroll, hover sobre un elemento con significado).
2. Bajar la velocidad general del cursor. Hoy `moverSuave()` usa 650 ms por defecto para cualquier distancia. Hacer la duracion proporcional a la distancia (por ejemplo 400 ms mas 0,6 ms por pixel, con minimo y maximo) para que un movimiento largo no parezca un salto.
3. Clic en el menu lateral: el cursor cruza la pantalla demasiado rapido. Usar una duracion mayor en `irA()` y trayectoria con ligera curva en lugar de recta.

### Parte Diario tras el login

4. Al iniciar sesion la app aterriza en "Parte Diario" y el cursor pasa por ella sin dar tiempo a verla. Mantener esa pantalla 2 o 3 segundos con el cursor lento (sin saltos) antes de ir al Dashboard. No hace falta interactuar.

### Pantallas sin contenido que desplazar

5. Turnos: `recorrer()` hace un scroll minimo que no aporta nada porque no hay mas filas visibles. Quitarlo de esa pantalla; tras abrir y cerrar los detalles, pasar a la siguiente seccion.
6. Calendario: ya no hace scroll, pero conviene mostrar tambien la vista semanal. Hay que localizar el selector de vista (mes/semana) en `frontend/src/app/(app)/manager/calendar/page.tsx`, pulsarlo y dejar unos segundos antes de seguir.
7. Regla general: antes de hacer scroll, comprobar si la pagina desborda (`document.documentElement.scrollHeight > innerHeight`) y saltarse el scroll si no. Evita estos casos para siempre.

### Ficha de usuario

8. Mismo problema de cursor "tembloroso" con la pantalla quieta (punto 1). Aplicar la solucion de ese punto. Se puede mantener el recorrido actual: resumen, pestana "Rates" (tarifas por turno y ajustes) y vuelta arriba.
9. Pestana "Rates": hoy se pulsa y el video permanece demasiado tiempo sin que pase nada (el bloque de scroll de unos 6 s mas la vuelta arriba). Reducir la permanencia a entre 1 y 3 segundos tras pulsar la pestana, y poco mas.
10. Opcional: en "Rates", pinchar en uno de los campos de tarifa y editarlo (borrar el valor y teclear otro, por ejemplo con `pressSequentially`) para que se vea que es editable. Decidir si se guarda o no:
    - Sin guardar: no altera los datos de demo, pero el usuario no ve el resultado.
    - Guardando con "Actualizar Configuracion": se ve el toast de confirmacion, pero cambia la tarifa en la BD local y, por tanto, los importes de grabaciones posteriores (ver notas).

### Final del video

11. El video termina de golpe tras Facturacion. Anadir un cierre que se note como final: por ejemplo, pulsar "Log Out (Salir)" en el menu lateral, esperar a que cargue el login y dejarlo 2 o 3 segundos con el cursor sin moverse (o con un movimiento lento), y terminar ahi. Alternativa: cerrar volviendo al Dashboard con un ultimo scroll suave y un fundido a negro al exportar (`fade=t=out` en el filtro de `editar-zoom.mjs`). Se puede combinar: cerrar sesion y fundido final de 1 s.
12. Al cerrar sesion con el bypass de desarrollo, la app puede volver a iniciar sesion sola como admin. El script ya intercepta `/api/auth/dev-status`, asi que debe mostrarse el login; comprobarlo en la primera prueba.

### Login

13. El login sigue pareciendo algo acelerado. Ya se ralentizo el tecleo (95 ms por tecla). Valorar bajar el cursor entre campos y alargar 0,5 s la pausa antes de pulsar Enter.

## Nuevo video: vista del trabajador

14. Grabar un segundo video iniciando sesion como monitor (por ejemplo `javier.molina@nievesur.es`, rol `worker`) para ver la app desde su lado. Crear `grabar-trabajador.mjs` reutilizando los helpers de `grabar-demo.mjs`; conviene extraerlos a un modulo comun (`lib.mjs`) antes de duplicar codigo.
15. Formato movil. La peticion es "modo dispositivo movil, 16:9"; un movil en vertical es 9:16. Propuesta: contexto con `devices['iPhone 13']` o viewport 390x844 con `deviceScaleFactor: 2`, `isMobile: true`, `hasTouch: true`, y `recordVideo.size` de 780x1688 (o reescalar a 1080x1920 al exportar). Si se prefiere horizontal, usar 1920x1080 como ahora. Confirmar con quien lo pida cual de los dos quiere antes de grabar.
16. Con `hasTouch` el raton no existe: sustituir `moverSuave`/`clic` por `locator.tap()` y mostrar el punto de toque (el cursor rojo se puede reutilizar como indicador de tap).
17. Recorrido sugerido, a validar mirando las pantallas que ve el monitor: login, parte diario propio, alta de una jornada propia (formulario con zoom), listado de sus jornadas con un detalle (desglose de pago) y su resumen.
18. Reutilizar `editar-zoom.mjs`. El video del trabajador tambien debe terminar con un cierre claro (punto 11)., adaptando `W` y `H` (hoy fijos a 1920x1080) a las dimensiones del video movil.

## Notas y avisos

- Cada grabacion crea registros reales en la BD local (2 por pasada en el video del manager), por lo que las cifras del dashboard cambian entre grabaciones. Para partir de cero: `docker compose -f docker-compose.dev.yml down -v`, y despues `./bin/dev`, `./bin/migrate` y `./bin/seed-demo`.
- En la lista de Usuarios aparece "Admin Vesotel" como administrador de empresa; es comportamiento de la app con los administradores de plataforma. Si molesta en el video, ocultar esa fila o ajustar el recorrido.
- El MP4 generado con `libopenh264` se veia negro en el reproductor del usuario, mientras que el WebM se veia bien. Al exportar el MP4 definitivo hay que comprobarlo; si falla, probar con otro codificador (`libx264` en otro equipo o `h264_vaapi`/`h264_nvenc` si hay hardware) o compartir el WebM.
- No se ha subido version SemVer: se trata como tooling sin efecto en despliegue (excepcion de la regla 8 del `CLAUDE.md`). Revisarlo antes del PR.
- `scripts/demo/node_modules` y `scripts/demo/videos/` estan ignorados por git.
- No hay commits ni push de este trabajo; los ficheros nuevos (`backend/demo_seed.py`, `bin/seed-demo`, `scripts/demo/`) y el cambio en `.gitignore` estan sin confirmar en el worktree.
