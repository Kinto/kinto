.. _filtering:

Filtering
#########

Plural endpoints (such as collections) support restricting the set of
returned results by means of filters. Filters are predicates that can
be expressed by query parameters. Elements of the plural endpoint
(such as records) that do not match the predicates are omitted from
the response.

**Single value**

* ``/collection?field=value``

.. **Multiple values**
..
.. * ``/collection?field=1,2``

**Minimum and maximum**

Prefix field name with ``min_`` or ``max_``:

* ``/collection?min_field=4000``

.. note::

    The lower and upper bounds are inclusive (*i.e equivalent to
    greater or equal*).

.. note::

   ``lt_`` and ``gt_`` can also be used to exclude the bound.

**Multiple values**

Prefix field with ``in_`` and provide comma-separated values.

* ``/collection?in_status=1,2,3``

**Exclude**

Prefix field name with ``not_``:

* ``/collection?not_field=0``

**Exclude multiple values**

Prefix field name with ``exclude_``:

* ``/collection?exclude_field=0,1``

.. note::

    Will return an error if a field is unknown.

.. note::

    The ``ETag`` and ``Last-Modified`` response headers will always be the same as
    the unfiltered collection.

One important use of this is when polling for changes.

Polling for changes
-------------------

The ``_since`` parameter is provided as an alias for ``gt_last_modified``.

* ``/collection?_since=1437035923844``

When filtering on ``last_modified`` every deleted records will appear in the
list with a ``deleted`` flag and a ``last_modified`` value that corresponds
to the deletion event.

If the ``If-None-Match: "<timestamp>"`` request header is provided as described in
the :ref:`section about timestamps <server-timestamps>` and if the
collection was not changed, a ``304 Not Modified`` response is returned.

.. note::

   The ``_before`` parameter is also available, and is an alias for
   ``lt_last_modified`` (*strictly inferior*).

.. note::

    ``_since`` and ``_before`` also accept a value between quotes (``"``) as
    it would be returned in the ``ETag`` response header
    (see :ref:`response timestamps <server-timestamps>`).

**Request**:

.. code-block:: http

    GET /articles?_since=1437035923844 HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Host: localhost:8000

**Response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, ETag, Next-Page, Total-Records, Last-Modified
    Content-Length: 436
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:08:11 GMT
    Last-Modified: Mon, 12 Apr 2015 11:12:07 GMT
    ETag: "1430222877724"
    Total-Records: 2

    {
        "data": [
            {
                "id": "dc86afa9-a839-4ce1-ae02-3d538b75496f",
                "last_modified": 1430222877724,
                "title": "MoCo",
                "url": "https://mozilla.com",
            },
            {
                "id": "23160c47-27a5-41f6-9164-21d46141804d",
                "last_modified": 1430140411480,
                "title": "MoFo",
                "url": "https://mozilla.org",
            },
            {
                "id": "11130c47-37a5-41f6-9112-32d46141804f",
                "deleted": true,
                "last_modified": 1430140411480
            }
        ]
    }
