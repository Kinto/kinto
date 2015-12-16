FROM python:3.5
WORKDIR /code
ADD . /code
RUN pip install cliquet[postgresql,monitoring]
RUN pip install -e .
RUN kinto --backend=memory init
CMD kinto start
