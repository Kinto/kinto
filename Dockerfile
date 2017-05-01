# Mozilla Kinto server
FROM debian:sid
MAINTAINER Storage Team irc://irc.freenode.net/#kinto

ADD . /code
ENV KINTO_INI /etc/kinto/kinto.ini

# Install build dependencies, build the virtualenv and remove build
# dependencies all at once to build a small image.
RUN \
    apt-get update; \
    apt-get install -y python3 python3-setuptools python3-pip libpq5; \
    apt-get install -y build-essential git python3-dev libssl-dev libffi-dev libpq-dev; \
    apt-get install -y nodejs; \
    npm install kinto/plugins/admin; \
    npm run build kinto/plugins/admin; \
    pip3 install -e /code[postgresql,monitoring]; \
    pip3 install kinto-pusher kinto-fxa kinto-attachment ; \
    kinto init --ini $KINTO_INI --host 0.0.0.0 --backend=memory; \
    apt-get remove -y -qq build-essential git python3-dev libssl-dev libffi-dev libpq-dev; \
    apt-get autoremove -y -qq; \
    apt-get clean -y

# Run database migrations and start the kinto server
CMD kinto migrate --ini $KINTO_INI && kinto start --ini $KINTO_INI
