.. _buckets:

Buckets
#######

A bucket is the parent object of collections and groups.

A bucket is a mapping with the following attributes:

* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the bucket object


.. _buckets-post:

Creating a bucket
=================

.. http:post:: /buckets

    :synopsis: Creates a new bucket. If ``id`` is not provided, it is automatically generated.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"id": "blog"}}' | http POST http://localhost:8888/v1/buckets --auth="bob:" --verbose

    .. sourcecode:: http

        POST /v1/buckets HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 25
        Content-Type: application/json; charset=utf-8
        Host: localhost:8888
        User-Agent: HTTPie/0.8.0

        {
            "data": {
                "id": "blog"
            }
        }


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
        Content-Length: 155
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 10 Sep 2015 08:34:32 GMT
        Server: waitress

        {
            "data": {
                "id": "blog",
                "last_modified": 1441874072429
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


.. _bucket-put:

Replacing a bucket
==================

.. http:put:: /buckets/(bucket_id)

    :synopsis: Creates or replaces a bucket with a specific ID.

    **Requires authentication**

    If the bucket exists but you don't have the ``write`` permission,
    you will get a ``403 Forbidden`` http response.

    **Example request**

    .. sourcecode:: bash

        $ http put http://localhost:8888/v1/buckets/blog --auth="bob:"

    .. sourcecode:: http

        PUT /v1/buckets/blog HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 155
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:19:10 GMT
        Server: waitress

        {
            "data": {
                "id": "blog",
                "last_modified": 1434640750988
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    .. note::

        In order to create only if it does not exist yet, a ``If-None-Match: *``
        request header can be provided. A ``412 Precondition Failed`` error response
        will be returned if the record already exists.


.. _bucket-get:

Retrieve an existing bucket
===========================

.. http:get:: /buckets/(bucket_id)

    :synopsis: Returns a specific bucket by its ID.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog --auth="bob:" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 13
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified, ETag
        Content-Length: 155
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:25:19 GMT
        Etag: "1434641119102"
        Last-Modified: Thu, 18 Jun 2015 15:25:19 GMT
        Server: waitress

        {
            "data": {
                "id": "blog",
                "last_modified": 1434640750988
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


.. _bucket-patch:

Updating an existing bucket
===========================

.. http:patch:: /buckets/(bucket_id)

    :synopsis: Modifies an existing bucket.

    **Requires authentication**

    .. note::

        Until a formalism is found to alter ACL principals (e.g. using ``+`` or ``-``)
        there is no difference in the behaviour between PATCH and PUT.


.. _bucket-delete:

Deleting a bucket
=================

.. http:delete:: /buckets/(bucket_id)

    :synopsis: Deletes a specific bucket and **everything under it**.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog --auth="bob:" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 67
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:29:42 GMT
        Server: waitress

        {
            "data": {
                "deleted": true,
                "id": "blog",
                "last_modified": 1434641382954
            }
        }


.. _buckets-get:

Retrieving all buckets
======================

.. http:get:: /buckets

    :synopsis: Returns the list of accessible buckets

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets --auth="bob:" --verbose

    .. sourcecode:: http

        GET /v1/buckets HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.8.0

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Total-Records, Last-Modified, ETag
        Content-Length: 54
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 10 Sep 2015 08:37:32 GMT
        Etag: "1441874072429"
        Last-Modified: Thu, 10 Sep 2015 08:34:32 GMT
        Server: waitress
        Total-Records: 1

        {
            "data": [
                {
                    "id": "blog",
                    "last_modified": 1441874072429
                }
            ]
        }
