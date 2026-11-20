FROM ghcr.io/astral-sh/uv:0.13.9 AS uv

FROM python:3.15-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.15-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/backend" \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy
WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --create-home appuser \
    && mkdir -p /app/docs /app/data \
    && chown -R appuser:appuser /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=uv /uv /usr/local/bin/uv
COPY --chown=appuser:appuser pyproject.toml uv.lock .python-version ./
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser scripts/check_numeric_policy.py ./scripts/check_numeric_policy.py
COPY --chown=appuser:appuser scripts/render-start.sh ./scripts/render-start.sh
COPY --chown=appuser:appuser scripts/render_wsgi.py ./scripts/render_wsgi.py
COPY --chown=appuser:appuser scripts/serve_backend.py ./scripts/serve_backend.py

USER appuser
EXPOSE 8000

# Gunicorn trusts secure-scheme headers from loopback; do not broaden that trust.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; h=os.environ.get('ALLOWED_HOSTS','localhost').split(',')[0].strip().lstrip('.'); h='localhost' if h=='*' else h; r=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/ready/', headers={'Host':h,'X-Forwarded-Proto':'https'}), timeout=3); assert r.status == 200"

CMD ["python", "scripts/serve_backend.py"]
