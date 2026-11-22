# ADR-0009: Modo de empresa: bandera `is_managed`

Estado: Aceptada (2026-11-22). La bandera ya existe en el modelo; los permisos
que dependen de ella se implementan con la matriz (ADR-0005).

## Contexto

Hay escuelas donde el manager lo controla todo y el monitor solo consulta, y
empresas libres donde el monitor lleva sus propios turnos y tarifas. Se
planteo un enum de modos (gestionada, autonoma, "personal"), pero el tercer
modo no tiene una regla propia que lo distinga (S7, S10, T1 de
`revision-base.md`, seccion 8).

## Decision

- El modo es una bandera booleana `is_managed` de la empresa: gestionada
  (`true`) o libre (`false`). Solo la cambia el PA (S1).
- No se crea un enum de modos ni un modo "personal" hasta que tenga una regla
  propia que no se pueda expresar con la bandera (por ejemplo, no poder anadir
  miembros).
- Que puede hacer el worker en cada modo es de dominio y vive en la matriz
  (ADR-0005) y en `docs/dominio/acceso.md` (R-ACC-70 y R-ACC-71): este ADR no
  lo repite.
- No se anaden mas banderas sueltas. Cuando haya facturacion, cada permiso
  opcional del worker colgara del plan de la empresa (modulos y limites por
  modulo, O12), no de una bandera nueva (seccion 8, "Autonomia frente a plan").
- El alta publica gratuita (O16, R-ACC-75 a 77) no es otro modo: es una empresa
  creada automaticamente con su usuario como unico worker. Si pasa a manager de
  su empresa, se resuelve por rol, no por modo.

## Consecuencias

- Un solo eje (gestionada o libre) simplifica la matriz y los tests por fila.
- Si un caso futuro necesita un tercer comportamiento, se decide con su regla
  y puede justificar un enum entonces; hasta entonces seria una abstraccion sin
  uso.
- Pendiente de implementar: la bandera existe, pero que el worker de una
  empresa libre edite su tarifa, bruto/neto e impuestos y que en gestionada sea
  espectador depende de la matriz unica.
- La dependencia del plan es decision de direccion: no hay facturacion por plan
  implementada (O11, O12).
