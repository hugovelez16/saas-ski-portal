# Documentación legal

> **Todos los textos de esta carpeta y las páginas legales públicas son una base y deben ser revisados y validados por un abogado o DPO antes de utilizarse con clientes.**

## Documentos

- [Plantilla de contrato de encargado del tratamiento (art. 28 RGPD)](contrato-encargado-tratamiento.md)

Páginas públicas de la aplicación (sin sesión), en `frontend/src/app/(legal)/`:

- `/aviso-legal`: aviso legal (art. 10 LSSI).
- `/privacidad`: política de privacidad (art. 13 RGPD).
- `/cookies`: política de cookies.
- `/terminos`: términos de uso del servicio.

## Configuración de los datos del titular y contacto

Los datos del titular de las páginas web están en un único fichero, `frontend/src/lib/legal-config.ts`, tomados del aviso legal y la política de privacidad de https://vesotel.com. Solo se muestra el mínimo del art. 10 LSSI en `/aviso-legal`, con un enlace a vesotel.com para ampliar información; las demás páginas nombran al titular y remiten al aviso legal. Los proveedores (alojamiento y correo) se indican por categoría, sin nombre.

El correo de contacto procede de la variable de entorno `NEXT_PUBLIC_CONTACT_EMAIL`; si no está definida, se usa `hola@vesotel.com`.

Los campos `PENDIENTE_DE_RELLENAR` de la plantilla de contrato se completan con cada escuela al firmarlo:

```sh
grep -rn PENDIENTE_DE_RELLENAR docs/legal
```

## Puntos a validar por el asesor

1. **Analítica y grabación de sesiones con PostHog.** PostHog está integrado en el frontend y se activa solo si `NEXT_PUBLIC_POSTHOG_KEY` tiene valor. Usa persistencia en memoria, sin instalar cookies ni utilizar `localStorage`; identifica al usuario por su id interno y graba sesiones con textos y campos enmascarados, salvo en el flujo de restablecimiento de contraseña. Hay que validar si el tratamiento requiere consentimiento previo y si la base jurídica de interés legítimo es suficiente.
2. **Almacenamiento local técnico.** La aplicación utiliza `localStorage` para `device_token`, `lastCompanyId`, `calendar_hours_preference`, `dataTable-visibility-*` y `admin_companies_view_mode`. El asesor debe validar su finalidad, necesidad, duración y el tratamiento aplicable a cada elemento.
3. **Aceptación de términos durante el alta.** Es una tarea futura: la aplicación no implementa actualmente una aceptación de términos en el alta. Véase el [informe de auditoría](../auditoria-propuesta-iliberis.md), apartado «Trabajo pendiente en producto».
