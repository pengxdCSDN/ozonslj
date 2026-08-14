ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ACR 每次发布传入不同版本值，便于从镜像元数据确认部署版本；不包含凭据或业务数据。
ARG RELEASE_REVISION=development
ENV OZONSLJ_RELEASE_REVISION=${RELEASE_REVISION}

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
COPY database/postgresql_schema.sql ./database/postgresql_schema.sql
COPY database/migrations ./database/migrations
COPY scripts/create_operator.py ./scripts/create_operator.py

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid 10001 --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
