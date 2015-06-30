.. _installation:

Installation
############

*Kinto* is based on top of the `cliquet <https://cliquet.rtfd.org>`_ project, and
as such, please refer to cliquet's documentation if details seem to be missing
here.


Run locally
===========

For development
---------------

By default, *Kinto* persists the records and internal cache in a PostgreSQL
database.

The default configuration will connect to the ``postgres`` database on
``localhost:5432``, with user/password ``postgres``/``postgres``.
See more details below about installation and setup of PostgreSQL.

::

    make serve


Using Docker
------------

Kinto uses `Docker Compose <http://docs.docker.com/compose/>`_, which takes
care of running and connecting PostgreSQL:

::

    docker-compose up


Authentication
--------------

By default, Kinto relies on Firefox Account OAuth2 Bearer tokens to authenticate
users.

See `cliquet documentation <http://cliquet.readthedocs.org/en/latest/configuration.html#authentication>`_
to configure authentication options.


Run in production
=================

*Kinto* is a usual python application.

Recommended settings for production are listed :ref:`in a dedicated section
<run-production>`, and another gives some :ref:`insights about deployment strategies.
<deployment>`.


Install and setup PostgreSQL
============================

 (*requires PostgreSQL 9.3 or higher*).

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

    kinto=$(sudo docker run -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 kinto-db)

    ...

    sudo docker stop $kinto


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew update
    brew install postgresql

Create the initial database:

::

    initdb /usr/local/var/postgres


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
