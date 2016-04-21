API
===

.. toctree::
   :maxdepth: 2

   versioning
   1.x/index


Changelog
---------

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
