.. include:: ../README.rst

.. figure :: images/logo.svg
    :align: center

    `Kinto-Un <http://dragonball.wikia.com/wiki/Flying_Nimbus>`_ is a magical,
    yellow cloud that serves as a way of transportation.


In short
========

It's as simple as that:

1. Pick up a name for your records collection;
2. Push the records on the server;
3. Pull the records from the server (ordered, filtered, paginated)

The server doesn't impose anything about the records data model.

*Kinto* is based on top of `cliquet <http://cliquet.readthedocs.org>`_.

Tutorial
========

Sometimes it is easier to get started by following a tutorial. Learn how to
store, manage and sync your data.

Using the HTTP API
==================

Interaction with a *Kinto* instance happens at some point using HTTP calls.
Find all you need to know via le links below:

- Buckets: Working with buckets;
- Collections : Handling collections | Sending and retrieving records;
- Permissions: Uderstanding permissions | Handling groups

Deployment
==========

- From scratch: Installation
- Deployment: Good practices | Configuration

Community
=========

- Contribution: Guidelines
- Keeping posted: 


Table of content
================

.. toctree::
   :maxdepth: 2

   api/index
   permissions
   installation
   configuration
   deployment
   contributing
   changelog
