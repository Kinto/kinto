############################
# Builder stage
############################
FROM python:3.10-bullseye AS python-builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_CACHE_DIR=/opt/uv-cache \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build

# Copy dependency metadata first for better layer caching
COPY pyproject.toml uv.lock LICENSE ./

# Copy project source
COPY kinto/ kinto/

# Build kinto-admin
WORKDIR /kinto-admin
COPY kinto/plugins/admin kinto/plugins/admin
COPY scripts/pull-kinto-admin.sh .
RUN bash pull-kinto-admin.sh
# Copy built admin into project
RUN cp -r /kinto-admin/kinto/plugins/admin/build /build/kinto/plugins/admin/
WORKDIR /build

# Install dependencies into /opt/venv
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync --locked --no-dev \
        --link-mode=copy \
        --extra postgresql \
        --extra memcached \
        --extra redis \
        --extra monitoring \
        --extra container \
        --no-editable

############################
# Runtime stage
############################
FROM python:3.10-slim-bullseye

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app

# Copy virtualenv from builder
COPY --from=python-builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    KINTO_INI=/etc/kinto/kinto.ini \
    PORT=8888 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/metrics

# Provide a default config at build time
RUN mkdir -p /etc/kinto && chown -R app:app /etc/kinto
RUN kinto init --ini /etc/kinto/kinto.ini --backend=memory --cache-backend=memory

WORKDIR /app
USER app
# Migrate and start the server
CMD ["sh", "-c", "kinto migrate --ini $KINTO_INI && kinto start --ini $KINTO_INI --port $PORT"]