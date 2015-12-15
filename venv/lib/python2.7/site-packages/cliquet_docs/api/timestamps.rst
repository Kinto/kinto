.. _server-timestamps:

#################
Server timestamps
#################

In order to avoid race conditions, each change is guaranteed to 
increment the timestamp of the related collection.
If two changes happen at the same millisecond, they will still have two different
timestamps.

The ``ETag`` header with the current timestamp of the collection for
the current user will be given on collection endpoints.

::

    ETag: "1432208041618"

On record enpoints, the ``ETag`` header value will contain the timestamp of the
record.


In order to bypass costly and error-prone HTTP date parsing, ``ETag`` headers
are not HTTP date values.

A human readable version of the timestamp (rounded to second) is provided though
in the ``Last-Modified`` response headers:

::

    Last-Modified: Wed May 20 17:22:38 2015 +0200


.. versionchanged:: 2.0

    In previous versions, cache and concurrency control was handled using
    ``If-Modified-Since`` and ``If-Unmodified-Since``. But since the HTTP date
    does not include milliseconds, they contained the milliseconds timestamp as
    integer. The current version using ``ETag`` is HTTP compliant (see
    `original discussion <https://github.com/mozilla-services/cliquet/issues/251>`_.)

.. note::

    The client may send ``If-Unmodified-Since`` or ``If-Modified-Since`` requests
    headers, but in the current implementation, they will be ignored.


Cache control
=============

In order to check that the client version has not changed, a ``If-None-Match``
request header can be used. If the response is ``304 Not Modified`` then
the cached version if still good.


Concurrency control
===================

In order to prevent race conditions, like overwriting changes occured in the interim for example,
a ``If-Match`` request header can be used. If the response is ``412 Precondition failed``
then the resource has changed meanwhile.

The client can then choose to:

* overwrite by repeating the request without ``If-Match``;
* reconcile the resource by fetching, merging and repeating the request.
