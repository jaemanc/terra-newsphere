"""Single validation cycle: syntax, real Redis retention/API cycle, frontend, deployment."""
import argparse
import ast
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-url", help="Dedicated EMPTY test Redis database; never production")
    parser.add_argument("--containers", action="store_true", help="Also build/start the full Kafka/Spark pipeline")
    parser.add_argument("--services-only", action="store_true", help="Resume service checks after syntax/build/config already passed")
    args = parser.parse_args()
    env = {**os.environ, "PYTHONPATH": f"{ROOT / 'backend'}:{ROOT}"}
    process = None
    temporary = None
    docker_redis = False
    try:
        if not args.services_only:
            for folder in ("backend", "collector", "spark", "scripts", "tests"):
                for path in (ROOT / folder).rglob("*.py"):
                    ast.parse(path.read_text(), filename=str(path))
            print("Python syntax: OK", flush=True)
            subprocess.run(["node", "--test", "src/geo.test.js"], cwd=ROOT / "frontend", check=True)
            # These checks do not need Docker access; report them before service startup.
            subprocess.run(["npm", "run", "build"], cwd=ROOT / "frontend", check=True)
            import yaml
            for path in [ROOT / "compose.yaml", *ROOT.rglob("k3s.yaml"), *list((ROOT / "deploy/k3s").glob("*.yaml"))]:
                list(yaml.safe_load_all(path.read_text()))
            print("Deployment YAML parse: OK", flush=True)
            if shutil.which("docker"):
                subprocess.run(["docker", "compose", "--profile", "ingest", "config", "--quiet"], cwd=ROOT, check=True)
                print("Docker Compose config: OK", flush=True)
            if shutil.which("kubectl"):
                subprocess.run(["kubectl", "kustomize", "deploy/k3s"], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
                print("K3s Kustomize render: OK", flush=True)
        if args.redis_url:
            env["TEST_REDIS_URL"] = args.redis_url
        else:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            env["TEST_REDIS_URL"] = f"redis://127.0.0.1:{port}/15"
            if shutil.which("redis-server"):
                temporary = tempfile.TemporaryDirectory(prefix="terra-verify-")
                process = subprocess.Popen(["redis-server", "--bind", "127.0.0.1", "--port", str(port),
                    "--save", "", "--appendonly", "no", "--dir", temporary.name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            else:
                subprocess.run(["docker", "run", "-d", "--rm", "--name", "terra-verify-redis",
                    "-p", f"127.0.0.1:{port}:6379", "redis:7.4.5-alpine", "redis-server", "--save", "", "--appendonly", "no"], check=True)
                docker_redis = True
            from redis import Redis
            database = Redis.from_url(env["TEST_REDIS_URL"])
            for attempt in range(50):
                try:
                    database.ping()
                    break
                except Exception:
                    time.sleep(.2)
            else:
                raise RuntimeError("Isolated test Redis failed to start")
            database.close()
        from redis import Redis
        database = Redis.from_url(env["TEST_REDIS_URL"])
        if database.dbsize() != 0:
            raise RuntimeError("Refusing to test against a nonempty Redis database")
        database.close()
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, env=env, check=True)
        if args.containers:
            subprocess.run(["docker", "compose", "--profile", "ingest", "up", "--build", "-d", "--wait"], cwd=ROOT, check=True)
            # A fresh URL prevents old directly seeded demo data from falsely passing.
            run_id = uuid4().hex
            subprocess.run(["docker", "compose", "run", "--rm", "--no-deps", "-e", f"DEMO_RUN_ID={run_id}",
                            "collector", "python", "/app/scripts/seed_demo.py", "--kafka"], cwd=ROOT, check=True)
            subprocess.run([sys.executable, "scripts/check_pipeline.py"], cwd=ROOT,
                           env={**env, "DEMO_RUN_ID": run_id}, check=True)
        print("Service checks: PASSED" if args.services_only else "Combined validation cycle: PASSED", flush=True)
    finally:
        if process:
            process.terminate()
            process.wait(timeout=10)
        if temporary:
            temporary.cleanup()
        if docker_redis:
            subprocess.run(["docker", "stop", "terra-verify-redis"], check=False, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
