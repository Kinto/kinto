.. _api-flush:


Flush Endpoint
##############


The Flush endpoint is used to flush (completely remove) all data from the
database backend. While this can be useful during development, but can be
dangerous at production. You can enable it including ``kinto.plugins.flush``
to your configuration file.


.. http:post:: /__flush__

    :synopsis: flush all the server data.

    **Optional authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http POST "http://localhost:8888/v1/__flush__" --verbose

    .. sourcecode:: http

        POST /v1/__flush__ HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.8

  **Example Response**

  .. sourcecode:: http

        HTTP/1.1 202 Accepted
        Content-Length: 2
        Content-Type: application/json
        Date: Thu, 09 Mar 2017 03:54:19 GMT
        Server: waitress
        X-Content-Type-Options: nosniff

        {}
