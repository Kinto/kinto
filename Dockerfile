# Mozilla Kinto server
FROM python:3.5
ADD kinto /code/kinto
ADD README.rst /code/
ADD CHANGELOG.rst /code/
ADD CONTRIBUTORS.rst /code/
ADD setup.py /code/
ADD MANIFEST.in /code/
RUN pip install cliquet[postgresql,monitoring]
RUN pip install -e /code
ENV KINTO_INI /etc/kinto/kinto.ini
RUN kinto --ini $KINTO_INI --backend=memory init
CMD kinto --ini $KINTO_INI migrate && kinto --ini $KINTO_INI start
