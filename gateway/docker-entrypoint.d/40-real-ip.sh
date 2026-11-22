#!/bin/sh
# Genera la configuracion de IP real a partir de TRUSTED_PROXIES.
# TRUSTED_PROXIES: lista de IP o CIDR separados por espacios (proxies de confianza).
# Sin variable, no se escribe nada y nginx no confia en ningun proxy.
set -eu

REAL_IP_DIR="${REAL_IP_DIR:-/etc/nginx/real-ip.d}"
OUT="${REAL_IP_DIR}/real-ip.conf"

# Valida una IPv4 (con CIDR opcional) o una IPv6 (con CIDR opcional).
# Rechaza el rango completo (0.0.0.0/0 y ::/0).
valid_entry() {
    entry="$1"
    addr="${entry%%/*}"
    mask=""
    case "$entry" in
        */*) mask="${entry#*/}" ;;
    esac

    case "$entry" in
        */) return 1 ;;
    esac
    case "$mask" in
        "") ;;
        0?*) return 1 ;;
        *[!0-9]*) return 1 ;;
        *) [ "${#mask}" -le 3 ] || return 1 ;;
    esac

    case "$addr" in
        *:*)
            # IPv6: solo hexadecimales y dos puntos; maximo 128 de mascara.
            case "$addr" in
                *[!0-9a-fA-F:]*) return 1 ;;
            esac
            case "$addr" in
                ::|*:::*) return 1 ;;
            esac
            [ -z "$mask" ] || { [ "$mask" -ge 32 ] && [ "$mask" -le 128 ]; } || return 1
            ;;
        *)
            # IPv4: cuatro octetos 0-255; maximo 32 de mascara.
            case "$addr" in
                *[!0-9.]*) return 1 ;;
            esac
            old_ifs="$IFS"
            IFS=.
            # shellcheck disable=SC2086
            set -- $addr
            IFS="$old_ifs"
            [ "$#" -eq 4 ] || return 1
            for octet in "$@"; do
                case "$octet" in
                    "") return 1 ;;
                esac
                [ "${#octet}" -le 3 ] || return 1
                [ "$octet" -le 255 ] || return 1
            done
            [ -z "$mask" ] || { [ "$mask" -ge 8 ] && [ "$mask" -le 32 ]; } || return 1
            ;;
    esac
    return 0
}

mkdir -p "$REAL_IP_DIR"
rm -f "$OUT"

if [ -z "${TRUSTED_PROXIES:-}" ]; then
    echo "[INFO] real-ip: TRUSTED_PROXIES vacia, no se confia en ningun proxy"
    exit 0
fi

tmp="${OUT}.tmp"
: > "$tmp"
count=0
for entry in $TRUSTED_PROXIES; do
    if ! valid_entry "$entry"; then
        rm -f "$tmp"
        echo "[ERROR] real-ip: entrada no valida en TRUSTED_PROXIES: ${entry}" >&2
        exit 1
    fi
    echo "set_real_ip_from ${entry};" >> "$tmp"
    count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
    rm -f "$tmp"
    echo "[INFO] real-ip: TRUSTED_PROXIES sin entradas, no se confia en ningun proxy"
    exit 0
fi

{
    echo "real_ip_header X-Forwarded-For;"
    echo "real_ip_recursive on;"
} >> "$tmp"
mv "$tmp" "$OUT"
echo "[INFO] real-ip: ${count} proxy(s) de confianza configurados"
