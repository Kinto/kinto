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

.. important::

    When collection is empty, its timestamp remains the same until new records
    are created.


Cache control
=============

In order to check that the client version has not changed, a ``If-None-Match``
request header can be used. If the response is ``304 Not Modified`` then
the cached version is still good.

+-----------------------------+--------------------------+
|                             | GET                      |
+=============================+==========================+
|| **If-None-Match: "<timestamp>"**                      |
+-----------------------------+--------------------------+
| Changed meanwhile           | Return response content  |
+-----------------------------+--------------------------+
| Not changed                 | Empty ``HTTP 304``       |
+-----------------------------+--------------------------+


Concurrency control
===================

In order to prevent race conditions, like overwriting changes occured in the interim for example,
a ``If-Match: "timestamp"`` request header can be used. If the response is ``412 Precondition failed``
then the resource has changed meanwhile.

Concurrency control also allows to make sure a creation won't overwrite any record using
the ``If-None-Match: *`` request header.

The following table gives a summary of the expected behaviour of a resource:

+-----------------------------+-------------+--------------+---------------+---------------+
|                             | POST        | PUT          | PATCH         | DELETE        |
+=============================+=============+==============+===============+===============+
|| **If-Match: "timestamp"**                                                               |
+-----------------------------+-------------+--------------+---------------+---------------+
| Changed meanwhile           | ``HTTP 412``| ``HTTP 412`` | ``HTTP 412``  | ``HTTP 412``  |
+-----------------------------+-------------+--------------+---------------+---------------+
| Not changed                 | Create      | Overwrite    | Modify        | Delete        |
+-----------------------------+-------------+--------------+---------------+---------------+
|| **If-None-Match: ***                                                                    |
+-----------------------------+-------------+--------------+---------------+---------------+
| Id exists                   | ``HTTP 412``| ``HTTP 412`` | No effect     | No effect     |
+-----------------------------+-------------+--------------+---------------+---------------+
| Id unknown                  | Create      | Create       | No effect     | No effect     |
+-----------------------------+-------------+--------------+---------------+---------------+

When the client receives a ``412 Precondition failed``, it can then choose to:

* overwrite by repeating the request without concurrency control;
* reconcile the resource by fetching, merging and repeating the request.


Replication
===========

In order to replicate the timestamps when importing existing records,
it is possible to force the last modified values.

When a record is created (via POST or PUT), the specified timestamp becomes
the new collection timestamp if it is in the future (i.e. greater than current
one). If it is in the past, the record is created with the timestamp in the past
but the collection timestamp is bumped into the future as usual.

When a record is replaced, modified or deleted, if the specified timestamp is less
or equal than the existing record, the value is simply ignored and the timestamp
is bumped into the future as usual.

See :ref:`the resource endpoints documentation <resource-endpoints>`.
