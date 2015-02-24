Kinto
=====

Kinto is a server allowing you to store and synchronize arbitrary data on "the
cloud", attached to your Firefox account.

It's as simple as that:

1. Decide on model for your data;
2. Push the data on the server;
3. Ask the server for the data (ordered, fileterd, paginated) and allow
   synchronisation.

The server doesn't impose anything about the client data model.

|travis| |readthedocs|

.. |travis| image:: https://travis-ci.org/mozilla-services/kinto.svg?branch=master
    :target: https://travis-ci.org/mozilla-services/kinto

.. |readthedocs| image:: https://readthedocs.org/projects/kinto/badge/?version=latest
    :target: http://kinto.readthedocs.org/en/latest/
    :alt: Documentation Status


Run locally
===========

Kinto is based on top of the `cliquet <https://cliquet.rtfd.org>`_ project, and
as such, please follow the installation insstruction there to get started.

::

    make serve


Run tests
=========

::

    make tests
