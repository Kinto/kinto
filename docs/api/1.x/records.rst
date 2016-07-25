.. _records:

Records
#######

Records belong to a collection. It is the data being stored and
synchronised.

A record is a mapping with the following attributes:

* ``data``: attributes of the record object
    * ``id``: the record object id
    * ``last_modified``: the timestamp of the last modification
* ``permissions``: the :term:`ACLs <ACL>` for the collection object


.. _records-post:

Uploading a record
==================

.. http:post:: /buckets/(bucket_id)/collections/(collection_id)/records

    :synopsis: Store a record in the collection. The ID will be assigned automatically.


    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"foo": "bar"}}' | http post http://localhost:8888/v1/buckets/blog/collections/articles/records --auth="token:bob-token" --verbose

    .. sourcecode:: http

        POST /v1/buckets/blog/collections/articles/records HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 25
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {
                "foo": "bar"
            }
        }

  **Example Response**

  .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 199
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:02:23 GMT
        Server: waitress

        {
            "data": {
                "foo": "bar",
                "id": "89881454-e4e9-4ef0-99a9-404d95900352",
                "last_modified": 1434646943915
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

.. include:: _details-post-list.rst

.. include:: _status-post-list.rst


.. _record-put:

Replacing a record
===================

.. http:put:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    :synopsis: Create or update a record in the collection.

    The POST body is a JSON mapping containing:

    - ``data``: the fields of the record;
    - ``permissions``: *optional* a json dict containing the permissions for
      the record to be created.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"foo": "baz"}}' | http put http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="token:bob-token" --verbose

    .. sourcecode:: http

        PUT /v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 25
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
          "data": {
              "foo": "baz"
          }
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 199
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:16:22 GMT
        Server: waitress

        {
          "data": {
              "foo": "baz",
              "id": "89881454-e4e9-4ef0-99a9-404d95900352",
              "last_modified": 1434647782623
          },
          "permissions": {
              "write": [
                  "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
              ]
          }
        }

.. include:: _details-put-object.rst

.. include:: _status-put-object.rst


.. _record-patch:

Updating a record
=================

.. http:patch:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    :synopsis: Update a record in the collection. Specify only the fields to be
               modified (all the rest will remain intact).

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"status": "done"}}' | http patch http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="token:bob-token" --verbose

    .. sourcecode:: http

        PATCH /v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 25
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
          "data": {
              "status": "done"
          }
        }

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 211
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:19:56 GMT
        Server: waitress

        {
          "data": {
              "status": "done",
              "title": "Midnight in Paris",
              "id": "89881454-e4e9-4ef0-99a9-404d95900352",
              "last_modified": 1434647996969
          },
          "permissions": {
              "write": [
                  "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
              ]
          }
        }

.. include:: _details-patch-object.rst

.. include:: _status-patch-object.rst


.. _records-get:

Retrieving stored records
=========================

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)/records

    :synopsis: Retrieve all the records in the collection.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles/records --auth="token:bob-token" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/collections/articles/records HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Next-Page, Total-Records, Last-Modified, ETag
        Content-Length: 110
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:24:38 GMT
        Etag: "1434648278603"
        Last-Modified: Thu, 18 Jun 2015 17:24:38 GMT
        Server: waitress
        Total-Records: 1

        {
            "data": [
                {
                    "baz": "bar",
                    "foo": "baz",
                    "id": "89881454-e4e9-4ef0-99a9-404d95900352",
                    "last_modified": 1434647996969
                }
            ]
        }


.. _record-get:

Retrieving a specific record
============================

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    :synopsis: Retrieve a specific record by its ID.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="token:bob-token" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 HTTP/1.1
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
        Content-Length: 211
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:29:59 GMT
        Etag: "1434648599199"
        Last-Modified: Thu, 18 Jun 2015 17:29:59 GMT
        Server: waitress

        {
            "data": {
                "baz": "bar",
                "foo": "baz",
                "id": "89881454-e4e9-4ef0-99a9-404d95900352",
                "last_modified": 1434647996969
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


.. _records-delete:

Delete stored records
=====================

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)/records

    :synopsis: Delete all the records in the collection.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections/articles/records --auth="token:bob-token" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/collections/articles/records HTTP/1.1
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
        Content-Length: 211
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:29:59 GMT
        Etag: "1434648599199"
        Last-Modified: Thu, 18 Jun 2015 17:29:59 GMT
        Server: waitress

        {
            "data": [{
                "deleted": true,
                "id": "89881454-e4e9-4ef0-99a9-404d95900352",
                "last_modified": 1434648749173
            }]
        }


.. _record-delete:

Deleting a single record
========================

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    :synopsis: Delete a record by its ID.

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="token:bob-token" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 HTTP/1.1
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
        Content-Length: 99
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 17:32:29 GMT
        Server: waitress

        {
            "data": {
                "deleted": true,
                "id": "89881454-e4e9-4ef0-99a9-404d95900352",
                "last_modified": 1434648749173
            }
        }
