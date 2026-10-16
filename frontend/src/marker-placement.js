// Presentation coordinates only: never write these points back to news records.
export function uncertainLocation(location) {
  return location.coordinate_source !== 'verified_place' || location.association_kind !== 'event';
}

function insideRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[i], [bx, by] = ring[j];
    if ((ay > y) !== (by > y) && x < (bx - ax) * (y - ay) / (by - ay) + ax) inside = !inside;
  }
  return inside;
}

export function countryAreas(features) {
  const result = new Map();
  for (const { properties, geometry } of features) {
    const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
    const areas = polygons.map(polygon => {
      const origin = polygon[0][0][0];
      const polar = polygon[0].some(([, latitude]) => Math.abs(latitude) > 89.9);
      const rings = polar ? polygon : polygon.map(ring => ring.map(([x, y]) => [origin + ((x - origin + 540) % 360) - 180, y]));
      const xs = rings[0].map(p => p[0]), ys = rings[0].map(p => p[1]);
      const west = Math.min(...xs), east = Math.max(...xs), south = Math.min(...ys), north = Math.max(...ys);
      const area = Math.abs(rings[0].reduce((sum, [x, y], i, ring) => {
        const next = ring[(i + 1) % ring.length]; return sum + x * next[1] - next[0] * y;
      }, 0));
      return { rings, west, east, south, north, area };
    });
    // Use the largest land polygon, avoiding overseas islands and tiny fragments.
    const largest = areas.sort((a, b) => b.area - a.area)[0];
    if (!result.has(properties.country_code) || largest.area > result.get(properties.country_code).area) {
      result.set(properties.country_code, largest);
    }
  }
  return result;
}

export function markerPosition(item, location, areas) {
  const fallback = { longitude: location.longitude, latitude: location.latitude };
  if (location.coordinate_source !== 'capital_fallback') return fallback;
  const area = areas.get(location.country_code);
  if (!area) return fallback;
  let seed = 2166136261;
  for (const character of `${item.news_id}:${location.country_code}`) seed = Math.imul(seed ^ character.charCodeAt(0), 16777619);
  const random = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
  for (let attempt = 0; attempt < 256; attempt++) {
    const x = area.west + random() * (area.east - area.west);
    const y = area.south + random() * (area.north - area.south);
    if (insideRing(x, y, area.rings[0]) && !area.rings.slice(1).some(ring => insideRing(x, y, ring))) {
      return { longitude: ((x + 540) % 360) - 180, latitude: y };
    }
  }
  return fallback;
}
