.. _selecting-fields:

Selecting fields
################

On ``GET`` requests with both plural and singular endpoints,
if the ``_fields`` parameter is provided, only the specified fields
are returned. The field names are separated with a comma.

This is vital in mobile contexts where bandwidth usage must be optimized.

Nested objects fields are specified using dots (e.g. ``address.street``).

.. note::

    The ``id`` and ``last_modified`` fields are always returned.

**Request**:

.. code-block:: http

    GET /articles?_fields=title,url HTTP/1.1
    Accept: application/json
    Authorization: Basic bWF0Og==
    Host: localhost:8000


**Response**:

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Allow-Origin: *
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, ETag, Next-Page, Total-Records, Last-Modified
    Content-Length: 436
    Content-Type: application/json; charset=UTF-8
    Date: Tue, 28 Apr 2015 12:08:11 GMT
    Last-Modified: Mon, 12 Apr 2015 11:12:07 GMT
    ETag: "1430222877724"
    Total-Records: 2

    {
        "data": [
            {
                "id": "dc86afa9-a839-4ce1-ae02-3d538b75496f",
                "last_modified": 1430222877724,
                "title": "MoCo",
                "url": "https://mozilla.com",
            },
            {
                "id": "23160c47-27a5-41f6-9164-21d46141804d",
                "last_modified": 1430140411480,
                "title": "MoFo",
                "url": "https://mozilla.org",
            }
        ]
    }
