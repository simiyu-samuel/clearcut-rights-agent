FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/services/api/src \
    PORT=8080 \
    DATABASE_URL=sqlite:////tmp/clearcut.db \
    STORAGE_ROOT=/tmp/clearcut/uploads

WORKDIR /app

COPY services/api/pyproject.toml services/api/pyproject.toml
COPY services/api/src services/api/src

RUN pip install --upgrade pip \
    && pip install "./services/api[agent]"

RUN useradd --create-home --uid 10001 clearcut \
    && mkdir -p /tmp/clearcut \
    && chown -R clearcut:clearcut /app /tmp/clearcut

USER clearcut

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn clearcut_api.main:app --host 0.0.0.0 --port ${PORT}"]
