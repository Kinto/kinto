Documentation
=============

Reading list is a service that aims to synchronize a list of articles URLs
between a set of devices owned by a same account.

.. image:: https://travis-ci.org/mozilla-services/readinglist.svg?branch=master
    :target: https://travis-ci.org/mozilla-services/readinglist

API
===

* `API Design proposal
  <https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal>`_


Run locally
===========

By default, readinglist persists its records inside a `Redis
<http://redis.io/>`_  database, so you need to have it installed (see the
"Install Redis" section below for more on this).

Once you have Redis installed, you just need to do:

::

    make serve


You can also change the configuration to persist everything in memory (not
recommended). To do that, edit your `conf/readinglist.ini` file to have the
following config::

    readinglist.backend = readinglist.backend.memory



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

Assuming you have `brew <http://brew.sh/>`_ installed, use it to install Redis:

::

    brew install redis

If you need to restart it (Bug after configuration update)::

    brew services restart redis




Run tests
=========

::

    make tests
