-- Atomic article + expiring region indexes. Retries never move the first timestamp forward.
local article_key = KEYS[1]
local item = cjson.decode(ARGV[1])
local now = tonumber(redis.call('TIME')[1])
local first = tonumber(ARGV[2])
local old_json = redis.call('GET', article_key)
local old = nil
if old_json then
    old = cjson.decode(old_json)
    first = math.min(first, tonumber(old._first_epoch))
end
local expires = first + 604800
if expires <= now then return 0 end
item._first_epoch = first
item._expires_epoch = expires
if old and tonumber(old._first_epoch) <= tonumber(ARGV[2]) then
    item.collected_at = old.collected_at
    item.expires_at = old.expires_at
end
local previous_indexes = old and old._indexes or {}
for _, key in ipairs(previous_indexes) do
    redis.call('ZREM', key, item.news_id)
end
local indexes = cjson.decode(ARGV[3])
item._indexes = indexes
redis.call('SET', article_key, cjson.encode(item), 'EXAT', expires)
for _, key in ipairs(indexes) do
    redis.call('ZREMRANGEBYSCORE', key, '-inf', now)
    redis.call('ZADD', key, expires, item.news_id)
    local last = redis.call('ZRANGE', key, -1, -1, 'WITHSCORES')
    redis.call('EXPIREAT', key, math.ceil(tonumber(last[2])))
end
return 1
