#!/bin/sh
set -eu
umask 077
acl=/tmp/terra-users.acl
printf 'user default off\n' > "$acl"
for role in api collector processor health; do
    secret="/run/secrets/redis_$role"
    test -s "$secret"
    digest=$(sha256sum "$secret")
    digest=${digest%% *}
    case "$role" in
        api) rules='~news:* +get +zrangebyscore +zrevrangebyscore +zcount +zremrangebyscore' ;;
        collector) rules='~news:seen:* ~collector:* +get +set' ;;
        processor) rules='~news:* +get +set +time +zrem +zremrangebyscore +zadd +zrange +expireat +evalsha +script|load' ;;
        health) rules='' ;;
    esac
    printf 'user %s on #%s resetkeys resetchannels -@all +auth +hello +ping +client|setinfo %s\n' "$role" "$digest" "$rules" >> "$acl"
done
exec redis-server /etc/redis/redis.conf --aclfile "$acl"
