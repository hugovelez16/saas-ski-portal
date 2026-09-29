#!/bin/bash

# ==============================================================================
# Script: sync_to_prod.sh
# Descripción: Migra la base de datos de desarrollo (local) a la de producción (remota).
# Uso: ./scripts/sync_to_prod.sh [ip_maquina_produccion] [usuario_ssh]
# ==============================================================================

# Cargar variables de entorno locales si existen
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
    set +a
fi

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ski_dev}"
SRC_CONTAINER="${COMPOSE_PROJECT_NAME}-postgres"
DST_CONTAINER=${3:-"ski_prod-postgres"}
DST_HOST=${1:-"10.192.168.114"}
DST_USER=${2:-"usuario"}
DB_USER="postgres"
DB_NAME="postgres"

# Colores para la terminal
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}   Migrador de Base de Datos: Dev -> Prod Remoto    ${NC}"
echo -e "${BLUE}===================================================${NC}"

# 1. Verificar si el contenedor de desarrollo (origen) está corriendo localmente
if [ -z "$(docker ps -q -f name=^/${SRC_CONTAINER}$)" ] && [ -n "$(docker ps -q -f name=^/${SRC_CONTAINER}-1$)" ]; then
    SRC_CONTAINER="${SRC_CONTAINER}-1"
fi

if [ "$(docker ps -q -f name=$SRC_CONTAINER)" ]; then
    echo -e "${GREEN}[OK]${NC} Contenedor de origen local ($SRC_CONTAINER) detectado."
else
    echo -e "${RED}[ERROR]${NC} El contenedor local ($SRC_CONTAINER) no está encendido."
    echo -e "       Inícialo con: docker compose -f docker-compose.dev.yml up -d"
    exit 1
fi

# 2. Verificar conectividad SSH con el servidor de producción
echo -e "${BLUE}Comprobando conexión SSH con $DST_USER@$DST_HOST...${NC}"
if ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no "$DST_USER@$DST_HOST" "echo '[OK] SSH'" >/dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Conexión SSH establecida con éxito."
else
    echo -e "${RED}[ERROR]${NC} No se pudo conectar por SSH a $DST_USER@$DST_HOST."
    echo -e "       Asegúrate de tener acceso SSH sin contraseña configurado."
    exit 1
fi

# 3. Verificar si el contenedor de producción está corriendo en el servidor remoto
echo -e "${BLUE}Verificando contenedor remoto $DST_CONTAINER...${NC}"
REMOTE_RUNNING=$(ssh "$DST_USER@$DST_HOST" "docker ps -q -f name=$DST_CONTAINER")
if [ -n "$REMOTE_RUNNING" ]; then
    echo -e "${GREEN}[OK]${NC} Contenedor remoto de producción ($DST_CONTAINER) detectado."
else
    echo -e "${RED}[ERROR]${NC} El contenedor de producción ($DST_CONTAINER) no está corriendo en el servidor remoto."
    exit 1
fi

# 4. Obtener información de producción para mostrar advertencias
PROD_USERS=$(ssh "$DST_USER@$DST_HOST" "docker exec -t $DST_CONTAINER psql -U $DB_USER -d $DB_NAME -tAc \"SELECT count(*) FROM users;\"" 2>/dev/null | tr -d '\r')
DEV_USERS=$(docker exec -t "$SRC_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM users;" 2>/dev/null | tr -d '\r')

echo -e "\n${YELLOW}====================== ADVERTENCIA ======================${NC}"
echo -e "${YELLOW}Vas a migrar datos de DESARROLLO (local) a PRODUCCIÓN (remoto).${NC}"
echo -e "  - Servidor Destino: $DST_HOST"
echo -e "  - Usuarios en Desarrollo (local): $DEV_USERS"
echo -e "  - Usuarios en Producción (remoto): $PROD_USERS"
echo -e "${RED}¡ESTO SOBRESESCRIBIRÁ COMPLETAMENTE LA BASE DE DATOS DE PRODUCCIÓN!${NC}"
echo -e "${YELLOW}=========================================================${NC}\n"

read -p "¿Deseas continuar con la migración? (escribe 'sí' para confirmar): " confirm
if [ "$confirm" != "sí" ] && [ "$confirm" != "si" ]; then
    echo -e "${BLUE}Operación cancelada.${NC}"
    exit 0
fi

# 5. Realizar copia de seguridad automática de producción antes de sobrescribir
BACKUP_FILE="backup_prod_$(date +%Y%m%d_%H%M%S).sql"
echo -e "${BLUE}Creando copia de seguridad de producción en: $BACKUP_FILE...${NC}"
ssh "$DST_USER@$DST_HOST" "docker exec -t $DST_CONTAINER pg_dump -U $DB_USER $DB_NAME --clean --if-exists --no-owner --no-privileges" > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    echo -e "${GREEN}[OK]${NC} Copia de seguridad guardada con éxito (${BACKUP_FILE})."
else
    echo -e "${RED}[ERROR]${NC} Falló la copia de seguridad. Abortando migración por seguridad."
    exit 1
fi

# 6. Ejecutar la migración
echo -e "${BLUE}Iniciando volcado de datos desde Desarrollo a Producción...${NC}"
docker exec -t "$SRC_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" --clean --if-exists --no-owner --no-privileges | \
ssh "$DST_USER@$DST_HOST" "docker exec -i $DST_CONTAINER psql -U $DB_USER $DB_NAME"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}===================================================${NC}"
    echo -e "${GREEN}   ¡ÉXITO! La base de datos ha sido migrada.        ${NC}"
    echo -e "${GREEN}===================================================${NC}"
else
    echo -e "${RED}[ERROR]${NC} Ocurrió un error durante la migración."
fi
