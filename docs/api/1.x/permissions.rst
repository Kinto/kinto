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
permission is prefixed by the type of child (for instance ``group:create``,
``collection:create`` on buckets). When a user is allowed to create a child, she is allowed
to read the parent attributes as well as listing accessible objects via the
plural endpoint.

The following table lists all permissions that can be associated to each kind
of object.

+----------------+------------------------+----------------------------------+
| Object         | Associated permissions | Description                      |
+================+========================+==================================+
| Configuration  | ``bucket:create``      | Create new buckets and list      |
|                |                        | existing buckets.                |
+----------------+------------------------+----------------------------------+
| Bucket         | ``read``               | Read all objects in the bucket.  |
|                +------------------------+----------------------------------+
|                | ``write``              | Write + read on the              |
|                |                        | bucket and all children objects. |
|                +------------------------+----------------------------------+
|                | ``collection:create``  | Create new                       |
|                |                        | collections in the bucket,       |
|                |                        | list accessible collections      |
|                |                        | and read bucket metadata.        |
|                +------------------------+----------------------------------+
|                | ``group:create``       | Create new groups                |
|                |                        | in the bucket,                   |
|                |                        | list accessible groups           |
|                |                        | and read bucket metadata.        |
+----------------+------------------------+----------------------------------+
| Collection     | ``read``               | Read all                         |
|                |                        | objects in the collection.       |
|                +------------------------+----------------------------------+
|                | ``write``              | Write and read all objects in    |
|                |                        | the collection.                  |
|                +------------------------+----------------------------------+
|                | ``record:create``      | Create new records               |
|                |                        | in the collection,               |
|                |                        | list accessible records          |
|                |                        | and read collection metadata.    |
+----------------+------------------------+----------------------------------+
| Record         | ``read``               | Read the record.                 |
|                |                        |                                  |
|                +------------------------+----------------------------------+
|                | ``write``              | Write and read the record.       |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| Group          | ``read``               | Read the group.                  |
|                |                        |                                  |
|                +------------------------+----------------------------------+
|                | ``write``              | Write and read the group.        |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+

.. important::

    Every modification of an object (including the creation of new objects)
    grant the ``write`` permission to their creator/editor.


.. note::

  There is no ``delete`` permission. Anyone with the ``write`` permission on an
  object can delete it.

.. _api-principals:

Principals
==========

During the authentication phase, a set of :term:`principals` for the current
authenticated *user* will be bound to to the request.

The main principal is considered the **user ID** and follows this formalism:
``{policy}:{identifier}`` (e.g. with :ref:`internal accounts <api-accounts>`: ``account:alice``).
When a user is added to :ref:`a group <groups>`, they receive a principal.

There are two special principals:

- ``system.Authenticated``: All *authenticated* users.
- ``system.Everyone``: Anyone (authenticated or anonymous). Using this
  principal is useful when a rule should apply to all users.

Those principals are used in the permissions definitions. For example, to give
the permission to read for everyone and to write for the *friends* group, the
definition is ``read: ["system.Everyone"], write: ["/buckets/pictures/groups/friends"]``.

.. note::

    A principal can also be another application (in order to provide *service to
    service* authentication).

.. _api-current-userid:

Get the current user ID and principals
--------------------------------------

The currently authenticated *user ID* can be obtained on the root URL.

.. code-block:: bash

    $ http GET http://localhost:8888/v1/ --auth bob:my-secret

.. code-block:: http
    :emphasize-lines: 15-23

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 288
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 09:48:47 GMT
    Server: waitress

    {
        "documentation": "https://kinto.readthedocs.io/",
        "hello": "cloud storage",
        "settings": {
            "kinto.batch_max_requests": 25
        },
        "url": "http://localhost:8888/v1/",
        "user": {
            "bucket": "4399ed6c-802e-3278-5d01-44f261f0bab4",
            "id": "account:bob",
            "principals": [
                "account:bob",
                "system.Everyone",
                "system.Authenticated"
            ]
        }
        "version": "1.4.0"
    }


In this case the user ID is: ``account:bob``

.. note::

    If Alice wants to share objects with Bob, Bob will need to give Alice his
    user ID - this is an easy way to obtain that ID.


.. _api-permissions-payload:

Permissions request payload
===========================

If the current user has the ``write`` permission on the object, the permissions
are returned in the ``permissions`` attribute  along the ``data`` attribute
in the JSON requests payloads.

Permissions can be replaced or modified independently from data.

``permissions`` is a JSON dict with the following structure::

    "permissions": {<permission>: [<list_of_principals>]}

Where ``<permission>`` is the permission name (e.g. ``read``, ``write``)
and ``<list_of_principals>`` should be replaced by an actual list of
:term:`principals`.

Example:

::

    {
        "data": {
            "title": "No Backend"
        },
        "permissions": {
            "write": ["twitter:leplatrem", "group:ldap:42"],
            "read": ["system.Authenticated"]
        }
    }

.. note::

    When an object is created or modified, the current :term:`user id`
    **is always added** among the ``write`` principals.


Retrieve objects permissions
============================

.. http:get:: /(object url)

    :synopsis: Retrieve the object data and permissions.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http GET http://localhost:8888/v1/buckets/default --auth bob:p4ssw0rd --verbose

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
                    "account:bob"
                ]
            }
        }


Modify object permissions
=========================

An object's permissions can be modified at the same time as the object
itself, using the same :ref:`PATCH <record-patch>` and :ref:`PUT
<record-put>` methods discussed in :ref:`the Records section
<records>`.

.. note::

   The user ID that updates *any* permissions is always added to the ``write``
   permission list. This is in order to prevent accidental loss of ownership on an
   object.


.. http:patch:: /(object url)

    :synopsis: Modify the set of principals granted permissions on the object.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ echo '{"permissions": {"read": ["system.Authenticated"]}}' | \
          http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks \
          --auth bob:p4ssw0rd

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
                    "account:bob"
                ]
            }
        }


.. http:put:: /(object url)

    :synopsis: Replace existing principals or permissions of the object.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ echo '{"permissions": {"write": ["groups:writers"]}}' | \
          http PUT https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks \
          --auth bob:p4ssw0rd

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
                    "groups:writers",
                    "account:bob"
                ]
            }
        }


List every permissions
======================

**Requires setting** ``kinto.experimental_permissions_endpoint`` to ``True``.


.. http:get:: /permissions

    :synopsis: Retrieve the list of permissions granted on every kind of objects.

    **Optional authentication**

    **Example request**

    .. sourcecode:: bash

        $ http GET https://kinto.dev.mozaws.net/v1/permissions --auth bob:p4ssw0rd

    .. sourcecode:: http

        GET /v1/permissions HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Length: 487
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 15 Jun 2016 16:00:22 GMT
        Server: waitress

        {
            "data": [
                {
                    "bucket_id": "2f9b1aaa-552d-48e8-1b78-371dd08688b3",
                    "collection_id": "test",
                    "id": "test",
                    "permissions": [
                        "write",
                        "read",
                        "record:create"
                    ],
                    "resource_name": "collection",
                    "uri": "/buckets/2f9b1aaa-552d-48e8-1b78-371dd08688b3/collections/test"
                },
                {
                    "bucket_id": "2f9b1aaa-552d-48e8-1b78-371dd08688b3",
                    "id": "2f9b1aaa-552d-48e8-1b78-371dd08688b3",
                    "permissions": [
                        "write",
                        "read",
                        "collection:create",
                        "group:create"
                    ],
                    "resource_name": "bucket",
                    "uri": "/buckets/2f9b1aaa-552d-48e8-1b78-371dd08688b3"
                }
            ]
        }

.. important::

    The inherited objects are not expanded. This means that if the current user
    has some permissions on a bucket, the sub-objects like collections, groups
    and records won't be explicitly listed.


List of available URL parameters
--------------------------------

- ``<prefix?><field name>``: :doc:`filter <filtering>` by value(s)
- ``_sort``: :doc:`order list <sorting>`
- ``_limit``: :doc:`pagination max size <pagination>`
- ``_token``: :doc:`pagination token <pagination>`
- ``_fields``: :doc:`filter the fields of the records <selecting_fields>`


Filtering, sorting, partial responses and paginating can all be combined together.

* ``?_sort=-last_modified&_limit=100&_fields=title``
