# Documentacion de dominio

Reglas de negocio de la plataforma, una entidad por fichero, cada regla con un
ID estable. Es la referencia que citan las issues, los tests y los revisores.

Los terminos estan en [../glosario.md](../glosario.md) y las decisiones sin
cerrar en [../preguntas-abiertas.md](../preguntas-abiertas.md).

## Fuente de verdad

Este directorio es la fuente de verdad del dominio. Sustituye a
`logica-negocio-empresa.md` (eliminado, ver historial de git).

Este directorio describe el comportamiento **objetivo**. Si el codigo hace otra
cosa, es un hallazgo: se registra con `/issue-create`, no se adapta la regla al
codigo.

## Ficheros y prefijos reservados

| Prefijo | Fichero | Contenido | Origen en `logica-negocio-empresa.md` (eliminado) |
|---|---|---|---|
| `R-ACC` | `acceso.md` | Token, sesion, empresa activa, roles, suplantacion de solo lectura ("ver como" retirado, P4), comprobaciones por peticion | 2.2, 3 y 9 |
| `R-EMP` | `empresa.md` | Atributos, ciclo de vida, empresa gestionada y suspendida, campos JSON | 4 |
| `R-MEM` | `membresia.md` | Alta, baja, reactivacion, rol y estado de la membresia | 2.3 y 5 |
| `R-TUR` | `turno.md` | Turnos (work logs): quien hace que, validaciones, recalculo, parte diario | 6 y 8 (parte diario) |
| `R-TAR` | `tarifa.md` | Tarifas por miembro, impuestos, overrides, calculo del importe y billing basica (P17) | 4.4 y 7 |
| `R-MOD` | `modulo.md` | Catalogo de modulos, suscripciones y `require_module` (la billing no es modulo, P17) | 8 |
| `R-AUD` | `auditoria.md` | Eventos que se registran y consulta de `audit_logs` | 10 |

Los ficheros se crean en las issues de cada entidad. Un prefijo nuevo se anade
primero a esta tabla, en su propio PR o en el que crea la entidad.

## Formato de las reglas

- **ID**: `R-<ENT>-nn`, con `<ENT>` uno de los prefijos de la tabla y `nn` de
  dos digitos (`R-TUR-01`, `R-TUR-02`...). Si se pasa de 99, tres digitos.
- **Estable**: un ID no se renumera ni se reutiliza. Una regla que deja de
  valer se marca `Retirada` y se conserva con su ID.
- **Una regla, una afirmacion comprobable**: quien, que y con que resultado
  (por ejemplo, el codigo HTTP). Si hace falta un "y ademas", son dos reglas.
- **Estado**:
  - `Cerrado`: decidido por el usuario.
  - `Confirmar`: propuesto, valido como punto de partida.
  - `Abierto`: sin decidir. Lleva el ID de su pregunta (`O1`, `O10`...) en
    `preguntas-abiertas.md`.
  - `Retirada`: ya no aplica. Se indica que la sustituye, si algo.
- **Origen**: de donde sale la regla (seccion de documento de origen,
  ID de pregunta cerrada, issue o ADR). Si cita un fichero eliminado, se
  indica `<fichero> (eliminado, ver historial de git)` sin perder la seccion.
- **Codigo**: opcional. Donde se aplica hoy (`backend/src/...`, `access_policy`),
  sin numeros de linea, que cambian.

Como citarlas:

- Issues: en "Reglas afectadas", con el ID y su texto.
- Tests: el ID en el nombre o en el docstring (`test_r_tur_03_...`).
- PR y revisores: el ID de cada regla que el cambio implementa o modifica.
- Cambiar el texto de una regla `Cerrado` exige decision del usuario.

## Plantilla de fichero por entidad

Copia este bloque en `docs/dominio/<entidad>.md`:

```markdown
# <Entidad>

Prefijo: `R-<ENT>`. Tabla: `<tabla>`. Modelo: `<Clase>` (`backend/models.py`).
Entidad de dominio: `backend/src/domain/entities/<fichero>.py` (si existe).

<Una o dos frases: que es y para que sirve. Enlace al termino del glosario.>

## Campos

| Campo | Tipo | Obligatorio | Descripcion y restricciones |
|---|---|---|---|
| `id` | UUID | Si | Identificador |
| `company_id` | UUID | Si | Empresa a la que pertenece (aislamiento) |

## Reglas

| ID | Regla | Estado | Origen |
|---|---|---|---|
| R-<ENT>-01 | <Quien puede hacer que y con que resultado> | Cerrado | ADR-0005 / #123 |
| R-<ENT>-02 | <...> | Abierto (O1) | preguntas-abiertas.md |

## Casos limite

| Caso | Resultado esperado | Regla |
|---|---|---|
| <Entrada o estado extremo> | <Codigo HTTP o efecto> | R-<ENT>-01 |

## Relacion con otras entidades

- <Entidad>: <como se relaciona y que reglas cruzan>.
```

Secciones obligatorias: Campos, Reglas y Casos limite. "Relacion con otras
entidades" es opcional.

## Limites

- Unas 200 lineas por fichero como maximo. Si una entidad las supera, se
  divide en `<entidad>-<subtema>.md` (por ejemplo `turno-calculo.md`) con el
  mismo prefijo y numeracion compartida, sin repetir IDs.
- Sin decisiones de implementacion (clases, endpoints concretos) salvo como
  referencia en la columna de origen o en el campo "Codigo".
- Texto plano y markdown estandar, sin emojis.
