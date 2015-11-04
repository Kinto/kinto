FROM python:2.7
WORKDIR /code
ADD . /code
RUN pip install -e .[postgresql,monitoring]
CMD pserve config/kinto.ini --reload
