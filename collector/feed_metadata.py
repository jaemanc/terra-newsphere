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
    korean_names = {"대한민국": "KR", "북한": "KP", "미국": "US", "중국": "CN", "일본": "JP",
                    "영국": "GB", "프랑스": "FR", "독일": "DE", "러시아": "RU", "우크라이나": "UA",
                    "이스라엘": "IL", "이란": "IR", "인도": "IN", "네팔": "NP", "파키스탄": "PK",
                    "캐나다": "CA", "호주": "AU", "브라질": "BR", "이탈리아": "IT", "스페인": "ES",
                    "베트남": "VN", "필리핀": "PH", "태국": "TH", "인도네시아": "ID"}
    for name, code in korean_names.items():
        # Match standalone names and Korean particles, not longer country names or person names.
        if code in geography.countries and re.search(r"(?<!\w)" + re.escape(name) + r"(?=[은는이가을를의에와과도\s.,·]|$)", text):
            reference = {"country_code": code, "role": "mentioned", "confidence": 0.5}
            if reference not in references:
                references.append(reference)
    return references[:20]
