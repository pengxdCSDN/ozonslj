ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
COPY database/postgres ./database/postgres
COPY scripts/create_operator.py ./scripts/create_operator.py

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid 10001 --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
