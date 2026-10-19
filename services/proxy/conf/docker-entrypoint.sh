#!/bin/sh
# The container engine's DNS differs (Docker: 127.0.0.11, Podman: 10.89.x.1):
# read it from resolv.conf so that the upstream names resolve everywhere.
set -e
DNS=$(awk '/^nameserver/ { print $2; exit }' /etc/resolv.conf)
sed -i "s|resolver [0-9.]* |resolver ${DNS:-127.0.0.11} |" /etc/nginx/nginx.conf
exec nginx -g 'daemon off;'
