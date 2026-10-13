FROM python:3.12.11-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/backend \
    PYSPARK_PYTHON=/app/.venv/bin/python PYSPARK_DRIVER_PYTHON=/app/.venv/bin/python \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
COPY backend ./backend
RUN --mount=type=secret,id=terra_ca,target=/tmp/terra_ca.crt \
    if [ -s /tmp/terra_ca.crt ]; then \
      cp /tmp/terra_ca.crt /usr/local/share/ca-certificates/terra-local.crt && update-ca-certificates; \
    fi \
    && PIP_CERT=$SSL_CERT_FILE pip install --no-cache-dir uv==0.12.9 \
    && UV_NATIVE_TLS=1 uv sync --frozen --no-dev --extra spark
ENV PATH=/app/.venv/bin:$PATH
COPY spark ./spark
COPY redis/write_news.lua ./redis/write_news.lua
COPY geo/generated ./geo/generated
RUN mkdir -p /opt/spark-ivy /var/lib/terra/checkpoints /tmp/spark \
    && spark-submit --master local[1] --conf spark.jars.ivy=/opt/spark-ivy \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.2 /app/spark/warmup.py \
    && useradd --uid 10001 --create-home app \
    && chown -R 10001:10001 /opt/spark-ivy /var/lib/terra /tmp/spark
USER 10001
CMD ["sh", "/app/spark/start.sh"]
