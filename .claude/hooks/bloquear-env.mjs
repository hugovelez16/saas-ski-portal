#!/usr/bin/env node
// Hook PreToolUse (Read, Grep, Bash): impide leer .env* (salvo .env.example),
// backend/keys/, *.pem y otras claves (CLAUDE.md regla 9). Es una red de
// seguridad: la barrera real es permissions.deny de .claude/settings.json.
// Fail-closed: si la entrada no se puede evaluar, bloquea.
// Excepcion en Bash: `test -f .env`, `grep -c '^CLAVE=' .env` y la lectura de
// los puertos o de COMPOSE_PROJECT_NAME (skills workspace-*).
import { evaluarEntrada } from './lib/bloquear-env.mjs';

let entrada = '';
for await (const trozo of process.stdin) entrada += trozo;

let motivo;
try {
  motivo = evaluarEntrada(JSON.parse(entrada));
} catch (e) {
  motivo = `no se pudo evaluar la entrada (${String(e.message).split('\n')[0]})`;
}

if (motivo) {
  process.stderr.write(
    `[ERROR] bloquear-env: ${motivo}. Los ficheros .env, backend/keys/ y las claves no se leen (CLAUDE.md regla 9). ` +
      "Usa .env.example, o solo 'test -f .env' y 'grep -c '^CLAVE=' .env'.\n",
  );
  process.exit(2);
}
