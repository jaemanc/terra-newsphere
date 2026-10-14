"""Poll for a demo event that travelled through Kafka -> real Spark -> Redis -> HTTP."""
import json
import os
import subprocess
import time
import urllib.request

from terra_newsphere.models import article_id

suffix = f"/{os.environ['DEMO_RUN_ID']}" if os.environ.get("DEMO_RUN_ID") else ""
mapping = subprocess.check_output(["docker", "compose", "port", "frontend", "8080"], text=True).strip().splitlines()[0]
port = mapping.rsplit(":", 1)[1]
news_id = article_id(f"https://example.com/terra-demo/KR{suffix}")
url = f"http://127.0.0.1:{port}/api/news/{news_id}"
for attempt in range(45):
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            article = json.load(response)
        assert article["is_demo"] and article["locations"][0]["country_code"] == "KR"
        print("Kafka -> Spark -> Redis -> FastAPI -> frontend proxy: PASSED")
        break
    except (OSError, AssertionError):
        time.sleep(2)
else:
    raise SystemExit("Pipeline failed to deliver the demo within 90 seconds")
