.. _buckets:

Buckets
#######

A bucket is the parent object of collections and groups. It can be viewed as
a namespace where all collection and groups are stored.

A bucket is a mapping with the following attributes:

* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the bucket object

Creating a bucket
=================


.. http:put:: /buckets/(bucket_id)

    **Requires authentication**

    Creates or replaces a bucket with a specific id.

    If the bucket exists and you don't have the ``write`` permission on
    it, you will get a ``403 Forbidden`` http response.

    **Example request**

    .. sourcecode:: bash

        $ echo '{"data": {}}' | http put :8888/v1/buckets/blog --auth="bob:"

    .. sourcecode:: http

        PUT /v1/buckets/blog HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 13
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {}
        }

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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    .. note::

        In order to create only if it does not exist yet, a ``If-None-Match: *``
        request header can be provided. A ``412 Precondition Failed`` error response
        will be returned if the record already exists.

Retrieve an already existing bucket
===================================

.. http:get:: /buckets/(bucket_id)

    **Requires authentication**

    Returns a specific bucket by its id.

    **Example request**

    .. sourcecode:: bash

        $ http get :8888/v1/buckets/blog --auth="bob:" --verbose

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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

Updating an existing bucket
===========================

.. http:put:: /buckets/(bucket_id)

    **Requires authentication**

    Modifies an existing bucket.

    .. note::

        Until a formalism is found to alter ACL principals (e.g. using ``+`` or ``-``)
        there is no difference in the behaviour between PATCH and PUT.

Deleting a bucket
=================


.. http:delete:: /buckets/(bucket_id)

    **Requires authentication**

    Deletes a specific bucket, and **everything under it**.

    **Example request**

    .. sourcecode:: bash

        $ http delete :8888/v1/buckets/blog --auth="bob:" --verbose

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
