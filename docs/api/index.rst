API
===

.. toctree::
   :maxdepth: 2

   versioning
   1.x/index


Changelog
---------

1.4 (unreleased)
''''''''''''''''

- Allow bucket to get arbitrary attributes.
- URLs with trailing slash are redirected only if the current URL does not exist
- Partial responses can now be specified for nested objects.
  For example, ``/records?_fields=address.street``.
- List responses are now sorted by last_modified descending by default
- Return 415 error response if client cannot accept JSON response
- Return 415 error response if client does not send JSON request


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
