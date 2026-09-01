FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.16

COPY pyproject.toml uv.lock ./
COPY shared/ ./shared/
COPY core/ ./core/
COPY worker/ ./worker/

RUN uv sync --frozen --no-dev --no-install-project --package anneal-worker && \
    uv sync --frozen --no-dev --package anneal-worker

FROM python:3.14-slim

WORKDIR /app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin anneal

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/core/src /app/core/src
COPY --from=builder /app/worker/src /app/worker/src
COPY --from=builder /app/shared/src /app/shared/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/core/src:/app/worker/src:/app/shared/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANNEAL_TRIGGER_NOW=true

USER anneal

CMD ["python", "-m", "worker.main"]
