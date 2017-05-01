.. _install:

Install Kinto
#############

To get the most out of the :ref:`tutorials <tutorials>`, it helps to
have a Kinto server running. You can use the Mozilla demo server, or
set up your own instance.

.. contents::
    :local:

.. _run-kinto-mozilla-demo:

Mozilla demo server
===================

A Kinto instance is running at https://kinto.dev.mozaws.net/v1/

It should be enough to get started, but the records are flushed every
day at 7:00 AM UTC.


.. _deploy-an-instance:

Deploying on cloud providers
============================

You want to get started with a working online Kinto server right now? You've
got a few different options:

.. |heroku-button| image:: ../images/heroku-button.png
   :target: https://dashboard.heroku.com/new?button-url=https%3A%2F%2Fgithub.com%2FKinto%2Fkinto-heroku&template=https%3A%2F%2Fgithub.com%2FKinto%2Fkinto-heroku>
   :alt: Deploy on Heroku

.. |scalingo-button| image:: ../images/scalingo-button.svg
   :target: https://my.scalingo.com/deploy?source=https://github.com/Kinto/kinto-scalingo
   :alt: Deploy on Scalingo

.. |alwaysdata-button| image:: ../images/alwaysdata-button.svg
   :target: https://kinto.github.io/kinto-alwaysdata/
   :alt: Deploy on Alwaysdata

+----------------+------------------------------------------------+------------------------+
| Provider       | What you get / Plan                            | Link / Install button  |
+================+================================================+========================+
| Heroku         | Free plan for up to 10.000 rows on PostgreSQL. |  |heroku-button|       |
+----------------+------------------------------------------------+------------------------+
| Scalingo       | 1 month free trial with 512MB RAM, 512MB       |  |scalingo-button|     |
|                | storage and a PostgreSQL database.             |                        |
+----------------+------------------------------------------------+------------------------+
| Alwaysdata     | Open an account and deploy Kinto on it.        |  |alwaysdata-button|   |
|                | 10 MB of free storage.                         |                        |
+----------------+------------------------------------------------+------------------------+


.. _run-kinto-docker:

Using Docker
============

If you have `Docker <https://docker.com/>`_, *Kinto* can be started locally with a single command:

::

    sudo docker run -p 8888:8888 kinto/kinto-server

The server should now be running on http://localhost:8888


Environment variables
---------------------

It is possible to specify most Kinto settings through environment variables.
For example, using an environment file:

.. code-block:: shell

    # kinto.env
    KINTO_USERID_HMAC_SECRET = tr0ub4d@ur
    KINTO_BATCH_MAX_REQUESTS = 200
    # KINTO_STORAGE_BACKEND = kinto.core.storage.postgresql
    # KINTO_STORAGE_URL = postgres://user:pass@localhost/kintodb

And running the container with:

::

    docker run --env-file ./kinto.env -p 8888:8888 kinto/kinto-server

The server should now be running on http://localhost:8888


Custom configuration file
-------------------------

Sometimes it is more convenient to specify the settings via an INI file.

Suppose you have a settings file locally in ``config/dev.ini``. With Docker, you can mount
local folders into the container. Therefore you can mount the ``config`` folder
into the container on ``/etc/kinto``, and specify that ``/etc/kinto/dev.ini`` is your
config file:

.. code-block:: shell

    sudo docker run -v `pwd`/config:/etc/kinto \
                    -e KINTO_INI=/etc/kinto/dev.ini \
                    -p 8888:8888 \
                    kinto/kinto-server


Using Docker Compose
--------------------

A sample configuration for `Docker Compose <http://docs.docker.com/compose/>`_
is provided in the Kinto repository. It pulls the *Kinto* container and runs it
with a *PostgreSQL* container.

::

    wget https://raw.githubusercontent.com/Kinto/kinto/master/docker-compose.yml
    sudo docker-compose up

Now you can:

- Stop the containers with ``docker-compose stop``.
- Start the containers with ``docker-compose up -d`` (``-d`` is for background/daemon).
- Connect to PostgreSQL service with ``docker-compose exec --user postgres db psql``.
- Install a plugin into kinto with ``docker-compose exec web pip3 install kinto-pusher``.
- Inspect the kinto config file with ``docker-compose exec web cat /etc/kinto/kinto.ini``.

If you want to change the settings, you need to mount a custom settings file
into the *Kinto* container. Hopefully Docker Compose lets you do that the exact
same way Docker does (assuming you have created the config file ``./config/kinto.ini``):

::

    db:
      image: postgres
      environment:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
    web:
      image: kinto/kinto-server
      links:
       - db
      ports:
       - "8888:8888"
      volumes:
        - ./config:/etc/kinto

Note that with the above example,``config/kinto.ini`` must define the following options
(where ``postgres:postgres`` is the user/password you defined in ``docker-compose.yml``):

::

    kinto.cache_backend = kinto.core.cache.postgresql
    kinto.cache_url = postgres://postgres:postgres@db/postgres
    kinto.storage_backend = kinto.core.storage.postgresql
    kinto.storage_url = postgres://postgres:postgres@db/postgres
    kinto.permission_backend = kinto.core.permission.postgresql
    kinto.permission_url = postgres://postgres:postgres@db/postgres

.. _run-kinto-python:

Using the Python package
========================

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

    dnf install libffi-devel openssl-devel python-devel python-virtualenv

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

    pip install --upgrade pip
    pip install kinto

::

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
`later on <https://kinto.readthedocs.io/en/latest/configuration/settings.html#backends>`_.

The server should now be running with the default configuration on http://localhost:8888

In order to specify a particular settings file: ::

    make serve SERVER_CONFIG=config/dev.ini

With `make`, it is also possible to specify arguments from environment variables: ::

    export SERVER_CONFIG=config/dev.ini

    make serve -e


See our :ref:`dedicated section about contributing <how-to-contribute>`!


Kinto Admin
-----------

In order to run a local :github:`Kinto Admin UI <Kinto/kinto-admin>` from a cloned
repo, the ``npm`` command must be available in order to build it with ::

    make build-kinto-admin


Go further
==========

Some suggestions for the next steps:

* :ref:`Follow our tutorials <tutorials>`
* :ref:`Configure PostgreSQL <postgresql-install>`
* :ref:`Run in production <run-production>`
