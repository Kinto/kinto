.. _api-utilities:

Utility endpoints for OPS and Devs
##################################

GET /
=====

The returned value is a JSON mapping containing:

.. versionchanged:: 3.0

- ``project_name``: the name of the service (e.g. ``"reading list"``)
- ``project_docs``: The URL to the service documentation. (this document!)
- ``project_version``: complete application/project version (``"3.14.116"``)
- ``http_api_version``: the MAJOR.MINOR version of the exposed HTTP API (``"1.1"``)
  defined in the project.
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
            "url": "http://github.com/mozilla-services/kinto-fxa"
          }
        }

**Optional**

- ``user``: A mapping with an ``id`` field and a list of ``principals``
  for the currently connected user id.
  The field is not present when no Authorization header is provided.


.. note::

    The ``project_version`` contains the source code version, whereas the ``http_api_version`` contains the exposed :term:`HTTP API` version.

    The source code of the service can suffer changes and have its *project version*
    incremented, without impacting the publicly exposed HTTP API.


GET /__heartbeat__
==================

Return the status of each service the application depends on. The
returned value is a JSON mapping containing:

- ``storage`` true if storage backend is operational
- ``cache`` true if cache backend operational
- ``permission`` true if permission backend operational

If ``kinto-fxa`` is installed, an additional key is present:

- ``oauth`` true if authentication is operational

Return |status-200| if the connection with each service is working properly
and |status-503| if something doesn't work.


GET /__lbheartbeat__
====================

Always return |status-200| with empty body.

Unlike the ``__heartbeat__`` health check endpoint, which return an error
when backends and other upstream services are unavailable, this should
always return |status-200|.

This endpoint is suitable for a load balancer membership test.
It the load balancer cannot obtain a response from this endpoint, it will
stop sending traffic to the instance and replace it.


.. _api-utilities-contribute:

GET /contribute.json
====================

The returned value is a JSON mapping containing open source contribution
information as advocated by https://www.contributejson.org


.. _api-utilities-version:

GET /__version__
==================

Return a JSON mapping containing information about what distribution
has been deployed by OPs.

::

    {
      "name":"kinto",
      "version":"3.3.2",
      "commit":"ab8db089ee63dc8e14f4bcfc427a86f311dd7e52",
      "source":"https://github.com/Kinto/kinto.git"
    }

The content of this view comes from a file, whose location is
specified via the ``kinto.version_json_path`` setting or ``KINTO_VERSION_JSON_PATH``
environment variable (*default location is* ``version.json`` *in current working directory*).

Return |status-404| if no ``version.json`` file is found.
