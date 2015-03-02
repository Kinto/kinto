FROM python:2.7
WORKDIR /code
ADD . /code
RUN python setup.py develop
CMD pserve config/kinto.ini --reload
