Working with buckets
====================

:ref:`Buckets <buckets>` enable the creation of collections handled by
a group of users.

As soon as there is a need to let people work on the same records set
or to work with the same collection, the solution is to create a :ref:`bucket <buckets>`.

:ref:`Buckets <buckets>` gives a public unique name to the collection.

The data is not anymore linked to a specific user that only has access
to her private data but is linked to the bucket and managed by
bucket's owners (those who have the ``write_bucket`` permission on the
bucket.

Access to buckets, groups, collections and records are granted using
:ref:`permissions <permissions>`.


Creating a new bucket
---------------------

``/buckets/<bucket_id>``

This endpoint defines the bucket resource.

* Handle the owner list as well as the buckets permissions


POST /buckets
'''''''''''''

**Requires authentication**

This endpoint creates a new bucket with a generated unique id.

By default the user id is used as the only owner.

**Optional parameters**

- ``permissions``: A mapping object that defines the list of user for
  each permission
 - ``write_bucket``: The list of users principals that have
   administration permissions on the bucket, the creator is
   automatically added to the owner list.
 - ``create_groups``: Permission to create new groups
 - ``create_collections``: Permission to create new collections

.. code-block:: http

    $ http POST http://localhost:8000/v1/buckets --auth "admin:"

    POST /v1/buckets HTTP/1.1
    Authorization: Basic YWRtaW46
    Content-Length: 0
    Host: localhost:8000
    User-Agent: HTTPie/0.9.2


    HTTP/1.1 201 Created
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 5 May 2015 18:24:37 GMT
    Server: waitress

    {
        "id": "fe66cdd5-07c0-40fa-b99d-3a30b779358c",
        "permissions": {
            "write_bucket": ["uid:basicauth_5d127220922673e346c0ebee46c23e6739dfa756"],
            "create_groups": [],
            "create_collections": [],
        }
    }
    


PUT /buckets/<bucket_id>
''''''''''''''''''''''''

**Requires authentication**

This endpoint creates a new bucket with a chosen id.

If the id is already taken, then a ``409 Conflict`` http error will be returned.

    $ http PUT http://localhost:8000/v1/buckets/servicedenuages --auth "admin:"

    PUT /v1/buckets/servicedenuages HTTP/1.1
    Authorization: Basic YWRtaW46
    Content-Length: 0
    Host: localhost:8000
    User-Agent: HTTPie/0.9.2

    HTTP/1.1 201 Created
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 5 May 2015 18:30:37 GMT
    Server: waitress

    {
        "id": "servicedenuages",
        "permissions": {
            "write_bucket": ["uid:basicauth_5d127220922673e346c0ebee46c23e6739dfa756"],
            "create_groups": [],
            "create_collections": [],
        }
    }


Updating a bucket
-----------------

PATCH /buckets/<bucket_id>
''''''''''''''''''''''''''

**Requires authentication**

This endpoint lets you update an existing bucket.

If you are not owner of the bucket you will get a ``403 Forbidden`` http error.

.. code-block:: http

    $ echo '{
              "permissions": {
                "write_bucket": ["+email:alexis@example.com"],
                "create_groups": ["+email:natim@example.com"]
              }
            }' | http PATCH http://localhost:8000/v1/buckets/servicedenuages --auth "admin:"

    PATCH /v1/buckets/servicedenuages HTTP/1.1
    Authorization: Basic YWRtaW46
    Content-Length: 160
    Content-Type: application/json
    Host: localhost:8000
    User-Agent: HTTPie/0.9.2

    {
        "permissions": {
            "write_bucket": [
                "+email:alexis@example.com"
            ], 
            "create_groups": [
                "+email:natim@example.com"
            ]
        }
    }

    HTTP/1.1 200 OK
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 5 May 2015 18:34:37 GMT
    Server: waitress

    {
        "id": "servicedenuages",
        "permissions": {
            "write_bucket": ["uid:basicauth_5d127220922673e346c0ebee46c23e6739dfa756",
                             "email:alexis@example.com"],
            "create_groups": ["email:natim@example.com"],
            "create_collections": [],
        }
    }

The PATCH endpoint let you add or remove users principals from
permissions sets. In case you want to override the set, you can use
the PUT endpoint.

You can use ``+principal`` to add one and ``-principal`` to remove one.


Getting bucket informations
---------------------------

PATCH /buckets/<bucket_id>
''''''''''''''''''''''''''

This endpoint lets you get bucket informations.

.. code-block:: http

    $ http GET http://localhost:8000/v1/buckets/servicedenuages

    GET /v1/buckets/servicedenuages HTTP/1.1
    Host: localhost:8000
    User-Agent: HTTPie/0.9.2

    HTTP/1.1 200 OK
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 5 May 2015 18:42:37 GMT
    Server: waitress

    {
        "id": "servicedenuages",
        "permissions": {
            "write_bucket": ["uid:basicauth_5d127220922673e346c0ebee46c23e6739dfa756",
                             "email:alexis@example.com"],
            "create_groups": ["email:natim@example.com"],
            "create_collections": [],
        }
    }
