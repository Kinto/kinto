.. _api-endpoints:

HTTP endpoints
##############

+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| Method   | URI                                                                                          | Description                                             |
+==========+==============================================================================================+=========================================================+
| `GET`    | :ref:`/ <api-utilities>`                                                                     | :ref:`Information about the running instance            |
|          |                                                                                              | <api-utilities>`                                        |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `POST`   | :ref:`/batch <batch>`                                                                        | :ref:`Send multiple operations in one request <batch>`  |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `GET`    | :ref:`/__heartbeat__ <api-utilities>`                                                        | :ref:`Return the status of dependent services           |
|          |                                                                                              | <api-utilities>`                                        |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `PUT`    | :ref:`/buckets/(bucket_id) <bucket-put>`                                                     | :ref:`Create or replaces a bucket <bucket-put>`         |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `GET`    | :ref:`/buckets/(bucket_id) <bucket-get>`                                                     | :ref:`Retrieve an existing bucket <bucket-get>`         |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `DELETE` | :ref:`/buckets/(bucket_id) <bucket-delete>`                                                  | :ref:`Delete a bucket <bucket-delete>`                  |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `PUT`    | :ref:`/buckets/(bucket_id)/collections/(collection_id) <collection-put>`                     | :ref:`Create or replace a collection <collection-put>`  |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `GET`    | :ref:`/buckets/(bucket_id)/collections/(collection_id) <collection-get>`                     | :ref:`Retreive an existing collection <collection-get>` |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `DELETE` | :ref:`/buckets/(bucket_id)/collections/(collection_id) <collection-delete>`                  | :ref:`Delete a collection <collection-delete>`          |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `POST`   | :ref:`/buckets/(bucket_id)/collections/(collection_id)/records <records-post>`               | :ref:`Upload a record <records-post>`                   |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `PUT`    | :ref:`/buckets/(bucket_id)/collections/(collection_id)/records/(record_id) <record-put>`     | :ref:`Replace a record <record-put>`                    |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `PATCH`  | :ref:`/buckets/(bucket_id)/collections/(collection_id)/records/(record_id) <record-patch>`   | :ref:`Update a record <record-patch>`                   |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `GET`    | :ref:`/buckets/(bucket_id)/collections/(collection_id)/records <records-get>`                | :ref:`Retrieve stored records <records-get>`            |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `GET`    | :ref:`/buckets/(bucket_id)/collections/(collection_id)/records/(record_id) <records-get>`    | :ref:`Retrieve a single record <records-get>`           |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+
| `DELETE` | :ref:`/buckets/(bucket_id)/collections/(collection_id)/records/(record_id) <record-delete>`  | :ref:`Delete a single record <record-delete>`           |
+----------+----------------------------------------------------------------------------------------------+---------------------------------------------------------+

Many of the listed endpoints are resource endpoints, which an be filtered,
paginated and interracted as described in :ref:`resource-endpoints`.

Kinto protocol
==============

In addition to the endpoints defined above, some aspects of the API might be
of interest:

.. toctree::
   :maxdepth: 2

   cliquet/versioning
   cliquet/authentication
   cliquet/resource
   cliquet/timestamps
   cliquet/backoff
   cliquet/errors
   cliquet/deprecation
   buckets
   collections
   records
   groups
