#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

SOURCE_ROOT=${SOURCE_ROOT:-/root/wd6zn_extracted}
COMPOSE=${COMPOSE:-docker compose}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-long1251374638}

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

warn() {
  echo "[WARN] $*" >&2
}

require_cmd() {
  command -v "$1" >/dev/null || fail "missing command: $1"
}

check_port() {
  local port="$1"
  local listeners
  listeners="$(ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print}' || true)"
  if [[ -n "$listeners" ]]; then
    if ! grep -q 'nginx' <<< "$listeners"; then
      warn "port $port is already listening; deploy may fail or route to another service"
      echo "$listeners" >&2
    fi
  fi
}

require_cmd docker
require_cmd curl
require_cmd openssl
require_cmd python3
require_cmd ss

$COMPOSE version >/dev/null || fail "compose command failed: $COMPOSE"

[[ -d "$SOURCE_ROOT/home" ]] || fail "SOURCE_ROOT missing home directory: $SOURCE_ROOT/home"
[[ -d "$SOURCE_ROOT/www" ]] || fail "SOURCE_ROOT missing www directory: $SOURCE_ROOT/www"

required_sql=(
  release_adb release_ddb release_gddb release_gsdb release_ldb release_mdb
  release_sdb release_sldb release_tdb wscyun_sdk wdgm houtai
)
for db in "${required_sql[@]}"; do
  [[ -f "$SOURCE_ROOT/home/db/$db.sql" ]] || fail "missing SQL: $SOURCE_ROOT/home/db/$db.sql"
done

check_port 81
check_port 82

if [[ "${START_GAME:-0}" == "1" ]]; then
  fail "START_GAME=1 is disabled for the default deployment path. Use: $COMPOSE --profile game up -d --build game"
fi

echo "[OK] preflight passed for web/mysql deployment"
