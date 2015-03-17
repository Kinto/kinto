Kinto
=====

Kinto is a server allowing you to store and synchronize arbitrary data on "the
cloud", attached to your Firefox account.

It's as simple as that:

1. Pick up a name for your records collection;
2. Push the records on the server;
3. Pull the records from the server (ordered, filtered, paginated)

The server doesn't impose anything about the records data model.

|travis| |readthedocs|

.. |travis| image:: https://travis-ci.org/mozilla-services/kinto.svg?branch=master
    :target: https://travis-ci.org/mozilla-services/kinto

.. |readthedocs| image:: https://readthedocs.org/projects/kinto/badge/?version=latest
    :target: http://kinto.readthedocs.org/en/latest/
    :alt: Documentation Status


Run locally
===========

Kinto is based on top of the `cliquet <https://cliquet.rtfd.org>`_ project, and
as such, please refer to cliquet's documentation regarding API and endpoints.


For development
---------------

By default, Kinto persists the records and internal cache in a PostgreSQL
database.

The default configuration will connect to the `postgres` database on
`localhost:5432`, with user/password `postgres/postgres`. See more details
below about installation and setup of PostgreSQL.

::

    $ make serve


Using Docker
------------

Kinto uses `Docker Compose <http://docs.docker.com/compose/>`_, which takes
care of running PostgreSQL:

::

    docker-compose up


Authentication
--------------

By default, Kinto relies on Firefox Account OAuth2 Bearer tokens to authenticate
users.

See `cliquet documentation <http://cliquet.readthedocs.org/en/latest/configuration.html#authentication>`_
to configure authentication options.


Install and setup PostgreSQL
============================

 (*requires PostgreSQL 9.3 or higher*).


Using Docker
------------

::

    docker run -e POSTGRES_PASSWORD=postgres -p 5434:5432 postgres


Linux
-----

On debian / ubuntu based systems:

::

    apt-get install postgresql postgresql-contrib


By default, the `postgres` user has no password and can connect using the
`postgres` system user. The following command will assign it as expected:

::

    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew update
    brew install postgresql

Create the initial database:

::

    initdb /usr/local/var/postgres


Install libffi
==============

Linux
-----

On debian / ubuntu based systems::

    apt-get install libffi-dev


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed, libffi installation becomes:

::

    brew install libffi pkg-config


Run tests
=========

::

    make tests
