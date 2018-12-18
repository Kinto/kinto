.. _tutorial-first-steps:

First steps with Kinto HTTP API
###############################

This tutorial will take you through your first API calls with a real
Kinto server, with an emphasis on those APIs used for syncing data
between devices and sharing data between users. You probably won't be
making calls to these APIs directly; instead, you'll use a client
library like *Kinto.js*.

In order to get the most out of this tutorial, you may want to have a
real Kinto server ready. You can read our :ref:`installation
<install>` guide to see how to set up your own Kinto instance if you
like. We'll be using the :ref:`Mozilla demo server <run-kinto-mozilla-demo>`.

.. important::

    In this tutorial we will use :ref:`Kinto internal accounts <api-accounts>`.
    But obviously it would work any authentication, like OpenID, LDAP etc.

In this tutorial, we'll set out to build an offline-first application,
following the typical architecture for a Kinto application. We'll have
a Kinto server somewhere in the cloud (represented here by the Mozilla
dev server). Our application will use a Kinto client library which
provides offline-first access. That library will maintain a local copy
of the data. The application will always have read/write access to the
data in the client, even when it's offline. When access to the server
is available, the client will sync up with it.

Unless you're writing a client library yourself, you won't be making
any of these API requests yourself, but seeing them may give you a
better understanding of how a Kinto application works and how to
structure your data when working with Kinto.

The problem
===========

There are several kinds of applications where *Kinto* is
particulary relevant as a storage backend.

Let's say that we want to make a `TodoMVC <http://todomvc.com/>`_
backend that will sync user tasks between the devices. The
requirements are that users can check off tasks as they complete them
and they can share their tasks with other users. We want tasks and
their states to be available on all devices.

Data model
==========

We'll start with a relatively simple data model. Each record will have
these fields:

  - ``description``: A string describing the task
  - ``status``: The status of the task, (e.g. ``todo``, ``doing`` or ``done``).

In order to keep each user's data separate, we'll use the default
*personal bucket*.

Account
=======

Since we use internal accounts, we will start by creating one :)

Using the `httpie <http://httpie.org>`_ tool, it is as simple as:

.. code-block:: shell

    $ echo '{"data": {"password": "s3cr3t"}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/accounts/bob -v

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Content-Length, Alert
    Connection: keep-alive
    Content-Length: 169
    Content-Type: application/json
    Date: Mon, 24 Sep 2018 17:19:45 GMT
    ETag: "1537809585495"
    Last-Modified: Mon, 24 Sep 2018 17:19:45 GMT
    Server: nginx
    X-Content-Type-Options: nosniff

    {
        "data": {
            "id": "bob",
            "last_modified": 1537809585495,
            "password": "$2b$12$e6XaBTSCS12WvIE7wa8BK.YoiERsPq2lCl7MNe0q2gR5XLiWBvzJq"
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }

.. note::

    Please `consider reading httpie documentation <https://github.com/jkbrzt/httpie#proxies>`_
    for more information (if you need to configure a proxy, for instance).

.. note::

    If this fails on your server, this means your server is not configured with the accounts feature enabled.
    You can double check by having a look at the ``"capabilities"`` field in the
    :ref:`root URL <api-utilities-hello>` (eg. ``https://kinto.dev.mozaws.net/v1/``).


Basic data storage APIs
=======================

Now that we have a user, we can authenticate and post a sample record in the
``tasks`` collection:

.. code-block:: shell

    $ echo '{"data": {"description": "Write a tutorial explaining Kinto", "status": "todo"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records \
             -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 253
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:39:56 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutorial explaining Kinto",
            "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
            "last_modified": 1436171996916,
            "status": "todo"
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }

.. note::

    With *Basic Auth* a unique identifier needs to be associated with each
    user. This identifier is built using the token value provided in the request.
    Therefore users cannot change their password easily without losing
    access to their data. :ref:`More information <authentication>`.

This also creates the ``tasks`` collection. Unlike other buckets, the
:ref:`collections <collections>` in the ``default`` :ref:`bucket
<buckets>` are created implicitly.

Let us fetch our new collection of tasks:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records \
           -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Next-Page, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 152
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:40:14 GMT
    ETag: "1436171996916"
    Last-Modified: Mon, 06 Jul 2015 08:39:56 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": [
            {
                "description": "Write a tutorial explaining Kinto",
                "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
                "last_modified": 1436171996916,
                "status": "todo"
            }
        ]
    }


Keep a note of the ``ETag`` and of the ``last_modified`` values
returned (here both ``"1436171996916"``) -- we'll need them for a later
example.

We can also update one of our tasks using its ``id``:

.. code-block:: shell

    $ echo '{"data": {"status": "doing"}}' | \
         http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/a5f490b2-218e-4d71-ac5a-f046ae285c55 \
              -v  --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 254
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:43:49 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutorial explaining Kinto",
            "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
            "last_modified": 1436172229372,
            "status": "doing"
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }


Sync user data between devices
==============================

Here you should ask yourself: what happens if another device updated the same
record in the interim - will this request overwrite those changes?

With the request shown above the answer is *yes*.

If you want the server to reject changes if the record was modified in the
interim, you must send the ``If-Match`` header.

In the ``If-Match`` header, you must send the ``ETag`` header value you
obtained while fetching the collection.

Let's try to modify the record using an obsolete value of ``ETag`` (obtained
while we fetched the collection earlier - you kept a note, didn't you?):

.. code-block:: shell

    $ echo '{"data": {"status": "done"}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/a5f490b2-218e-4d71-ac5a-f046ae285c55 \
            If-Match:'"1434641515332"' \
            -v  --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 412 Precondition Failed
    Connection: keep-alive
    Content-Length: 98
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:45:07 GMT
    ETag: "1436172229372"
    Last-Modified: Mon, 06 Jul 2015 08:43:49 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "code": 412,
        "errno": 114,
        "error": "Precondition Failed",
        "message": "Resource was modified meanwhile"
    }

As expected here, the server rejects the modification with a |status-412|
error response.

In order to update this record safely we can fetch the last version of this
single record and merge attributes locally:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/a5f490b2-218e-4d71-ac5a-f046ae285c55 \
           -v  --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 254
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:45:57 GMT
    ETag: "1436172229372"
    Last-Modified: Mon, 06 Jul 2015 08:43:49 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutorial explaining Kinto",
            "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
            "last_modified": 1436172229372,
            "status": "doing"
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }


The strategy to merge local changes is left to the application and
might depend on the application's requirements. A *three-way merge* is
possible when changes do not affect the same fields or if both objects
are equal. Prompting the user to decide what version should be kept,
or to resolve the conflict manually, might also be an option.

.. note::

    Don't run away! Remember, you will most likely use a library like
    :github:`Kinto/kinto.js`, which provides nice abstractions to
    interact with the Kinto API.

Once merged, we can send back again our modifications using the last
record ``ETag`` value:

.. code-block:: shell

    $ echo '{"data": {"status": "done"}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/a5f490b2-218e-4d71-ac5a-f046ae285c55 \
            If-Match:'"1436172229372"' \
            -v  --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 253
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:47:22 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutorial explaining Kinto",
            "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
            "last_modified": 1436172442466,
            "status": "done"
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }


You can also delete the record and use the same mechanism to avoid conflicts:

.. code-block:: shell

    $ http DELETE https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/a5f490b2-218e-4d71-ac5a-f046ae285c55 \
           If-Match:'"1436172442466"' \
           -v  --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 99
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 06 Jul 2015 08:48:21 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "deleted": true,
            "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
            "last_modified": 1436172501156
        }
    }


Likewise, we can query the list of changes (updates and deletions) that occured
since we last fetched the collection.

Just add the ``_since`` querystring filter, using the value of any ``ETag`` (or
``last_modified`` data field):

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records?_since="1434642603605" \
           -v  --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Next-Page, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 101
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:29:54 GMT
    ETag: "1434641474977"
    Last-Modified: Thu, 18 Jun 2015 15:31:14 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": [
            {
                "deleted": true,
                "id": "a5f490b2-218e-4d71-ac5a-f046ae285c55",
                "last_modified": 1434644823180
            }
        ]
    }


The list will be empty if no change occurred. If you would prefer to receive a
|status-304| response in this case, simply send the ``If-None-Match``
header with the last ``ETag`` value.


Sync and share data between users
=================================

In this example, instead of using the *personal bucket* we will create an
application-specific bucket called ``todo``.

.. code-block:: shell

    $ http PUT https://kinto.dev.mozaws.net/v1/buckets/todo \
        -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 155
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:33:17 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "todo",
            "last_modified": 1434645197868
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }

By default the creator is granted sole administrator privileges (see ``write``
permission). In order to allow collaboration additional permissions will need
to be added.

In our case, we want people to be able to create and share tasks, so we will
create a ``tasks`` collection with the ``record:create`` permission for
authenticated users (i.e. ``system.Authenticated``):

.. code-block:: shell

    $ echo '{"permissions": {"record:create": ["system.Authenticated"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks \
            -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 197
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:37:48 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "tasks",
            "last_modified": 1434645468367
        },
        "permissions": {
            "record:create": [
                "system.Authenticated"
            ],
            "write": [
                "account:bob"
            ]
        }
    }

.. note::

   As you may noticed, you are automatically added to the ``write``
   permission of any objects you create.


Now Alice can create a task in this collection:

.. code-block:: shell

    $ echo '{"data": {"description": "Alice task", "status": "todo"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'alice:p4ssw0rd'

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 231
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:41:50 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Alice task",
            "id": "2fa91620-f4fa-412e-aee0-957a7ad2dc0e",
            "last_modified": 1434645840590,
            "status": "todo"
        },
        "permissions": {
            "write": [
                "account:alice"
            ]
        }
    }

And Bob can also create a task:

.. code-block:: shell

    $ echo '{"data": {"description": "Bob new task", "status": "todo"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 232
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:44:39 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Bob new task",
            "id": "10afe152-b5bb-4aff-b77e-10be44587057",
            "last_modified": 1434645879088,
            "status": "todo"
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }


If Alice wants to share a task with Bob, she can give him the ``read``
permission on her records:

.. code-block:: shell

    $ echo '{"permissions": {
        "read": ["account:bob"]
    }}' | \
    http PATCH https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e \
        -v --auth 'alice:p4ssw0rd'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 273
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:50:57 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "2fa91620-f4fa-412e-aee0-957a7ad2dc0e",
            "last_modified": 1434646257547
            "description": "Alice task",
            "status": "todo"
        },
        "permissions": {
            "read": [
                "account:bob"
            ],
            "write": [
                "account:alice"
            ]
        }
    }


If Bob wants to get the record list, he will get his records as well as Alice's ones:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
           -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Last-Modified, ETag
    Content-Length: 371
    Content-Type: application/json; charset=UTF-8
    Etag: "1434646257547"

    {
        "data": [
            {
                "description": "Bob new task",
                "id": "10afe152-b5bb-4aff-b77e-10be44587057",
                "last_modified": 1434645879088,
                "status": "todo"
            },
            {
                "description": "Alice task",
                "id": "2fa91620-f4fa-412e-aee0-957a7ad2dc0e",
                "last_modified": 1434646257547,
                "status": "todo"
            }
        ]
    }


Working with groups
===================

To go further, you may want to allow users to share data with a group
of users.

Let's add the permission for authenticated users to create groups in the ``todo``
bucket:

.. code-block:: shell

    $ echo '{"permissions": {"group:create": ["system.Authenticated"]}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/todo \
            -v --auth 'bob:s3cr3t'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 195
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:59:29 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "todo",
            "last_modified": 1434646769990
        },
        "permissions": {
            "group:create": [
                "system.Authenticated"
            ],
            "write": [
                "account:bob"
            ]
        }
    }

Now Alice can create a group of her friends (Bob and Mary):

.. code-block:: shell

    $ echo '{"data": {
        "members": ["account:bob",
                    "account:mary"]
    }}' | http PUT https://kinto.dev.mozaws.net/v1/buckets/todo/groups/alice-friends \
        -v --auth 'alice:p4ssw0rd'

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 330
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 17:03:24 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "alice-friends",
            "last_modified": 1434647004644,
            "members": [
                "account:bob",
                "account:mary"
            ]
        },
        "permissions": {
            "write": [
                "account:alice"
            ]
        }
    }

Now Alice can share records directly with her group of friends:

.. code-block:: shell

    $ echo '{
        "permissions": {
            "read": ["/buckets/todo/groups/alice-friends"]
        }
    }' | \
    http PATCH https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e \
        -v --auth 'alice:p4ssw0rd'

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 237
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 17:06:09 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "2fa91620-f4fa-412e-aee0-957a7ad2dc0e",
            "last_modified": 1434647169157
        },
        "permissions": {
            "read": [
                "account:bob",
                "/buckets/todo/groups/alice-friends"
            ],
            "write": [
                "account:alice"
            ]
        }
    }

And now Mary can access the record:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e \
        -v --auth 'mary:wh1sp3r'


.. note::

    The records of the personal bucket can also be shared! In order to
    obtain its ID, just use ``GET /buckets/default`` to get its ID,
    and then share its content using the full URL
    (e.g. ``/buckets/b86b26b8-be36-4eaa-9ed9-2e6de63a5252``)!


Conclusion
==========

In this tutorial you have seen some of the concepts exposed by *Kinto*:

- Using the default personal user bucket
- Handling synchronisation and conflicts
- Creating a bucket to share data between users
- Creating groups, collections and records
- Modifying objects permissions, for users and groups

More details about :ref:`permissions <api-permissions>`, :ref:`HTTP API headers and
status codes <kinto-api-endpoints>`.

.. note::

    We plan to improve our documentation and make sure it is as easy as
    possible to get started with *Kinto*.

    Please do not hesitate to :ref:`give us feedback <how-to-contribute>`, and if you are
    interested in making improvements, you're welcome to join us!
