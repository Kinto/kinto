.. _records:

Records
#######


/buckets/<bucket_id>/collections/<collection_id>/records
========================================================

**Requires authentication**

End-point for the collection of records:

* ``POST``: Create record
* ``GET``: Fetch, sort and filter records

.. note::

    A collection is considered empty by default. In other words, no error will
    be thrown if the collection id is unknown.

See `cliquet resource documentation
<http://cliquet.readthedocs.org/en/latest/api/resource.html#get-resource>`_
for more details on available operations.


/buckets/<bucket_id>/collections/<collection_id>/records/<record_id>
====================================================================

**Requires authentication**

End-point for a single record of the collection:

* ``GET``: Fetch
* ``PATCH``: Modify
* ``PUT``: Replace
* ``DELETE``: Delete


See `cliquet record documentation <http://cliquet.readthedocs.org/en/latest/api/resource.html#get-resource-id>`_
for more details on available operations.
