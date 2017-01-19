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

* A bucket's quota is a limit on the size of bucket attributes, group
  attributes, collection attributes, and record attributes.
* Deleted objects are considered to have a size zero so if you add something
  and remove it, it will look like it was never created for the
  quota even if its tombstone is still there.
* The quota plugin only works with the transactional storage backends
  (e.g. PostgreSQL)
* The quota plugin should be activated before adding some data in a
  bucket or collection. If activated after, the size of the data
  already present will be added to the quota limit even if this data
  is deleted later.


Configuration
=============

You can configure three types of quotas:

* **QUOTA_BYTES**: The maximum total amount (in bytes) of data that
  can be stored in a bucket or collection, as measured by the JSON
  stringification of every value plus every key's length.
* **QUOTA_BYTES_PER_ITEM**: The maximum size (in bytes) of each
  individual item in the bucket or collection, as measured by the JSON
  stringification of its value plus its key length.
* **MAX_ITEMS**: The maximum number of objects that can be stored in
  a collection or bucket.

You can configure it in the INI settings file.

For buckets:

* Globally for every buckets using ``kinto.quotas.bucket_max_bytes``,
  ``kinto.quotas.bucket_max_bytes_per_item`` and
  ``kinto.quotas.bucket_max_items``
* Specifically for some buckets using
  ``kinto.quotas.bucket_{bucket_id}_max_bytes``,
  ``kinto.quotas.bucket_{bucket_id}_max_bytes_per_item`` and
  ``kinto.quotas.bucket_{bucket_id}_max_items`` e.g.
  ``kinto.quotas.bucket_blocklists_max_items``

For collections:

* Globally for every bucket collections using ``kinto.quotas.collection_max_bytes``,
  ``kinto.quotas.collection_max_bytes_per_item`` and
  ``kinto.quotas.collection_max_items``
* Specifically for every collection in a given bucket using
  ``kinto.quotas.collection_{bucket_id}_max_bytes``,
  ``kinto.quotas.collection_{bucket_id}_max_bytes_per_item`` and
  ``kinto.quotas.collection_{bucket_id}_max_items`` e.g.
  ``kinto.quotas.collection_blocklists_max_items``
* Specifically for a given bucket collection using
  ``kinto.quotas.collection_{bucket_id}_{collection_id}_max_bytes``,
  ``kinto.quotas.collection_{bucket_id}_{collection_id}_max_bytes_per_item`` and
  ``kinto.quotas.collection_{bucket_id}_{collection_id}_max_items`` e.g.
  ``kinto.quotas.collection_blocklists_certificates_max_items``


How does it work?
=================

If the quota is exceeded the server will return a ``507 Insufficient
Storage`` HTTP error.

**Example Response**

.. sourcecode:: http

    HTTP/1.1 507 Insufficient Storage
    Access-Control-Expose-Headers: Backoff,Retry-After,Alert,Content-Length
    Content-Length: 132
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 12 Aug 2016 10:14:29 GMT
    Server: waitress

    {
        "code": 507,
        "errno": 121,
        "error": "Insufficient Storage",
        "message": "Collection maximum number of objects exceeded (2 > 1 objects)"
    }
