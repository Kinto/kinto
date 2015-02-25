Cliquet toolkit
===============


|travis| |readthedocs|

.. |travis| image:: https://travis-ci.org/mozilla-services/cliquet.svg?branch=master
    :target: https://travis-ci.org/mozilla-services/cliquet

.. |readthedocs| image:: https://readthedocs.org/projects/cliquet/badge/?version=latest
    :target: http://cliquet.readthedocs.org/en/latest/
    :alt: Documentation Status



API
===

* `API Design proposal
  <https://github.com/mozilla-services/cliquet/wiki/API-Design-proposal>`_
* `Online documentation <http://cliquet.readthedocs.org/en/latest/>`_



Run locally
===========

By default, cliquet persists its sessions and its records inside a `Redis <http://redis.io/>`_
database, so it has to be installed first (see the "Install Redis" section below for
more on this).

Once Redis is installed:

::

    make serve


Storage backend
===============

Install PostgreSQL
==================

Client only
-----------

Install PostgreSQL client headers::

    sudo apt-get install libpq-dev

Install cliquet with related dependencies::

    pip install cliquet[postgresql]


With Docker
-----------

::
    postgres=$(sudo docker run -d -p 5432:5432 postgres)

Create the test database::

 $ psql -h localhost -U postgres -W
 #> CREATE DATABASE "testdb";

Tag and save the container::

    sudo docker commit $postgres cliquet-empty

Stop the container::

    sudo docker stop $postgres

In the future ::

    cliquet=$(sudo docker run -d -p 5432:5432 cliquet-empty)

    ...

    sudo docker stop $cliquet


Install Redis
=============

Linux
-----

On debian / ubuntu based systems::

    apt-get install redis-server


or::

    yum install redis

OS X
----

Assuming `brew <http://brew.sh/>`_ is installed, Redis installation becomes:

::

    brew install redis

To restart it (Bug after configuration update)::

    brew services restart redis


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

:note:

    A dedicated database ``testdb`` is used for PostgreSQL storage tests,
    make sure it's created before running the tests.
