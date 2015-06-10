.. _collections:

Collections
###########

A collection belongs to a bucket and stores records.

A collection is a mapping with the following attributes:

* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the collection object


.. .. note::

..     By default users have a bucket that is used for their own data.
..     Application can use this default bucket with the ``~`` shortcut.
..     ie: ``/buckets/~/collections/contacts`` will be the current user contacts.


PUT /buckets/<bucket_id>/collections/<collection_id>
====================================================

**Requires authentication**

Creates or replaces a collection object.

.. code-block:: http

    $ http PUT http://localhost:8888/v1/buckets/blog/collections/articles  --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 47
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:10:30 GMT
    Server: waitress

    {
        "id": "articles",
        "last_modified": 1433941830569,
        "permissions": {
            "write": [
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ]
        }
    }


GET /buckets/<bucket_id>/collections/<collection_id>
====================================================

**Requires authentication**

Returns the collection object.

.. code-block:: http

    $ http GET http://localhost:8888/v1/buckets/blog/collections/articles  --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified
    Content-Length: 47
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:11:25 GMT
    Last-Modified: 1433941885974
    Server: waitress

    {
        "id": "articles",
        "last_modified": 1433941830569,
        "permissions": {
            "write": [
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ]
        }
    }


DELETE /buckets/<bucket_id>/collections/<collection_id>
=======================================================

**Requires authentication**

Deletes a specific collection, and **everything under it**.

.. code-block:: http

    $ http DELETE http://localhost:8888/v1/buckets/blog/collections/articles  --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 62
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:13:55 GMT
    Server: waitress

    {
        "deleted": true,
        "id": "articles",
        "last_modified": 1433942035743
    }
