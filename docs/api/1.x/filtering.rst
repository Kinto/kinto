.. _filtering:

Filtering
#########

Plural endpoints (such as collections) support restricting the set of
returned results by means of filters. Filters are predicates that can
be expressed by query parameters. Elements of the plural endpoint
(such as records) that do not match the predicates are omitted from
the response.

Most filters are expressed using a query parameter of the form
``[operator_]field=value``. The (optional) operator is one from the
list below. The field name can be simple or a dotted field
name. Values can be any JSON encoded value (e.g. ``24``, ``"hello"``,
``[1, 2, 4]``, ``{"flavor": "strawberry"}``, ``true``, or
``null``). Anything not recognized as a JSON value is interpreted as a
string.

Single value
------------

* ``/collection?field=value``

Examples:

* ``/collection?author=2``

  Matches any record whose ``author`` field is equal to the number 2.

* ``/collection?author="Ben"``

  Matches any record whose ``author`` field is equal to the string Ben.

* ``/collection?author=Ben``

  Same as the previous example, but relying on the behavior that
  anything that isn't JSON is a string.

* ``/collection?author="2.0"``

  Matches any record whose ``author`` field is equal to the string
  value ``"2.0"``. This is useful if your records contain something
  numeric-ish but not quite numeric, like a version number.

It also works with multiple values:

* ``/collection?field=[1,2]``

Or even objects:

* ``/collection?field={"checked": true}``

Sub-objects
-----------

* ``/collection?field.subfield=value``

Search in array fields
----------------------

* ``/collection?contains_field=value``

  Matches any records whose ``field`` array field contains ``value``. Value can
  be an integer, a string, an object, or a list of such.

  In the value is a list, it only matches records whose field contains
  all the values listed.

* ``/collection?contains_any_field=value``

  Same as the previous filter, but if the value is a list, it matches
  all records whose field contains at least one of the listed values.

Examples:

* ``/collection?contains_colors=["red","blue"]``

  Matches any record whose ``colors`` array field contains ``red`` and
  ``blue`` elements.

* ``/collection?contains_any_colors=["red","blue"]``

  Matches any record whose ``colors`` array field contains ``red`` or
  ``blue`` strings.

* ``/collection?contains_any_aliases=[{"ll": "ls -l"}, {"gti": "git"}]``

  Matches any record whose ``aliases`` array field contains ``{"ll": "ls -l"}`` or
  ``{"gti": "git"}`` objects.


Comparison
----------

The filters ``lt`` and ``gt`` are available to compare against values.

* ``/collection?gt_orders=100``

  Retrieve any records whose ``orders`` field is (strictly) greater
  than 100.

This bound is exclusive (i.e., in the previous example, it would not
retrieve a record whose ``orders`` field was equal to 100). To check
"greater than or equal", use ``min``. To check "less than or equal",
use ``max``.

* ``/collection?min_orders=100``

  Retrieve any records whose ``orders`` field is greater than or equal
  to 100.

At the present time, the comparison order between values of different
types is not defined. For example, if you have a record like
``{"author": 1}`` and another like ``{"author": "2"}``, requesting
``/collection?gt_author=1`` may return the second one, or it may
not. However, a comparison operator will match whatever order you get
by sorting, and the ordering will include all records.

Multiple values
---------------

Prefix field with ``in_`` and provide comma-separated values.

* ``/collection?in_status=1,2,3``

Exclude
-------

Prefix field name with ``not_``:

* ``/collection?not_field=0``

Exclude multiple values
-----------------------

Prefix field name with ``exclude_``:

* ``/collection?exclude_field=0,1``

Search string fields
--------------------

Prefix field name with ``like_``:

* ``/collection?like_field=foo``

The specified value can also contain wildchars:

* ``/collection?like_field=foo*`` (starts with ``foo``)
* ``/collection?like_field=*foo`` (ends with ``foo``)
* ``/collection?like_field=*foo*`` (equivalent to ``like_field=foo``)

Field existence
---------------

You can request records that have a certain field (for example, ``author``) using ``has_author=true`` or those that don't have that field by using ``has_author=false``.

* ``/collection?has_field=true``

Note that a record like ``{"author": null}`` still counts as "having" that field.

Polling for changes
-------------------

.. note::

    The ``ETag`` and ``Last-Modified`` response headers will always be the same as
    the unfiltered collection.

One important use of this is when polling for changes.

The ``_since`` parameter is provided as an alias for ``gt_last_modified``.

* ``/collection?_since=1437035923844``

When filtering on ``last_modified`` every deleted records will appear in the
list with a ``deleted`` flag and a ``last_modified`` value that corresponds
to the deletion event.

If the ``If-None-Match: "<timestamp>"`` request header is provided as described in
the :ref:`section about timestamps <server-timestamps>` and if the
collection was not changed, a |status-304| response is returned.

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
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, ETag, Next-Page, Last-Modified
    Content-Length: 436
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:08:11 GMT
    Last-Modified: Mon, 12 Apr 2015 11:12:07 GMT
    ETag: "1430222877724"

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
