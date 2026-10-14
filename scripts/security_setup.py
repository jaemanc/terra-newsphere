"""Keep local credentials in ignored .env; derive container secret files."""
import os
import secrets
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(root: Path):
    environment = root / ".env"
    if not environment.exists():
        descriptor = os.open(environment, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write((root / ".env.example").read_text())
    environment.chmod(0o600)
    lines = environment.read_text().splitlines()
    directory = root / ".runtime/security"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    for role in ("api", "collector", "processor", "health"):
        path = directory / f"redis_{role}"
        key = f"REDIS_{role.upper()}_PASSWORD"
        matches = [index for index, line in enumerate(lines) if line.partition("=")[0].strip() == key]
        if len(matches) > 1:
            raise ValueError(f"Duplicate {key} in .env")
        tokens = shlex.split(lines[matches[0]].partition("=")[2], comments=True) if matches else []
        if len(tokens) > 1:
            raise ValueError(f"Quote {key} if it contains spaces")
        password = tokens[0] if tokens else ""
        if not password:
            # Import existing credentials without rotating the running services.
            password = path.read_text() if path.exists() else secrets.token_hex(32)
            if not password or any(character.isspace() for character in password):
                raise ValueError(f"Invalid existing secret for {key}")
            line = f"{key}={password}"
            if matches:
                lines[matches[0]] = line
            else:
                lines.append(line)
        if password != password.strip() or any(character in password for character in "\r\n\x00"):
            raise ValueError(f"Invalid {key}")
        if not path.exists() or path.read_text() != password:
            if path.exists():
                path.chmod(0o600)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "w") as output:
                output.write(password)
    environment.write_text("\n".join(lines) + "\n")
    # Compose bind-backed secrets retain host permissions; containers have different UIDs.
    # The enclosing directory remains private to the host user.
    for path in directory.glob("redis_*"):
        path.chmod(0o444)
    print("Credentials managed in ignored .env; container secret files ready (values omitted)")


def main():
    prepare(ROOT)


if __name__ == "__main__":
    main()
