"""Tile the locked NASA surface image; Pillow is needed only for offline asset preparation."""
import hashlib
import json
import urllib.request
from pathlib import Path

import PIL
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT / "geo/imagery-source.json").read_text())
    if PIL.__version__ != source["pillow_version"]:
        raise RuntimeError("Use the pinned Pillow version in geo/imagery-source.json")
    cache = ROOT / ".cache/imagery/nasa-bmng-base-2004-07-21600.jpg"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix(".download")
        with urllib.request.urlopen(source["url"], timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(cache)
    if hashlib.sha256(cache.read_bytes()).hexdigest() != source["sha256"]:
        raise RuntimeError("NASA source checksum changed; refusing to package unverified data")
    target = ROOT / "frontend/public/imagery" / source["asset_id"]
    target.mkdir(parents=True, exist_ok=True)
    size, maximum = source["tile_size"], source["maximum_level"]
    dimensions = tuple(source["dimensions"])
    assert dimensions == (size * 2 ** (maximum + 1), size * 2 ** maximum)
    # The verified source is deliberately larger than Pillow's generic image safety default.
    Image.MAX_IMAGE_PIXELS = dimensions[0] * dimensions[1]
    files = {}
    with Image.open(cache) as image:
        if image.size != dimensions or image.mode != "RGB":
            raise RuntimeError("Unexpected NASA image dimensions or color mode")
        for level in range(maximum + 1):
            columns, rows = 2 ** (level + 1), 2 ** level
            layer = image if level == maximum else image.resize(
                (columns * size, rows * size), Image.Resampling.LANCZOS)
            for x in range(columns):
                folder = target / str(level) / str(x)
                folder.mkdir(parents=True, exist_ok=True)
                for y in range(rows):
                    path = folder / f"{y}.jpg"
                    with layer.crop((x * size, y * size, (x + 1) * size, (y + 1) * size)) as tile:
                        tile.save(path, quality=source["jpeg_quality"], optimize=True, subsampling=0)
                    data = path.read_bytes()
                    files[str(path.relative_to(target))] = {"bytes": len(data),
                                                           "sha256": hashlib.sha256(data).hexdigest()}
            if layer is not image:
                layer.close()
    manifest = {"source": source, "tiling": "GeographicTilingScheme, north-origin XYZ",
                "files": files, "total_bytes": sum(item["bytes"] for item in files.values())}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"NASA basemap: {len(files)} tiles, {manifest['total_bytes']} bytes, source resolution preserved")


if __name__ == "__main__":
    main()
