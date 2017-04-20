.. _buckets:

Buckets
#######

A bucket is the parent object of collections and groups.

A bucket is a mapping with the following attributes:

* ``data``: (*optional*) attributes of the bucket object
    * ``id``: the bucket object id
    * ``last_modified``: the timestamp of the last modification
* ``permissions``: the :term:`ACLs <ACL>` for the bucket object


.. _buckets-post:

Creating a bucket
=================

.. http:post:: /buckets

    :synopsis: Creates a new bucket. If ``id`` is not provided, it is automatically generated.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"id": "blog"}}' | http POST http://localhost:8888/v1/buckets --auth="token:bob-token" --verbose

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

A bucket also accept arbitrary attributes.
For example, you may want to store some application settings there.

.. include:: _details-post-list.rst

.. include:: _status-post-list.rst


.. _bucket-put:

Replacing a bucket
==================

.. http:put:: /buckets/(bucket_id)

    :synopsis: Creates or replaces a bucket with a specific ID.

    **Requires authentication**

    If the bucket exists but you don't have the ``write`` permission,
    you will get a |status-403| http response.

    **Example request**

    .. sourcecode:: bash

        $ http put http://localhost:8888/v1/buckets/blog --auth="token:bob-token"

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

.. include:: _details-put-object.rst

.. include:: _status-put-object.rst


.. _bucket-get:

Retrieve an existing bucket
===========================

.. http:get:: /buckets/(bucket_id)

    :synopsis: Returns a specific bucket by its ID.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog --auth="token:bob-token" --verbose

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

.. include:: _details-get-object.rst

.. include:: _status-get-object.rst


.. _bucket-patch:

Updating an existing bucket
===========================

.. http:patch:: /buckets/(bucket_id)

    :synopsis: Modifies an existing bucket.

    **Requires authentication**

.. include:: _details-patch-object.rst

.. include:: _status-patch-object.rst


.. _bucket-delete:

Deleting a bucket
=================

.. http:delete:: /buckets/(bucket_id)

    :synopsis: Deletes a specific bucket and **everything under it**.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog --auth="token:bob-token" --verbose

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

.. include:: _details-delete-object.rst

.. include:: _status-delete-object.rst


.. _buckets-get:

Retrieving all buckets
======================

.. http:get:: /buckets

    :synopsis: Returns the list of accessible buckets

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets --auth="token:bob-token" --verbose

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

.. include:: _details-get-list.rst

.. include:: _status-get-list.rst


.. _buckets-delete:

Delete all buckets
=======================

.. http:delete:: /buckets

    :synopsis: Delete every writable buckets for this user

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets --auth="token:bob-token" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic YWxpY2U6
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
        Content-Length: 101
        Content-Type: application/json; charset=UTF-8
        Date: Fri, 26 Feb 2016 14:12:22 GMT
        Server: waitress

        {
            "data": [
                {
                    "deleted": true,
                    "id": "e64db3f9-6a60-1acf-fc3a-7d1ba7e823aa",
                    "last_modified": 1456495942515
                }
            ]
        }

.. include:: _details-delete-list.rst

.. include:: _status-delete-list.rst


.. _buckets-default-id:

Personal bucket «default»
=========================

When the built-in plugin ``kinto.plugins.default_bucket`` is enabled in configuration, a bucket ``default`` is available.

As explained in the :ref:`section about collections<collections>`, the ``default``
bucket implicitly creates the collections objects on their first use.


.. http:get:: /buckets/default

    :synopsis: Returns the current user personnal bucket.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/default -v --auth='token:bob-token'

    .. sourcecode:: http

        GET /v1/buckets/default HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.8.0

    **Example Response**

    .. sourcecode:: http
        :emphasize-lines: 12

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Content-Length, Expires, Alert, Retry-After, Last-Modified, ETag, Pragma, Cache-Control, Backoff
        Content-Length: 187
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 28 Oct 2015 16:29:00 GMT
        Etag: "1446049740955"
        Last-Modified: Wed, 28 Oct 2015 16:29:00 GMT
        Server: waitress

        {
            "data": {
                "id": "b8f3fa97-3e0a-00ae-7f07-ce8ce05ce0e5",
                "last_modified": 1446049740955
            },
            "permissions": {
                "write": [
                    "basicauth:62e79bedacd2508c7da3dfb16e9724501fb4bdf9a830de7f8abcc8f7f1496c35"
                ]
            }
        }


For convenience, the actual default bucket id is provided in the root URL of *Kinto*:

.. http:get:: /

    :synopsis: Obtain current user personnal bucket in root URL.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/ -v --follow --auth='token:bob-token'

    **Example Response**

    .. sourcecode:: http
        :emphasize-lines: 19

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
        Content-Length: 400
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 28 Oct 2015 16:52:49 GMT
        Server: waitress

        {
            "hello": "kinto",
            "version": "1.7.0.dev0"
            "url": "http://localhost:8888/v1/",
            "documentation": "https://kinto.readthedocs.io/",
            "settings": {
                "batch_max_requests": 25,
            },
            "user": {
                "id": "basicauth:62e79bedacd2508c7da3dfb16e9724501fb4bdf9a830de7f8abcc8f7f1496c35",
                "bucket": "b8f3fa97-3e0a-00ae-7f07-ce8ce05ce0e5",
            }
        }
