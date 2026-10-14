"""Small live proof of ACLs, frontend isolation, headers and burst rejection."""
import concurrent.futures
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request


def execute(service, code):
    subprocess.run(["docker", "compose", "exec", "-T", service, "python", "-c", code], check=True)


def main():
    execute("api", '''from terra_newsphere.connection import redis_client
from redis import Redis
from redis.exceptions import AuthenticationError, ResponseError
client=redis_client(); assert client.ping()
for probe in (lambda: client.eval("return 1",0), lambda: client.set("security:probe","1",ex=1)):
    try: probe()
    except ResponseError: pass
    else: raise AssertionError("API acquired write/script privilege")
try: Redis(host="redis").ping()
except AuthenticationError: pass
else: raise AssertionError("Unauthenticated Redis accepted")
print("Redis authentication and API ACL: PASSED")''')
    execute("collector", '''from terra_newsphere.connection import redis_client
from redis.exceptions import ResponseError
client=redis_client(); assert client.ping()
try: client.get("news:article:"+"0"*64)
except ResponseError: pass
else: raise AssertionError("Collector acquired article access")
print("Collector ACL: PASSED")''')
    execute("spark", '''from terra_newsphere.connection import redis_client
from redis.exceptions import ResponseError
client=redis_client(); assert client.ping()
try: client.config_get("bind")
except ResponseError: pass
else: raise AssertionError("Processor acquired admin privilege")
print("Processor ACL: PASSED")''')
    check_web()


def check_web():
    # Probe IPs as well as DNS names; missing DNS alone is not network isolation.
    for service, port in (("redis", "6379"), ("kafka", "9092")):
        cid = subprocess.check_output(["docker", "compose", "ps", "-q", service], text=True).strip()
        networks = json.loads(subprocess.check_output(["docker", "inspect", "--format",
            "{{json .NetworkSettings.Networks}}", cid], text=True))
        hosts = [service] + [network["IPAddress"] for network in networks.values()]
        for host in hosts:
            result = subprocess.run(["docker", "compose", "exec", "-T", "frontend", "nc",
                "-z", "-w", "1", host, port], capture_output=True)
            if result.returncode == 0:
                raise AssertionError("Frontend reached private service " + service)
    mapping = subprocess.check_output(["docker", "compose", "port", "frontend", "8080"], text=True).strip()
    base = "http://" + mapping
    with urllib.request.urlopen(base, timeout=5) as response:
        for header in ("Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options"):
            assert response.headers.get(header), header
    with urllib.request.urlopen(base + "/api/health", timeout=5) as response:
        assert response.headers.get("X-Frame-Options") == "DENY"
    def request(number):
        req = urllib.request.Request(base + "/api/health", headers={"X-Forwarded-For": f"203.0.113.{number}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(request, range(1, 61)))
    assert 429 in codes and 200 in codes, codes
    assert set(codes) <= {200, 429}, codes
    time.sleep(5)
    assert request(1) == 200
    print("Frontend isolation, security headers, spoof-resistant 429 and recovery: PASSED")


if __name__ == "__main__":
    check_web() if "--web-only" in sys.argv else main()
