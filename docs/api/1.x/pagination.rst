.. _paginating:

Paginating
##########

Plural endpoints support limiting the number of elements returned. For
example, you can retrieve a fixed number of records in a
collection. To do this, provide a ``_limit`` query parameter
specifying the number of records to return.

If there are more records for this collection than the limit, the
response will provide a ``Next-Page`` header with the URL for the
Next-Page.

When there is no more ``Next-Page`` response header, there is nothing
more to fetch.

Pagination works on any plural endpoint.

.. note::

    The ``Next-Page`` URL will contain a continuation token (``_token``).

    It is recommended to add precondition headers (``If-Match`` or
    ``If-None-Match``), in order to detect changes on collection while
    iterating through the pages.

Counting
--------

In order to count the number of records, for a specific field value for example,
without fetching the actual collection, a ``HEAD`` request can be
used. The ``Total-Records`` response header will then provide the
total number of records.
