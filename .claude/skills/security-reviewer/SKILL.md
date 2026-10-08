---
name: security-reviewer
description: Checklist de seguridad de saas-ski-portal: JWT RS256 en cookies HttpOnly, RBAC por roles, aislamiento por empresa, bypass dev y secretos expuestos. Usar al anadir autenticacion, endpoints sensibles, manejo de secretos o revisiones de seguridad.
---

# Security Reviewer (checklist)

El detalle de directivas vive en el agente `security-reviewer` (`.claude/agents/security-reviewer.md`). Esta skill solo aporta la lista de comprobacion rapida y el escaneo de secretos.

## Checklist por endpoint nuevo

- Usa `Depends(auth.get_verified_user)` (o `require_module(...)` si pertenece a un modulo de pago).
- Comprueba rol de plataforma o rol de empresa (`CompanyRole`) y pertenencia a la empresa activa antes de operar.
- Toda consulta filtra por `company_id` / `user_id` segun el caso (sin IDOR entre empresas).
- Entrada validada con esquemas Pydantic; sin SQL concatenado.
- Errores sin trazas ni datos internos (ver skill `error-handling`).

## Checklist de cambios en autenticacion

- Tokens solo en cookies `HttpOnly`; nada en `localStorage`/`sessionStorage`.
- `/auth/dev-login` sigue limitado a `dev_seed.is_dev_mode()` y las variables de bypass no estan en `docker-compose.prod.yml`.
- Sin claves PEM ni contrasenas por defecto versionadas (`backend/keys/`, `.env`).

## Escaneo de secretos

```bash
git grep -nEi "(password|secret|token)\s*=\s*[\"'][^\"']{8,}[\"']|BEGIN (RSA )?PRIVATE KEY" -- ':!*.lock' ':!package-lock.json' ':!*.example'
```

## Dependencias

```bash
cd frontend && npm audit
```
