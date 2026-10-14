"""Create local secrets once. Never print or overwrite existing credentials."""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / ".runtime/security"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for role in ("api", "collector", "processor", "health"):
        path = directory / f"redis_{role}"
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(descriptor, "w") as output:
            output.write(secrets.token_hex(32))
    # Compose bind-backed secrets retain host permissions; containers have different UIDs.
    # The enclosing directory remains private to the host user.
    for path in directory.glob("redis_*"):
        path.chmod(0o444)
    print("Service secrets ready in .runtime/security (values omitted)")


if __name__ == "__main__":
    main()
