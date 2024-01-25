# Mozilla Kinto server

FROM node:lts-bullseye-slim as node-builder
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl
COPY scripts/build-kinto-admin.sh .
COPY /kinto/plugins/admin ./kinto/plugins/admin
RUN bash build-kinto-admin.sh

FROM python:3.10-slim-bullseye as python-builder
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install kinto-attachment kinto-emailer httpie

FROM python:3.10-slim-bullseye
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev
RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app

WORKDIR /app
COPY --from=python-builder /opt/venv /opt/venv
COPY . /app
COPY --from=node-builder /kinto/plugins/admin/build ./kinto/plugins/admin/build

ARG KINTO_VERSION=1
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_KINTO=${KINTO_VERSION} \
    KINTO_INI=/etc/kinto/kinto.ini \
    PORT=8888 \
    PATH="/opt/venv/bin:$PATH"

RUN \
    pip install -e /app[postgresql,memcached,monitoring] -c /app/requirements.txt && \
    kinto init --ini $KINTO_INI --host 0.0.0.0 --backend=memory --cache-backend=memory

USER app
# Run database migrations and start the kinto server
CMD kinto migrate --ini $KINTO_INI && kinto start --ini $KINTO_INI --port $PORT
