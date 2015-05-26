.. _schemas:

Schemas
#######

A `JSON schema <http://json-schema.org/>`_ can optionally be associated to a
collection.

Once a schema is set, records will be validated during creation or update.

If the validation fails, a ``400 Bad Request`` error response will be
returned.


Schema migrations
=================

*Kinto* does not take care of schema migrations. But it gives the basics for clients
to manage it.

If the validation succeeds, the record will receive a ``schema`` field with the
schema version (i.e. its ``last_modified`` timestamp).

It becomes possible to use ``schema`` as a filter on the collection
endpoint in order to obtain the records that were not validated against a particular
version of the schema.

For example, ``GET /buckets/default/collections/articles/records?min_schema=123456``.


Retrieving the current schema
=============================

.. http:get:: /buckets/(bucket_id)/collections/(collection_id)/schema

    :synopsis: Returns the schema of the collection in this bucket.

    If no schema was defined, a ``404 Not Found`` error response is returned.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http GET http://localhost:8888/v1/buckets/blog/collections/articles/schema --auth "admin:"

    .. sourcecode:: http

        GET /buckets/blog/collections/articles/schema HTTP/1.1
        Accept: application/json
        Accept-Encoding: gzip, deflate
        Authorization: Basic Ym9iOg==
        Connection: keep-alive
        Content-Type: application/json
        Host: localhost:8888
        User-Agent: HTTPie/0.9.2

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert, Last-Modified
        Content-Length: 131
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 10 Jun 2015 10:06:28 GMT
        Last-Modified: 1433930788461
        Server: waitress

        {
            "title": "Blog post schema",
            "type": "object",
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
            ]
        }


Set or replace a schema
=======================

.. http:put:: /buckets/(bucket_id)/collections/(collection_id)/schema

    :synopsis: Associates a JSON schema to the collection in this bucket.

    Associates a JSON schema to the collection in this bucket.

    The schema itself is validated against the `JSON Schema specification version 4
    <http://json-schema.org/>`_.

    If a schema was already defined, it will be replaced.

    .. note::

        Existing records are left intact. If some records do not match the new
        schema, they will be validated only when updated.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ echo '{
            "title": "Blog post schema",
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["title"]
        }' | http PUT http://localhost:8888/v1/buckets/blog/collections/articles/schema --auth "admin:"

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 131
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 10 Jun 2015 10:05:56 GMT
        Server: waitress

        {
            "title": "Blog post schema",
            "type": "object",
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
            ]
        }


Now that a schema has been defined, the posted records must match it:

.. code-block:: bash

    $ echo '{
        "body": "Fails if no title"
    }' | http POST http://localhost:8888/v1/buckets/blog/collections/articles/records --auth "admin:"

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


Remove a schema
===============

.. http:delete:: /buckets/(bucket_id)/collections/(collection_id)/schema

    :synopsis: Removes the schema from the collection in this bucket.

    If no schema was defined, a ``404 Not Found`` error response is returned.

    **Requires authentication**

    **Example request**

    .. sourcecode:: bash

        $ http DELETE http://localhost:8888/v1/buckets/blog/collections/articles/schema --auth "admin:"

    **Example response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Backoff, Retry-After, Alert
        Content-Length: 16
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 10 Jun 2015 10:11:21 GMT
        Server: waitress

        {
            "deleted": true
        }
