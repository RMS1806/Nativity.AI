#!/bin/bash
set -e

# Render sets $PORT dynamically — bake it into the nginx config at container start
: "${PORT:=10000}"
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

exec supervisord -c /etc/supervisord.conf
