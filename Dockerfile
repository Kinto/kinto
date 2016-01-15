# Mozilla Kinto server
FROM debian:sid
MAINTAINER Storage Team irc://irc.freenode.net/#kinto

ADD kinto /code/kinto
ADD CHANGELOG.rst README.rst CONTRIBUTORS.rst setup.py MANIFEST.in /code/
ENV KINTO_INI /etc/kinto/kinto.ini

# Install build dependencies, build the virtualenv and remove build
# dependencies all at once to build a small image.
RUN \
    apt-get update; \
    apt-get install -y python3 libpq5; \
    apt-get install -y build-essential git python3-dev python3-setuptools libssl-dev libffi-dev libpq-dev; \
    easy_install3 pip; \
    pip install cliquet[postgresql,monitoring]; \
    pip install -e /code; \
    kinto --ini $KINTO_INI --backend=memory init; \
    apt-get remove -y -qq build-essential git python3-dev libssl-dev libffi-dev libpq-dev; \
    apt-get autoremove -y -qq; \
    apt-get clean -y

# Run database migrations and start the kinto server
CMD kinto --ini $KINTO_INI migrate && kinto --ini $KINTO_INI start
