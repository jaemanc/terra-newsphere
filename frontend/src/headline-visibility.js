// Nearest markers win; publication time breaks ties. No popularity is inferred.
export function visibleHeadlines(candidates) {
  const visible = [];
  for (const candidate of [...candidates].sort((a, b) => a.distance - b.distance || b.timestamp - a.timestamp || a.id.localeCompare(b.id))) {
    const a = candidate.bounds;
    if (!visible.some(({ bounds: b }) => a.x < b.x + b.width && a.x + a.width > b.x
      && a.y < b.y + b.height && a.y + a.height > b.y)) visible.push(candidate);
  }
  return new Set(visible.map(candidate => candidate.label));
}
