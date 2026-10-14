export function shortHeadline(title, limit = 26) {
  const characters = Array.from(String(title || '').replace(/\s+/gu, ' ').trim());
  return characters.length > limit ? characters.slice(0, limit).join('').trimEnd() + '...' : characters.join('');
}

export function latestNewsEntity(entities) {
  const timestamp = entity => {
    const item = entity.news;
    return Date.parse(item.published_at) || Date.parse(item.collected_at)
      || (Date.parse(item.expires_at) - 604800000) || 0;
  };
  return entities.filter(entity => entity.news)
    .reduce((latest, entity) => !latest || timestamp(entity) > timestamp(latest) ? entity : latest, null);
}
