.. _api-utilities:

Utility endpoints for OPS and Devs
##################################

GET /
=====

The returned value is a JSON mapping containing:

.. versionchanged:: 2.12

- ``project_name``: the name of the service (e.g. ``"reading list"``)
- ``project_docs``: The URL to the service documentation. (this document!)
- ``project_version``: complete application/project version (``"3.14.116"``)
- ``http_api_version``: the MAJOR.MINOR version of the exposed HTTP API (``"1.1"``)
  defined in configuration.
- ``cliquet_protocol_version``: the cliquet protocol version (``"2"``)
- ``url``: absolute URI (without a trailing slash) of the API (*can be used by client to build URIs*)
- ``eos``: date of end of support in ISO 8601 format (``"yyyy-mm-dd"``, undefined if unknown)
- ``settings``: a mapping with the values of relevant public settings for clients

  - ``batch_max_requests``: Number of requests that can be made in a batch request.
  - ``readonly``: Only requests with read operations are allowed.

- ``capabilities``: a mapping used by clients to detect optional features of the API.

  - Example:

    .. code-block:: javascript

        {
          "auth-fxa": {
            "description": "Firefox Account authentication",
            "url": "http://github.com/mozilla-services/cliquet-fxa"
          }
        }

**Optional**

- ``user``: A mapping with an ``id`` field for the currently connected user id.
  The field is not present when no Authorization header is provided.


.. note::

    The ``project_version`` contains the source code version, whereas the ``http_api_version`` contains the exposed :term:`HTTP API` version.

    The source code of the service can suffer changes and have its *project version*
    incremented, without impacting the publicly exposed HTTP API.

    The ``cliquet_protocol_version`` is an internal notion tracking the version
    for some aspects of the API (e.g. synchronization of REST resources, utilities endpoints, etc.). It will differ from the ``http_api_version`` since the service
    will provide additionnal endpoints and conventions.


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


GET /__lbheartbeat__
====================

Always return ``200`` with empty body.

Unlike the ``__heartbeat__`` health check endpoint, which return an error
when backends and other upstream services are unavailable, this should
always return 200.

This endpoint is suitable for a load balancer membership test.
It the load balancer cannot obtain a response from this endpoint, it will
stop sending traffic to the instance and replace it.
