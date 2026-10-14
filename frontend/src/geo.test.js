import assert from 'node:assert/strict';
import test from 'node:test';
import { locationName, locationsName } from './geo.js';
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
