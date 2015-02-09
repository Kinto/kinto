Readinglist
===========

Reading list is a service that aims to synchronize a list of articles URLs
between a set of devices owned by a same account.

|travis| |readthedocs|

.. |travis| image:: https://travis-ci.org/mozilla-services/readinglist.svg?branch=master
    :target: https://travis-ci.org/mozilla-services/readinglist

.. |readthedocs| image:: https://readthedocs.org/projects/readinglist/badge/?version=latest
    :target: http://readinglist.readthedocs.org/en/latest/
    :alt: Documentation Status

API
===

* `API Design proposal
  <https://github.com/mozilla-services/readinglist/wiki/API-Design-proposal>`_
* `Online documentation <http://readinglist.readthedocs.org/en/latest/>`_


Run locally
===========

By default, readinglist persists its records inside a `Redis
<http://redis.io/>`_  database, so it has to be installed first (see the
"Install Redis" section below for more on this).

Once Redis is installed:

::

    make serve


Configuration can be changed to persist everything in memory (not
recommended). To do that, `conf/readinglist.ini` file should have the
following config::

    readinglist.storage_backend = readinglist.storage.memory



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




Run tests
=========

::

    make tests
