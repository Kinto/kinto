.. _installation:

Installation
############

*Kinto* is meant to be relatively straightforward to install, and we've
provided fairly extensive documentation to get you up and running. That said,
some dependencies might make the process harder than it should be -
we've got some notes on crypto libraries and PostgreSQL at the end of this page.

Run locally
===========

To test Kinto quickly
---------------------

In general, in order to run Kinto, it is as simple as running the following
commands::

    pip install kinto
    wget https://raw.githubusercontent.com/Kinto/kinto/master/config/kinto.ini
    pserve kinto.ini

For development
---------------

By default, for convenience, *Kinto* persists the records, permissions and
internal cache in a **volatile** memory backend. On every restart, the server
will loose its data, and multiple processes are not handled properly.

::

    make serve


Using Docker
------------

Kinto uses `Docker Compose <http://docs.docker.com/compose/>`_, which takes
care of running and connecting to a PostgreSQL container:

::

    docker-compose up

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


The instructions below will create a local ``postgres`` database on
``localhost:5432``, with user/password ``postgres``/``postgres``.

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

Install docker:

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


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew update
    brew install postgresql

Create the initial database:

::

    initdb /usr/local/var/postgres
