.. _collections:

Collections
###########

A collection belongs to a bucket and stores records.

A collection is a mapping with the following attribute:

* ``schema``: (*optional*) a JSON schema to validate the collection records

.. note::

    By default users are assigned to a bucket that is used for their
    personal data.

    Application can use this default bucket with the ``default``
    shortcut: ie ``/buckets/default/collections/contacts`` will be
    the current user contacts.

    Internally the user default bucket is assigned to an id that can
    later be used to share data from a user personnal bucket.

    Collection on a the default bucket are created silently on first access.


Creating a collection
=====================


.. http:put:: /buckets/(bucket_id)/collections/(collection_id)

    **Requires authentication**
    Creates or replaces a collection object.

    A collection is the parent object of records. It can be viewed as a container where records permissions are assigned globally.

    .. sourcecode:: bash

        $ echo '{"data": {}}' | http put http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:" --verbose

    **Example Request**

    .. sourcecode:: http

        PUT /v1/buckets/blog/collections/articles HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Length: 13
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

        {
            "data": {}
        }

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
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }

    .. note::

        In order to create only if it does not exist yet, a ``If-None-Match: *``
        request header can be provided. A ``412 Precondition Failed`` error response
        will be returned if the record already exists.


Retrieving an existing collection
=================================

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)

    **Requires authentication**


    Returns the collection object.

    .. sourcecode:: bash

        $ http get http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:" --verbose


    **Example Request**

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
                    "basicauth:206691a25679e4e1135f16aa77ebcf211c767393c4306cfffe6cc228ac0886b6"
                ]
            }
        }


Deleting a collection
=====================

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)

    **Requires authentication**

    Deletes a specific collection, and **everything under it**.

    .. sourcecode:: bash

        $ http delete http://localhost:8888/v1/buckets/blog/collections/articles --auth="bob:" --verbose

    **Example Request**

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


Collection JSON schema
======================

A `JSON schema <http://json-schema.org/>`_ can optionally be associated to a
collection.

Once a schema is set, records will be validated during creation or update.

If the validation fails, a ``400 Bad Request`` error response will be
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
    }' | http PATCH "http://localhost:8888/v1/buckets/default/collections/articles" --auth admin: --verbose

.. code-block:: http

    PATCH /v1/buckets/default/collections/articles HTTP/1.1
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
                "basicauth:780f1ecd9f57b01bef79608b45916d3bddd17f83461ac6240402e0ffff3596c5"
            ]
        }
    }



Records validation
------------------

Once a schema has been defined, the posted records must match it:

.. code-block:: bash

    $ echo '{"data": {
        "body": "Fails if no title"
    }}' | http POST http://localhost:8888/v1/buckets/blog/collections/articles/records --auth "admin:"

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
                "description": "u'title' is a required property",
                "location": "body",
                "name": "title"
            }
        ],
        "errno": 107,
        "error": "Invalid parameters",
        "message": "u'title' is a required property"
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

For example, ``GET /buckets/default/collections/articles/records?min_schema=123456``.


Remove a schema
---------------

In order to remove the schema of a collection, just modify the ``schema`` field
to an empty mapping.


**Example request**

.. code-block:: bash

    echo '{"data": {"schema": {}} }' | http PATCH "http://localhost:8888/v1/buckets/default/collections/articles" --auth admin: --verbose

.. code-block:: http

    PATCH /v1/buckets/default/collections/articles HTTP/1.1
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
                "basicauth:780f1ecd9f57b01bef79608b45916d3bddd17f83461ac6240402e0ffff3596c5"
            ]
        }
    }
