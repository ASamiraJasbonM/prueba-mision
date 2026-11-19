# syntax=docker/dockerfile:1
# Digests freeze the complete multi-platform image indexes.
FROM node:22-bookworm-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS builder
WORKDIR /app
# Keep dependency installation cached until the npm lockfile changes.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY . .
ARG API_URL=/api/
ARG CONFIGURATION=production
# Generate environment/CSP only inside this build stage; repository sources stay intact.
RUN node docker/configure-build.mjs "$API_URL" "$CONFIGURATION" \
    && npm run build -- --configuration="$CONFIGURATION" \
    && node docker/finalize-index.mjs \
    && test -s dist/datapulse/browser/index.html

# Alpine 3.24 base; require the patched nginx package below.
FROM nginxinc/nginx-unprivileged:stable-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03 AS runtime
# Apply available security fixes from the same Alpine branch before dropping root.
# Refresh this cached layer/base digest when the mandatory Trivy gate reports new CVEs.
USER root
# nginx 1.30.7-r0 fixes CVE-2026-113425, 121810, 123007, 123633,
# 118899 and 123634. The bound also invalidates the previous cached layer.
# These unused dynamic modules pin nginx to the vulnerable vendor build.
RUN apk del nginx-module-geoip nginx-module-image-filter nginx-module-njs nginx-module-xslt \
    && apk upgrade --no-cache \
    && apk add --no-cache 'nginx>=1.30.7-r0'
WORKDIR /usr/share/nginx/html
ENV BACKEND_URL=http://backend:8000 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENVSUBST_FILTER=^(BACKEND_URL|NGINX_LOCAL_RESOLVERS)$
# Only static output/configuration crosses from the Node stage into the runtime.
COPY --from=builder --chown=nginx:nginx /app/dist/datapulse/browser/ ./
COPY --from=builder --chown=nginx:nginx /app/docker/security-headers.conf /etc/nginx/security-headers.conf
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx nginx.conf /etc/nginx/templates/default.conf.template
COPY --chmod=755 docker/14-validate-backend.sh /docker-entrypoint.d/14-validate-backend.sh
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3     CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
STOPSIGNAL SIGQUIT
CMD ["nginx", "-g", "daemon off;"]
