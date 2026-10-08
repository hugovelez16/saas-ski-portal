---
name: error-handling
description: Estandarizacion de respuestas de error HTTP, manejo de excepciones en FastAPI y gestion de errores en el frontend Next.js de saas-ski-portal.
---

# Estandarizacion y Manejo de Errores (error-handling)

## 1. Respuestas de error en el backend

Formato JSON consistente (el que genera `HTTPException`):

```json
{ "detail": "Descripcion clara del error" }
```

| Codigo | Uso en saas-ski-portal |
|---|---|
| `400` | Regla de negocio incumplida o dato invalido (ej. email ya registrado, contrasena actual incorrecta). |
| `401` | Token ausente, expirado, en lista negra o con firma RS256 invalida (`auth.get_current_user` / `get_verified_user`). |
| `403` | Token valido sin permiso: rol insuficiente, otra empresa, 2FA pendiente o modulo no contratado (`require_module`). |
| `404` | Usuario, empresa o jornada inexistente (o fuera del ambito de la empresa activa). |
| `409` | Conflicto de estado o duplicado cuando aplique. |
| `422` | Validacion Pydantic (la genera FastAPI). |
| `500` | Error no controlado; nunca exponer trazas al cliente. |

## 2. FastAPI

```python
from fastapi import HTTPException, status

raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
```

- Los routers actuales (`backend/routers/`) levantan `HTTPException` directamente; mantener ese patron y no filtrar excepciones internas.
- Registrar el detalle tecnico en logs del servidor (`logger.exception(...)`) y devolver un mensaje generico en los 500.
- Para no revelar existencia de recursos de otra empresa, preferir `404` o `403` de forma coherente con los endpoints vecinos.

## 3. Frontend (Next.js App Router)

1. Cliente HTTP: `frontend/src/infrastructure/http/HttpClient.ts` (axios con `withCredentials`, sesion por cookies `HttpOnly`). El manejo de `401` y el reintento del login de desarrollo estan en `frontend/src/context/AuthContext.tsx`.
2. Mostrar `error.response?.data?.detail` en el formulario o notificacion en errores `4xx` de negocio.
3. Errores de renderizado: usar los limites de error de App Router (`error.tsx` por segmento) y `frontend/src/app/global-error.tsx` para el nivel raiz, en lugar de componentes `ErrorBoundary` propios.
