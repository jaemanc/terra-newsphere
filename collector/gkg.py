"""Bounded GKG metadata enrichment; country mentions are not precise event locations."""
import tempfile
import zipfile
from urllib.parse import urlsplit

from terra_newsphere.models import canonical_url


def enrich_locations(client, events, geography):
    by_url = {canonical_url(event["source"]["url"]): event for event in events}
    pointer = client.get("https://data.gdeltproject.org/gdeltv2/lastupdate.txt")
    pointer.raise_for_status()
    files = [line.split() for line in pointer.text.splitlines()]
    candidate = next((parts for parts in files if len(parts) == 3 and parts[2].endswith(".gkg.csv.zip")), None)
    if not candidate or int(candidate[0]) > 16 * 1024 * 1024:
        return
    parts = urlsplit(candidate[2])
    if parts.hostname != "data.gdeltproject.org" or not parts.path.startswith("/gdeltv2/"):
        return
    url = "https://data.gdeltproject.org" + parts.path
    fips = geography.data.get("fips_to_iso", {})
    with tempfile.TemporaryFile() as temporary:
        size = 0
        with client.stream("GET", url) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 16 * 1024 * 1024:
                    return
                temporary.write(chunk)
        temporary.seek(0)
        with zipfile.ZipFile(temporary) as archive:
            for info in archive.infolist():
                if info.file_size > 256 * 1024 * 1024 or not info.filename.endswith(".csv"):
                    continue
                with archive.open(info) as binary:
                    for index in range(50000):
                        line = binary.readline(262145)
                        if not line:
                            break
                        if len(line) > 262144:
                            # Oversized source rows end this bounded enrichment pass.
                            break
                        line = line.decode("utf-8", errors="replace")
                        columns = line.rstrip("\n").split("\t")
                        if len(columns) < 11 or columns[2] != "1":
                            continue
                        try:
                            event = by_url.get(canonical_url(columns[4]))
                        except ValueError:
                            continue
                        if event is None:
                            continue
                        references = []
                        # V2Locations uses # delimiters and FIPS codes, never ISO by assumption.
                        for mention in columns[10].split(";"):
                            attributes = mention.split("#")
                            code = fips.get(attributes[2]) if len(attributes) >= 3 else None
                            reference = {"country_code": code, "role": "mentioned", "confidence": .5}
                            if code and reference not in references:
                                references.append(reference)
                        for reference in references:
                            if reference not in event["location_references"]:
                                event["location_references"].append(reference)
                        event["location_references"] = event["location_references"][:20]
