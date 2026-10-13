import json
import os
from pathlib import Path

from .models import Location

ROOT = Path(__file__).resolve().parents[2]
GEO_DIR = Path(os.environ.get("GEOGRAPHY_DIR", ROOT / "geo/generated"))


class Geography:
    def __init__(self, directory: Path = GEO_DIR):
        self.data = json.loads((directory / "regions.json").read_text())
        self.countries = self.data["countries"]
        self.regions = self.data["regions"]

    def resolve(self, reference: dict) -> Location | None:
        # Source publisher country and headline guesses are deliberately not accepted.
        country = self.countries.get(reference.get("country_code"))
        if not country or reference.get("role") not in {"event", "mentioned"}:
            return None
        confidence = float(reference.get("confidence", 0))
        region_id = reference.get("adm2_id") or reference.get("adm1_id")
        if region_id:
            region = self.regions.get(region_id)
            if not region or region["country_code"] != reference["country_code"]:
                return None
            if reference.get("dataset_version") != region["dataset_version"]:
                return None
            if reference.get("adm2_id") and reference.get("adm1_id") != region["adm1_id"]:
                return None
            return Location(**region, country_name=country["name"], confidence=confidence,
                            association_kind=reference["role"])
        if reference.get("location_type") not in (None, "country"):
            return None
        capital = country.get("capital")
        if not capital:
            return None
        return Location(country_code=reference["country_code"], country_name=country["name"],
                        latitude=capital["latitude"], longitude=capital["longitude"],
                        location_type="country", coordinate_source="capital_fallback",
                        confidence=confidence, dataset_version=country["dataset_version"],
                        association_kind=reference["role"])

    def validate(self, location: Location) -> None:
        reference = location.model_dump()
        reference["role"] = location.association_kind
        expected = self.resolve(reference)
        if expected is None or expected.model_dump() != location.model_dump():
            raise ValueError("Location does not match bundled geographic data")
