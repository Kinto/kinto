# Mozilla Kinto server
FROM stackbrew/debian:sid
MAINTAINER Storage Team irc://irc.freenode.net/#kinto
WORKDIR /home/kinto
ADD . /home/kinto

# Install build dependencies, build the virtualenv and remove build
# dependencies all at once to build a small image.
RUN \
    apt-get update; \
    apt-get install -y python3 python3-pip python3-venv git build-essential make; \
    apt-get install -y python3-dev libssl-dev libffi-dev libpq5 libpq-dev; \
    python3 -m venv /home/kinto; \
    bin/pip install cliquet[postgresql,monitoring]; \
    bin/pip install -e .; \
    bin/kinto --ini /etc/kinto/kinto.ini --backend=memory init; \
    apt-get remove -y -qq git build-essential git make python3-pip python3-venv libssl-dev libffi-dev libpq-dev python3-dev; \
    apt-get autoremove -y -qq; \
    apt-get clean -y

# Run database migrations and start the kinto server
CMD bin/kinto --ini /etc/kinto/kinto.ini migrate && bin/kinto --ini /etc/kinto/kinto.ini start
