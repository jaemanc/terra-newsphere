#!/bin/sh
set -eu
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/.cache/python"
mkdir -p .runtime
set --
if [ "${TERRA_SKIP_TLS_VERIFY:-0}" = "1" ]; then
  set -- --allow-insecure-host pypi.org --allow-insecure-host files.pythonhosted.org \
    --allow-insecure-host github.com
  export npm_config_strict_ssl=false
fi
printf '%s\n' 'Preparing Python dependencies' > .runtime/setup-stage.txt
uv sync "$@" --python 3.12 --extra api --extra collector --extra geo --extra dev
printf '%s\n' 'Preparing frontend dependencies' > .runtime/setup-stage.txt
npm --prefix frontend ci --cache "$PWD/.cache/npm" --ignore-scripts --fetch-retries=0
printf '%s\n' 'Preparing static geography' > .runtime/setup-stage.txt
if [ ! -f frontend/public/geo/manifest.json ] || [ ! -f geo/generated/regions.json ] || \
   [ ! -f frontend/public/geo/countries.geojson ] || [ ! -f frontend/public/geo/adm2/KR.geojson ]; then
  .venv/bin/python scripts/build_geo.py
fi
if [ ! -f .env ]; then
  cp .env.example .env
fi
printf '%s\n' 'Local setup completed' > .runtime/setup-stage.txt
