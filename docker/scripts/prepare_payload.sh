#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_ROOT="${1:-/root/wd6zn_extracted}"
TARGET="$(cd "$(dirname "$0")/.." && pwd)/data/rootfs"

if [[ -d "$TARGET/home/1" && -d "$TARGET/www/wwwroot" ]]; then
  echo "[INFO] payload 已存在: $TARGET"
  exit 0
fi

[[ -d "$SOURCE_ROOT/home" ]] || { echo "[ERROR] 找不到 $SOURCE_ROOT/home" >&2; exit 1; }
[[ -d "$SOURCE_ROOT/www" ]] || { echo "[ERROR] 找不到 $SOURCE_ROOT/www" >&2; exit 1; }

mkdir -p "$TARGET"
echo "[INFO] 复制服务端文件到 $TARGET"
cp -a "$SOURCE_ROOT/home" "$TARGET/"
cp -a "$SOURCE_ROOT/www" "$TARGET/"

find "$TARGET/home" -type f \( -name 'qd' -o -name 'gb' -o -name 'sk' -o -name 'sk2' -o -name '*.sh' -o -name 'run*' -o -name 'rungs*' -o -name 'magic_Linux32' \) -exec chmod +x {} + 2>/dev/null || true
find "$TARGET/www" -type d -exec chmod u+rwx,go+rx {} +
find "$TARGET/www" -type f -exec chmod u+rw,go+r {} +
