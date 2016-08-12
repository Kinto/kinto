.. _api-quotas:

Quotas management
#################

When the built-in plugin ``kinto.plugins.quotas`` is enabled in
configuration, it becomes possible to configure quotas for a bucket or
a collection.

Clients can check for the ``quotas`` capability in the
:ref:`root URL endpoint <api-utilities>`.

.. note::

    In terms of performance, enabling this plugin generates two or
    three additional queries on backends per request.

* The bucket quota consider the bucket attributes, groups attributes,
  collections attributes, records attributes.
* Deleted items size is considered to be null so if you add something
  and remove it, it will looks like it was never created for the
  quota even if its tombstone is still there.
* The quota plugins only works with the transactional storage backends
  (i.e PostgreSQL)


Configuration
=============

You can configure three types of quotas:

* **QUOTA_BYTES**: The maximum total amount (in bytes) of data that
  can be stored in sync storage, as measured by the Canonical JSON
  stringification of every value plus every key's length.
* **QUOTA_BYTES_PER_ITEM**: The maximum size (in bytes) of each
  individual item in sync storage, as measured by the Canonical JSON
  stringification of its value plus its key length.
* **MAX_ITEMS**: The maximum number of items that can be stored in
  sync storage.

You can configure it at multiple levels.

For buckets:

* Globally for each buckets using ``kinto.quotas.bucket_max_bytes``,
  ``kinto.quotas.bucket_max_bytes_per_item`` and
  ``kinto.quotas.bucket_max_items``
* Specifically for some buckets using
  ``kinto.quotas.bucket_{bucket_name}_max_bytes``,
  ``kinto.quotas.bucket_{bucket_name}_max_bytes_per_item`` and
  ``kinto.quotas.bucket_{bucket_name}_max_items`` i.e
  ``kinto.quotas.bucket_blocklists_max_items``

For collections:

* Globally for each bucket collections using ``kinto.quotas.collection_max_bytes``,
  ``kinto.quotas.collection_max_bytes_per_item`` and
  ``kinto.quotas.collection_max_items``
* Specifically for every collection in a given bucket using
  ``kinto.quotas.collection_{bucket_name}_max_bytes``,
  ``kinto.quotas.collection_{bucket_name}_max_bytes_per_item`` and
  ``kinto.quotas.collection_{bucket_name}_max_items`` i.e
  ``kinto.quotas.collection_blocklists_max_items``
* Specifically for a given bucket collection using
  ``kinto.quotas.collection_{bucket_name}_{collection_name}_max_bytes``,
  ``kinto.quotas.collection_{bucket_name}_{collection_name}_max_bytes_per_item`` and
  ``kinto.quotas.collection_{bucket_name}_{collection_name}_max_items`` i.e
  ``kinto.quotas.collection_blocklists_certificates_max_items``


How does it works?
==================

If the quota is exceeded the server will return a ``507 Insufficient
Storage`` HTTP error.

.. code-block:: json

    HTTP/1.1 507 Insufficient Storage
    Access-Control-Expose-Headers: Backoff,Retry-After,Alert,Content-Length
    Content-Length: 115
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 12 Aug 2016 10:14:29 GMT
    Server: waitress

    {
        "code": 507, 
        "errno": 121, 
        "error": "Insufficient Storage", 
        "message": "There was not enough space to save the resource"
    }
