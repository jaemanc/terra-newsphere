"""Publisher-provided snippets and explicit place mentions, never guessed events."""
import re
from html.parser import HTMLParser


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def mentioned_locations(text: str, geography) -> list[dict]:
    # These are names in the source text, not the publisher's country or an event claim.
    # Short/ambiguous names (people, US state, food) need a stronger source signal.
    ambiguous = {"georgia", "jordan", "chad", "turkey", "guinea", "congo"}
    names = {country["name"]: code for code, country in geography.countries.items()
             if len(country["name"]) > 3 and country["name"].lower() not in ambiguous}
    names.update({"China": "CN", "United States": "US", "United Kingdom": "GB",
                  "South Korea": "KR", "North Korea": "KP", "Ivory Coast": "CI",
                  "DR Congo": "CD", "Republic of Congo": "CG", "Türkiye": "TR"})
    references = []
    for name, code in names.items():
        if code not in geography.countries:
            continue
        if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE):
            reference = {"country_code": code, "role": "mentioned", "confidence": 0.5}
            if reference not in references:
                references.append(reference)
    for name, code in {"US": "US", "U.S.": "US", "UK": "GB", "UAE": "AE"}.items():
        if code in geography.countries and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text):
            reference = {"country_code": code, "role": "mentioned", "confidence": 0.5}
            if reference not in references:
                references.append(reference)
    return references[:20]
