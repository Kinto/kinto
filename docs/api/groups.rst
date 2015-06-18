.. _groups:

Groups
######

A group associates a name to a list of principals. It is useful in order to
handle permissions. Groups are handled in buckets.

A group is a mapping with the following attributes:

* ``members``: a list of :term:`principals <principal>`
* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the group object
  (e.g who has the rights to read or update the group itself.)

Creating a group
================

.. http:post:: /buckets/(bucket_id)/groups

    **Requires authentication**

    Creates a new bucket's group with a generated id.

    .. sourcecode:: bash

        $ echo '{"data": {"members": ["basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"]}}' | http POST :8888/v1/buckets/blog/groups --auth="bob:" --verbose

    **Example Request**

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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            },
            "permissions": {
                "write": [
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

Replacing a group
=================

.. http:post:: /buckets/(bucket_id)/groups/(group_id)

    **Requires authentication**

    Creates or replaces a group with a chosen id.

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"members": ["basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"]}}' | http put :8888/v1/buckets/blog/groups/readers --auth="bob:" --verbose

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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            },
            "permissions": {
                "write": [
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    .. note::

        In order to create only if does not exist yet, a ``If-None-Match: *``
        request header can be provided. A ``412 Precondition Failed`` error
        response will be returned if the record already exists.

Retrieving a group
==================

.. http:get:: /buckets/(bucket_idà/groups/(group_id)

    **Requires authentication**

    Returns the group object.

    **Example Request**

    .. sourcecode:: bash

        $ http get :8888/v1/buckets/blog/groups/readers --auth="bob:" --verbose

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
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            },
            "permissions": {
                "write": [
                    "basicauth_206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

Deleting a group
================

.. http:delete:: /buckets/(bucket_id)/groups/(group_id)

    **Requires authentication**

    Deletes a specific group.

    **Example Request**

    .. sourcecode:: bash

        $ http delete :8888/v1/buckets/blog/groups/readers --auth="bob:" --verbose

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
