Paginate
########

If the ``_limit`` parameter is provided, the number of records returned is limited.

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
