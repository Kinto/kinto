# Mozilla Kinto server
FROM python:3.5
WORKDIR /code
ADD . /code
RUN pip install cliquet[postgresql,monitoring]
RUN pip install -e .
RUN kinto --ini /etc/kinto/kinto.ini --backend=memory init
CMD kinto --ini /etc/kinto/kinto.ini migrate && kinto --ini /etc/kinto/kinto.ini start
