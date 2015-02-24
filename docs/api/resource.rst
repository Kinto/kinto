#################
API Documentation
#################

.. _http-apis:

GET /{resource}
===============

XXX define the resource get endpoint.

Filtering
---------

**Single value**

* ``/resource?field=value``

**Multiple values**

* ``/resource?field,2``

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
    Will return an error if an attribute is unknown.

:note:
    The ``Last-Modified`` response header will always be the same as
    the unfiltered collection.

Sorting
-------

* ``/resource?_sort=-last_modified,title``

.. :note:
..     Items will be ordered by ``-stored_on`` by default (i.e. newest first).

:note:
    Ordering on a boolean field gives ``true`` values first.

:note:
    Will return an error if an attribute is unknown.


Counting
--------

In order to count the number of records, by status for example,
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
every deleted articles will appear in the list with a deleted status (``status=2``).

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


POST /resource
==============

**Requires authentication**

Used to create a resource on the server. The POST body is a JSON.

XXX

The POST response body is the newly created record, if all posted values are valid. Additional optional attributes can also be specified:

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.


Conflicts
---------

Articles URL are unique per user (both ``url`` and ``resolved_url``).

:note:
    A ``url`` always resolves towards the same URL. If ``url`` is not unique, then
    its ``resolved_url`` won't either.

:note:
    Unicity on URLs is determined the full URL, including location hash.
    (e.g. http://news.com/day-1.html#paragraph1, http://spa.com/#/content/3)

:note:
    Deleted items should be taken into account for URL unicity.

If an article is created with an URL that already exists, a ``200`` response
is returned with the existing record in the body.


DELETE /resource
================

**Requires authentication**

Delete multiple records.

The DELETE response is a JSON mapping with an ``items`` attribute, returning
the list of records that were deleted.

It supports the same filtering capabilities as GET.

If the request header ``If-Unmodified-Since`` is provided, and if the collection
has changed meanwhile, a ``412 Precondition failed`` error is returned.


GET /articles/<id>
==================

**Requires an FxA OAuth authentication**

Returns a specific article by its id.

For convenience and consistency, a header ``Last-Modified`` will also repeat the
value of ``last_modified``.

If the request header ``If-Modified-Since`` is provided, and if the record has not
changed meanwhile, a ``304 Not Modified`` is returned.

:note:
    Even though article URLs are unique together, we use the article id field
    to target individual records.


DELETE /articles/<id>
=====================

**Requires an FxA OAuth authentication**

Delete a specific article by its id.

The DELETE response is the record that was deleted.

If the record is missing (or already deleted), a ``404 Not Found`` is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    Once deleted, an article will appear in the collection with a deleted status
    (``status=2``) and will have most of its fields empty.


PATCH /articles/<id>
====================

**Requires an FxA OAuth authentication**

Modify a specific article by its id. The PATCH body is a JSON
mapping containing a subset of articles fields.

The PATCH response is the modified record (full).

**Modifiable fields**

- ``title``
- ``excerpt``
- ``favorite``
- ``unread``
- ``status``
- ``read_position``

Since article fields resolution is performed by the client in the first version
of the API, the following fields are also modifiable:

- ``is_article``
- ``resolved_url``
- ``resolved_title``

**Errors**

If the record is missing (or already deleted), a ``404 Not Found`` error is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    ``last_modified`` is updated to the current server timestamp, only if a
    field value was changed.

:note:
    Changing ``read_position`` never generates conflicts.

:note:
    ``read_position`` is ignored if the value is lower than the current one.

:note:
    If ``unread`` is changed to false, ``marked_read_on`` and ``marked_read_by``
    are expected to be provided.

:note:
    If ``unread`` was already false, ``marked_read_on`` and ``marked_read_by``
    are not updated with provided values.

:note:
    If ``unread`` is changed to true, ``marked_read_by``, ``marked_read_on``
    and ``read_position`` are reset to their default value.

:note:
    As mentionned in the *Validation section*, an article status cannot take the value ``2``.


Conflicts
---------

If changing the article ``resolved_url`` violates the unicity constraint, a
``409 Conflict`` error response is returned (see :ref:`error channel <error-responses>`).

:note:

    Note that ``url`` is a readonly field, and thus cannot generate conflicts
    here.
