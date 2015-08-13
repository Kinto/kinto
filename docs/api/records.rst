.. _records:

Records
#######

Records belong to a collection. It is the data being stored and
synchronized.

.. _records-post:

Uploading a record
==================

.. http:post:: /buckets/(bucket_id)/collections/(collection_id)/records

    **Requires authentication**

    Stores a record in the collection, and its id will be assigned automatically.

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"foo": "bar"}}' | http post http://localhost:8888/v1/buckets/blog/collections/articles/records --auth="bob:" --verbose


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

.. _record-put:

Replacing a record
===================

.. http:put:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    **Requires authentication**

    Creates or updates a record in the collection.

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"foo": "baz"}}' | http put http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="bob:" --verbose

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

.. _record-patch:

Updating a record
=================

.. http:patch:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    **Requires authentication**

    Updates a record in the collection. Specify only the fields to be modified,
    all the rest will remain intact.

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"status": "done"}}' | http patch http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="bob:" --verbose

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

.. _records-get:

Retrieving stored records
=========================

Records can be paginated, filtered, and conflicts detected.
To do so, refer to :ref:`resource-endpoints` for more details on available
operations on collection retrieval.

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)/records

    **Requires authentication**

    Retrieves all the records in the collection.

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles/records --auth="bob:" --verbose

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

    **Requires authentication**

    Retrieves a specific record by its id.

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="bob:" --verbose

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

.. _record-delete:

Deleting a record
=================

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)/records/(record_id)

    Deletes a record, from its id.

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections/articles/records/89881454-e4e9-4ef0-99a9-404d95900352 --auth="bob:" --verbose

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
