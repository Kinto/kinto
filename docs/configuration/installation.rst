.. _installation:

Installation
############

Depending on the platform, and chosen configuration, some libraries or
extra services are required.

.. note::

    If you are just interesting in trying *Kinto*, a pre-installed and pre-configured
    :ref:`demo instance is publicly available <run-kinto-mozilla-demo>`.


.. _crypto-install:

Cryptography libraries
======================

Linux
-----

On Debian / Ubuntu based systems::

    apt-get install libffi-dev libssl-dev

On RHEL-derivatives::

    apt-get install libffi-devel openssl-devel

OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew install libffi openssl pkg-config


.. _postgresql-install:

Install and setup PostgreSQL
============================

(*requires PostgreSQL 9.4 or higher*).

*Kinto* dependencies do not include *PostgreSQL* tooling and drivers by
default. In order to install them, run:

::

    make install-postgres

.. note::

        The ``make`` commands are only available when Kinto was installed from
        sources. The `underlying commands are available on Github
        <https://github.com/Kinto/kinto/blob/684c31c/Makefile#L22-L26>`_.

The instructions in the sections below will help you create a local ``postgres``
database on ``localhost:5432``, with user/password ``postgres``/``postgres``.

Once done, just uncomment the backends lines mentionning *Postgresql* in the
default configuration file :file:`config/kinto.ini`.


Client libraries only
---------------------

Install PostgreSQL client headers::

    sudo apt-get install libpq-dev


Full server
-----------

In Ubuntu/Debian based::

    sudo apt-get install postgresql


By default, the ``postgres`` user has no password and can hence only connect
if ran by the ``postgres`` system user. The following command will assign it:

::

    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"


Server using Docker
-------------------

Install `Docker <https://docker.com/>`_:

On Ubuntu you can do:

::

    sudo apt-get install docker.io

Run the official PostgreSQL container locally:

::

    postgres=$(sudo docker run -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 postgres)

Tag and save the current state with::

    sudo docker commit $postgres kinto-db


In the future, run the tagged version of the container ::

    kintodb=$(sudo docker run -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 kinto-db)

    ...

    sudo docker stop $kintodb


In order to build the Kinto container locally and run it against a PostgreSQL
container, Kinto supports `Docker Compose <http://docs.docker.com/compose/>`_:

::

    docker-compose up


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew update
    brew install postgresql

Create the initial database:

::

    initdb /usr/local/var/postgres
