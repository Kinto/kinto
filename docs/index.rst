Cliquet documentation
=====================

Cliquet is a toolkit, built on top of `Cornice <https://cornice.rtfd.org>`_ to
ease the creation of HTTP services.

Cliquet doesn't try to be a framework: the generated APIs are well defined and
follow a specific protocol. The goal is to produce APIs which are easy to
consume for the clients and follow some well known patterns.

It's an implementation of a series of opinionated good practices we follow at
Mozilla.

It is built around the notion of resources: you define a set of resources and
cliquet generates the APIs out of that.

It handles the storage for you (by default in PostgreSQL) and proposes a set of
APIs we found the be useful.

Cliquet is built on the shoulders of giants: Pyramid is doing all the heavy
HTTP stuff and Postgres for the storage.

Here are the steps you need to follow to use cliquet:

1. Think about your data model;
2. Translate this model into a resource (it's a class);
3. XXX;
4. Profit!

.. toctree::
   :maxdepth: 2

   model
   authentication
   api
   batch
   utilities
   timestamps
   versionning
   backoff
   errors


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

