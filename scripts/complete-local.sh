#!/bin/sh
# One permission request for local prerequisites and the final validation cycle.
set -eu
export PYTHONPATH="$PWD/backend:$PWD"
sh scripts/setup.sh
# Docker is required for an isolated real Redis and the actual Kafka/Spark cycle.
printf '%s\n' 'Checking Docker availability' > .runtime/setup-stage.txt
docker info --format '{{.Architecture}}'
printf '%s\n' 'Running final combined validation cycle' > .runtime/setup-stage.txt
set -- --containers
if [ "${TERRA_VERIFY_SERVICES_ONLY:-0}" = "1" ]; then
  set -- "$@" --services-only
fi
.venv/bin/python scripts/verify.py "$@"
printf '%s\n' 'Final combined validation passed' > .runtime/setup-stage.txt
