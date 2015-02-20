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

By default, cliquet persists its records inside a `Redis
<http://redis.io/>`_  database, so it has to be installed first (see the
"Install Redis" section below for more on this).

Once Redis is installed:

::

    make serve


Configuration can be changed to persist everything in memory (not
recommended). To do that, `conf/cliquet.ini` file should have the
following config::

    cliquet.storage_backend = cliquet.storage.memory



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
