FROM python:3.12.11-slim-bookworm
WORKDIR /app
ARG ROLE=api
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/backend:/app
COPY pyproject.toml uv.lock ./
COPY backend ./backend
RUN pip install --no-cache-dir uv==0.12.9 && uv sync --frozen --no-dev --extra ${ROLE}
ENV PATH=/app/.venv/bin:$PATH
COPY redis/write_news.lua ./redis/write_news.lua
COPY geo/generated ./geo/generated
COPY collector ./collector
COPY scripts/seed_demo.py ./scripts/seed_demo.py
RUN useradd --uid 10001 --create-home app
USER 10001
CMD ["uvicorn", "terra_newsphere.api:app", "--host", "0.0.0.0", "--port", "8000"]
