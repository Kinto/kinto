.. _get-started:

Get started
###########

Use the demo server or run your own Kinto, and follow our :ref:`tutorials <tutorials>`
for the JavaScript client or the raw HTTP API!

.. contents::
    :local:


.. _run-kinto-mozilla-demo:

Mozilla demo server
===================

A Kinto instance is running at https://kinto.dev.mozaws.net/v1/

It should be enough to get started, but the records are flushed every
day at 7:00 AM UTC.


.. _deploy-an-instance-on-heroku:

Deploy an instance on Heroku
============================

You want to get started with a working online Kinto server right now?

.. image:: https://www.herokucdn.com/deploy/button.png
   :target: https://dashboard.heroku.com/new?button-url=https%3A%2F%2Fgithub.com%2FKinto%2Fkinto-heroku&template=https%3A%2F%2Fgithub.com%2FKinto%2Fkinto-heroku>
   :alt: Deploy on Heroku

You have got a free plan for up to 10000 rows.

.. _deploy-an-instance-on-scalingo:

Deploy an instance on Scalingo
==============================

You want to get started with a working online Kinto server right now?

.. image:: https://cdn.scalingo.com/deploy/button.svg
   :target: https://my.scalingo.com/deploy?source=https://github.com/Scalingo/kinto-scalingo
   :alt: Deploy on Scalingo

You have got a free plan for a 512MB (512MB RAM, 512MB on disk) PostgreSQL database.

.. _run-kinto-docker:

Using Docker
============

If you have `Docker <https://docker.com/>`_, *Kinto* can be started locally with a single command:

::

    sudo docker run -p 8888:8888 kinto/kinto-server

The server should now be running on http://localhost:8888


Custom configuration
--------------------

It is possible to specify every Kinto setting through environment variables.
For example, using an environment file:

.. code-block:: shell

    # kinto.env
    KINTO_USERID_HMAC_SECRET = tr0ub4d@ur
    KINTO_BATCH_MAX_REQUESTS = 200
    # KINTO_STORAGE_BACKEND = cliquet.storage.postgresql
    # KINTO_STORAGE_URL = postgres://user:pass@localhost/kintodb

And running the container with:

::

    docker run --env-file ./kinto.env -p 8888:8888 kinto/kinto-server

The server should now be running on http://localhost:8888


Using Docker Compose
--------------------

A sample configuration for `Docker Compose <http://docs.docker.com/compose/>`_
is provided in the Kinto repository. It pulls the *Kinto* container and runs it
with a *PostgreSQL* container.

::

    wget https://raw.githubusercontent.com/Kinto/kinto/master/docker-compose.yml
    sudo docker-compose up


.. _run-kinto-python:

Using the Python package
========================

Installing Python 2.7/3.4+ on Ubuntu
------------------------------------

Use the following commands to install prerequisites for Python:

::

    sudo apt-get install build-essential checkinstall
    sudo apt-get install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev

Download Python 2.7 using the following commands. You can also download the latest version in place of the one specified below.

::

    cd ~/Downloads/
    wget http://wwww.python.org/ftp/python/2.7.5/Python-2.7.5.tgz

Extract and go to the directory.

::

    tar -xvf Python-2.7.5.tgz
    cd Python-2.7.5

Now, install using the following commands:

::

    ./configure
    make
    sudo make install



Backends
--------

Postgresql
----------

To install the server locally, use the following command

::

    sudo apt-get update
    sudo apt-get install postgresql postgresql-contrib

Redis
-----

Use the following commands to install the prerequisites and dependencies for Redis

::

    sudo apt-get update
    sudo apt-get install build-essential
    sudo apt-get install tcl8.5

Download Redis, untar it and move into that directory using the following commands

::

    wget http://download.redis.io/releases/redis-stable.tar.gz
    tar xzf redis-stable.tar.gz
    cd redis-stable

Install using the following commands

::

    make
    make test
    sudo make install

To access the script move into the utils directory and run the install script

::

    cd utils
    sudo ./install_server.sh

As the script runs, you can choose the default options by pressing enter. Once the script completes, the redis-server will be running in the background.  
You can start and stop redis with the following commands

::

    sudo service redis_6379 start
    sudo service redis_6379 stop

You can access the redis database by typing
::
    redis-cli

You now have redis installed and running. The prompt will look like this:
::
    redis 127.0.0.1:6379>


System requirements
-------------------

Depending on the platform and chosen configuration, some libraries or
extra services are required.

The following commands will install necessary tools for cryptography
and Python packaging like `Virtualenv <https://virtualenv.pypa.io/>`_.

Linux
'''''

On Debian / Ubuntu based systems::

    apt-get install libffi-dev libssl-dev python-dev python-virtualenv

On RHEL-derivatives::

    apt-get install libffi-devel openssl-devel python-devel python-virtualenv

OS X
''''

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew install libffi openssl pkg-config python

    pip install virtualenv


Quick start
-----------

By default, for convenience, *Kinto* persists the records, permissions and
internal cache in a **volatile** memory backend. On every restart, the server
will lose its data, and multiple processes are not handled properly.

But it should be enough to get started!


Create a Python isolated environment (*optional*):

::

    virtualenv env/
    source env/bin/activate

Then install the package using the default configuration:

::

    pip install kinto
    kinto init
    kinto migrate
    kinto start

The server should now be running on http://localhost:8888


.. _run-kinto-from-source:

From sources
============

If you plan on contributing, this is the way to go!

This will install every necessary packages to run the tests, build the
documentation etc.

Make sure you have the system requirements listed in the
:ref:`Python package <run-kinto-python>` section.

::

    git clone https://github.com/Kinto/kinto.git
    cd kinto/
    make serve

During the installation, you will be asked which backend you would like to use:

::

    $ Select the backend you would like to use: (1 - postgresql, 2 - redis, default - memory)

If you don't know, just push "enter" to choose the default Memory backend.
You can always change your backend selection
`later on <https://kinto.readthedocs.org/en/latest/configuration/settings.html#backends>`_.

The server should now be running with the default configuration on http://localhost:8888

In order to specify a particular settings file: ::

    make serve SERVER_CONFIG=config/dev.ini

With `make`, it is also possible to specify arguments from environment variables: ::

    export SERVER_CONFIG=config/dev.ini

    make serve -e


See :ref:`dedicated section about contributing <contributing>`!


Go further
==========

Some suggestions for the next steps:

* :ref:`Follow our tutorials <tutorials>`
* :ref:`Configure PostgreSQL <postgresql-install>`
* :ref:`Run in production <run-production>`
