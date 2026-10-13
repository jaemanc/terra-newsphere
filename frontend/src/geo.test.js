import assert from 'node:assert/strict';
import test from 'node:test';
import { locationName, locationsName } from './geo.js';

test('country-only news stays country-only; known regions and multiple locations are shown', () => {
  const country = { country_code: 'KR', country_name: 'South Korea', coordinate_source: 'capital_fallback' };
  const district = { ...country, region_name: 'Gangwon', district_name: 'Sokcho-si' };
  assert.equal(locationName(country, 'ko'), '대한민국');
  assert.equal(locationName(district, 'ko'), '대한민국 · 강원 · 속초시');
  assert.equal(locationName(district, 'en'), 'South Korea · Gangwon · Sokcho-si');
  assert.equal(locationName({ ...country, region_name: 'Seoul', district_name: 'Jongno-gu' }, 'ko'), '대한민국 · 서울 · 종로구');
  assert.equal(locationsName([country, country, district], 'ko'), '대한민국 / 대한민국 · 강원 · 속초시');
});
