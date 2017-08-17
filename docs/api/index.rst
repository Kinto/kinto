API
===

.. toctree::
   :maxdepth: 2

   versioning
   1.x/index


Changelog
---------

1.17 (2017-06-15)
'''''''''''''''''

- Filtering with like can now contain wild chars (eg. ``?like_nobody=*you*``)
  It is thus now impossible to search for the ``*`` character with this operator.
- New ``has_`` filter operator (fixes #344).
- JSON values are now accepted as filter values (fixes #1215, #1216, and #1217).

1.16 (2017-05-15)
'''''''''''''''''

- Groups can now be created with a simple ``PUT`` (fixes #793)
- Batch requests now raise ``400`` on unknown attributes (#1163).

1.15 (2017-03-03)
'''''''''''''''''

- ``If-Match`` and ``If-None-Match`` precondition headers now check the ETag for
  strict equality. Previous versions would allow requests if they seemed
  to be more recent than the current version.
- ``If-Match`` now raises ``412`` if a record doesn't exist.
- A |status-409| error response is now returned when some backend integrity
  constraint is violated (instead of |status-503|).

1.14 (2017-01-11)
'''''''''''''''''

- Add an OpenAPI 2.0 specification on ``GET /__api__`` endpoint.

1.13 (2016-12-19)
'''''''''''''''''

- Add ``DELETE`` to the history endpoint.
- Add a ``basicauth`` capability when activated on the server

1.12 (2016-11-18)
'''''''''''''''''

- Add a list of ``principals`` to ``hello`` view.
- ``details`` attribute present in response of 404 errors.
- Add support of *JSON patch* format to ``PATCH`` endpoints when using
  ``Content-Type: application/json-patch+json`` (as in RFC 6902).
  For more details, see `JSON-Patch Format <1.x/records.html#json-patch-operations>`_.
- Add support of *JSON merge* format to ``PATCH`` endpoints when using
  ``Content-Type: application/merge-patch+json`` (as in RFC 7396).
  which allows to remove attributes by passing ``null`` values.

1.11 (2016-10-04)
'''''''''''''''''

- Parent attributes are now readable if children creation is allowed
- Return an empty list on the plural endpoint instead of |status-403| if the ``create``
  permission is allowed
- Now returns a |status-412| instead of a |status-403| if the ``If-None-Match: *`` header is
  provided and the ``create`` permission is allowed
- The ``permissions`` attribute is now empty in the response if the user does not
  have the permission to write.


1.10 (2016-09-15)
'''''''''''''''''

- Add substring query to filtering on plural endpoints (e.g ``?like_person=Tim``)


1.9 (2016-08-17)
''''''''''''''''

- Add new endpoint ``GET /__version__`` to retrieve the information
  about the deployed version.
- Allow sub-object filtering on plural endpoints (e.g ``?person.name=Eliot``)
- Allow sub-object sorting on plural endpoints (e.g ``?_sort=person.name``)

1.8 (2016-07-19)
''''''''''''''''

- Add new endpoint ``GET /v1/permissions`` to retrieve the list of permissions
  granted on every kind of object.

1.7 (2016-06-14)
''''''''''''''''

- Allow record IDs to be any string instead of just UUID.

1.6 (2016-05-24)
''''''''''''''''

- Added the ``GET /contribute.json`` endpoint for open-source information.


1.5 (2016-04-21)
''''''''''''''''

- Allow groups to get arbitrary attributes.

1.4 (2016-03-08)
''''''''''''''''

- Allow bucket to get arbitrary attributes.
- Delete every (writable) buckets using ``DELETE /v1/buckets``
- Delete every (writable) collections using ``DELETE /v1/buckets/<bucket-id>/collections``
- URLs with trailing slash are redirected only if the current URL does not exist
- Partial responses can now be specified for nested objects.
  For example, ``/records?_fields=address.street``.
- List responses are now sorted by last_modified descending by default
- Return 415 error response if client cannot accept JSON response
- Return 415 error response if client does not send JSON request
- Add the ``GET /v1/__lbheartbeat__`` endpoint, for load balancer membership test

.. note::

    The ``capabilities`` object in the :ref:`root URL <api-utilities>` response
    now contains some ``flush_endpoint``, ``schema``, and ``default_bucket`` entries
    if the features are enabled in settings (#270).

1.3 (2016-01-28)
''''''''''''''''

- Forward slashes (``/``) are not escaped anymore in JSON responses (#537)
- The API capabilities can be exposed in a ``capabilities`` attribute in the
  root URL (#628). Clients can rely on this to detect optional features on the
  server (e.g. enabled plugins).


1.2 (2016-01-15)
''''''''''''''''

- Fields can be filtered in GET requests using ``_fields=f1,f2`` in querystring
- New collections can be created via ``POST`` requests


1.1 (2015-12-01)
''''''''''''''''

- Renamed fields in the :ref:`root URL view <api-utilities>`
- Added user information like user id and default bucket id in
  :ref:`root URL view <api-utilities>`


1.0 (2015-06-17)
''''''''''''''''

- Initial working version.
