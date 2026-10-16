import fixtures from './demo-locations.json' with { type: 'json' };

const names = new Intl.DisplayNames(['ko'], { type: 'region' });
const topics = [['Science example', '과학 소식 예시'], ['Community example', '지역 소식 예시'], ['Environment example', '환경 소식 예시']];
const startedAt = Date.now();
const records = fixtures.locations.flatMap(({ news_ids, ...location }) => news_ids.map((news_id, topic) => {
  const en = location.district_name || location.region_name || location.country_name;
  const ko = location.district_name || location.region_name || names.of(location.country_code);
  return { news_id, source: { provider: 'Demo', publisher: 'TerraNewsphere Demo', url: 'https://example.com/' },
    content: { title: `[Demo] ${en}: ${topics[topic][0]}`, language: 'en', thumbnail_url: null,
      summary: 'This is a fictional story for exploring the demo. It is not a real report. The source link opens an example website.',
      translations: { ko: { title: `[데모] ${ko}: ${topics[topic][1]}`,
        summary: '화면 체험을 위한 가상 기사이며 실제 보도가 아닙니다. 예시 링크는 실제 기사 대신 예제 사이트로 연결됩니다.' } } },
    locations: [location], category: 'other', is_demo: true,
    published_at: new Date(startedAt - topic * 60000).toISOString(), collected_at: new Date(startedAt).toISOString(),
    expires_at: new Date(startedAt + 604800000).toISOString() };
}));
const byId = new Map(records.map(record => [record.news_id, record]));
const json = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });

// This module is loaded only by the demo build; it never calls a news API or Redis.
export function demoNewsResponse(path) {
  const url = new URL(path, 'https://demo.invalid');
  const current = records.filter(record => Date.parse(record.expires_at) > Date.now());
  if (url.pathname === '/api/news/stats') return json({ total: current.length, complete: true, expires_at: current[0]?.expires_at });
  if (url.pathname === '/api/news/markers') {
    const params = url.searchParams;
    let matches = current.filter(record => ['country', 'adm1', 'adm2'].every((key) => {
      const value = params.get(key);
      return !value || record.locations.some(location => location[key === 'country' ? 'country_code' : `${key}_id`] === value);
    }));
    if (params.has('bbox')) {
      const [west, south, east, north] = params.get('bbox').split(',').map(Number);
      matches = matches.filter(record => record.locations.some(({ longitude: x, latitude: y }) =>
        y >= south && y <= north && (west <= east ? x >= west && x <= east : x >= west || x <= east)));
    }
    const cursor = Number(params.get('cursor') || 0), limit = Math.min(200, Number(params.get('limit') || 100));
    return json({ items: matches.slice(cursor, cursor + limit).map(record => ({ ...record.content,
      news_id: record.news_id, url: record.source.url, publisher: record.source.publisher, locations: record.locations,
      published_at: record.published_at, collected_at: record.collected_at, expires_at: record.expires_at, is_demo: true })),
      next_cursor: cursor + limit < matches.length ? cursor + limit : null });
  }
  const record = byId.get(url.pathname.split('/').at(-1));
  return record && Date.parse(record.expires_at) > Date.now() ? json(record) : json({ detail: 'Demo story not found' }, 404);
}
