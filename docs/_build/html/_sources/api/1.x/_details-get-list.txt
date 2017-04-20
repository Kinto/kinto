A ``Total-Records`` response header indicates the total number of objects
of the list (not the response, since it can be paginated).

A ``Last-Modified`` response header provides a human-readable (rounded to second)
of the current collection timestamp.

For cache and concurrency control, an ``ETag`` response header gives the
value that consumers can provide in subsequent requests using ``If-Match``
and ``If-None-Match`` headers (see :ref:`section about timestamps <server-timestamps>`).


List of available URL parameters
--------------------------------

- ``<prefix?><field name>``: :doc:`filter <filtering>` by value(s)
- ``_since``, ``_before``: polling changes
- ``_sort``: :doc:`order list <sorting>`
- ``_limit``: :doc:`pagination max size <pagination>`
- ``_token``: :doc:`pagination token <pagination>`
- ``_fields``: :doc:`filter the fields of the records <selecting_fields>`


Filtering, sorting, partial responses and paginating can all be combined together.

* ``?_sort=-last_modified&_limit=100&_fields=title``
