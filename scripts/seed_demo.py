"""Synthetic development stories. Not real news or translated source content."""
import argparse
import os
from datetime import datetime, timezone

from terra_newsphere.normalize import normalize
from terra_newsphere.store import NewsStore


def demo_events(store):
    now = datetime.now(timezone.utc).isoformat()
    suffix = f"/{os.environ['DEMO_RUN_ID']}" if os.environ.get("DEMO_RUN_ID") else ""
    titles = {"KR": "[데모] 서울에서 시작하는 지구 뉴스 탐색", "US": "[Demo] Exploring news across North America",
              "GB": "[Demo] A new perspective on European stories", "JP": "[Demo] Discover stories across Japan",
              "BR": "[Demo] A window into South America", "AU": "[Demo] Stories from the southern hemisphere"}
    for country, title in titles.items():
        if country not in store.geography.countries:
            continue
        yield {"schema_version": 1, "source": {"provider": "DEMO", "publisher": "TerraNewsphere Demo",
               "url": f"https://example.com/terra-demo/{country}{suffix}"},
               "content": {"title": title, "language": "ko" if country == "KR" else "en",
                           "summary": None}, "published_at": now, "collected_at": now,
               "location_references": [{"country_code": country, "role": "event", "confidence": 1}],
               "is_demo": True}
    for region_id, region in store.geography.regions.items():
        if region["location_type"] != "adm2":
            continue
        reference = {**region, "role": "event", "confidence": 1}
        yield {"schema_version": 1, "source": {"provider": "DEMO", "publisher": "TerraNewsphere Demo",
               "url": f"https://example.com/terra-demo/region/{region_id}{suffix}"},
               "content": {"title": f"[데모] {region['region_name']} · {region['district_name']}의 지역 마커", "language": "ko"},
               "published_at": now, "collected_at": now, "location_references": [reference], "is_demo": True}
        break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kafka", action="store_true", help="Send through Kafka/Spark instead of directly saving")
    args = parser.parse_args()
    store = NewsStore()
    try:
        if args.kafka:
            import json
            from kafka import KafkaProducer
            producer = KafkaProducer(bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092").split(","),
                                     acks="all", value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode())
            try:
                for event in demo_events(store):
                    producer.send(os.environ.get("KAFKA_TOPIC", "news.raw"), event).get(timeout=30)
            finally:
                producer.close()
        else:
            for event in demo_events(store):
                store.save(normalize(event, store.geography))
        print("Seeded clearly labelled synthetic demo stories")
    finally:
        store.redis.close()


if __name__ == "__main__":
    main()
