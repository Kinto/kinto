.. _server-timestamps:

#################
Server timestamps
#################

In order to avoid race conditions, each change is guaranteed to
increment the timestamp of the related list.
If two changes happen at the same millisecond, they will still have two different
timestamps.

The ``ETag`` header with the current timestamp of the list for
the current user will be given on list endpoint.

::

    ETag: "1432208041618"

On object enpoints, the ``ETag`` header value will contain the timestamp of the
object.

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

    When the list is empty, its timestamp remains the same until new objects
    are created.


Cache control
=============

In order to check that the client version has not changed, a ``If-None-Match``
request header can be used. If the response is |status-304| then
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


.. _concurrency control:

Concurrency control
===================

In order to prevent race conditions, like overwriting changes occured in the interim for example,
a ``If-Match: "timestamp"`` request header can be used. If the response is |status-412|
then the resource has changed meanwhile.

Concurrency control also allows to make sure a creation won't overwrite any object using
the ``If-None-Match: *`` request header.

The following table gives a summary of the expected behaviour of a resource:

+-----------------------------+-------------+-------------+-------------+-------------+-------------+
|                             | GET         | POST        | PUT         | PATCH       | DELETE      |
+=============================+=============+=============+=============+=============+=============+
|| **If-Match: "timestamp"**                                                                        |
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
| Not changed                 | Fetch       | Fetch       | Overwrite   | Modify      | Delete      |
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
| Changed meanwhile           | ``HTTP 412``| ``HTTP 412``| ``HTTP 412``| ``HTTP 412``| ``HTTP 412``|
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
|| **If-Match: ***                                                                                  |
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
| Id exists                   | Fetch       | Fetch       | Overwrite   | Modify      | Delete      |
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
| Id unknown                  | ``HTTP 412``| ``HTTP 412``| ``HTTP 412``| ``HTTP 412``| ``HTTP 412``|
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
|| **If-None-Match: ***                                                                             |
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
| Id exists                   | ``HTTP 412``| ``HTTP 412``| ``HTTP 412``| ``HTTP 412``| ``HTTP 412``|
+-----------------------------+-------------+-------------+-------------+-------------+-------------+
| Id unknown                  | No effect   | Create      | Create      | No effect   | No effect   |
+-----------------------------+-------------+-------------+-------------+-------------+-------------+


When the client receives a |status-412|, it can then choose to:

* overwrite by repeating the request without concurrency control;
* reconcile the resource by fetching, merging and repeating the request.


Replication
===========

In order to replicate the timestamps when importing existing records,
it is possible to force the last modified values.

When an object is created (via POST or PUT), the specified timestamp becomes
the new list timestamp if it is in the future (i.e. greater than current
one). If it is in the past, the record is created with the timestamp in the past
but the list timestamp is bumped into the future as usual.

When an object is replaced, modified or deleted, if the specified timestamp is less
or equal than the existing object, the value is simply ignored and the timestamp
is bumped into the future as usual.

When an object is deleted, a ``last_modified`` timestamp can be forced
by passing it in the query string using ``?last_modified=<value>``.
