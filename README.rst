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

::

    make serve


Run tests
=========

::

    make tests
