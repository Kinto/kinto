.. _api-history:

History of changes
##################

When the built-in plugin ``kinto.plugins.history`` is enabled in configuration,
it becomes possible to track the history of changes via a new endpoint ``GET /buckets/<bid>/history``.

Clients can check for the ``history`` capability in the :ref:`root URL endpoint <api-utilities>`.

.. note::

    In terms of performance, enabling this plugin generates three additional queries
    on backends per request (i.e. per transaction).

* Creations/updates/deletions of every kind of object is tracked per bucket;
* Both data and permissions changes are provided in history entries;
* Only the new version of the record is stored in the history entry for each action;
* The history only shows the actions that were performed on objects where the user had read or write permission;
* When requested anonymously, the history only shows actions on publicly readable/writable objects;
* The ``default_bucket`` plugin is supported;
* Entries can be filtered and sorted as any list endpoint.


.. _history-get:

Retrieve history
================

.. http:get:: /buckets/(bucket_id)/history

    :synopsis: Retrieve the history, ordered by `-last_modified` by default.

    **Optional authentication**

    **Example Request**

    .. sourcecode:: bash

        $ http GET http://localhost:8888/v1/buckets/blog/history --auth="token:bob-token" --verbose

    .. sourcecode:: http

        GET /v1/buckets/blog/history HTTP/1.1
        Accept: */*
        Accept-Encoding: gzip, deflate
        Authorization: Basic dG9rZW46Ym9iLXRva2Vu
        Connection: keep-alive
        Host: localhost:8888

  **Example Response**

  .. sourcecode:: http

        HTTP/1.1 200 OK
        Access-Control-Expose-Headers: Content-Length, Expires, Alert, Retry-After, Last-Modified, Total-Records, ETag, Pragma, Cache-Control, Backoff, Next-Page
        Cache-Control: no-cache, no-store
        Content-Length: 1906
        Content-Type: application/json; charset=UTF-8
        Date: Wed, 20 Jul 2016 09:15:02 GMT
        Etag: "1469006098757"
        Last-Modified: Wed, 20 Jul 2016 09:14:58 GMT
        Server: waitress
        Total-Records: 4

        {
            "data": [
                {
                    "action": "update",
                    "collection_id": "articles",
                    "date": "2016-07-20T11:18:36.530281",
                    "id": "cb98ecd7-a66f-4f9d-82c5-73d06930f4f2",
                    "last_modified": 1469006316530,
                    "record_id": "b3b76c56-b6df-4195-8189-d79da4a128e1",
                    "resource_name": "record",
                    "target": {
                        "data": {
                            "id": "b3b76c56-b6df-4195-8189-d79da4a128e1",
                            "last_modified": 1469006316529,
                            "title": "Modified title"
                        },
                        "permissions": {
                            "write": [
                                "basicauth:43181ac0ae7581a23288c25a98786ef9db86433c62a04fd6071d11653ee69089"
                            ]
                        }
                    },
                    "timestamp": 1469006098757,
                    "uri": "/buckets/blog/collections/articles/records/b3b76c56-b6df-4195-8189-d79da4a128e1",
                    "user_id": "basicauth:43181ac0ae7581a23288c25a98786ef9db86433c62a04fd6071d11653ee69089",
                }
            ]
        }

As other list endpoints, the entries can be filtered and sorted using the querystring.

* ``?_since="<timestamp>"`` and ``?_before="<timestamp>"`` to filter by timestamp/last_modified
* ``?_limit=<N>``: limits to N entries (use ``Next-Page`` response header for pagination)
* ``?uri=<URI>``: to filter on a particular object
* ``?collection=<id>``: to filter on a particular collection
* ``?resource_name=<bucket|group|collection|record>``: to filter by object type
* See :ref:`filtering`, :ref:`sorting`, :ref:`paginating` and :ref:`selecting-fields`.

.. note::

    If the server defines a ``kinto.paginate_by`` setting, the list will be limited by default.


Conflict resolution
===================

Having the journal of operations of an object possibly allows to resolve update conflicts automatically.

For example, if Alice receives a |status-412| error response when she tries to update a record,
she can use the history entries for this particular record filtering from a the timestamp of her local copy, in order
to merge the changes that happened remotely with her local ones.

.. sourcecode:: bash

    $ RECORD_URI="buckets/blog/collections/articles/records/xyz"
    $ LOCAL_TIMESTAMP="1469006098757"
    $ http GET http://localhost:8888/v1/buckets/blog/history?uri=$RECORD_URI&_since=$LOCAL_TIMESTAMP --auth="token:bob-token" --verbose

Each entries gives the state in which the record was modified. Computing the difference between
two steps and applying it to the local record is a possible way of solving conflicts automatically.
