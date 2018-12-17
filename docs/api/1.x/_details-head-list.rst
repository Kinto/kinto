Unlike GET requests, HEAD requests contain an additional header called ``Total-Objects``
(and ``Total-Records`` for backwards compatibility) which is a count of all objects
in the collection with the current filtering.

List of available URL parameters for HEAD
-----------------------------------------

- ``<prefix?><field name>``: :doc:`filter <filtering>` by value(s)
- ``_since``, ``_before``: polling changes
- ``_token``: :doc:`pagination token <pagination>`
