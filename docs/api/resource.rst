.. _resource-endpoints:

##################
Resource endpoints
##################

GET /{collection}
=================

**Requires authentication**

Returns all records of the current user for this collection.

The returned value is a JSON mapping containing:

- ``items``: the list of records, with exhaustive attributes

A ``Total-Records`` response header indicates the total number of records
of the collection.

A ``Last-Modified`` response header provides the current timestamp of the
collection (see :ref:`section about timestamps <server-timestamps>`).
It is likely to be used by consumer to provide ``If-Modified-Since`` or
``If-Unmodified-Since`` headers in subsequent requests.

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

**Exclude**

Prefix attribute name with ``not_``:

* ``/collection?not_field=0``

.. note::

    Will return an error if a field is unknown.

.. note::

    The ``Last-Modified`` response header will always be the same as
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

* ``/collection?_since=123456``

When filtering on ``last_modified`` every deleted records will appear in the
list with a deleted status (``deleted=true``).

If the request header ``If-Modified-Since`` is provided, and if the
collection has not suffered changes meanwhile, a ``304 Not Modified``
response is returned.

.. note::

   The ``_to`` parameter is also available, and is an alias for
   ``lt_last_modified`` (*strictly inferior*).


Paginate
--------

If the ``_limit`` parameter is provided, the number of records returned is limited.

If there are more records for this collection than the limit, the
response will provide a ``Next-Page`` header with the URL for the
Next-Page.

When there is no more ``Next-Page`` response header, there is nothing
more to fetch.

Pagination works with sorting and filtering.

.. note::

    The ``Next-Page`` URL will contain a continuation token (``_token``).

    It is recommended to add precondition headers (``If-Modified-Since`` or
    ``If-Unmodified-Since``), in order to detect changes on collection while
    iterating through the pages.


List of available URL parameters
--------------------------------

- ``<prefix?><attribute name>``: filter by value(s)
- ``_since``, ``_to``: polling changes
- ``_sort``: order list
- ``_limit``: pagination max size
- ``_token``: pagination token


Filtering, sorting and paginating can all be combined together.

* ``/collection?_sort=-last_modified&_limit=100``


HTTP Status Codes
-----------------

* ``200 OK``: The request was processed
* ``304 Not Modified``: Collection did not change since value in ``If-Modified-Since`` header
* ``400 Bad Request``: The request querystring is invalid
* ``412 Precondition Failed``: Collection changed since value in ``If-Unmodified-Since`` header


POST /{collection}
==================

**Requires authentication**

Used to create a record in the collection. The POST body is a JSON
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

Since some fields can be :ref:`defined as unique <resource-class>` per collection
(per user), some conflicts may appear when creating records.

.. note::

    Empty values are not taken into account for field unicity.

.. note::

    Deleted records are not taken into account for field unicity.

If a conflict occurs, an error response is returned with status ``409``.
A ``existing`` attribute in the response gives the offending record.


HTTP Status Codes
-----------------

.. * ``200 OK``: This record already exists, here is the one stored on the database;

* ``201 Created``: The record was created
* ``400 Bad Request``: The request body is invalid
* ``409 Conflict``: Unicity constraint on fields is violated
* ``412 Precondition Failed``: Collection changed since value in ``If-Unmodified-Since`` header


DELETE /{collection}
====================

**Requires authentication**

Delete multiple records. **Disabled by default**, see :ref:`configuration`.

The DELETE response is a JSON mapping with an ``items`` attribute, returning
the list of records that were deleted.

It supports the same filtering capabilities as GET.

If the request header ``If-Unmodified-Since`` is provided, and if the collection
has changed meanwhile, a ``412 Precondition failed`` error is returned.


HTTP Status Codes
-----------------

* ``200 OK``: The records were deleted;
* ``405 Method Not Allowed``: This endpoint is not available;
* ``412 Precondition Failed``: Collection changed since value in ``If-Unmodified-Since`` header


GET /{collection}/<id>
======================

**Requires authentication**

Returns a specific record by its id.

For convenience and consistency, a header ``Last-Modified`` will also repeat the
value of the ``last_modified`` field.

If the request header ``If-Modified-Since`` is provided, and if the record has not
changed meanwhile, a ``304 Not Modified`` is returned.


HTTP Status Code
----------------

* ``200 OK``: The request was processed
* ``304 Not Modified``: Record did not change since value in ``If-Modified-Since`` header
* ``412 Precondition Failed``: Record changed since value in ``If-Unmodified-Since`` header


DELETE /{collection}/<id>
=========================

**Requires authentication**

Delete a specific record by its id.

The DELETE response is the record that was deleted.

If the record is missing (or already deleted), a ``404 Not Found`` is returned.
The consumer might decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

.. note::

    Once deleted, a record will appear in the collection when polling for changes,
    with a deleted status (``delete=true``) and will have most of its fields empty.

HTTP Status Code
----------------

* ``200 OK``: The record was deleted
* ``412 Precondition Failed``: Collection changed since value in ``If-Unmodified-Since`` header


PUT /{collection}/<id>
======================

**Requires authentication**

Create or replace a record with its id. The PUT body is a JSON
mapping validating the resource schema fields.

Validation and conflicts behaviour is similar to creating records (``POST``).

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

HTTP Status Code
----------------

* ``200 OK``: The record was replaced
* ``400 Bad Request``: The record is invalid
* ``409 Conflict``: If replacing this record violates a field unicity constraint
* ``412 Precondition Failed``: Collection changed since value in ``If-Unmodified-Since`` header


PATCH /{collection}/<id>
========================

**Requires authentication**

Modify a specific record by its id. The PATCH body is a JSON
mapping containing a subset of the resource schema fields.

The PATCH response is the modified record (full).

**Errors**

If a read-only field is modified, a ``400 Bad request`` error is returned.

If the record is missing (or already deleted), a ``404 Not Found`` error is returned.
The consumer might decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

.. note::

    ``last_modified`` is updated to the current server timestamp, only if a
    field value was changed.


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
* ``412 Precondition Failed``: Collection changed since value in ``If-Unmodified-Since`` header
