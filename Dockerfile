# Mozilla Kinto server
FROM stackbrew/debian:sid

MAINTAINER Storage Team irc://irc.freenode.net/#kinto

RUN \
    apt-get update; \
    apt-get install -y python3 python3-pip python3-venv git build-essential make; \
    apt-get install -y python3-dev libssl-dev libffi-dev libpq5 libpq-dev; \
    python3 -m venv /home/kinto; \
    /home/kinto/bin/pip install cliquet[postgresql,monitoring] kinto; \
    /home/kinto/bin/kinto --ini /home/kinto/config/kinto.ini --backend=memory init; \
    apt-get remove -y -qq git build-essential git make python3-pip python3-venv libssl-dev libffi-dev libpq-dev; \
    apt-get autoremove -y -qq; \
    apt-get clean -y

WORKDIR /home/kinto

# run the test
CMD bin/kinto migrate && bin/kinto start
