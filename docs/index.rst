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

Tutorials
=========

Sometimes it is easier to get started by following a
tutorial. :ref:`Learn how to store, sync and share your data <tutorials>`.

Using the HTTP API
==================

Interaction with a *Kinto* instance happens at some point using HTTP calls.
Find all you need to know via the links below:

- Buckets: :ref:`Working with buckets <buckets>`
- Collections : :ref:`Handling collections <collections>` |
  :ref:`Sending and retrieving records <records>`
- Permissions: :ref:`Understanding permissions <permissions>` |
  :ref:`Handling groups <groups>`

Deployment
==========

- From scratch: :ref:`installation`.
- Deployment: :ref:`Good practices <deployment>` | :ref:`configuration`

Community
=========

- How to contribute: :ref:`Guidelines <contributing>`

Table of content
================

.. toctree::
   :maxdepth: 1

   installation
   tutorials/index
   configuration
   deployment
   permissions
   api/index
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
