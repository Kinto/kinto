.. _buckets:

Buckets
#######

A bucket is the parent object of collections and groups. It can be viewed as
a namespace where all collection and groups are stored.

A bucket is a mapping with the following attributes:

* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the bucket object


PUT /buckets/<bucket_id>
========================

**Requires authentication**

Creates or replaces a bucket with a specific id.

If the bucket exists and you don't have the ``write`` permission on
it, you will get a ``403 Forbidden`` http response.

.. code-block:: http

    $ http PUT http://localhost:8888/v1/buckets/blog  --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 43
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 12:54:53 GMT
    Server: waitress

    {
        "id": "blog",
        "last_modified": 1433940893322,
        "permissions": {
            "write": ["basicauth:5d127220922673e346c0ebee46c23e6739dfa756"]
        }
    }

.. note::

    In order to create only if does not exist yet, a ``If-None-Match: *``
    request header can be provided. A ``412 Precondition Failed`` error response
    will be returned if the record already exists.


GET /buckets/<bucket_id>
========================

**Requires authentication**

Returns a specific bucket by its id.

.. code-block:: http

    $ http GET http://localhost:8888/v1/buckets/blog  --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified, ETag
    Content-Length: 43
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:03:26 GMT
    Last-Modified: 1433941406398
    Server: waitress

    {
        "id": "blog",
        "last_modified": 1433940893322,
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


PATCH /buckets/<bucket_id>
==========================

**Requires authentication**

Modifies an existing bucket.

.. note::

    Until a formalism is found to alter ACL principals (e.g. using ``+`` or ``-``)
    there is no difference in the behaviour between PATCH and PUT.

.. The PATCH endpoint let you add or remove users principals from
.. permissions sets. In case you want to override the set, you can use
.. the PUT endpoint.

.. You can use ``+principal`` to add one and ``-principal`` to remove one.

.. .. code-block:: http

..     $ echo '{
..               "permissions": {
..                 "write": ["+fxa:af3e077eb9f5444a949ad65aa86e82ff"],
..                 "groups:create": ["+fxa:70a9335eecfe440fa445ba752a750f3d"]
..               }
..             }' | http PATCH http://localhost:8000/v1/buckets/servicedenuages --auth "admin:"

..     PATCH /v1/buckets/servicedenuages HTTP/1.1
..     Authorization: Basic YWRtaW46

..     {
..         "permissions": {
..             "write_bucket": [
..                 "+fxa:af3e077eb9f5444a949ad65aa86e82ff"
..             ],
..             "create_groups": [
..                 "+fxa:70a9335eecfe440fa445ba752a750f3d"
..             ]
..         }
..     }

..     HTTP/1.1 200 OK
..     Content-Type: application/json; charset=UTF-8

..     {
..         "id": "servicedenuages",
..         "permissions": {
..             "write": [
..                 "basicauth:5d127220922673e346c0ebee46c23e6739dfa756",
..                 "fxa:af3e077eb9f5444a949ad65aa86e82ff"
..             ],
..             "groups:create": [
..                 "fxa:70a9335eecfe440fa445ba752a750f3d"
..             ]
..         }
..     }



DELETE /buckets/<bucket_id>
===========================

**Requires authentication**

Deletes a specific bucket, and **everything under it**.

.. code-block:: http

    $ http DELETE http://localhost:8888/v1/buckets/blog  --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 58
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:07:17 GMT
    Server: waitress

    {
        "deleted": true,
        "id": "blog",
        "last_modified": 1433941637723
    }
