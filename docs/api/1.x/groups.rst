.. _groups:

Groups
######

A group associates a name to a list of :ref:`principals <api-principals>`.
It is useful in order to handle permissions. Groups are defined in buckets.

A group is a mapping with the following attributes:

* ``data``: attributes of the group object
    * ``id``: the group object id
    * ``last_modified``: the timestamp of the last modification
    * ``members``: a list of :ref:`principals <api-principals>`
* ``permissions``: the :term:`ACLs <ACL>` for the group object
  (e.g who is allowed to read or update the group object itself.)


When used in permissions definitions, the full group URI has to be used:

.. code-block:: none

    {
        "write": ["/buckets/blog/groups/authors", "github:lili"],
        "read": ["system.Everyone"]
    }


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

.. include:: _status-post-list.rst


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

.. include:: _details-put-object.rst

.. include:: _status-put-object.rst


.. _group-patch:

Modify a group
==============

.. http:patch:: /buckets/(bucket_id)/groups/(group_id)

    :synopsis: Modifies an existing group.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"members": ["basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"]}}' | http patch http://localhost:8888/v1/buckets/blog/groups/readers --auth="token:bob-token" --verbose

    .. sourcecode:: http

        PATCH /v1/buckets/blog/groups/readers HTTP/1.1
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

        HTTP/1.1 200 OK
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

.. include:: _details-patch-object.rst

.. include:: _status-patch-object.rst


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

.. include:: _details-get-object.rst

.. include:: _status-get-object.rst


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

.. include:: _details-get-list.rst

.. include:: _status-get-list.rst


.. _groups-delete:

Deleting all groups
===================

.. http:delete:: /buckets/(bucket_id)/groups

    :synopsis: Delete every writable group in the bucket.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/groups --auth="token:bob-token" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/groups HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic dG9rZW46Ym9iLXRva2Vu
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.3

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
        Content-Length: 72
        Content-Type: application/json; charset=UTF-8
        Date: Sun, 20 Nov 2016 03:04:57 GMT
        Server: waitress

        {
            "data": [
                {
                    "deleted": true,
                    "id": "readers",
                    "last_modified": 1479611097155
                }
            ]
        }



.. include:: _details-delete-list.rst

.. include:: _status-delete-list.rst


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

.. include:: _details-delete-object.rst

.. include:: _status-delete-object.rst
