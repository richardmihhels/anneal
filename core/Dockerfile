FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY shared/ ./shared/
COPY core/ ./core/

RUN uv sync --frozen --no-dev --no-install-project --package anneal-core && \
    uv sync --frozen --no-dev --package anneal-core

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/core/src /app/core/src
COPY --from=builder /app/shared/src /app/shared/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/core/src:/app/shared/src" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000"]
