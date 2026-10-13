# Geography attribution

- Natural Earth 5.1.2, 1:110m countries and populated places. Public domain. [Terms](https://www.naturalearthdata.com/about/terms-of-use/), [source](https://github.com/nvkelso/natural-earth-vector/tree/v5.1.2).
- geoBoundaries gbOpen, South Korea ADM1/ADM2. Original license, boundary ID, immutable source URL and represented year are recorded per dataset in `geo/sources.json` and in the public manifest. [Dataset and attribution](https://www.geoboundaries.org/), [API](https://www.geoboundaries.org/api.html), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Geometry is simplified for globe rendering. Administrative IDs use `boundaryID:shapeID`, not national official codes. ADM2 parents are derived from at least 80% polygon overlap with the selected ADM1 dataset; ambiguous relationships fail the build. Coordinates are original unsimplified polygon centroids or Natural Earth capital points, used as presentation fallbacks.
