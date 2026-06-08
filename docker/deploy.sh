#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "[INFO] 已生成 .env，可按需修改后重新运行。"
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

COMPOSE=${COMPOSE:-docker compose}
SOURCE_ROOT=${SOURCE_ROOT:-/root/wd6zn_extracted}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-long1251374638}
IMPORT_DB=${IMPORT_DB:-1}
FORCE_IMPORT_DB=${FORCE_IMPORT_DB:-0}
REMOVE_BACKDOORS=${REMOVE_BACKDOORS:-1}

is_ipv4() {
  [[ "$1" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  local IFS=. a b c d
  read -r a b c d <<< "$1"
  for n in "$a" "$b" "$c" "$d"; do
    [[ "$n" -ge 0 && "$n" -le 255 ]] || return 1
  done
}

detect_public_ip() {
  local value ep
  for ep in https://ifconfig.me https://icanhazip.com https://api.ipify.org https://ipinfo.io/ip; do
    value="$(curl -fsS --connect-timeout 5 --max-time 10 "$ep" 2>/dev/null | tr -d '[:space:]' || true)"
    if is_ipv4 "$value"; then
      printf '%s' "$value"
      return 0
    fi
  done
  return 1
}

if [[ -z "${PUBLIC_IP:-}" ]]; then
  PUBLIC_IP="$(detect_public_ip)" || { echo "[ERROR] 无法自动获取公网 IP，请在 .env 设置 PUBLIC_IP" >&2; exit 1; }
fi
is_ipv4 "$PUBLIC_IP" || { echo "[ERROR] PUBLIC_IP 不是 IPv4: $PUBLIC_IP" >&2; exit 1; }

command -v docker >/dev/null || { echo "[ERROR] 未安装 docker" >&2; exit 1; }
command -v curl >/dev/null || { echo "[ERROR] 未安装 curl" >&2; exit 1; }
command -v openssl >/dev/null || { echo "[ERROR] 未安装 openssl" >&2; exit 1; }

./scripts/prepare_payload.sh "$SOURCE_ROOT"
PUBLIC_IP="$PUBLIC_IP" MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" REMOVE_BACKDOORS="$REMOVE_BACKDOORS" \
  python3 ./scripts/rewrite_config.py ./data/rootfs

$COMPOSE up -d --build mysql
./scripts/wait_mysql.sh

if [[ "$IMPORT_DB" == "1" ]]; then
  if [[ ! -f ./data/.db-imported || "$FORCE_IMPORT_DB" == "1" ]]; then
    MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" COMPOSE="$COMPOSE" ./scripts/import_db.sh
    date > ./data/.db-imported
  else
    echo "[INFO] 数据库已导入过；如需重建，设置 FORCE_IMPORT_DB=1。"
  fi
fi

$COMPOSE up -d --build web game

echo "[OK] Docker 部署完成"
echo "[OK] SDK/API: http://$PUBLIC_IP:81"
echo "[OK] 代理后台: http://$PUBLIC_IP:82/admin"
echo "[OK] 注册页: http://$PUBLIC_IP:82/reg"
if [[ "${START_GAME:-0}" != "1" ]]; then
  echo "[INFO] game 容器默认未启动游戏进程；确认后把 .env 的 START_GAME=1，再执行: $COMPOSE up -d game"
fi
