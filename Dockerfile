FROM python:2.7
WORKDIR /code
ADD . /code
RUN pip install cliquet[postgresql,monitoring]
RUN pip install -e .
CMD kinto --ini config/kinto.ini start
