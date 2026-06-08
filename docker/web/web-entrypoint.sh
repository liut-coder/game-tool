#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p /run/php-fpm /var/lib/php/session /var/log/nginx
chown -R nginx:nginx /var/lib/php/session || true
/usr/sbin/php-fpm -D
exec /usr/sbin/nginx -g 'daemon off;'
