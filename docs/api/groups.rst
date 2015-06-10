.. _groups:

Groups
######

A group is a mapping with the following attributes:

* ``members``: a list of :term:`principals <principal>`
* ``permissions``: (*optional*) the :term:`ACLs <ACL>` for the group object


POST /buckets/<bucket_id>/groups
================================

**Requires authentication**

Creates a new bucket's group with a generated id.

.. code-block:: http

    $ echo '{
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
    }' | http POST http://localhost:8888/v1/buckets/blog/groups --auth "admin:"
    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 98
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:18:11 GMT
    Server: waitress

    {
        "id": "uIRoB42c",
        "last_modified": 1433942291346,
        "members": [
            "fxa:fae307e97bf5494a4a46d95aa86e2f8f"
        ]
    }



PUT /buckets/<bucket_id>/groups/<group_id>
==========================================

**Requires authentication**

Creates or replaces a group with a chosen id.

.. code-block:: http

    $ echo '{
        "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f"]
    }' | http PUT http://localhost:8888/v1/buckets/blog/groups/moderators --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 100
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:18:52 GMT
    Server: waitress

    {
        "id": "moderators",
        "last_modified": 1433942332896,
        "members": [
            "fxa:fae307e97bf5494a4a46d95aa86e2f8f"
        ]
    }


GET /buckets/<bucket_id>/groups/<group_id>
==========================================

**Requires authentication**

Returns the group object.

.. code-block:: http

    $ http GET http://localhost:8888/v1/buckets/blog/groups/moderators --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified
    Content-Length: 100
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:19:46 GMT
    Last-Modified: 1433942386420
    Server: waitress

    {
        "id": "moderators",
        "last_modified": 1433942332896,
        "members": [
            "fxa:fae307e97bf5494a4a46d95aa86e2f8f",
            "fxa:70a9335eecfe440fa445ba752a750f3d"
        ],
        "permissions": {
            "write": [
                "fxa:af3e077eb9f5444a949ad65aa86e82ff"
            ]
        }
    }


PATCH /buckets/<bucket_id>/groups/<group_id>
============================================

**Requires authentication**

Modifies a specific group.

.. note::

    Until a formalism is found to alter members (e.g. using ``+`` or ``-``)
    there is no difference in the behaviour between PATCH and PUT.



.. The PATCH endpoint let you add or remove users principals from
.. permissions and member sets.

.. In case you want to override the set, you can use the ``PUT`` endpoint.

.. You can use ``+principal`` to add one and ``-principal`` to remove one.

.. .. code-block:: http

..     $ echo '{
..               "members": ["+fxa:70a9335eecfe440fa445ba752a750f3d"]
..               "permissions": {
..                 "write": ["+fxa:af3e077eb9f5444a949ad65aa86e82ff"]
..               }
..             }' | http PATCH http://localhost:8000/v1/buckets/cloudservices_blog/groups/moderators --auth "admin:"

..     PATCH /v1/buckets/cloudservices_blog/groups/moderators HTTP/1.1
..     Authorization: Basic YWRtaW46

..     {
..         "members": [
..             "+fxa:70a9335eecfe440fa445ba752a750f3d"
..         ],
..         "permissions": {
..             "write": [
..                 "+fxa:af3e077eb9f5444a949ad65aa86e82ff"
..             ]
..         }
..     }

..     HTTP/1.1 200 OK
..     Content-Type: application/json; charset=UTF-8

..     {
..         "id": "moderators",
..         "members": ["fxa:fae307e97bf5494a4a46d95aa86e2f8f", "fxa:70a9335eecfe440fa445ba752a750f3d"]
..         "permissions": {
..             "write": [
..                 "fxa:af3e077eb9f5444a949ad65aa86e82ff"
..             ]
..         }
..     }


DELETE /buckets/<bucket_id>/groups/<group_id>
=============================================

**Requires authentication**

Deletes a specific group.

.. code-block:: http

    $ http DELETE http://localhost:8888/v1/buckets/blog/groups/moderators --auth "admin:"
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 64
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 13:22:20 GMT
    Server: waitress

    {
        "deleted": true,
        "id": "moderators",
        "last_modified": 1433942540448
    }
