.. _api-utilities:

Utility endpoints for OPS and Devs
##################################

GET /
=====

The returned value is a JSON mapping containing:

- ``hello``: the name of the service (e.g. ``"reading list"``)
- ``protocol_version``: the cliquet protocol version (``"2"``)
- ``version``: complete application/project version (``"X.Y.Z"``)
- ``url``: absolute URI (without a trailing slash) of the API (*can be used by client to build URIs*)
- ``eos``: date of end of support in ISO 8601 format (``"yyyy-mm-dd"``, undefined if unknown)
- ``documentation``: The URL to the service documentation. (this document!)
- ``settings``: a mapping with the values of relevant public settings for clients
    - ``batch_max_requests``: Number of requests that can be made in a batch request.
    - ``readonly``: Only requests with read operations are allowed.
- ``user``: A mapping with an ``id`` field for the currently connected user id.
   The field is not present when no Authorization header is provided.


GET /__heartbeat__
==================

Return the status of each service the application depends on. The
returned value is a JSON mapping containing:

- ``storage`` true if storage backend is operational
- ``cache`` true if cache backend operational
- ``permission`` true if permission backend operational

If ``cliquet-fxa`` is installed, an additional key is present:

- ``oauth`` true if authentication is operational

Return ``200`` if the connection with each service is working properly
and ``503`` if something doesn't work.
