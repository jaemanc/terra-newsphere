import assert from 'node:assert/strict';
import test from 'node:test';
import { locationName, locationsName, primaryLocation } from './geo.js';
import { shortHeadline, latestNewsEntity } from './news-labels.js';

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
