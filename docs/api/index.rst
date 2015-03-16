API Endpoints
#############

.. _api-endpoints:

See `cliquet API documentation <http://cliquet.readthedocs.org/en/latest/api/index.html>`_
for an exhaustive list of features and endpoints of the Kinto API.


/collections/<collection_id>/records
====================================

**Requires authentication**

End-point for the collection of records:

* Create record
* Fetch, sort and filter records

.. note ::

    A collection is considered empty by default. In other words, no error will
    be thrown if the collection id is unknown.

.. note ::

    Records are private by user.


See `cliquet resource documentation <http://cliquet.readthedocs.org/en/latest/api/resource.html#get-resource>`_
for more details on available operations.


/collections/<collection_id>/records/<id>
=========================================

**Requires authentication**

End-point for a single record of the collection:

* Fetch
* Modify
* Replace
* Delete


See `cliquet record documentation <http://cliquet.readthedocs.org/en/latest/api/resource.html#get-resource-id>`_
for more details on available operations.
