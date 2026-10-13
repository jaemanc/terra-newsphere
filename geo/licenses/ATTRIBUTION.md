# Geography attribution

- Natural Earth 5.1.2, 1:50m countries and 1:110m populated places. Public domain. [Terms](https://www.naturalearthdata.com/about/terms-of-use/), [source](https://github.com/nvkelso/natural-earth-vector/tree/v5.1.2).
- Natural Earth II low-resolution shaded relief map, public domain, bundled with the pinned CesiumJS 1.131.0 package. Local tile levels 0–2 are copied into frontend static assets. [Natural Earth raster data](https://www.naturalearthdata.com/downloads/10m-raster-data/10m-natural-earth-2/).
- geoBoundaries gbOpen, South Korea ADM1: Natural Earth, Public Domain. ADM2: geoBoundaries/citypopulation.de, Creative Commons Attribution 3.0. Original license, boundary ID, immutable source URL and represented year are recorded per dataset in `geo/sources.json` and in the public manifest. [Dataset and attribution](https://www.geoboundaries.org/), [API](https://www.geoboundaries.org/api.html), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

Geometry is simplified for globe rendering. Administrative IDs use `boundaryID:shapeID`, not national official codes. ADM2 parents are derived from at least 80% polygon overlap with the selected ADM1 dataset; ambiguous relationships are omitted from the bundle and documented in the manifest. Coordinates are original unsimplified polygon centroids or Natural Earth capital points, used as presentation fallbacks.

Country boundaries use 0.01-degree simplification. Label anchors are polygon interior representative points, separate from news coordinates. Runtime overview uses the bundled raster; close views use vector polygons and borders.
