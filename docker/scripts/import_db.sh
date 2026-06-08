#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
COMPOSE=${COMPOSE:-docker compose}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-long1251374638}

mysql_exec() {
  $COMPOSE exec -T -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql mysql -uroot "$@"
}

mysql_sh() {
  $COMPOSE exec -T -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql sh -c "$1"
}

main_dbs=(release_adb release_ddb release_dmdb release_gddb release_gsdb release_ldb release_mdb release_sdb release_sldb release_tdb wscyun_sdk wdgm houtai)
zone2_dbs=(zy_adb zy_ddb zy_dmdb zy_gddb zy_gsdb zy_ldb zy_mdb zy_sdb zy_sldb zy_tdb)

echo "[INFO] 重建主区数据库"
for db in "${main_dbs[@]}"; do
  mysql_exec -e "DROP DATABASE IF EXISTS \`$db\`; CREATE DATABASE \`$db\` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
done

echo "[INFO] 导入主区 SQL"
for db in release_adb release_ddb release_gddb release_gsdb release_ldb release_mdb release_sdb release_sldb release_tdb wscyun_sdk; do
  mysql_sh "mysql -uroot --default-character-set=latin1 $db < /seed/db/$db.sql"
done
mysql_sh "mysql -uroot --default-character-set=utf8mb4 wdgm < /seed/db/wdgm.sql"
mysql_sh "mysql -uroot --default-character-set=utf8 houtai < /seed/db/houtai.sql"

echo "[INFO] 重建二区数据库"
for db in "${zone2_dbs[@]}"; do
  mysql_exec -e "DROP DATABASE IF EXISTS \`$db\`; CREATE DATABASE \`$db\` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
done

if [[ -d ./data/rootfs/home/db/2 ]]; then
  echo "[INFO] 导入二区 SQL"
  for db in "${zone2_dbs[@]}"; do
    if [[ -f "./data/rootfs/home/db/2/$db.sql" ]]; then
      mysql_sh "mysql -uroot --default-character-set=latin1 $db < /seed/db/2/$db.sql"
    fi
  done
fi

echo "[INFO] 修正数据库内服务端 DB Host 为 127.0.0.1"
mysql_exec release_adb -e "UPDATE config SET value=REPLACE(value, '\"Host\":\"${PUBLIC_IP:-109.110.170.79}\"', '\"Host\":\"127.0.0.1\"') WHERE value LIKE '%\"Host\":\"%';" || true
mysql_exec zy_adb -e "UPDATE config SET value=REPLACE(value, '\"Host\":\"${PUBLIC_IP:-109.110.170.79}\"', '\"Host\":\"127.0.0.1\"') WHERE value LIKE '%\"Host\":\"%';" || true

echo "[OK] 数据库导入完成"
