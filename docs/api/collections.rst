.. _collections:

Collections
###########

A collection belongs to a bucket and stores records.

A collection is a mapping with the following attribute:

* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the collection object

.. note::

    By default users are assigned to a bucket that is used for their
    personal data.

    Application can use this default bucket with the ``default``
    shortcut: ie ``/buckets/default/collections/contacts`` will be
    the current user contacts.

    Internally the user default bucket is assigned to an id that can
    later be used to share data from a user personnal bucket.

    Collection on a the default bucket are created silently on first access.


.. _collection-put:

Creating a collection
=====================


.. http:put:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Creates or replaces a collection object.

    **Requires authentication**

    A collection is the parent object of records. It can be viewed as a container where records permissions are assigned globally.

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {}}' | http put http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:" --verbose

    .. sourcecode:: http

        PUT /v1/buckets/blog/collections/articles HTTP/1.1
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

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 159
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:36:34 GMT
        Server: waitress

        {
            "data": {
                "id": "articles",
                "last_modified": 1434641794149
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


.. _collection-get:

Retrieving an existing collection
=================================

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Returns the collection object.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/collections/articles HTTP/1.1
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
        Content-Length: 159
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:52:31 GMT
        Etag: "1434642751314"
        Last-Modified: Thu, 18 Jun 2015 15:52:31 GMT
        Server: waitress

        {
            "data": {
                "id": "articles",
                "last_modified": 1434641794149
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


.. _collection-delete:

Deleting a collection
=====================

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Deletes a specific collection, and **everything under it**.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/collections/articles HTTP/1.1
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
        Content-Length: 71
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:54:02 GMT
        Server: waitress

        {
            "data": {
                "deleted": true,
                "id": "articles",
                "last_modified": 1434642842010
            }
        }
