#!/bin/bash

# ==============================================================================
# Script: sync_db.sh
# Descripción: Sincroniza la base de datos de producción a la de desarrollo.
# Uso: ./scripts/sync_db.sh [nombre_contenedor_origen]
# ==============================================================================

# Cargar variables de entorno locales si existen
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env 2>/dev/null || true
    set +a
fi

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ski_dev}"
SRC_CONTAINER=${1:-"ski_prod-postgres"}
DST_CONTAINER="${COMPOSE_PROJECT_NAME}-postgres"
DB_USER="postgres"
DB_NAME="postgres"

# Detectar contenedor de destino local si tiene sufijo -1 o nombre directo
if [ -z "$(docker ps -q -f name=^/${DST_CONTAINER}$)" ] && [ -n "$(docker ps -q -f name=^/${DST_CONTAINER}-1$)" ]; then
    DST_CONTAINER="${DST_CONTAINER}-1"
elif [ -z "$(docker ps -q -f name=^/${DST_CONTAINER}$)" ] && [ -n "$(docker ps -q -f name=^/ski-dev-postgres$)" ]; then
    DST_CONTAINER="ski-dev-postgres"
fi

# Colores para la terminal
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}   Sincronizador de Base de Datos: Remoto -> Local  ${NC}"
echo -e "${BLUE}===================================================${NC}"

# 1. Verificar si el contenedor de desarrollo (destino) está corriendo
if [ "$(docker ps -q -f name=$DST_CONTAINER)" ]; then
    echo -e "${GREEN}[OK]${NC} Contenedor de destino local ($DST_CONTAINER) detectado."
else
    echo -e "${RED}[ERROR]${NC} El contenedor de destino ($DST_CONTAINER) no está encendido."
    echo -e "       Asegúrate de ejecutar: docker compose -f docker-compose.dev.yml up -d"
    exit 1
fi

# 2. Configurar servidor de origen
echo -e "${BLUE}Configuración del Servidor de Origen:${NC}"
read -p "Introduce la IP del servidor de origen [172.20.10.120] (o escribe 'local' para contenedor local): " SRC_IP
SRC_IP=${SRC_IP:-"172.20.10.120"}

if [ "$SRC_IP" = "local" ]; then
    # Verificar si el contenedor de origen está corriendo localmente
    if [ "$(docker ps -q -f name=$SRC_CONTAINER)" ]; then
        echo -e "${GREEN}[OK]${NC} Contenedor de origen local ($SRC_CONTAINER) detectado."
        
        # Preguntar confirmación
        echo -e "${YELLOW}ADVERTENCIA: Se borrarán todos los datos en DESARROLLO ($DST_CONTAINER)${NC}"
        read -p "¿Deseas continuar con la sobrescritura? (s/n): " confirm
        if [[ ! $confirm =~ ^[sS]$ ]]; then
            echo "Operación cancelada."
            exit 0
        fi

        echo -e "${BLUE}Copiando datos desde el contenedor local $SRC_CONTAINER a $DST_CONTAINER...${NC}"
        
        # Ejecutar dump y restore en un solo flujo
        docker exec "$SRC_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" --clean --if-exists --no-owner --no-privileges | \
        docker exec -i "$DST_CONTAINER" psql -U "$DB_USER" "$DB_NAME"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}¡Éxito! La base de datos de desarrollo ha sido actualizada.${NC}"
        else
            echo -e "${RED}[ERROR]${NC} Falló la transferencia de datos."
        fi
    else
        echo -e "${RED}[ERROR]${NC} No se encontró el contenedor '$SRC_CONTAINER' corriendo localmente."
        exit 1
    fi
else
    # Pedir usuario SSH para la conexión remota
    read -p "Introduce el usuario SSH para $SRC_IP [usuario]: " SSH_USER
    SSH_USER=${SSH_USER:-"usuario"}

    # Verificar conectividad SSH
    echo -e "${BLUE}Comprobando conexión SSH con $SSH_USER@$SRC_IP...${NC}"
    if ssh -o ConnectTimeout=3 -o BatchMode=yes -o StrictHostKeyChecking=no "$SSH_USER@$SRC_IP" "echo '[OK] SSH'" >/dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC} Conexión SSH establecida con éxito."
    else
        echo -e "${RED}[ERROR]${NC} No se pudo conectar por SSH a $SSH_USER@$SRC_IP."
        echo -e "       Asegúrate de tener acceso SSH sin contraseña configurado."
        exit 1
    fi

    # Verificar si el contenedor está corriendo en el servidor remoto
    echo -e "${BLUE}Verificando contenedor remoto en $SRC_IP...${NC}"
    REMOTE_RUNNING=$(ssh "$SSH_USER@$SRC_IP" "docker ps -q -f name=$SRC_CONTAINER" 2>/dev/null)
    if [ -z "$REMOTE_RUNNING" ]; then
        # Intentar auto-detección con otros nombres comunes
        for ALT_NAME in "ski_prod-postgres-1" "ski-prod-postgres" "ski_dev-postgres-1" "ski-dev-postgres"; do
            REMOTE_RUNNING=$(ssh "$SSH_USER@$SRC_IP" "docker ps -q -f name=$ALT_NAME" 2>/dev/null)
            if [ -n "$REMOTE_RUNNING" ]; then
                SRC_CONTAINER=$ALT_NAME
                break
            fi
        done
    fi

    if [ -n "$REMOTE_RUNNING" ]; then
        echo -e "${GREEN}[OK]${NC} Contenedor remoto ($SRC_CONTAINER) detectado en $SRC_IP."
    else
        echo -e "${RED}[ERROR]${NC} No se encontró un contenedor Postgres de Ski corriendo en $SRC_IP."
        exit 1
    fi

    # Preguntar confirmación
    echo -e "${YELLOW}ADVERTENCIA: Se borrarán todos los datos en DESARROLLO ($DST_CONTAINER)${NC}"
    read -p "¿Deseas continuar con la sobrescritura? (s/n): " confirm
    if [[ ! $confirm =~ ^[sS]$ ]]; then
        echo "Operación cancelada."
        exit 0
    fi

    echo -e "${BLUE}Copiando datos desde remoto $SSH_USER@$SRC_IP ($SRC_CONTAINER) a local $DST_CONTAINER...${NC}"
    
    # Ejecutar dump desde el servidor remoto a través de SSH e insertar en el contenedor de desarrollo local
    ssh "$SSH_USER@$SRC_IP" "docker exec $SRC_CONTAINER pg_dump -U $DB_USER $DB_NAME --clean --if-exists --no-owner --no-privileges" | \
    docker exec -i "$DST_CONTAINER" psql -U "$DB_USER" "$DB_NAME"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}¡Éxito! La base de datos de desarrollo ha sido actualizada.${NC}"
        
        # Ejecutar migraciones pendientes en backend local
        BACKEND_CONTAINER=$(docker ps -q -f name="${COMPOSE_PROJECT_NAME}-backend" || docker ps -q -f name=ski-dev-backend || docker ps -q -f name=ski_dev-backend-1)
        if [ -n "$BACKEND_CONTAINER" ]; then
            echo -e "${BLUE}Aplicando migraciones Alembic pendientes...${NC}"
            docker exec "$BACKEND_CONTAINER" alembic upgrade head
            echo -e "${GREEN}[OK]${NC} Esquema de base de datos sincronizado con las últimas migraciones."
        fi
    else
        echo -e "${RED}[ERROR]${NC} Falló la transferencia de datos."
    fi
fi
echo -e "${BLUE}===================================================${NC}"
