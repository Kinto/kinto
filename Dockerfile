# Mozilla Kinto server
FROM python:3.10-bullseye AS python-builder
RUN python -m venv /opt/venv
ARG KINTO_VERSION=1
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_KINTO=${KINTO_VERSION} \
    PATH="/opt/venv/bin:$PATH"
# At this stage we only fetch and build all dependencies.

# Pull kinto-admin before building kinto so we can cache it
WORKDIR /kinto-admin
COPY kinto/plugins/admin kinto/plugins/admin
COPY scripts/pull-kinto-admin.sh .
RUN bash pull-kinto-admin.sh

WORKDIR /pkg-kinto
COPY constraints.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r constraints.txt
COPY kinto/ kinto/
RUN cp -r /kinto-admin/kinto/plugins/admin/build kinto/plugins/admin/
RUN pip install ".[postgresql,memcached,monitoring]" -c constraints.txt && pip install kinto-attachment kinto-emailer httpie

FROM python:3.10-slim-bullseye
RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app

COPY --from=python-builder /opt/venv /opt/venv

ENV KINTO_INI=/etc/kinto/kinto.ini \
    PORT=8888 \
    PATH="/opt/venv/bin:$PATH" \
    PROMETHEUS_MULTIPROC_DIR="/tmp/metrics"

RUN kinto init --ini $KINTO_INI --host 0.0.0.0 --backend=memory --cache-backend=memory

WORKDIR /app
USER app

# Run database migrations and start the kinto server
CMD ["sh", "-c", "kinto migrate --ini $KINTO_INI && kinto start --ini $KINTO_INI --port $PORT"]
