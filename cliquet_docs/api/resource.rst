.. _resource-endpoints:

##################
Resource endpoints
##################

GET /{collection}
=================

**Requires authentication**

Returns all records of the current user for this collection.

The returned value is a JSON mapping containing:

- ``data``: the list of records, with exhaustive fields;
- ``permissions``: *optional* a json dict containing the permissions for
  the collection of records.

A ``Total-Records`` response header indicates the total number of records
of the collection.

A ``Last-Modified`` response header provides a human-readable (rounded to second)
of the current collection timestamp.

For cache and concurrency control, an ``ETag`` response header gives the
value that consumers can provide in subsequent requests using ``If-Match``
and ``If-None-Match`` headers (see :ref:`section about timestamps <server-timestamps>`).

**Request**:

.. code-block:: http

    GET /articles HTTP/1.1
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
            }
        ]
    }


Filtering
---------

**Single value**

* ``/collection?field=value``

.. **Multiple values**
..
.. * ``/collection?field=1,2``

**Minimum and maximum**

Prefix attribute name with ``min_`` or ``max_``:

* ``/collection?min_field=4000``

.. note::

    The lower and upper bounds are inclusive (*i.e equivalent to
    greater or equal*).

.. note::

   ``lt_`` and ``gt_`` can also be used to exclude the bound.

**Multiple values**

Prefix attribute with ``in_`` and provide comma-separated values.

* ``/collection?in_status=1,2,3``

**Exclude**

Prefix attribute name with ``not_``:

* ``/collection?not_field=0``

**Exclude multiple values**

Prefix attribute name with ``exclude_``:

* ``/collection?exclude_field=0,1``

.. note::

    Will return an error if a field is unknown.

.. note::

    The ``ETag`` and ``Last-Modified`` response headers will always be the same as
    the unfiltered collection.

Sorting
-------

* ``/collection?_sort=-last_modified,field``

.. note::

    Ordering on a boolean field gives ``true`` values first.

.. note::

    Will return an error if a field is unknown.


Counting
--------

In order to count the number of records, for a specific field value for example,
without fetching the actual collection, a ``HEAD`` request can be
used. The ``Total-Records`` response header will then provide the
total number of records.

See :ref:`batch endpoint <batch>` to count several collections in one request.


Polling for changes
-------------------

The ``_since`` parameter is provided as an alias for ``gt_last_modified``.

* ``/collection?_since=1437035923844``

When filtering on ``last_modified`` every deleted records will appear in the
list with a ``deleted`` flag and a ``last_modified`` value that corresponds
to the deletion event.

If the request header ``If-None-Match`` is provided as described in
the :ref:`section about timestamps <server-timestamps>` and if the
collection was not changed, a ``304 Not Modified`` response is returned.

.. note::

   The ``_before`` parameter is also available, and is an alias for
   ``lt_last_modified`` (*strictly inferior*).


.. versionchanged:: 2.4::

   ``_to`` was renamed ``_before`` and is now deprecated.
    It will be supported until the next major version of Cliquet.


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


Paginate
--------

If the ``_limit`` parameter is provided, the number of records returned is limited.

If there are more records for this collection than the limit, the
response will provide a ``Next-Page`` header with the URL for the
Next-Page.

When there is no more ``Next-Page`` response header, there is nothing
more to fetch.

Pagination works with sorting, filtering and polling.

.. note::

    The ``Next-Page`` URL will contain a continuation token (``_token``).

    It is recommended to add precondition headers (``If-Match`` or
    ``If-None-Match``), in order to detect changes on collection while
    iterating through the pages.


List of available URL parameters
--------------------------------

- ``<prefix?><attribute name>``: filter by value(s)
- ``_since``, ``_before``: polling changes
- ``_sort``: order list
- ``_limit``: pagination max size
- ``_token``: pagination token


Filtering, sorting and paginating can all be combined together.

* ``/collection?_sort=-last_modified&_limit=100``


HTTP Status Codes
-----------------

* ``200 OK``: The request was processed
* ``304 Not Modified``: Collection did not change since value in ``If-None-Match`` header
* ``400 Bad Request``: The request querystring is invalid
* ``412 Precondition Failed``: Collection changed since value in ``If-Match`` header


POST /{collection}
==================

**Requires authentication**

Used to create a record in the collection. The POST body is a JSON mapping
containing:

- ``data``: the values of the resource schema fields;
- ``permissions``: *optional* a json dict containing the permissions for
  the record to be created.

The POST response body is a JSON mapping containing:

- ``data``: the newly created record, if all posted values are valid;
- ``permissions``: *optional* a json dict containing the permissions for
  the requested resource.

If the request header ``If-Match`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.


**Request**:

.. code-block:: http

    POST /articles HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Content-Type: application/json; charset=utf-8
    Host: localhost:8000

    {
        "data": {
            "title": "Wikipedia FR",
            "url": "http://fr.wikipedia.org"
        }
    }

**Response**:

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 422
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:35:02 GMT

    {
        "data": {
            "id": "cd30c031-c208-4fb9-ad65-1582d2a7ad5e",
            "last_modified": 1430224502529,
            "title": "Wikipedia FR",
            "url": "http://fr.wikipedia.org"
        }
    }


Validation
----------

If the posted values are invalid (e.g. *field value is not an integer*)
an error response is returned with status ``400``.

See :ref:`details on error responses <error-responses>`.


Conflicts
---------

Since some fields can be :ref:`defined as unique <resource-class>` per collection
(per user), some conflicts may appear when creating records.

.. note::

    Empty values are not taken into account for field unicity.

.. note::

    Deleted records are not taken into account for field unicity.

If a conflict occurs, an error response is returned with status ``409``.
A ``details`` attribute in the response provides the offending record and
field name. See :ref:`dedicated section about errors <error-responses>`_.


HTTP Status Codes
-----------------

.. * ``200 OK``: This record already exists, here is the one stored on the database;

* ``201 Created``: The record was created
* ``400 Bad Request``: The request body is invalid
* ``409 Conflict``: Unicity constraint on fields is violated
* ``412 Precondition Failed``: Collection changed since value in ``If-Match`` header


DELETE /{collection}
====================

**Requires authentication**

Delete multiple records. **Disabled by default**, see :ref:`configuration`.

The DELETE response is a JSON mapping containing:

- ``data``: list of records that were deleted, without schema fields.

It supports the same filtering capabilities as GET.

If the request header ``If-Match`` is provided, and if the collection
has changed meanwhile, a ``412 Precondition failed`` error is returned.


**Request**:

.. code-block:: http

    DELETE /articles HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Host: localhost:8000

**Response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 193
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:38:36 GMT

    {
        "data": [
            {
                "deleted": true,
                "id": "cd30c031-c208-4fb9-ad65-1582d2a7ad5e",
                "last_modified": 1430224716097
            },
            {
                "deleted": true,
                "id": "dc86afa9-a839-4ce1-ae02-3d538b75496f",
                "last_modified": 1430224716098
            }
        ]
    }


HTTP Status Codes
-----------------

* ``200 OK``: The records were deleted;
* ``405 Method Not Allowed``: This endpoint is not available;
* ``412 Precondition Failed``: Collection changed since value in ``If-Match`` header


GET /{collection}/<id>
======================

**Requires authentication**

Returns a specific record by its id. The GET response body is a JSON mapping
containing:

- ``data``: the record with exhaustive schema fields;
- ``permissions``: *optional* a json dict containing the permissions for
  the requested record.

If the request header ``If-None-Match`` is provided, and if the record has not
changed meanwhile, a ``304 Not Modified`` is returned.

**Request**:

.. code-block:: http

    GET /articles/d10405bf-8161-46a1-ac93-a1893d160e62 HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Host: localhost:8000

**Response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, ETag, Last-Modified
    Content-Length: 438
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:42:42 GMT
    ETag: "1430224945242"

    {
        "data": {
            "id": "d10405bf-8161-46a1-ac93-a1893d160e62",
            "last_modified": 1430224945242,
            "title": "No backend",
            "url": "http://nobackend.org"
        }
    }


HTTP Status Code
----------------

* ``200 OK``: The request was processed
* ``304 Not Modified``: Record did not change since value in ``If-None-Match`` header
* ``412 Precondition Failed``: Record changed since value in ``If-Match`` header


DELETE /{collection}/<id>
=========================

**Requires authentication**

Delete a specific record by its id.

The DELETE response is the record that was deleted. The DELETE response is a JSON mapping containing:

- ``data``: the record that was deleted, without schema fields.

If the record is missing (or already deleted), a ``404 Not Found`` is returned.
The consumer might decide to ignore it.

If the request header ``If-Match`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

.. note::

    Once deleted, a record will appear in the collection when polling for changes,
    with a deleted status (``delete=true``) and will have most of its fields empty.

HTTP Status Code
----------------

* ``200 OK``: The record was deleted
* ``412 Precondition Failed``: Record changed since value in ``If-Match`` header


PUT /{collection}/<id>
======================

**Requires authentication**

Create or replace a record with its id. The PUT body is a JSON mapping containing:

- ``data``: the values of the resource schema fields;
- ``permissions``: *optional* a json dict containing the permissions for
  the record to be created.

The PUT response body is a JSON mapping containing:

- ``data``: the newly created/updated record, if all posted values are valid;
- ``permissions``: *optional* the newly created permissions dict, containing
  the permissions for the created record.

Validation and conflicts behaviour is similar to creating records (``POST``).

If the request header ``If-Match`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.


**Request**:

.. code-block:: http

    PUT /articles/d10405bf-8161-46a1-ac93-a1893d160e62 HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Content-Type: application/json; charset=utf-8
    Host: localhost:8000

    {
        "data": {
            "title": "Static apps",
            "url": "http://www.staticapps.org"
        }
    }

**Response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 439
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:46:36 GMT
    ETag: "1430225196396"

    {
        "data": {
            "id": "d10405bf-8161-46a1-ac93-a1893d160e62",
            "last_modified": 1430225196396,
            "title": "Static apps",
            "url": "http://www.staticapps.org"
        }
    }


HTTP Status Code
----------------

* ``201 Created``: The record was created
* ``200 OK``: The record was replaced
* ``400 Bad Request``: The record is invalid
* ``409 Conflict``: If replacing this record violates a field unicity constraint
* ``412 Precondition Failed``: Record was changed or deleted since value
  in ``If-Match`` header.

.. note::

    A ``If-None-Match: *`` request header can be used to make sure the ``PUT``
    won't overwrite any record.


PATCH /{collection}/<id>
========================

**Requires authentication**

Modify a specific record by its id. The PATCH body is a JSON mapping containing:

- ``data``: a subset of the resource schema fields;
- ``permissions``: *optional* a json dict containing the permissions for
  the record to be modified.

The PATCH response body is a JSON mapping containing:

- ``data``: the modified record (*full by default*);
- ``permissions``: *optional* the newly created permissions dict, containing
  the permissions for the modified record.

If a request header ``Response-Behavior`` is set to ``light``,
only the fields whose value was changed are returned. If set to
``diff``, only the fields whose value became different than
the one provided are returned.


**Request**:

.. code-block:: http

    PATCH /articles/d10405bf-8161-46a1-ac93-a1893d160e62 HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Content-Type: application/json; charset=utf-8
    Host: localhost:8000

    {
        "data": {
            "title": "No Backend"
        }
    }

**Response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 439
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:46:36 GMT
    ETag: "1430225196396"

    {
        "data": {
            "id": "d10405bf-8161-46a1-ac93-a1893d160e62",
            "last_modified": 1430225196396,
            "title": "No Backend",
            "url": "http://nobackend.org"
        }
    }


If the record is missing (or already deleted), a ``404 Not Found`` error is returned.
The consumer might decide to ignore it.

If the request header ``If-Match`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

.. note::

    ``last_modified`` is updated to the current server timestamp, only if a
    field value was changed.


Read-only fields
----------------

If a read-only field is modified, a ``400 Bad request`` error is returned.


Conflicts
---------

If changing a record field violates a field unicity constraint, a
``409 Conflict`` error response is returned (see :ref:`error channel <error-responses>`).


HTTP Status Code
----------------

* ``200 OK``: The record was modified
* ``400 Bad Request``: The request body is invalid, or a read-only field was
  modified
* ``409 Conflict``: If modifying this record violates a field unicity constraint
* ``412 Precondition Failed``: Record changed since value in ``If-Match`` header


Protected resources
===================

All of the described endpoints can be either *protected* or not. Protecting
an enpoint means that only *principals* which have been granted access will
be able to issue requests successfully.

In the case of a *protected* resource, body is a JSON mapping containing a
``permissions`` key in addition to the ``data`` key. Permissions can also be
replaced and modified independantly from data.

On a request, ``permissions`` is a json dict containing the permissions for
the record to be modified. It has the following signature::

    'permissions': {'{permission}': [{list_of_principals}]}

`{permission}` is a placeholder for the permission name (e.g. `read`, `write`,
`create`) and `{list_of_principals}` should be replaced by an actual list of
principals.

``permissions`` is also added to JSON mapping response bodies, and contains
the *modified* version of the permissions in case of a modification, or the
list of permissions in case of a read operation.


.. versionchanged:: 2.6::

    With a ``PATCH`` request, the list of principals for the specified permissions
    is now replaced by the one provided.
