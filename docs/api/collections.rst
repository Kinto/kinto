Working with collections
========================

.. _collections:

Collections are always linked to a `bucket <buckets>`_.


.. note:: 

    By default users have a bucket that is used for their own data.

    Application can use this default bucket with the ``~`` shortcut.

	ie: ``/buckets/~/collections/contacts`` will be the current user contacts.


/buckets/<bucket_id>/collections/<collection_id>
================================================

**Requires authentication**

End-point for the collection of records:

* Create record
* Fetch, sort and filter records

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

* Fetch
* Modify
* Replace
* Delete


See `cliquet record documentation <http://cliquet.readthedocs.org/en/latest/api/resource.html#get-resource-id>`_
for more details on available operations.
