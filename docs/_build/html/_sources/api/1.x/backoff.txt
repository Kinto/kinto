##################
Backoff indicators
##################

.. _backoff-indicators:

Backoff header on heavy load
============================


A ``Backoff`` header will be added to the success responses (>=200 and
<400) when the server is under heavy load. It provides the client with
a number of seconds during which it should avoid doing unnecessary
requests.

::

    Backoff: 30

.. note::

    The back-off time is configurable on the server.

.. note::

    In other implementations at Mozilla, there was
    ``X-Weave-Backoff`` and ``X-Backoff`` but the ``X-`` prefix for
    header `has been deprecated since
    <http://tools.ietf.org/html/rfc6648>`_.


Retry-After indicators
======================

A ``Retry-After`` header will be added if response is an error (>=500).
See more details about :ref:`error responses <error-responses>`.
