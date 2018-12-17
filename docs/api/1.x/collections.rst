.. _collections:

Collections
###########

A collection belongs to a bucket and stores records.

A collection is a mapping with the following attributes:

* ``data``: (*optional*) attributes of the collection object
    * ``id``: the collection object id
    * ``last_modified``: the timestamp of the last modification
    * ``schema``: (*optional*) a JSON schema to validate the collection records
    * ``cache_expires``: (*optional*, in seconds) add client cache headers on   read-only requests.
      :ref:`More details...<collection-caching>`
    * and any field you might need
* ``permissions``: the :term:`ACLs <ACL>` for the collection object


.. note::


    When the built-in plugin ``kinto.plugins.default_bucket`` is enabled in
    configuration, a bucket ``default`` is available.

    Users are assigned to that bucket which can be used for their personal data.

    When going through the ``default`` bucket, the collections are created
    silently upon first access.

    Applications can use this default bucket (e.g. ``/buckets/default/collections/contacts`` will be
    the contacts of the current user.

    Internally the user default bucket is assigned to an ID, and users can share
    data from their personnal bucket, by sharing :ref:`its URL using the full ID <buckets-default-id>`.


.. _collections-get:

List bucket collections
=======================

.. http:get:: /buckets/(bucket_id)/collections

   :synopsis: List bucket's readable collections

   **Requires authentication**

   **Example Request**

   .. sourcecode:: bash

      $ http GET http://localhost:8888/v1/buckets/blog/collections --auth="bob:p4ssw0rd" --verbose

   .. sourcecode:: http

      GET /v1/buckets/blog/collections HTTP/1.1
      Accept: */*
      Accept-Encoding: gzip, deflate
      Authorization: Basic YWxpY2U6
      Connection: keep-alive
      Host: localhost:8888
      User-Agent: HTTPie/0.9.2

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Access-Control-Expose-Headers: Content-Length, Expires, Alert, Retry-After, Last-Modified, ETag, Pragma, Cache-Control, Backoff, Next-Page
      Cache-Control: no-cache
      Content-Length: 144
      Content-Type: application/json; charset=UTF-8
      Date: Fri, 26 Feb 2016 14:14:40 GMT
      Etag: "1456496072475"
      Last-Modified: Fri, 26 Feb 2016 14:14:32 GMT
      Server: waitress

      {
          "data": [
              {
                  "id": "scores",
                  "last_modified": 1456496072475
              },
              {
                  "id": "game",
                  "last_modified": 1456496060675
              },
              {
                  "id": "articles",
                  "last_modified": 1456496056908
              }
          ]
      }

.. include:: _details-get-list.rst

.. include:: _details-head-list.rst

.. include:: _status-get-list.rst


.. _collections-delete:

Delete bucket collections
=========================

.. http:delete:: /buckets/(bucket_id)/collections

    :synopsis: Delete every writable collections in this bucket

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections --auth="bob:p4ssw0rd" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/collections HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic YWxpY2U6
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
        Content-Length: 189
        Content-Type: application/json; charset=UTF-8
        Date: Fri, 26 Feb 2016 14:19:21 GMT
        Server: waitress

        {
            "data": [
                {
                    "deleted": true,
                    "id": "articles",
                    "last_modified": 1456496361303
                },
                {
                    "deleted": true,
                    "id": "game",
                    "last_modified": 1456496361304
                },
                {
                    "deleted": true,
                    "id": "scores",
                    "last_modified": 1456496361305
                }
            ]
        }

.. include:: _details-delete-list.rst

.. include:: _status-delete-list.rst


.. _collections-post:

Creating a collection
=====================

.. http:post:: /buckets/(bucket_id)/collections

   :synopsis: Creates a new collection. If ``id`` is not provided, it is automatically generated.

   **Requires authentication**

   **Example Request**

   .. sourcecode:: bash

      $ echo '{"data": {"id": "articles"}}' | http POST http://localhost:8888/v1/buckets/blog/collections --auth="bob:p4ssw0rd" --verbose

   .. sourcecode:: http

      POST /v1/buckets/blog/collections HTTP/1.1
      Accept: application/json
      Accept-Encoding: gzip, deflate
      Authorization: Basic Ym9iOg==
      Connection: keep-alive
      Content-Length: 29
      Content-Type: application/json
      Host: 127.0.0.1:8888
      User-Agent: HTTPie/0.9.2

      {
          "data": {
              "id": "articles"
          }
      }

   .. sourcecode:: http

      HTTP/1.1 201 Created
      Access-Control-Expose-Headers: Retry-After, Content-Length, Alert, Backoff
      Content-Length: 159
      Content-Type: application/json; charset=UTF-8
      Date: Thu, 21 Jan 2016 00:41:25 GMT
      Server: waitress

      {
          "data": {
              "id": "articles",
              "last_modified": 1453336885287
          },
          "permissions": {
              "write": [
                  "account:bob"
              ]
          }
      }

.. include:: _details-post-list.rst

.. include:: _status-post-list.rst


.. _collection-put:

Replacing a collection
======================


.. http:put:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Creates or replaces a collection object.

    **Requires authentication**

    A collection is the parent object of records. It can be viewed as a container where records permissions are assigned globally.

    **Example Request**

    .. sourcecode:: bash

        $ http put http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:p4ssw0rd" --verbose

    .. sourcecode:: http

        PUT /v1/buckets/blog/collections/articles HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 159
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:36:34 GMT
        Server: waitress

        {
            "data": {
                "id": "articles",
                "last_modified": 1434641794149
            },
            "permissions": {
                "write": [
                    "account:bob"
                ]
            }
        }

.. include:: _details-put-object.rst

.. include:: _status-put-object.rst


.. _collection-patch:

Updating a collection
=====================


.. http:patch:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Updates a collection object.

    **Requires authentication**

    A collection is the parent object of records. It can be viewed as
    a container where records permissions are assigned globally.

    **Example Request**

    .. sourcecode:: bash

        $ echo '{"data": {"fingerprint": "9cae1b2d0f2b7d09bcf5c1bf51544274"}}' | http patch http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:p4ssw0rd" --verbose

    .. sourcecode:: http

        PATCH /v1/buckets/blog/collections/articles HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 62
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {
                "fingerprint": "9cae1b2d0f2b7d09bcf5c1bf51544274"
            }
        }

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 208
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:36:34 GMT
        Server: waitress

        {
            "data": {
                "id": "articles",
                "last_modified": 1434641794149,
                "fingerprint": "9cae1b2d0f2b7d09bcf5c1bf51544274"
            },
            "permissions": {
                "write": [
                    "account:bob"
                ]
            }
        }

.. include:: _details-patch-object.rst

.. include:: _status-patch-object.rst


.. _collection-get:

Retrieving an existing collection
=================================

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Returns the collection object.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:p4ssw0rd" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/collections/articles HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2


    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified, ETag
        Content-Length: 159
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:52:31 GMT
        Etag: "1434642751314"
        Last-Modified: Thu, 18 Jun 2015 15:52:31 GMT
        Server: waitress

        {
            "data": {
                "id": "articles",
                "last_modified": 1434641794149
            },
            "permissions": {
                "write": [
                    "account:bob"
                ]
            }
        }

.. include:: _details-get-object.rst

.. include:: _status-get-object.rst


.. _collection-delete:

Deleting a collection
=====================

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)

    :synopsis: Deletes a specific collection and **everything under it**.

    **Requires authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:p4ssw0rd" --verbose

    .. sourcecode:: http

        DELETE /v1/buckets/blog/collections/articles HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 0
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 71
        Content-Type: application/json; charset=UTF-8
        Date: Thu, 18 Jun 2015 15:54:02 GMT
        Server: waitress

        {
            "data": {
                "deleted": true,
                "id": "articles",
                "last_modified": 1434642842010
            }
        }

.. include:: _details-delete-object.rst

.. include:: _status-delete-object.rst


.. _collection-json-schema:

Collection JSON schema
======================

**Requires setting** ``kinto.experimental_collection_schema_validation`` to ``True``.

A `JSON schema <http://json-schema.org/>`_ can optionally be associated to a
collection.

Once a schema is set, records will be validated during creation or update.

If the validation fails, a |status-400| error response will be
returned.

.. note::

    JSON schema is quite verbose and not an ideal solution for every use-case.
    However it is universal and supported by many programming languages
    and environments.


Set or replace a schema
-----------------------

Just modify the ``schema`` attribute of the collection object:

**Example request**

.. code-block:: bash

    $ echo '{
      "data": {
        "schema": {
          "title": "Blog post schema",
          "type": "object",
          "properties": {
              "title": {"type": "string"},
              "body": {"type": "string"}
          },
          "required": ["title"]
        }
      }
    }' | http PATCH "http://localhost:8888/v1/buckets/blog/collections/articles" --auth bob:p4ssw0rd --verbose

.. code-block:: http

    PATCH /v1/buckets/blog/collections/articles HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWRtaW46
    Connection: keep-alive
    Content-Length: 236
    Content-Type: application/json; charset=utf-8
    Host: localhost:8888
    User-Agent: HTTPie/0.8.0

    {
        "data": {
            "schema": {
                "properties": {
                    "body": {
                        "type": "string"
                    },
                    "title": {
                        "type": "string"
                    }
                },
                "required": [
                    "title"
                ],
                "title": "Blog post schema",
                "type": "object"
            }
        }
    }

**Example response**

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 300
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 21 Aug 2015 12:31:40 GMT
    Etag: "1440160300818"
    Last-Modified: Fri, 21 Aug 2015 12:31:40 GMT
    Server: waitress

    {
        "data": {
            "id": "articles",
            "last_modified": 1440160300818,
            "schema": {
                "properties": {
                    "body": {
                        "type": "string"
                    },
                    "title": {
                        "type": "string"
                    }
                },
                "required": [
                    "title"
                ],
                "title": "Blog post schema",
                "type": "object"
            }
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }



Records validation
------------------

Once a schema has been defined, the posted records must match it:

.. code-block:: bash

    $ echo '{"data": {
        "body": "Fails if no title"
    }}' | http POST http://localhost:8888/v1/buckets/blog/collections/articles/records --auth "bob:p4ssw0rd"

.. code-block:: http

    HTTP/1.1 400 Bad Request
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert
    Content-Length: 192
    Content-Type: application/json; charset=UTF-8
    Date: Wed, 10 Jun 2015 10:17:01 GMT
    Server: waitress

    {
        "code": 400,
        "details": [
            {
                "description": "'title' is a required property",
                "location": "body",
                "name": "title"
            }
        ],
        "errno": 107,
        "error": "Invalid parameters",
        "message": "'title' is a required property"
    }



Schema migrations
-----------------

*Kinto* does not take care of schema migrations. But it gives the basics for clients
to manage it.

If the validation succeeds, the record will receive a ``schema`` field with the
schema version (i.e. the collection current ``last_modified`` timestamp).

It becomes possible to use this ``schema`` field as a filter on the collection
records endpoint in order to obtain the records that were not validated against a particular
version of the schema.

For example, ``GET /buckets/blog/collections/articles/records?min_schema=123456``.


Remove a schema
---------------

In order to remove the schema of a collection, just modify the ``schema`` field
to an empty mapping.


**Example request**

.. code-block:: bash

    echo '{"data": {"schema": {}} }' | http PATCH "http://localhost:8888/v1/buckets/blog/collections/articles" --auth bob:p4ssw0rd --verbose

.. code-block:: http

    PATCH /v1/buckets/blog/collections/articles HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWRtaW46
    Connection: keep-alive
    Content-Length: 26
    Content-Type: application/json; charset=utf-8
    Host: localhost:8888
    User-Agent: HTTPie/0.8.0

    {
        "data": {
            "schema": {}
        }
    }

**Example response**

.. code-block:: http

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length
    Content-Length: 171
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 21 Aug 2015 12:27:04 GMT
    Etag: "1440159981842"
    Last-Modified: Fri, 21 Aug 2015 12:26:21 GMT
    Server: waitress

    {
        "data": {
            "id": "articles",
            "last_modified": 1440159981842,
            "schema": {}
        },
        "permissions": {
            "write": [
                "account:bob"
            ]
        }
    }


Same schema for every collection
--------------------------------

It is possible to define a JSON schema that will apply to every collections records inside a bucket.

This can be useful when a particular application creates collections whose records should all be validated against the same schema.

To achieve that, instead of storing the definition in the ``schema`` field in the metadata of a particular collection, the definition can be stored in the ``record:schema`` field in the metadata of the bucket.

.. code-block:: http

    PATCH /v1/buckets/blog HTTP/1.1
    Accept: application/json
    Accept-Encoding: gzip, deflate
    Authorization: Basic YWRtaW46
    Connection: keep-alive
    Content-Length: 236
    Content-Type: application/json; charset=utf-8
    Host: localhost:8888
    User-Agent: HTTPie/0.8.0

    {
        "data": {
            "record:schema": {
                "properties": {
                    "body": {
                        "type": "string"
                    },
                    "title": {
                        "type": "string"
                    }
                },
                "required": [
                    "title"
                ],
                "title": "Blog post schema",
                "type": "object"
            }
        }
    }

Collection metadata validation
------------------------------

By default, only a few fields in the collection metadata must respect a particular schema (eg. ``schema``, ``cache_expires``...), and metadata will accept any kind of additional fields.

In order to validate the additional fields, it is possible to define a schema on the parent bucket metadata.

To achieve that, just modify the ``collection:schema`` attribute of the parent bucket object:

**Example request**

.. code-block:: bash

    $ echo '{
      "data": {
        "collection:schema": {
          "title": "Admin Collection",
          "type": "object",
          "properties": {
              "uiSchema": {"type": "object"},
          }
        }
      }
    }' | http PATCH "http://localhost:8888/v1/buckets/blog" --auth bob:p4ssw0rd --verbose


.. _collection-caching:

Collection caching
==================

With the ``cache_expires`` attribute on a collection, it is possible to add client
cache control response headers for read-only requests.
The client (or cache server or proxy) will use them to cache the collection
records for a certain amount of time, in seconds.

For example, set it to ``3600`` (1 hour):

.. code-block:: bash

    echo '{"data": {"cache_expires": 3600} }' | http PATCH "http://localhost:8888/v1/buckets/blog/collections/articles" --auth bob:p4ssw0rd

From now on, the cache control headers are set for the `GET` requests:

.. code-block:: bash

    http  "http://localhost:8888/v1/buckets/blog/collections/articles/records" --auth bob:p4ssw0rd

.. code-block:: http
    :emphasize-lines: 3,8

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Last-Modified, ETag, Cache-Control, Expires, Pragma
    Cache-Control: max-age=3600
    Content-Length: 11
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 14 Sep 2015 13:51:47 GMT
    Etag: "1442238450779"
    Expires: Mon, 14 Sep 2015 14:51:47 GMT
    Last-Modified: Mon, 14 Sep 2015 13:47:30 GMT
    Server: waitress

    {
        "data": [{}]
    }


If set to ``0``, the collection records become explicitly uncacheable (``no-cache``).

.. code-block:: bash

    echo '{"data": {"cache_expires": 0} }' | http PATCH "http://localhost:8888/v1/buckets/blog/collections/articles" --auth bob:p4ssw0rd

.. code-block:: http
    :emphasize-lines: 3,8,10

    HTTP/1.1 200 OK
    Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Content-Length, Next-Page, Last-Modified, ETag, Cache-Control, Expires, Pragma
    Cache-Control: max-age=0, must-revalidate, no-cache, no-store
    Content-Length: 11
    Content-Type: application/json; charset=UTF-8
    Date: Mon, 14 Sep 2015 13:54:51 GMT
    Etag: "1442238450779"
    Expires: Mon, 14 Sep 2015 13:54:51 GMT
    Last-Modified: Mon, 14 Sep 2015 13:47:30 GMT
    Pragma: no-cache
    Server: waitress

    {
        "data": []
    }

.. note::

    This can also be forced from settings, see :ref:`configuration section <configuration-client-caching>`.
