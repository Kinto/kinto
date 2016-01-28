.. _groups:

Groups
######

A group associates a name to a list of :term:`principals <principal>`.
It is useful in order to handle permissions. Groups are defined in buckets.

A group is a mapping with the following attributes:

* ``members``: a list of :term:`principals <principal>`
* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the group object
  (e.g who is allowed to read or update the group itself.)

.. _groups-post:

Creating a group
================

.. http:post:: /buckets/(bucket_id)/groups

    :synopsis: Creates a new bucket group with a generated ID.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"members": ["basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"]}}' | http POST http://localhost:8888/v1/buckets/blog/groups --auth="token:bob-token" --verbose

    .. sourcecode:: http

        POST /v1/buckets/blog/groups HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 102
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {
                "members": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 248
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 16:17:02 GMT
        Server: waitress

        {
            "data": {
                "id": "wZjuQfpS",
                "last_modified": 1434644222033,
                "members": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

.. _group-put:

Replacing a group
=================

.. http:put:: /buckets/(bucket_id)/groups/(group_id)

    :synopsis: Creates or replaces a group with a chosen ID.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"members": ["basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"]}}' | http put http://localhost:8888/v1/buckets/blog/groups/readers --auth="token:bob-token" --verbose

    .. sourcecode:: http

        PUT /v1/buckets/blog/groups/readers HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 102
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {
                "members": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 247
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 16:41:01 GMT
        Server: waitress

        {
            "data": {
                "id": "readers",
                "last_modified": 1434645661227,
                "members": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    .. note::

        In order to create only if does not exist yet, a ``If-None-Match: *``
        request header can be provided. A ``412 Precondition Failed`` error
        response will be returned if the record already exists.

.. _group-get:

Retrieving a group
==================

.. http:get:: /buckets/(bucket_id)/groups/(group_id)

    :synopsis: Returns the group object.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/groups/readers --auth="token:bob-token" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/groups/readers HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified, ETag
        Content-Length: 247
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 16:44:07 GMT
        Etag: "1434645847532"
        Last-Modified: Thu, 18 Jun 2015 16:44:07 GMT
        Server: waitress

        {
            "data": {
                "id": "readers",
                "last_modified": 1434645661227,
                "members": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


.. _groups-get:

Retrieving all groups
=====================

.. http:get:: /buckets/(bucket_id)/groups

    :synopsis: Returns the list of groups for the bucket.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/groups --auth="token:bob-token" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/groups HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Total-Records, Last-Modified, ETag
        Content-Length: 147
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 13 Aug 2015 12:16:05 GMT
        Etag: "1439468156451"
        Last-Modified: Thu, 13 Aug 2015 12:15:56 GMT
        Server: waitress
        Total-Records: 1

        {
            "data": [
                {
                    "id": "vAQSwSca",
                    "last_modified": 1439468156451,
                    "members": [
                        "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                    ]
                }
            ]
        }



.. _group-delete:

Deleting a group
================

.. http:delete:: /buckets/(bucket_id)/groups/(group_id)

    :synopsis: Deletes a specific group.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/groups/readers --auth="token:bob-token" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/groups/readers HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 70
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 16:47:29 GMT
        Server: waitress

        {
            "data": {
                "deleted": true,
                "id": "readers",
                "last_modified": 1434646049488
            }
        }
