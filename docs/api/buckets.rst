Working with buckets
====================

Creating a new bucket
---------------------

``/buckets/<bucket_id>``

This endpoint defines the bucket resource:

* Its permissions


POST /buckets
'''''''''''''

**Requires authentication**

This endpoint creates a new bucket with a generated unique id.

By default the user id is used for its write permission.

.. code-block:: http

    $ http POST http://localhost:8000/v1/buckets --auth "admin:"
    POST /v1/buckets HTTP/1.1
    Authorization: Basic YWRtaW46

    HTTP/1.1 201 Created

    {
        "id": "857d952b-e9fa-4b9f-b60e-cb633a557ced",
        "permissions": {
            "write": ["basicauth:5d127220922673e346c0ebee46c23e6739dfa756"]
        }
    }


PUT /buckets/<bucket_id>
''''''''''''''''''''''''

**Requires authentication**

This endpoint creates a new bucket with a chosen id.

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


Updating a bucket
-----------------

PATCH /buckets/<bucket_id>
''''''''''''''''''''''''''

**Requires authentication**

This endpoint lets you update an existing bucket.

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


Getting bucket informations
---------------------------

GET /buckets/<bucket_id>
''''''''''''''''''''''''

This endpoint lets you get bucket informations.

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
        },
        "collections": []
    }


Removing a bucket
-----------------

This endpoint lets you delete a bucket and everything inside.

.. code-block:: http

    $ http DELETE http://localhost:8000/v1/buckets/servicedenuages

    DELETE /v1/buckets/servicedenuages HTTP/1.1

    HTTP/1.1 204 No Content
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
