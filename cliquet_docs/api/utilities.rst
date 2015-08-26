.. _api-utilities:

Utility endpoints for OPS and Devs
##################################

GET /
=====

The returned value is a JSON mapping containing:

- ``hello``: the name of the service (e.g. ``"reading list"``)
- ``version``: complete version (``"X.Y.Z"``)
- ``commit``: the HEAD git revision number when run from a git repository.
- ``url``: absolute URI (without a trailing slash) of the API (*can be used by client to build URIs*)
- ``eos``: date of end of support in ISO 8601 format (``"yyyy-mm-dd"``, undefined if unknown)
- ``documentation``: The URL to the service documentation. (this document!)
- ``settings``: a mapping with the values of relevant public settings for clients
    - ``cliquet.batch_max_requests``: Number of requests that can be made in a batch request.
- ``userid``: The connected perso user id. The field is not present
  when no Authorization header is provided.


GET /__heartbeat__
==================

Return the status of each service the application depends on. The
returned value is a JSON mapping containing:

- ``storage`` true if operational
- ``cache`` true if operational
- ``oauth`` true if operational, or `null` if not enabled

Return ``200`` if the connection with each service is working properly
and ``503`` if something doesn't work.
