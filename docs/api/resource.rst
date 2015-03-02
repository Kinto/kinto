##################
Resource endpoints
##################

.. _resource-endpoints:

GET /{resource}
===============

**Requires authentication**

Returns all records of the current user for this resource.

The returned value is a JSON mapping containing:

- ``items``: the list of records, with exhaustive attributes

A ``Total-Records`` header is sent back to indicate the estimated
total number of records included in the response.

A header ``Last-Modified`` will provide the current timestamp of the
collection (*see Server timestamps section*).  It is likely to be used
by client to provide ``If-Modified-Since`` or ``If-Unmodified-Since``
headers in subsequent requests.


Filtering
---------

**Single value**

* ``/resource?field=value``

.. **Multiple values**
..
.. * ``/resource?field=1,2``

**Minimum and maximum**

Prefix attribute name with ``min_`` or ``max_``:

* ``/resource?min_field=4000``

:note:
    The lower and upper bounds are inclusive (*i.e equivalent to
    greater or equal*).

:note:
   ``lt_`` and ``gt_`` can also be used to exclude the bound.

**Exclude**

Prefix attribute name with ``not_``:

* ``/resource?not_field=0``

:note:
    Will return an error if a field is unknown.

:note:
    The ``Last-Modified`` response header will always be the same as
    the unfiltered collection.

Sorting
-------

* ``/resource?_sort=-last_modified,field``

:note:
    Ordering on a boolean field gives ``true`` values first.

:note:
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

The ``_since`` parameter is provided as an alias for
``gt_last_modified``.

* ``/resource?_since=123456``

The new value of the collection latest modification is provided in
headers (*see Server timestamps section*).

When filtering on ``last_modified`` (i.e. with ``_since`` or ``_to`` parameters),
every deleted records will appear in the list with a deleted status (``deleted=true``).

If the request header ``If-Modified-Since`` is provided, and if the
collection has not suffered changes meanwhile, a ``304 Not Modified``
response is returned.

:note:
   The ``_to`` parameter is also available, and is an alias for
   ``lt_last_modified`` (*strictly inferior*).


Paginate
--------

If the ``_limit`` parameter is provided, the number of items is limited.

If there are more items for this collection than the limit, the
response will provide a ``Next-Page`` header with the URL for the
Next-Page.

When there is not more ``Next-Page`` response header, there is nothing
more to fetch.

Pagination works with sorting and filtering.


List of available URL parameters
--------------------------------

- ``<prefix?><attribute name>``: filter by value(s)
- ``_since``: polling changes
- ``_sort``: order list
- ``_limit``: pagination max size
- ``_token``: pagination token


Combining all parameters
------------------------

Filtering, sorting and paginating can all be combined together.

* ``/resource?_sort=-last_modified&_limit=100``


HTTP Status Codes
-----------------

* ``200 OK``: The request have been processed
* ``304 Not Modified``: Collection items did not change since ``If-Unmodified-Since`` header value
* ``400 Bad Request``: The request body is invalid
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable


POST /{resource}
================

**Requires authentication**

Used to create a record on the server. The POST body is a JSON
mapping containing the values of the resource schema fields.


The POST response body is the newly created record, if all posted values are valid.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.


Validation
----------

If the posted values are invalid (e.g. *field value is not an integer*)
an error response is returned with status ``400``.

See :ref:`details on error responses <error-responses>`.


Conflicts
---------

Since field can be :ref:`defined as unique <resource-class>` per user, some
conflicts may appear when creating records.

:note:
    Empty values are not taken into account for field unicity.

:note:
    Deleted records are not taken into account for field unicity.

If a conflict occurs, an error response is returned with status ``409``.
A ``existing`` attribute in the response gives the offending record.


HTTP Status Codes
-----------------

* ``200 OK``: The request have been processed
* ``400 Bad Request``: The request body is invalid
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable


DELETE /{resource}
==================

**Requires authentication**

Delete multiple records. **Disabled by default**, see :ref:`configuration`.

The DELETE response is a JSON mapping with an ``items`` attribute, returning
the list of records that were deleted.

It supports the same filtering capabilities as GET.

If the request header ``If-Unmodified-Since`` is provided, and if the collection
has changed meanwhile, a ``412 Precondition failed`` error is returned.


HTTP Status Codes
-----------------

* ``200 OK``: The request have been processed
* ``405 Method Not Allowed``: This endpoint is not available
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable


GET /{resource}/<id>
====================

**Requires authentication**

Returns a specific record by its id.

For convenience and consistency, a header ``Last-Modified`` will also repeat the
value of ``last_modified``.

If the request header ``If-Modified-Since`` is provided, and if the record has not
changed meanwhile, a ``304 Not Modified`` is returned.


HTTP Status Code
----------------

* ``200 OK``: The request have been processed
* ``304 Not Modified``: Item did not change since ``If-Unmodified-Since`` header value
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable


DELETE /{resource}/<id>
=======================

**Requires authentication**

Delete a specific record by its id.

The DELETE response is the record that was deleted.

If the record is missing (or already deleted), a ``404 Not Found`` is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    Once deleted, a record will appear in the collection when polling for changes,
    with a deleted status (``delete=true``) and will have most of its fields empty.

HTTP Status Code
----------------

* ``200 OK``: The request have been processed
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable


PUT /{resource}/<id>
====================

**Requires authentication**

Create or replace a record with its id. The PUT body is a JSON
mapping validating the resource schema fields.

Validation and conflicts behaviour is similar to creating records (``POST``).

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

HTTP Status Code
----------------

* ``200 OK``: The request have been processed
* ``400 Bad Request``: If the record id does not match an existing record
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable


PATCH /{resource}/<id>
======================

**Requires authentication**

Modify a specific record by its id. The PATCH body is a JSON
mapping containing a subset of the resource schema fields.

The PATCH response is the modified record (full).

**Errors**

If a read-only field is modified, a ``400 Bad request`` error is returned.

If the record is missing (or already deleted), a ``404 Not Found`` error is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    ``last_modified`` is updated to the current server timestamp, only if a
    field value was changed.


Conflicts
---------

If changing a record field violates a field unicity constraint, a
``409 Conflict`` error response is returned (see :ref:`error channel <error-responses>`).


HTTP Status Code
----------------

* ``200 OK``: The request have been processed
* ``400 Bad Request``: The request body is invalid
* ``412 Precondition Failed``: Collection items changed since provided ``If-Unmodified-Since`` header value
* ``503 Service Unavailable``: The service is currently Unavailable
