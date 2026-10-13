"""Build small static GeoJSON and matching location IDs; never run at request time."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import httpx
import pycountry
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend/public/geo"
GENERATED = ROOT / "geo/generated"
LOCK = ROOT / "geo/sources.json"
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"


def download(client, url):
    response = client.get(url)
    response.raise_for_status()
    return response.json()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-sources", action="store_true", help="Resolve current geoBoundaries once and lock immutable URLs")
    args = parser.parse_args()
    verify_tls = os.environ.get("TERRA_SKIP_TLS_VERIFY", "0") != "1"
    with httpx.Client(timeout=120, follow_redirects=True, verify=verify_tls) as client:
        if args.refresh_sources or not LOCK.exists():
            sources = {"natural_earth": {"version": "5.1.2", "license": "Public domain",
                       "countries": NE_BASE + "ne_110m_admin_0_countries.geojson",
                       "capitals": NE_BASE + "ne_110m_populated_places.geojson"}, "geoboundaries": []}
            for level in ("ADM1", "ADM2"):
                metadata = download(client, f"https://www.geoboundaries.org/api/current/gbOpen/KOR/{level}/")
                # API points at a commit-specific URL; refuse a mutable branch reference.
                url = metadata["gjDownloadURL"]
                if "/main/" in url or "/master/" in url:
                    raise ValueError("geoBoundaries download URL must identify an immutable commit")
                sources["geoboundaries"].append({"country_code": "KR", "level": level,
                    "boundary_id": metadata["boundaryID"], "url": url,
                    "license": metadata["boundaryLicense"],
                    "license_source": metadata.get("licenseSource"),
                    "source": metadata.get("boundarySource"),
                    "year": metadata.get("boundaryYearRepresented"),
                    "build_date": metadata.get("buildDate")})
            write(LOCK, sources)
        sources = json.loads(LOCK.read_text())
        countries_raw = download(client, sources["natural_earth"]["countries"])
        capitals_raw = download(client, sources["natural_earth"]["capitals"])
        capitals = {}
        for feature in capitals_raw["features"]:
            props = feature["properties"]
            if props.get("ADM0CAP") == 1:
                code = props.get("ISO_A2")
                lon, lat = feature["geometry"]["coordinates"]
                capitals[code] = {"name": props["NAME"], "latitude": lat, "longitude": lon}
        countries, features, fips_to_iso = {}, [], {}
        for feature in countries_raw["features"]:
            props = feature["properties"]
            code = props.get("ISO_A2_EH") or props.get("ISO_A2")
            if not code or pycountry.countries.get(alpha_2=code) is None:
                continue
            name = props.get("NAME_EN") or props["ADMIN"]
            countries[code] = {"name": name, "dataset_version": "NaturalEarth:5.1.2",
                               "capital": capitals.get(code)}
            fips = props.get("FIPS_10")
            if fips and len(fips) == 2 and fips != "-99":
                if fips in fips_to_iso and fips_to_iso[fips] != code:
                    raise ValueError(f"Ambiguous FIPS mapping: {fips}")
                fips_to_iso[fips] = code
            geometry = shape(feature["geometry"]).simplify(0.05, preserve_topology=True)
            features.append({"type": "Feature", "properties": {"country_code": code, "name": name},
                             "geometry": mapping(geometry)})
        write(PUBLIC / "countries.geojson", {"type": "FeatureCollection", "features": features})
        regions, parent_shapes, assets = {}, [], {}
        for source in sources["geoboundaries"]:
            raw = download(client, source["url"])
            output = []
            version = "geoBoundaries:" + source["boundary_id"]
            for feature in raw["features"]:
                props = feature["properties"]
                geometry = shape(feature["geometry"])
                if not geometry.is_valid:
                    geometry = geometry.buffer(0)
                region_id = source["boundary_id"] + ":" + props["shapeID"]
                region = {"country_code": source["country_code"], "dataset_version": version,
                          "latitude": geometry.centroid.y, "longitude": geometry.centroid.x,
                          "coordinate_source": "region_centroid"}
                if source["level"] == "ADM1":
                    region.update(adm1_id=region_id, adm2_id=None, region_name=props["shapeName"],
                                  district_name=None, location_type="adm1")
                    parent_shapes.append((region_id, geometry))
                else:
                    matches = [(parent, polygon.intersection(geometry).area) for parent, polygon in parent_shapes
                               if polygon.intersects(geometry)]
                    if not matches:
                        raise ValueError(f"No ADM1 parent for {region_id}")
                    parent, overlap = max(matches, key=lambda match: match[1])
                    if overlap / geometry.area < 0.8:
                        raise ValueError(f"Ambiguous ADM1 parent for {region_id}")
                    region.update(adm1_id=parent, adm2_id=region_id,
                                  region_name=regions[parent]["region_name"], district_name=props["shapeName"],
                                  location_type="adm2")
                regions[region_id] = region
                output.append({"type": "Feature", "properties": {"region_id": region_id,
                    "shape_id": props["shapeID"], "name": props["shapeName"],
                    "country_code": source["country_code"], "adm1_id": region["adm1_id"],
                    "dataset_version": version},
                    "geometry": mapping(geometry.simplify(0.01, preserve_topology=True))})
            relative = f"{source['level'].lower()}/{source['country_code']}.geojson"
            write(PUBLIC / relative, {"type": "FeatureCollection", "features": output})
            assets.setdefault(source["country_code"], {})[source["level"].lower()] = relative
        write(GENERATED / "regions.json", {"countries": countries, "regions": regions, "fips_to_iso": fips_to_iso})
        files = {str(path.relative_to(PUBLIC)): {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "bytes": path.stat().st_size} for path in PUBLIC.rglob("*.geojson")}
        write(PUBLIC / "manifest.json", {"countries": "countries.geojson", "administrative": assets,
               "sources": sources, "files": files, "format": "GeoJSON", "simplification_degrees": {"adm0": 0.05, "adm1_adm2": 0.01}})
        print(f"Bundled {len(countries)} countries, {len(regions)} administrative regions")


if __name__ == "__main__":
    main()
