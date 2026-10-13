FROM python:3.12.11-slim-bookworm
WORKDIR /app
ARG ROLE=api
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/backend:/app \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
COPY pyproject.toml uv.lock ./
COPY backend ./backend
RUN --mount=type=secret,id=terra_ca,target=/tmp/terra_ca.crt \
    if [ -s /tmp/terra_ca.crt ]; then \
      cp /tmp/terra_ca.crt /usr/local/share/ca-certificates/terra-local.crt && update-ca-certificates; \
    fi \
    && PIP_CERT=$SSL_CERT_FILE pip install --no-cache-dir uv==0.12.9 \
    && UV_NATIVE_TLS=1 uv sync --frozen --no-dev --extra ${ROLE}
ENV PATH=/app/.venv/bin:$PATH
COPY redis/write_news.lua ./redis/write_news.lua
COPY geo/generated ./geo/generated
COPY collector ./collector
COPY scripts/seed_demo.py ./scripts/seed_demo.py
RUN useradd --uid 10001 --create-home app
USER 10001
CMD ["uvicorn", "terra_newsphere.api:app", "--host", "0.0.0.0", "--port", "8000"]
