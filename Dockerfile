# Mozilla Kinto server
FROM python:3.7-slim

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app
WORKDIR /app
COPY . /app

ENV KINTO_INI /etc/kinto/kinto.ini
ENV PORT 8888

# Install build dependencies, build the virtualenv and remove build
# dependencies all at once to build a small image.
RUN \
    apt-get update; \
    apt-get install -y gcc libpq5 curl libssl-dev libffi-dev libpq-dev gnupg2; \
    curl -sL https://deb.nodesource.com/setup_10.x | bash -; \
    apt-get install -y nodejs; \
    cd kinto/plugins/admin; npm install; npm run build; \
    pip3 install -e /app[postgresql,memcached,monitoring] -c /app/requirements.txt; \
    pip3 install kinto-attachment kinto-emailer kinto-elasticsearch kinto-portier kinto-redis; \
    kinto init --ini $KINTO_INI --host 0.0.0.0 --backend=memory --cache-backend=memory; \
    apt-get purge -y -qq gcc libssl-dev libffi-dev libpq-dev curl nodejs; \
    apt-get autoremove -y -qq; \
    apt-get clean -y

USER app
# Run database migrations and start the kinto server
CMD kinto migrate --ini $KINTO_INI && kinto start --ini $KINTO_INI --port $PORT
