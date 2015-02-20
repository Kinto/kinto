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

Configuration can be changed to persist the records in different storage engines.


In-Memory
---------

Useful for development or testing purposes, but records are lost after each server restart.

In configuration::

    cliquet.storage_url.storage_backend = cliquet.storage.memory


Redis
-----

Useful for very low server load, but won't scale since records sorting and filtering
are performed in memory.

In configuration::

    cliquet.storage_backend = cliquet.storage.redis

*(Optional)* Instance location URI can be customized::

    cliquet.storage_url = redis://localhost:6379/0


PostgreSQL
----------

Recommended in production (*requires PostgreSQL 9.3 or higher*).

Install PostgreSQL client headers::

    sudo apt-get install libpq-dev

Install cliquet with related dependencies::

    pip install cliquet[postgresql]

In configuration::

    cliquet.storage_backend = cliquet.storage.postgresql

*(Optional)* Instance location URI can be customized::

    cliquet.storage_url = postgres://user:pass@db.server.lan:5432/dbname


*(Optional*) Memory usage parameters::

    # Number of connections * postgres work_mem
    pool_minconn = 4
    pool_maxconn = 10
    # Max number of records * number of web workers
    max_fetch_size = 10000



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
