#!/usr/bin/env bash
# Fija el campo "Estado" de una issue en el Project "saas-ski-portal".
# Si la issue no esta en el Project, la anade. El numero del Project y los ids
# del campo y de sus opciones se resuelven por titulo en cada ejecucion.
# Uso: scripts/project-estado.sh <numero-issue> "<Estado>"
set -euo pipefail

OWNER="hugovelez16"
REPO="saas-ski-portal"
PROJECT_TITLE="saas-ski-portal"
FIELD="Estado"
VALIDOS=("Backlog" "Listo para agente" "En curso" "En revision" "Hecho")

if [[ $# -ne 2 ]]; then
  echo "[ERROR] Uso: $0 <numero-issue> \"<Estado>\"" >&2
  exit 1
fi

numero="$1"
estado="$2"

valido=false
for v in "${VALIDOS[@]}"; do
  [[ "$v" == "$estado" ]] && valido=true
done
if [[ "$valido" != true ]]; then
  echo "[ERROR] Estado no valido: '$estado'. Validos: ${VALIDOS[*]}" >&2
  exit 1
fi

project_num=$(gh project list --owner "$OWNER" --format json \
  --jq ".projects[] | select(.title == \"$PROJECT_TITLE\") | .number")
if [[ -z "$project_num" ]]; then
  echo "[ERROR] No existe el Project '$PROJECT_TITLE' de $OWNER" >&2
  exit 1
fi
if [[ "$project_num" == *$'\n'* ]]; then
  echo "[ERROR] Hay varios Projects '$PROJECT_TITLE' de $OWNER: $(echo "$project_num" | tr '\n' ' ')" >&2
  exit 1
fi

project_id=$(gh project view "$project_num" --owner "$OWNER" --format json --jq '.id')

campos=$(gh project field-list "$project_num" --owner "$OWNER" --format json)
field_id=$(jq -r --arg f "$FIELD" '.fields[] | select(.name == $f) | .id' <<<"$campos")
option_id=$(jq -r --arg f "$FIELD" --arg e "$estado" \
  '.fields[] | select(.name == $f) | .options[] | select(.name == $e) | .id' <<<"$campos")
if [[ -z "$field_id" || -z "$option_id" ]]; then
  echo "[ERROR] No se encontro el campo '$FIELD' o la opcion '$estado' en el Project" >&2
  exit 1
fi

url="https://github.com/$OWNER/$REPO/issues/$numero"
item_id=$(gh project item-add "$project_num" --owner "$OWNER" --url "$url" --format json --jq '.id')

gh project item-edit --id "$item_id" --project-id "$project_id" \
  --field-id "$field_id" --single-select-option-id "$option_id" >/dev/null

echo "[INFO] Issue #$numero -> $estado"
