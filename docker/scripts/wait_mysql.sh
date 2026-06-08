#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1091
source .env
set +a
COMPOSE=${COMPOSE:-docker compose}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-long1251374638}

echo "[INFO] 等待 MySQL 就绪"
for _ in $(seq 1 90); do
  if $COMPOSE exec -T -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql mysqladmin ping -uroot --silent >/dev/null 2>&1; then
    echo "[INFO] MySQL ready"
    exit 0
  fi
  sleep 2
done

echo "[ERROR] MySQL 启动超时，查看: $COMPOSE logs mysql" >&2
exit 1
