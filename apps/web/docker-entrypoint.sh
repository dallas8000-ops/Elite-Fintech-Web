#!/bin/sh
set -e
PORT="${PORT:-80}"
sed "s/listen 80;/listen ${PORT};/" /etc/nginx/conf.d/default.conf > /tmp/default.conf
mv /tmp/default.conf /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
