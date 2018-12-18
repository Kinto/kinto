.. _tutorial-permissions:

Step by step permissions API tutorial
#####################################

Let's use one of the :ref:`application examples <permissions-setups-blog>`: using *Kinto* as
a storage API for a blog application.

.. note::

    Some general details are provided in the :ref:`kinto-concepts` and :ref:`api-permissions`
    sections. Make sure you are familiar with main concepts before starting this.

.. important::

    In this tutorial, we use the :ref:`internal accounts plugin <api-accounts>`.

    We create the following accounts::

        $ echo '{"data": {"password": "s3cr3t"}}' | http PUT http://localhost:8888/v1/accounts/julia
        $ echo '{"data": {"password": "wh1sp3r"}}' | http PUT http://localhost:8888/v1/accounts/natim


Basic permission setup
======================

The ``servicedenuages-blog`` bucket will contain two collections: ``articles`` and
``comments``.

Let's start by giving all authenticated users read access to the bucket.

.. code-block:: shell

    $ echo '{"permissions": {"read": ["system.Authenticated"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 203
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:20:37 GMT
    ETag: "1437056437581"
    Last-Modified: Thu, 16 Jul 2015 14:20:37 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "servicedenuages-blog",
            "last_modified": 1437056437581
        },
        "permissions": {
            "read": [
                "system.Authenticated"
            ],
            "write": [
                "account:julia"
            ]
        }
    }


Now, with that same user, let's create two collections in this
buckets: ``articles`` and ``comments``.

.. code-block:: shell

    $ http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 159
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:40:39 GMT
    ETag: "1437057639758"
    Last-Modified: Thu, 16 Jul 2015 14:40:39 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "articles",
            "last_modified": 1437057639758
        },
        "permissions": {
            "write": [
                "account:julia"
            ]
        }
    }

.. code-block:: shell

    $ http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 159
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:41:39 GMT
    ETag: "1437057699755"
    Last-Modified: Thu, 16 Jul 2015 14:41:39 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "comments",
            "last_modified": 1437057699755
        },
        "permissions": {
            "write": [
                "account:julia"
            ]
        }
    }

Thanks to the ``read`` permission that we set previously, all authenticated users
will be able to read both collections.

Let's verify that. Create an article:

.. code-block:: shell

    $ echo '{"data":{"title": "My article", "content": "my content", "published_at": "Thu Jul 16 16:44:15 CEST 2015"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Backoff: 10
    Connection: keep-alive
    Content-Length: 278
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:43:45 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "content": "my content",
            "id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c",
            "last_modified": 1437057825171,
            "published_at": "Thu Jul 16 16:44:15 CEST 2015",
            "title": "My article"
        },
        "permissions": {
            "write": [
                "account:julia"
            ]
        }
    }

Indeed, using another user like *natim*, we can read the article:

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records/b8c4cc34-f184-4b4d-8cad-e135a3f0308c \
        --auth natim:wh1sp3r

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Last-Modified, ETag
    Connection: keep-alive
    Content-Length: 278
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:46:49 GMT
    ETag: "1437057825171"
    Last-Modified: Thu, 16 Jul 2015 14:43:45 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "content": "my content",
            "id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c",
            "last_modified": 1437057825171,
            "published_at": "Thu Jul 16 16:44:15 CEST 2015",
            "title": "My article"
        },
        "permissions": {
            "write": [
                "account:julia"
            ]
        }
    }

If we want authenticated users to be able to create a comment, we can PATCH the
permissions of the ``comments`` collections:

.. code-block:: shell

    $ echo '{"permissions": {"record:create": ["system.Authenticated"]}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 200
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:49:38 GMT
    ETag: "1437057699755"
    Last-Modified: Thu, 16 Jul 2015 14:41:39 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "comments",
            "last_modified": 1437057699755
        },
        "permissions": {
            "record:create": [
                "system.Authenticated"
            ],
            "write": [
                "account:julia"
            ]
        }
    }

Now every authenticated user, like *natim* here, can add a comment.

.. code-block:: shell

    $ echo '{"data":{"article_id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c", "comment": "my comment", "author": "*natim*"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments/records \
        --auth natim:wh1sp3r

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 248
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:50:44 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "article_id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c",
            "author": "*natim*",
            "comment": "my comment",
            "id": "5e2292d5-8818-4cd4-be7d-d5a834d36de6",
            "last_modified": 1437058244384
        },
        "permissions": {
            "write": [
                "account:natim"
            ]
        }
    }


Permissions and groups
======================

So far only the creator of the initial bucket (i.e. julia, the blog admin) can write
articles. Let's invite some writers to create articles!

We will create a new group called ``writers`` with *natim* as one of the members.

.. code-block:: shell

    $ echo '{"data": {"members": ["account:natim"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/groups/writers \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 247
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:54:58 GMT
    ETag: "1437058498218"
    Last-Modified: Thu, 16 Jul 2015 14:54:58 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "writers",
            "last_modified": 1437058498218,
            "members": [
                "account:natim"
            ]
        },
        "permissions": {
            "write": [
                "account:julia"
            ]
        }
    }

Now we grant the `write` permission on the blog bucket to the ``writers`` group.

.. code-block:: shell

    $ echo '{"permissions": {"write": ["/buckets/servicedenuages-blog/groups/writers"]}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog \
        --auth julia:s3cr3t

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 254
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:56:55 GMT
    ETag: "1437056437581"
    Last-Modified: Thu, 16 Jul 2015 14:20:37 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "id": "servicedenuages-blog",
            "last_modified": 1437056437581
        },
        "permissions": {
            "read": [
                "system.Authenticated"
            ],
            "write": [
                "account:julia",
                "/buckets/servicedenuages-blog/groups/writers"
            ]
        }
    }

Now *natim* can write new articles!

.. code-block:: shell

    $ echo '{"data":{"title": "natim article", "content": "natims content", "published_at": "Thu Jul 16 16:59:16 CEST 2015"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records \
        --auth natim:wh1sp3r

.. code-block:: http

    HTTP/1.1 201 Created
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Connection: keep-alive
    Content-Length: 285
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 14:58:47 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": {
            "content": "natims content",
            "id": "f9a61750-f61f-402b-8785-1647c9325a5d",
            "last_modified": 1437058727907,
            "published_at": "Thu Jul 16 16:59:16 CEST 2015",
            "title": "natim article"
        },
        "permissions": {
            "write": [
                "account:natim"
            ]
        }
    }


Listing records
===============

One can fetch the list of articles.

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Last-Modified, ETag
    Connection: keep-alive
    Content-Length: 351
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 15:06:20 GMT
    ETag: "1437058727907"
    Last-Modified: Thu, 16 Jul 2015 14:58:47 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": [
            {
                "content": "natims content",
                "id": "f9a61750-f61f-402b-8785-1647c9325a5d",
                "last_modified": 1437058727907,
                "published_at": "Thu Jul 16 16:59:16 CEST 2015",
                "title": "natim article"
            },
            {
                "content": "my content",
                "id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c",
                "last_modified": 1437057825171,
                "published_at": "Thu Jul 16 16:44:15 CEST 2015",
                "title": "My article"
            }
        ]
    }

Or the list of comments.

.. code-block:: shell

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments/records

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Last-Modified, ETag
    Connection: keep-alive
    Content-Length: 147
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 15:08:48 GMT
    ETag: "1437058244384"
    Last-Modified: Thu, 16 Jul 2015 14:50:44 GMT
    Server: nginx/1.4.6 (Ubuntu)

    {
        "data": [
            {
                "article_id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c",
                "author": "natim",
                "comment": "my comment",
                "id": "5e2292d5-8818-4cd4-be7d-d5a834d36de6",
                "last_modified": 1437058244384
            }
        ]
    }
