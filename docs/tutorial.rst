.. _tutorial:

A first app with Kinto
######################

There are actually two kinds of app that you may want to use Kinto with:

  - App to sync user data between her devices.
  - App to sync and share data between user, with fined-grained permissions

Most of the app will fit in one or the other.


Build an app to sync user data between her devices
==================================================

Let say that we want to do a TodoMVC backend that will sync user tasks
between her devices.


In order to separate data between each user, we will use the default
user bucket to create our collection:

.. code-block:: http

    $ echo '{"data": {}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks \
             --auth 'user:password'

    PUT /v1/buckets/default/collections/tasks HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 13
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {}
    }

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 155
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 15:18:18 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "tasks", 
            "last_modified": 1434640698718
        }, 
        "permissions": {
            "write": [
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

As soon as the collection has been created, you may want to start to add some tasks in it.

Let start with a really simple data model:

  - ``description``: A string describing the task
  - ``status``: The status of the task, either ``todo``, ``doing`` or ``done``.

.. code-block:: http

    $ echo '{"data": {"description": "Write a tutoriel explaining Kinto", "status": "todo"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records \
             --auth 'user:password'

    POST /v1/buckets/default/collections/tasks/records HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 81
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {
            "description": "Write a tutoriel explaining Kinto", 
            "status": "todo"
        }
    }

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 253
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 15:31:55 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutoriel explaining Kinto", 
            "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
            "last_modified": 1434641515332, 
            "status": "todo"
        }, 
        "permissions": {
            "write": [
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }


Let's grab our new list of tasks:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records \
           --auth 'user:password'
    GET /v1/buckets/default/collections/tasks/records HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Next-Page, Total-Records, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 152
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 15:34:04 GMT
    ETag: "1434641474977"
    Last-Modified: Thu, 18 Jun 2015 15:31:14 GMT
    Server: nginx/1.4.6 (Ubuntu)
    Total-Records: 1

    {
        "data": [
            {
                "description": "Write a tutoriel explaining Kinto", 
                "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
                "last_modified": 1434641515332, 
                "status": "todo"
            }
        ]
    }


We can also update our tasks:

.. code-block:: http

    $ echo '{"data": {"status": "doing"}}' | \
         http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 \
              -v  --auth 'user:password'

    PATCH /v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 30
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {
            "status": "doing"
        }
    }

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 254
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 15:50:03 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutoriel explaining Kinto", 
            "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
            "last_modified": 1434642603605, 
            "status": "doing"
        }, 
        "permissions": {
            "write": [
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

There you should ask yourself, what happens if another device already
updated the record in between, will I override its change?

You've got two conflicts resolution behaviors:

- Server wins, in that case the server will reject changes in case
  something changed on server side.
- Client wins, in that case the change will override previous changes

The previous call is the Client wins behavior.

In case you want the server to prevent you from overridding changes,
you must send the ``If-Match`` header:

Let say, we didn't refresh the server since our first POST and we send
the ETag we had back then ``"1434641515332"``:

.. code-block:: http

    $ echo '{"data": {"status": "doing"}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 \
            If-Match:'"1434641515332"' \
            -v  --auth 'user:password'

    PATCH /v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 29
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    If-Match: "1434641515332"
    User-Agent: HTTPie/0.9.2

    {
        "data": {
            "status": "done"
        }
    }

    HTTP/1.1 412 Precondition Failed
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Connection: keep-alive
    Content-Length: 98
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:08:31 GMT
    ETag: "1434642603605"
    Last-Modified: Thu, 18 Jun 2015 15:50:03 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "code": 412, 
        "errno": 114, 
        "error": "Precondition Failed", 
        "message": "Resource was modified meanwhile"
    }

The server reject the modification with a 412 error code.

In order to fix that, we can either ask for the record we tried to
update:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 \
           -v  --auth 'user:password'

    GET /v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2


    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 254
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:13:21 GMT
    ETag: "1434641474977"
    Last-Modified: Thu, 18 Jun 2015 15:31:14 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutoriel explaining Kinto", 
            "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
            "last_modified": 1434642603605, 
            "status": "doing"
        }, 
        "permissions": {
            "write": [
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

Or we can ask the list of changes from the last time we've synced our local store, filtering on the ``_since`` attribute with the value of the last collection ETag:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records?_since=1434641515332 \
           -v  --auth 'user:password'

    GET /v1/buckets/default/collections/tasks/records?_since=1434641515332 HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Next-Page, Total-Records, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 153
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:14:44 GMT
    ETag: "1434641474977"
    Last-Modified: Thu, 18 Jun 2015 15:31:14 GMT
    Server: nginx/1.4.6 (Ubuntu)
    Total-Records: 1

    {
        "data": [
            {
                "description": "Write a tutoriel explaining Kinto", 
                "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
                "last_modified": 1434642603605, 
                "status": "doing"
            }
        ]
    }

Now that we've got the list of the record that changed, we can handle the conflict.

We can either do three-way merge (if our changes and server changes on
the object did not happened on the same fields) or if both objects are
actually equals.

Or if changes did happened on the same field, we must decide or ask
the user to decide, which version we have to keep (server version or
client version).

The we can try to send back again our modifications using the new record ``last_modified`` value:

.. code-block:: http

    $ echo '{"data": {"status": "done"}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 \
            If-Match:'"1434642603605"' \
            -v  --auth 'user:password'

    PATCH /v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 29
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    If-Match: "1434642603605"
    User-Agent: HTTPie/0.9.2

    {
        "data": {
            "status": "done"
        }
    }

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 253
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:21:16 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "description": "Write a tutoriel explaining Kinto", 
            "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
            "last_modified": 1434644476758, 
            "status": "done"
        }, 
        "permissions": {
            "write": [
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

You can also delete the record and use the same mechanism for
synchronization:

.. code-block:: http

    $ http DELETE https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 \
           If-Match:'"1434644476758"' \
           -v  --auth 'user:password'

    DELETE /v1/buckets/default/collections/tasks/records/23eed462-c063-4ae0-81b0-8bf2210bfe86 HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 0
    Host: kinto.dev.mozaws.net
    If-Match: "1434644476758"
    User-Agent: HTTPie/0.9.2

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Backoff: 10
    Connection: keep-alive
    Content-Length: 99
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:27:03 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "deleted": true, 
            "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
            "last_modified": 1434644823180
        }
    }

If you want to sync your local store with record deletion, you can use
the ``_since`` parameter with the last ETag you had:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/default/collections/tasks/records?_since=1434642603605 \
           -v  --auth 'user:password'

    GET /v1/buckets/default/collections/tasks/records?_since=1434642603605 HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2


    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Next-Page, Total-Records, Last-Modified, ETag
    Backoff: 10
    Connection: keep-alive
    Content-Length: 101
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 18 Jun 2015 16:29:54 GMT
    ETag: "1434641474977"
    Last-Modified: Thu, 18 Jun 2015 15:31:14 GMT
    Server: nginx/1.4.6 (Ubuntu)
    Total-Records: 0

    {
        "data": [
            {
                "deleted": true, 
                "id": "23eed462-c063-4ae0-81b0-8bf2210bfe86", 
                "last_modified": 1434644823180
            }
        ]
    }


Build an app to share and sync data between user
================================================

The only difference with what we've describe above is that you will
not use the ``default`` user bucket, but you will create a bucket for
your app:

.. code-block:: http

    $ echo '{"data": {}}' | http PUT https://kinto.dev.mozaws.net/v1/buckets/todo -v --auth 'user:password'

    PUT /v1/buckets/todo HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 13
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {}
    }

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
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

Then you will have to define permissions about what you want people to
be able to do with your bucket.

In our case, we want people to be able create and share ``tasks``, so
we will create a collection with the ``record:create`` permission for
authenticated users:

.. code-block:: http

    $ echo '{"data": {}, "permissions": {"record:create": ["system.Authenticated"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks \
            -v --auth 'user:password'

    PUT /v1/buckets/todo/collections/tasks HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 73
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {}, 
        "permissions": {
            "record:create": [
                "system.Authenticated"
            ]
        }
    }

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
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

.. note::

   As you may noticed, you are automatically added to the ``write``
   permission of any objects you are creating.


Then Alice can create a task:

.. code-block:: http

    $ echo '{"data": {"description": "Alice task", "status": "todo"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'alice:alicepassword'

    POST /v1/buckets/todo/collections/tasks/records HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWxpY2U6YWxpY2VwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 59
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {
            "description": "Alice task", 
            "status": "todo"
        }
    }

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
                "basicauth_9be2b51de8544fbed4539382d0885f8643c0185c90fb23201d7bbe86d70b4a44"
            ]
        }
    }

And Bob can create a task:

.. code-block:: http

    $ echo '{"data": {"description": "Bob new task", "status": "todo"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'bob:bobpassword'

    POST /v1/buckets/todo/collections/tasks/records HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic Ym9iOmJvYnBhc3N3b3Jk
    Connection: keep-alive
    Content-Length: 60
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2
    
    {
        "data": {
            "description": "Bob new task", 
            "status": "todo"
        }
    }

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
                "basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148"
            ]
        }
    }


The Alice can see only her tasks:

.. code-block::

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'alice:alicepassword'

    GET /v1/buckets/todo/collections/tasks/records HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWxpY2U6YWxpY2VwYXNzd29yZA==
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2


And Bob can see only his tasks:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'bob:bobpassword'

    GET /v1/buckets/todo/collections/tasks/records HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic Ym9iOmJvYnBhc3N3b3Jk
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

If Alice want to share a task with Bob, she can give him the ``read`` permission:

.. code-block:: http

    $ echo '{
        "data": {},
        "permissions": {
            "read": ["basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148"]
        }
    }' | \
    http PUT https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e \
        -v --auth 'alice:alicepassword'

    PUT /v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWxpY2U6YWxpY2VwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 118
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {}, 
        "permissions": {
            "read": [
                "basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148"
            ]
        }
    }

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
        }, 
        "permissions": {
            "read": [
                "basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148"
            ], 
            "write": [
                "basicauth_9be2b51de8544fbed4539382d0885f8643c0185c90fb23201d7bbe86d70b4a44"
            ]
        }
    }


Then Bob can now see the one tasks that Alice shared with him:

.. code-block:: http

And Bob can see only his tasks:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records \
        -v --auth 'bob:bobpassword'

    GET /v1/buckets/todo/collections/tasks/records HTTP/1.1
    Accept: */*
    Accept-Encoding: gzip, deflate
    Authorization: Basic Ym9iOmJvYnBhc3N3b3Jk
    Connection: keep-alive
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2


Here we are sharing records, but if you share a collection, you share
all the items of this collection with the same right and same for buckets.

Working with groups
===================

To go further, you may want to allow user to share data with a group of people.

Let's add the right for people to create group in our ``todo`` bucket:

.. code-block:: http

    $ echo '{"data": {}, "permissions": {"group:create": ["system.Authenticated"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/todo \
            -v --auth 'user:password'

    PUT /v1/buckets/todo HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic dXNlcjpwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 72
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {}, 
        "permissions": {
            "group:create": [
                "system.Authenticated"
            ]
        }
    }

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
                "basicauth_10ea4e5fbf849196a4fe8a9c250b737dd5ef17abbeb8f99692d62828465a9823"
            ]
        }
    }

Then Alice can create a group of her friends Bob and Mary:

.. code-block:: http

    $ echo '{"data": {
        "members": ["basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148",
                    "basicauth_8d1661a89bd2670f3c42616e3527fa30521743e4b9825fa4ea05adc45ef695b6"]
    }}' | http PUT https://kinto.dev.mozaws.net/v1/buckets/todo/groups/alice-friends \
        -v --auth 'alice:alicepassword'

    PUT /v1/buckets/todo/groups/alice-friends HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWxpY2U6YWxpY2VwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 180
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {
            "members": [
                "basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148", 
                "basicauth_8d1661a89bd2670f3c42616e3527fa30521743e4b9825fa4ea05adc45ef695b6"
            ]
        }
    }

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
                "basicauth_a103c2e714a04615783de8a03fef1c7fee221214387dd07993bb9aed1f2f2148", 
                "basicauth_8d1661a89bd2670f3c42616e3527fa30521743e4b9825fa4ea05adc45ef695b6"
            ]
        }, 
        "permissions": {
            "write": [
                "basicauth_9be2b51de8544fbed4539382d0885f8643c0185c90fb23201d7bbe86d70b4a44"
            ]
        }
    }

The alice can share here record directly with her group of friends:

.. code-block:: http

    $ echo '{
        "data": {},
        "permissions": {
            "read": ["/buckets/todo/groups/alice-friends"]
        }
    }' | \
    http PUT https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e \
        -v --auth 'alice:alicepassword'

    PUT /v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWxpY2U6YWxpY2VwYXNzd29yZA==
    Connection: keep-alive
    Content-Length: 122
    Content-Type: application/json
    Host: kinto.dev.mozaws.net
    User-Agent: HTTPie/0.9.2

    {
        "data": {}, 
        "permissions": {
            "read": [
                "/buckets/todo/groups/alice-friends"
            ]
        }
    }

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
                "/buckets/todo/groups/alice-friends"
            ], 
            "write": [
                "basicauth_9be2b51de8544fbed4539382d0885f8643c0185c90fb23201d7bbe86d70b4a44"
            ]
        }
    }

Then Mary can get back the record:

.. code-block:: http

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/todo/collections/tasks/records/2fa91620-f4fa-412e-aee0-957a7ad2dc0e \
        -v --auth 'mary:marypassword'




Conclusion
==========

In this tutoriel, you have see all the concept exposed by Kinto:

- Using the default personal user bucket to sync user data
- Creating a bucket to share data between people
- Adding Bucket, Collection and Records
- Editing object's permissions
- Adding a group and assigning permission to a group
- Using ``If-Match``, ``ETag`` and ``_since`` to handle synchronization and conflict handling
