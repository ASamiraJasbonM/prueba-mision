# Verification/toolbox image only, never the application runtime.
FROM postgres:16-alpine
RUN apk add --no-cache gnupg curl
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_NO_DEV=1 UV_NO_SYNC=1
COPY pyproject.toml uv.lock .python-version /build/
RUN cd /build && uv sync --frozen --no-dev --python 3.12
WORKDIR /workspace
ENTRYPOINT []
