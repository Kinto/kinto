Working with groups
===================

.. _groups:


Creating a new group
---------------------

``/buckets/<bucket_id>/groups/<group_id>``

This endpoint defines the group resource:

* Its permissions
* Its members


POST /buckets/<bucket_id>/groups
''''''''''''''''''''''''''''''''

**Requires authentication**

This endpoint creates a new bucket's group with a generated unique id.

.. code-block:: http

    $ echo '{
              "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
            }' | http POST http://localhost:8000/v1/buckets/cloudservices_blog/groups --auth "admin:"
    POST /v1/buckets/cloudservices_blog/groups HTTP/1.1
    Authorization: Basic YWRtaW46

    HTTP/1.1 201 Created

    {
        "id": "5d875b92-ef9a-49bf-6b0e-bc6353a5c7ed",
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
    }


PUT /buckets/<bucket_id>/groups/<group_id>
''''''''''''''''''''''''''''''''''''''''''

**Requires authentication**

This endpoint creates a new group with a chosen id.

.. code-block:: http

    $ echo '{
              "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
            }' | http PUT http://localhost:8000/v1/buckets/cloudservices_blog/groups/moderators \
          --auth "admin:"

    {
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
    }

    PUT /v1/buckets/cloudservices_blog/groups/moderators HTTP/1.1
    Authorization: Basic YWRtaW46

    HTTP/1.1 201 Created

    {
        "id": "moderators",
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
    }


Updating a group
----------------

PATCH /buckets/<bucket_id>/groups/<group_id>
''''''''''''''''''''''''''''''''''''''''''''

**Requires authentication**

This endpoint lets you update an existing bucket.

The PATCH endpoint let you add or remove users principals from
permissions and member sets. 

In case you want to override the set, you can use the PUT endpoint.

You can use ``+principal`` to add one and ``-principal`` to remove one.

.. code-block:: http

    $ echo '{
              "members": ["+fxa:70a9335eecfe440fa445ba752a750f3d"]
              "permissions": {
                "write": ["+fxa:af3e077eb9f5444a949ad65aa86e82ff"]
              }
            }' | http PATCH http://localhost:8000/v1/buckets/cloudservices_blog/groups/moderators --auth "admin:"

    PATCH /v1/buckets/cloudservices_blog/groups/moderators HTTP/1.1
    Authorization: Basic YWRtaW46

    {
        "members": [
            "+fxa:70a9335eecfe440fa445ba752a750f3d"
        ],
        "permissions": {
            "write": [
                "+fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ]
        }
    }

    HTTP/1.1 200 OK
    Content-Type: application/json; charset=UTF-8

    {
        "id": "moderators",
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f", "fxa:70a9335eecfe440fa445ba752a750f3d"]
        "permissions": {
            "write": [
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ]
        }
    }


Getting group information
-------------------------

GET /buckets/<bucket_id>/groups/<group_id>
''''''''''''''''''''''''''''''''''''''''''

This endpoint lets you get groups information.

.. code-block:: http

    $ http GET http://localhost:8000/v1/buckets/cloudservices_blog/groups/moderators

    GET /v1/buckets/cloudservices_blog/groups/moderators HTTP/1.1

    HTTP/1.1 200 OK
    Content-Type: application/json; charset=UTF-8

    {
        "id": "moderators",
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f", "fxa:70a9335eecfe440fa445ba752a750f3d"]
        "permissions": {
            "write": [
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ]
        }
    }


Removing a group
----------------

This endpoint lets you delete a group.

.. code-block:: http

    $ http DELETE http://localhost:8000/v1/buckets/cloudservices_blog/groups/moderators

    DELETE /v1/buckets/cloudservices_blog/groups/moderators HTTP/1.1

    HTTP/1.1 204 No Content
    Content-Type: application/json; charset=UTF-8
