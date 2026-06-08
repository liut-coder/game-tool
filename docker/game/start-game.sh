#!/usr/bin/env bash
set -Eeuo pipefail

chmod -R u+rwX /home/1 /home/2 2>/dev/null || true
find /home/1 /home/2 -type f \( -name 'qd' -o -name 'gb' -o -name '*.sh' -o -name 'run*' -o -name 'rungs*' -o -name 'magic_Linux32' \) -exec chmod +x {} + 2>/dev/null || true

if [[ "${START_GAME:-0}" == "1" ]]; then
  echo "[INFO] starting zone1: /home/1/qd"
  bash /home/1/qd || true
  if [[ "${START_ZONE2:-0}" == "1" && -f /home/2/qd ]]; then
    echo "[INFO] starting zone2: /home/2/qd"
    bash /home/2/qd || true
  fi
else
  echo "[INFO] START_GAME=0，未启动游戏二进制。把 .env 改成 START_GAME=1 后重启 game 容器。"
fi

while true; do sleep 3600; done
