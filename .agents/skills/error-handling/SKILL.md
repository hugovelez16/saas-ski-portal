---
name: error-handling
description: Estandarizacion de respuestas de error HTTP, manejo de excepciones en FastAPI y gestion de errores en React para poc-portal.
---

# Estandarizacion y Manejo de Errores (error-handling)

Esta skill establece las directivas para la captura, estructuracion y comunicacion de errores tanto en el backend FastAPI como en la aplicacion cliente React.

## 1. Estandar de Respuestas HTTP en Backend

Todas las respuestas de error emitidas por la API REST deben mantener un formato JSON consistente:

```json
{
  "detail": "Descripcion clara y precisa del error en espanol"
}
```

### Codigos de Estado y Casos de Uso

| Codigo HTTP | Denominacion | Contexto de Aplicacion en POC Portal |
|---|---|---|
| `400 Bad Request` | Solicitud Incorrecta | Peticion malformada o violacion de reglas de negocio antes de procesamiento. |
| `401 Unauthorized` | No Autorizado | Token ausente, expirado o con firma invalida en Azure AD / JWT. |
| `403 Forbidden` | Acceso Denegado | Token valido pero el usuario carece del rol necesario (ej. `solicitante` intentando aprobar un ticket). |
| `404 Not Found` | No Encontrado | El ticket, usuario o recurso solicitado no existe en la base de datos. |
| `409 Conflict` | Conflicto | El `slug` de Snowflake ya se encuentra registrado o la transicion de estado no es valida. |
| `422 Unprocessable` | Entidad No Procesable | Fallo de validacion en esquemas Pydantic v2 (campos obligatorios, formato regex de slug invalido). |
| `500 Internal Error` | Error de Servidor | Excepcion no controlada. Nunca exponer trazas de depuracion (*tracebacks*) al cliente. |

## 2. Manejo de Excepciones en FastAPI

1. **Uso de `HTTPException` Explicitas**:
   ```python
   from fastapi import HTTPException, status

   raise HTTPException(
       status_code=status.HTTP_404_NOT_FOUND,
       detail="El ticket con el slug especificado no existe"
   )
   ```

2. **Captura Global de Excepciones No Controladas**:
   - Registrar el detalle tecnico en los logs del servidor (`logger.exception(...)`).
   - Retornar un mensaje sobrio y seguro al cliente:
     `{"detail": "Se produjo un error interno en el servidor. Por favor, contacte con el administrador."}`

## 3. Gestion de Errores en Frontend (React / Axios)

1. **Interceptores de Axios**:
   - En `src/services/api.ts`, capturar errores en el pipeline de respuesta:
     - Si el error es `401 Unauthorized`: limpiar el token en memoria y redirigir al flujo de autenticacion MSAL.
     - Si el error es `403 Forbidden`: mostrar alerta de permisos insuficientes.
     - Si el error es `404`, `409` o `422`: extraer `error.response?.data?.detail` y presentarlo en el formulario o componente de notificacion (Toast).

2. **Limites de Error (Error Boundaries)**:
   - Implementar componentes `ErrorBoundary` en las vistas principales (`Dashboard`, `NewTicket`, `Reviews`) para evitar que un fallo en un componente desmonte toda la interfaz de usuario.
