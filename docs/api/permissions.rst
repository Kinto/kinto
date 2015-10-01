.. _api-permissions:

Permissions
###########

As described in the :ref:`concepts section <concepts-permissions>`, permissions
can be set on any object.

Formalism
=========

On each kind of object the set of permissions can be:

+------------+-----------------------------------------+
| Permission | Description                             |
+============+=========================================+
| **read**   | Any listed :term:`principal` can read   |
|            | the object.                             |
+------------+-----------------------------------------+
| **write**  | Any listed :term:`principal` can write  |
|            | the object, which further implies       |
|            | *read*, *update*, and *delete*.         |
+------------+-----------------------------------------+
| **create** | Any listed :term:`principal` can create |
|            | a new *child object*.                   |
+------------+-----------------------------------------+

In the case of a creation, since an object can have several kinds of children, the
permission is prefixed by the type of child (for instance ``groups:create``,
``collections:create``).

The following table lists all permissions that can be associated to each kind
of object.

+----------------+------------------------+----------------------------------+
| Object         | Associated permissions | Description                      |
+================+========================+==================================+
| Configuration  | ``buckets:create``     | Create new buckets.              |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| Bucket         | ``read``               | Read all objects in the bucket.  |
|                |                        |                                  |
|                +------------------------+----------------------------------+
|                | ``write``              | Write + read on the              |
|                |                        | bucket and all children objects. |
|                +------------------------+----------------------------------+
|                | ``collections:create`` | Create new                       |
|                |                        | collections in the bucket.       |
|                +------------------------+----------------------------------+
|                | ``groups:create``      | Create new groups                |
|                |                        | in the bucket.                   |
+----------------+------------------------+----------------------------------+
| Collection     | ``read``               | Read all                         |
|                |                        | objects in the collection.       |
|                +------------------------+----------------------------------+
|                | ``write``              | Write and read all objects in    |
|                |                        | the collection.                  |
|                +------------------------+----------------------------------+
|                | ``records:create``     | Create new records               |
|                |                        | in the collection.               |
+----------------+------------------------+----------------------------------+
| Record         | ``read``               | Read the record.                 |
|                |                        | record.                          |
|                +------------------------+----------------------------------+
|                | ``write``              | Write and read the record.       |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| Group          | ``read``               | Read the group                   |
|                |                        | group.                           |
|                +------------------------+----------------------------------+
|                | ``write``              | Write and read the group         |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+

Every modification of an object (including the creation of new objects)
grant the `write` permission to their creator.


.. note::

  There is no ``delete`` permission. Anyone with the ``write`` permission on an
  object can delete it.


Principals
==========

During the authentication phase, a set of :term:`principal`s for the current
authenticated *user* will be bound to to the request.

The main principal is considered the **user ID** and follows this formalism:
``{type}:{identifier}`` (e.g. for Firefox Account: ``fxa:32aa95a474c984d41d395e2d0b614aa2``).

There are two special principals:

- ``system.Authenticated``: All *authenticated* users.
- ``system.Everyone``: Anyone (authenticated or anonymous). Using this
  principal is useful when a rule should apply to all users.

.. note::

    A user can also be another application (in order to provide *service to
    service* authentication).

Get the current user ID
-----------------------

The currently authenticated *user ID* can be obtained on the root URL.

.. code-block:: http
    :emphasize-lines: 16

    $ http GET http://localhost:8888/v1/ --auth user:pass
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 288
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 09:48:47 GMT
    Server: waitress

    {
        "documentation": "https://kinto.readthedocs.org/",
        "hello": "cloud storage",
        "settings": {
            "kinto.batch_max_requests": 25
        },
        "url": "http://localhost:8888/v1/",
        "userid": "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6",
        "version": "1.4.0"
    }


In this case the user ID is: ``basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6``

.. note::

    If Alice wants to share objects with Bob, Bob will need to give Alice his
    user ID - this is an easy way to obtain that ID.



Retrieve permissions
====================

.. http:get:: /(object url)

    :synopsis: Retrieve the object data and permissions.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http GET http://localhost:8888/v1/buckets/default --auth="bob:" --verbose

    .. sourcecode:: http

        GET /v1/buckets/default HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Last-Modified, ETag
        Connection: keep-alive
        Content-Length: 187
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 20 Aug 2015 16:18:48 GMT
        ETag: "1440087528171"
        Last-Modified: Thu, 20 Aug 2015 16:18:48 GMT
        Server: nginx/1.4.6 (Ubuntu)

        {
            "data": {
                "id": "fec930f1-4e30-5b1c-2a63-0fafbe508d48",
                "last_modified": 1440087528171
            },
            "permissions": {
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


Add a permission
================

.. http:patch:: /(object url)

    :synopsis: Add principals or permissions to the object.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ echo '{"permissions": {"read": ["system.Authenticated"]}}' | \
          http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks \
          --auth bob:

    .. sourcecode:: http

        PATCH /v1/buckets/default/collections/tasks HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 52
        Content-Type: application/json; charset=utf-8
        Host: kinto.dev.mozaws.net
        User-Agent: HTTPie/0.8.0

        {
            "permissions": {
                "read": [
                    "system.Authenticated"
                ]
            }
        }

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
        Connection: keep-alive
        Content-Length: 188
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 20 Aug 2015 16:43:51 GMT
        ETag: "1440089003843"
        Last-Modified: Thu, 20 Aug 2015 16:43:23 GMT
        Server: nginx/1.4.6 (Ubuntu)

        {
            "data": {
                "id": "tasks",
                "last_modified": 1440089003843
            },
            "permissions": {
                "read": [
                    "system.Authenticated"
                ],
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


Replace or remove permissions
=============================

.. note::

   The user ID that *updates* the permissions is always granted the `write`
   permission. This is in order to prevent accidental loss of ownership on an
   object.


.. http:put:: /(object url)

    :synopsis: Replace existing principals or permissions of the object.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ echo '{"permissions": {"write": ["groups:writers"]}}' | \
          http PUT https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks \
          --auth bob:

    .. sourcecode:: http

        PUT /v1/buckets/default/collections/tasks HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 57
        Content-Type: application/json; charset=utf-8
        Host: kinto.dev.mozaws.net
        User-Agent: HTTPie/0.8.0

        {
            "permissions": {
                "write": [
                    "groups:writers"
                ]
            }
        }

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
        Connection: keep-alive
        Content-Length: 182
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 20 Aug 2015 16:50:37 GMT
        ETag: "1440089437221"
        Last-Modified: Thu, 20 Aug 2015 16:50:37 GMT
        Server: nginx/1.4.6 (Ubuntu)

        {
            "data": {
                "id": "tasks",
                "last_modified": 1440089437221
            },
            "permissions": {
                "write": [
                    "groups:writers"
                ],
                "write": [
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }
