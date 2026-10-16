import assert from 'node:assert/strict';
import test from 'node:test';
import { runInNewContext } from 'node:vm';
import { locationName, locationsName, primaryLocation } from './geo.js';
import { shortHeadline, latestNewsEntity } from './news-labels.js';
import { demoNewsResponse } from './demo-news.js';

test('decluttering restores recycled labels after Cesium clears their entity ID', () => {
  let render;
  const style = { fillColor: 'white', outlineColor: 'black' };
  const labels = [0, 1].map(id => ({
    id: { id: String(id), news: {}, label: {} }, clusterShow: true, position: {},
    computeScreenSpacePosition: () => ({}), isDestroyed: () => false,
  }));
  const collection = { length: 2, get: i => labels[i], isDestroyed: () => false };
  const globe = { camera: { positionWC: {} }, canvas: { clientWidth: 800, clientHeight: 600 },
    scene: { postRender: { addEventListener: fn => { render = fn; } }, requestRender() {} } };
  const Cesium = {
    EllipsoidalOccluder: class { isPointVisible() { return true; } }, Ellipsoid: { WGS84: {} },
    Cartesian3: { distanceSquared: () => 1 }, Color: { TRANSPARENT: 'transparent' },
    Label: { getScreenSpaceBoundingBox: () => ({ x: 10, y: 10, width: 100, height: 20 }) },
  };
  const source = readFileSync(new URL('./headline-declutter.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export function', 'function');
  const declutter = runInNewContext(`${source}\ndeclutterHeadlines`, {
    Cesium, labelStyle: style, visibleHeadlines,
  });
  declutter(globe, { clustering: { _labelCollection: collection } });
  render();
  assert.equal(labels[1].fillColor, 'transparent');
  // EntityCluster returns removed labels to its pool and clears their IDs.
  labels[1].id = undefined;
  assert.doesNotThrow(() => render());
  assert.equal(labels[1].fillColor, 'white');
  assert.equal(labels[0].id.label.fillColor, 'white');
});

test('standalone demo paginates fictional stories and filters the geographic hierarchy', async () => {
  const first = await demoNewsResponse('/api/news/markers?country=KR&limit=200').json();
  assert.equal(first.items.length, 200);
  const second = await demoNewsResponse(`/api/news/markers?country=KR&limit=200&cursor=${first.next_cursor}`).json();
  assert.equal(second.next_cursor, null);
  const items = [...first.items, ...second.items];
  assert.equal(new Set(items.map(item => item.news_id)).size, items.length);
  assert(items.every(item => item.is_demo && item.locations.every(location => location.country_code === 'KR')));
  const district = items.find(item => item.locations[0].adm2_id);
  const location = district.locations[0];
  const filtered = await demoNewsResponse(`/api/news/markers?country=KR&adm1=${location.adm1_id}&adm2=${location.adm2_id}`).json();
  assert.deepEqual(filtered.items.map(item => item.news_id), [district.news_id]);
  const article = await demoNewsResponse(`/api/news/${district.news_id}`).json();
  assert.equal(article.source.url, 'https://example.com/');
  assert(article.content.translations.ko.title.startsWith('[데모]'));
  assert.equal(demoNewsResponse('/api/news/missing').status, 404);
});

test('demo endpoints stop returning expired examples', async () => {
  const page = await demoNewsResponse('/api/news/markers?limit=1').json();
  const item = page.items[0], originalNow = Date.now;
  Date.now = () => Date.parse(item.expires_at) + 1;
  try {
    assert.equal((await demoNewsResponse('/api/news/stats').json()).total, 0);
    assert.deepEqual((await demoNewsResponse('/api/news/markers').json()).items, []);
    assert.equal(demoNewsResponse(`/api/news/${item.news_id}`).status, 404);
  } finally { Date.now = originalNow; }
});

test('globe headlines are a single line, add literal dots only after truncation, and preserve Unicode', () => {
  assert.equal(shortHeadline('  A\nshort title  ', 20), 'A short title');
  assert.equal(shortHeadline('Long headline for the globe', 8), 'Long hea...');
  assert.equal(shortHeadline('서울에서 새 소식이 나왔습니다', 6), '서울에서 새...');
  assert.equal(shortHeadline('🌍🌏🌎 news', 2), '🌍🌏...');
  const old = { news: { published_at: '2026-10-12T00:00:00Z', collected_at: '2026-10-14T00:00:00Z' } };
  const recent = { news: { published_at: '2026-10-13T00:00:00Z' } };
  assert.equal(latestNewsEntity([{}, old, recent]), recent);
  const discovered = { news: { published_at: null, collected_at: '2026-10-14T00:00:00Z' } };
  assert.equal(latestNewsEntity([recent, discovered]), discovered);
  assert.equal(latestNewsEntity([{}]), null);
});

test('country-only news stays country-only; known regions and multiple locations are shown', () => {
  const country = { country_code: 'KR', country_name: 'South Korea', coordinate_source: 'capital_fallback' };
  const district = { ...country, region_name: 'Gangwon', district_name: 'Sokcho-si' };
  assert.equal(locationName(country, 'ko'), '대한민국');
  assert.equal(locationName(district, 'ko'), '대한민국 · 강원 · 속초시');
  assert.equal(locationName(district, 'en'), 'South Korea · Gangwon · Sokcho-si');
  assert.equal(locationName({ ...country, region_name: 'Seoul', district_name: 'Jongno-gu' }, 'ko'), '대한민국 · 서울 · 종로구');
  assert.equal(locationsName([country, country, district], 'ko'), '대한민국 / 대한민국 · 강원 · 속초시');
});

test('one stable article anchor prefers event, confidence, then detail without removing associations', () => {
  const mention = code => ({ country_code: code, association_kind: 'mentioned', confidence: .5, location_type: 'country' });
  const locations = [mention('AE'), mention('US'), mention('IR')];
  const original = structuredClone(locations);
  assert.equal(primaryLocation(locations), locations[0]);
  assert.deepEqual(locations, original);
  assert.equal(primaryLocation([]), null);
  const event = { ...mention('IR'), association_kind: 'event', confidence: .4 };
  assert.equal(primaryLocation([...locations, event]), event);
  const confident = { ...event, confidence: .9 };
  assert.equal(primaryLocation([event, confident]), confident);
  const district = { ...confident, location_type: 'adm2' };
  assert.equal(primaryLocation([confident, district]), district);
  assert.equal(locationsName(locations, 'en'), 'United Arab Emirates / United States / Iran');
});

import { countryAreas, markerPosition, uncertainLocation } from './marker-placement.js';
import { readFileSync } from 'node:fs';

test('country-only display points are stable, varied, inside land and outside holes; real coordinates remain intact', () => {
  const square = [[0,0],[10,0],[10,10],[0,10],[0,0]];
  const hole = [[3,3],[7,3],[7,7],[3,7],[3,3]];
  const areas = countryAreas([{properties:{country_code:'XX'},geometry:{type:'Polygon',coordinates:[square,hole]}}]);
  const location = {country_code:'XX',longitude:1,latitude:1,coordinate_source:'capital_fallback',association_kind:'mentioned'};
  const snapshot = structuredClone(location), points = new Set();
  for(let n=0;n<100;n++) {
    const item={news_id:String(n)}, point=markerPosition(item,location,areas);
    assert.deepEqual(point,markerPosition(item,location,areas));
    assert(point.longitude>0&&point.longitude<10&&point.latitude>0&&point.latitude<10);
    assert(!(point.longitude>3&&point.longitude<7&&point.latitude>3&&point.latitude<7));
    points.add(JSON.stringify(point));
  }
  assert.equal(points.size,100);assert.deepEqual(location,snapshot);
  assert(uncertainLocation(location));
  const exact={...location,coordinate_source:'verified_place',association_kind:'event'};
  assert.equal(uncertainLocation(exact),false);
  assert(uncertainLocation({...exact,association_kind:'mentioned'}));
  assert(uncertainLocation({...exact,coordinate_source:'region_centroid'}));
  assert.deepEqual(markerPosition({news_id:'1'},exact,areas),{longitude:1,latitude:1});
  assert.deepEqual(markerPosition({news_id:'1'},location,new Map()),{longitude:1,latitude:1});
  const dateLine=countryAreas([{properties:{country_code:'XX'},geometry:{type:'Polygon',coordinates:[[[170,-10],[-170,-10],[-170,10],[170,10],[170,-10]]]}}]);
  assert(Math.abs(markerPosition({news_id:'date-line'},location,dateLine).longitude)>=170);
  const polar=countryAreas([{properties:{country_code:'XX'},geometry:{type:'Polygon',coordinates:[[[-180,-90],[180,-90],[180,-80],[-180,-80],[-180,-90]]]}}]);
  assert(markerPosition({news_id:'polar'},location,polar).latitude < -80);
  const countries=JSON.parse(readFileSync(new URL('../public/geo/countries.geojson',import.meta.url)));
  const realAreas=countryAreas(countries.features);
  const australia=markerPosition({news_id:'australia'}, {...location,country_code:'AU'}, realAreas);
  assert(australia.latitude < -15); // AU has separate territory features; prefer its mainland.
  const france={...location,country_code:'FR'};
  const point=markerPosition({news_id:'france'},france,realAreas);
  assert(point.longitude>-6&&point.longitude<10&&point.latitude>41&&point.latitude<52);
});

import { visibleHeadlines } from './headline-visibility.js';
test('overlapping headlines keep the nearest, then newest; separated titles return on zoom', () => {
  const make=(id,x,distance,timestamp=0)=>({id,label:id,bounds:{x,y:10,width:100,height:20},distance,timestamp});
  const far=make('far',0,20,100), near=make('near',30,10), separate=make('separate',200,50);
  assert.deepEqual([...visibleHeadlines([far,near,separate])],['near','separate']);
  assert.deepEqual([...visibleHeadlines([make('old',0,10,1),make('new',0,10,2)])],['new']);
  assert.equal(visibleHeadlines([far,{...near,bounds:{...near.bounds,x:110}},separate]).size,2);
  assert.equal(visibleHeadlines([far,{...near,bounds:{...near.bounds,x:100}},make('separate',200,50)]).size,3);
  assert.deepEqual([...visibleHeadlines([])],[]);
});
