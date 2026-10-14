#!/bin/sh
set -eu
export TRUSTED_PROXY_CIDR="${TRUSTED_PROXY_CIDR:-127.0.0.1/32}"
envsubst '${TRUSTED_PROXY_CIDR}' < /etc/nginx/terra-template.conf > /tmp/terra-nginx.conf
exec nginx -g 'daemon off;'
