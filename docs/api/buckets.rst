.. _buckets:

Buckets
#######

PUT /buckets/<bucket_id>
========================

**Requires authentication**

Creates or replaces a bucket with a specific id.

If the bucket exists and you don't have the ``write`` permission on
it, you will get a ``403 Forbidden`` http response.

.. code-block:: http

    $ http PUT http://localhost:8000/v1/buckets/servicedenuages --auth "admin:"

    PUT /v1/buckets/servicedenuages HTTP/1.1
    Authorization: Basic YWRtaW46

    HTTP/1.1 201 Created

    {
        "id": "servicedenuages",
        "permissions": {
            "write": ["basicauth:5d127220922673e346c0ebee46c23e6739dfa756"]
        }
    }


PATCH /buckets/<bucket_id>
==========================

**Requires authentication**

Modifies an existing bucket.

If you are not owner of the bucket you will get a ``403 Forbidden`` http response.

The PATCH endpoint let you add or remove users principals from
permissions sets. In case you want to override the set, you can use
the PUT endpoint.

You can use ``+principal`` to add one and ``-principal`` to remove one.

.. code-block:: http

    $ echo '{
              "permissions": {
                "write": ["+fxa:af3e077eb9f5444a949ad65aa86e82ff"],
                "groups:create": ["+fxa:70a9335eecfe440fa445ba752a750f3d"]
              }
            }' | http PATCH http://localhost:8000/v1/buckets/servicedenuages --auth "admin:"

    PATCH /v1/buckets/servicedenuages HTTP/1.1
    Authorization: Basic YWRtaW46

    {
        "permissions": {
            "write_bucket": [
                "+fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ],
            "create_groups": [
                "+fxa:70a9335eecfe440fa445ba752a750f3d"
            ]
        }
    }

    HTTP/1.1 200 OK
    Content-Type: application/json; charset=UTF-8

    {
        "id": "servicedenuages",
        "permissions": {
            "write": [
                "basicauth:5d127220922673e346c0ebee46c23e6739dfa756",
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ],
            "groups:create": [
                "fxa:70a9335eecfe440fa445ba752a750f3d"
            ]
        }
    }


GET /buckets/<bucket_id>
========================

**Requires authentication**

Returns a specific bucket by its id.

.. code-block:: http

    $ http GET http://localhost:8000/v1/buckets/servicedenuages

    GET /v1/buckets/servicedenuages HTTP/1.1

    HTTP/1.1 200 OK
    Content-Type: application/json; charset=UTF-8

    {
        "id": "servicedenuages",
        "permissions": {
            "write": [
                "basicauth:5d127220922673e346c0ebee46c23e6739dfa756",
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ],
            "groups:create": [
                "fxa:70a9335eecfe440fa445ba752a750f3d"
            ]
        }
    }


DELETE /buckets/<bucket_id>
===========================

**Requires authentication**

Deletes a specific bucket, and **everything under it**.

.. code-block:: http

    $ http DELETE http://localhost:8000/v1/buckets/servicedenuages

    DELETE /v1/buckets/servicedenuages HTTP/1.1

    HTTP/1.1 204 No Content
    Content-Type: application/json; charset=UTF-8
