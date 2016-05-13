################
Batch operations
################

.. _batch:

POST /batch
===========

**Requires authentication**

The POST body is a mapping, with the following attributes:

- ``requests``: the list of requests
- ``defaults``: (*optional*) default requests values in common for all requests

 Each request is a JSON mapping, with the following attribute:

- ``method``: HTTP verb
- ``path``: URI
- ``body``: a mapping
- ``headers``: (*optional*), otherwise take those of batch request


.. code-block:: http

    POST /batch HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Content-Length: 728
    Host: localhost:8888
    User-Agent: HTTPie/0.9.2

    {
      "defaults": {
        "method" : "POST",
        "path" : "/articles",
      },
      "requests": [
        {
          "body" : {
            "data" : {
              "title": "MoFo",
              "url" : "http://mozilla.org",
              "added_by": "FxOS",
            },
            "permissions": {
              "read": ["system.Everyone"]
            }
          }
        },
        {
          "body" : {
            "data" : {
              "title": "MoCo",
              "url" : "http://mozilla.com"
              "added_by": "FxOS",
            }
          }
        },
        {
          "method" : "PATCH",
          "path" : "/articles/409",
          "body" : {
            "data" : {
              "read_position" : 3477
            }
          }
          "headers" : {
            "Response-Behavior": "light"
          }
        }
      ]
    }


The response body is a list of all responses:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
    Content-Length: 1674
    Date: Wed, 17 Feb 2016 18:44:39 GMT
    Server: waitress

    {
      "responses": [
        {
          "status": 201,
          "path" : "/articles",
          "body" : {
            "data" : {
              "id": 411,
              "title": "MoFo",
              "url" : "http://mozilla.org",
              ...
            }
          },
          "headers": {
            ...
          }
        },
        {
          "status": 201,
          "path" : "/articles",
          "body" : {
            "data" : {
              "id": 412,
              "title": "MoCo",
              "url" : "http://mozilla.com",
              ...
            }
          },
          "headers": {
            ...
          }
        },
        {
          "status": 200,
          "path" : "/articles/409",
          "body" : {
            "data" : {
              "id": 409,
              "url": "...",
              ...
              "read_position" : 3477
            }
          },
          "headers": {
            ...
          }
        }
      ]
    }

HTTP Status Codes
-----------------

* ``200 OK``: The request has been processed
* ``400 Bad Request``: The request body is invalid
* ``50X``: One of the sub-request has failed with a ``50X`` status

.. warning::

    Since the requests bodies are necessarily mappings, posting arbitrary data
    (*like raw text or binary*) is not supported.

.. note::

     Responses are executed and provided in the same order than requests.


About transactions
------------------

The whole batch of requests is executed under one transaction only.

In order words, if one of the sub-request fails with a 503 status for example, then
every previous operation is rolled back.

.. important::

    With the current implementation, if a sub-request fails with a 4XX status
    (eg. ``412 Precondition failed`` or ``403 Unauthorized`` for example) the
    transaction is **not** rolled back.
