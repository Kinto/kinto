.. _permissions-api:

Permissions
###########

Before to start, make sure to have read the :ref:`Understanding
permissions <permissions>` paragraph.

Permissions can be added on any objects (:ref:`buckets <buckets>`,
:ref:`groups <groups>`, :ref:`collections <collections>`,
:ref:`records <records>`)

By default the ``write`` permission is given to the creator of an
object.


How do I get my Kinto user id?
==============================

To be able to add permissions for a user, the user id is needed.

The currently authenticated user id can be obtained on the root url.

.. code-block::
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
            "cliquet.batch_max_requests": 25
        },
        "url": "http://localhost:8888/v1/",
        "userid": "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6",
        "version": "1.4.0"
    }


In this case the user id is: ``basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6``

.. note::

    In case of sharing, users need a way to share their user id with
    people that needs to give them permission.


Object permissions
==================

.. note::

    Please make sure to have read the :ref:`permission documentation <permissions>`
    first.

For instance, we can look at our *personal bucket* permissions.

.. code-block::

    $ http GET http://localhost:8888/v1/buckets/default --auth user:pass
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Last-Modified, ETag
    Content-Length: 187
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 09:59:30 GMT
    Etag: "1437040770742"
    Last-Modified: Thu, 16 Jul 2015 09:59:30 GMT
    Server: waitress

    {
        "data": {
            "id": "46524be8-0ad7-3ac6-e260-71f8993feffa",
            "last_modified": 1437040770742
        },
        "permissions": {
            "write": [
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }


Similarly, the permissions of a collection can be obtained with a ``GET``:

.. code-block::

    $ http GET http://localhost:8888/v1/buckets/default/collections/tasks --auth user:pass
    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Last-Modified, ETag
    Content-Length: 156
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 10:00:30 GMT
    Etag: "1437040830468"
    Last-Modified: Thu, 16 Jul 2015 10:00:30 GMT
    Server: waitress

    {
        "data": {
            "id": "tasks",
            "last_modified": 1437040830468
        },
        "permissions": {
            "write": [
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }


Managing object permissions
===========================

Permissions can be specified during the creation of an object, and can
later be updated using PUT or PATCH.

.. note::

   The user that updates the permissions is always given the ``write``
   permission, in order to prevent loosing ownership on the object.

A :ref:`blog bucket <permissions-use-cases>` could be created with the following to
give read access to everyone.

.. code-block::

    $ echo '{"data":{}, "permissions": {"read": ["system.Authenticated"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog \
        --auth user:pass

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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

Now it will be possible to create two collections (``articles`` and
``comments``) in this bucket. Users will be able to read their content.

.. code-block::

    $ http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles \
        --auth user:pass

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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

    $ echo '{"data":{}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments \
        --auth user:pass

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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

We can add an article.

.. code-block::

    $ echo '{"data":{"title": "My article", "content": "my content", "published_at": "Thu Jul 16 16:44:15 CEST 2015"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records \
        --auth user:pass

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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

Everybody can read the article:

.. code-block::

    $ http GET https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records/b8c4cc34-f184-4b4d-8cad-e135a3f0308c \
        --auth natim:
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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

If we want everyone to be able to add a comment, we can PATCH the
permissions of the ``comments`` collections.

.. code-block::

    $ echo '{"permissions": {"record:create": ["system.Authenticated"]}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments \
        --auth user:pass

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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

Now everyone can add a comment.

.. code-block::

    $ echo '{"data":{"article_id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c", "comment": "my comment", "author": "Natim"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments/records \
        --auth natim:

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
            "author": "Natim",
            "comment": "my comment",
            "id": "5e2292d5-8818-4cd4-be7d-d5a834d36de6",
            "last_modified": 1437058244384
        },
        "permissions": {
            "write": [
                "basicauth:df93ca0ecaeaa3126595f6785b39c408be2539173c991a7b2e3181a9826a69bc"
            ]
        }
    }

Permissions and groups
======================

It is possible to give an ACL to a group.

As described in the :ref:`use case page <permissions-use-cases>`, let us create a
new group ``writers``:


.. code-block::

    $ echo '{"data": {"members": ["basicauth:df93ca0ecaeaa3126595f6785b39c408be2539173c991a7b2e3181a9826a69bc"]}}' | \
        http PUT https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/groups/writers \
        --auth user:pass

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
                "basicauth:df93ca0ecaeaa3126595f6785b39c408be2539173c991a7b2e3181a9826a69bc"
            ]
        },
        "permissions": {
            "write": [
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6"
            ]
        }
    }

Then we can give the write ACL on the bucket for the group.

.. code-block::

    $ echo '{"permissions": {"write": ["/buckets/servicedenuages-blog/groups/writers"]}}' | \
        http PATCH https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog \
        --auth user:pass

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
                "basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6",
                "/buckets/servicedenuages-blog/groups/writers"
            ]
        }
    }

Now the user Natim can create articles.

.. code-block::

    $ echo '{"data":{"title": "Natim article", "content": "natims content", "published_at": "Thu Jul 16 16:59:16 CEST 2015"}}' | \
        http POST https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records \
        --auth natim:
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
        "title": "Natim article"
    },
    "permissions": {
        "write": [
            "basicauth:df93ca0ecaeaa3126595f6785b39c408be2539173c991a7b2e3181a9826a69bc"
        ]
    }
}


Listing shared items
====================

One can fetch the list of articles.

.. code-block::

    $ http GET \
        https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/articles/records \
        --auth natim:

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Total-Records, Last-Modified, ETag
    Connection: keep-alive
    Content-Length: 351
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 15:06:20 GMT
    ETag: "1437058727907"
    Last-Modified: Thu, 16 Jul 2015 14:58:47 GMT
    Server: nginx/1.4.6 (Ubuntu)
    Total-Records: 2

    {
        "data": [
            {
                "content": "natims content",
                "id": "f9a61750-f61f-402b-8785-1647c9325a5d",
                "last_modified": 1437058727907,
                "published_at": "Thu Jul 16 16:59:16 CEST 2015",
                "title": "Natim article"
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

    $ http GET \
        https://kinto.dev.mozaws.net/v1/buckets/servicedenuages-blog/collections/comments/records \
        --auth natim:

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Total-Records, Last-Modified, ETag
    Connection: keep-alive
    Content-Length: 147
    Content-Type: application/json; charset=UTF-8
    Date: Thu, 16 Jul 2015 15:08:48 GMT
    ETag: "1437058244384"
    Last-Modified: Thu, 16 Jul 2015 14:50:44 GMT
    Server: nginx/1.4.6 (Ubuntu)
    Total-Records: 1

    {
        "data": [
            {
                "article_id": "b8c4cc34-f184-4b4d-8cad-e135a3f0308c",
                "author": "Natim",
                "comment": "my comment",
                "id": "5e2292d5-8818-4cd4-be7d-d5a834d36de6",
                "last_modified": 1437058244384
            }
        ]
    }
