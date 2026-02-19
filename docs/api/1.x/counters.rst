.. _api-counters:


Counters Endpoint
#################


The Counters endpoint exposes the number of objects per resource in storage. You can enable it by including ``kinto.plugins.counters``
to your configuration file.


.. http:get:: /__counters__
    :synopsis: retrieve the number of objects per resource.

    **Example Request**

    .. sourcecode:: bash

        $ http GET "http://localhost:8888/v1/__counters__" --verbose

    .. sourcecode:: http

        GET /v1/__counters__ HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate, zstd
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/3.2.4

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Content-Length, Content-Type, Alert
        Content-Length: 182
        Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none';
        Content-Type: application/json
        Date: Wed, 18 Feb 2026 10:59:05 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {
            "objects": {
                "account": 23,
                "bucket": 10,
                "collection": 310,
                "group": 213,
                "history": 22186,
                "record": 34547
            },
            "tombstones": {
                "account": 1,
                "collection": 70,
                "group": 51,
                "history": 6875,
                "record": 99282
            }
        }
