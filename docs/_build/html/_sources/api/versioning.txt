.. _api-versioning:

##############
API Versioning
##############


The :term:`HTTP API` exposed by the service will be consumed by clients, like
a Javascript client.

The :term:`HTTP API` is subject to changes. It follows the
:term:`Kinto-Core HTTP API`.

When the :term:`HTTP API` is changed, its version is incremented.
The :term:`HTTP API` version follows a :term:`Semantic Versioning`
pattern and uses this rule to be incremented:

1. any change to the :term:`HTTP API` that is backward compatible increments
   the **MINOR** number, and the modification in the documentation should reflect
   this with a header like "Added in 1.x".

2. any change to the :term:`HTTP API` that is backward incompatible increments
   the **MAJOR** number, and the differences are summarized at the begining of
   the documentation, a new document for that **MAJOR** version is created.

.. note::

   We're not using the **PATCH** level of Semantic Versioning,
   since bug fixes have no impact on the exposed HTTP API; if they do
   MINOR or MAJOR should be incremented.

We want to avoid **MAJOR** changes as much as possible in the future, and stick
with 1.x as long as we can.

A client that interacts with the service can query the server to know what
is its :term:`HTTP API` version. This is done with a query on the root view,
as described in :ref:`the root API description <api-utilities>`.

If a client relies on a feature that was introduced at a particular version,
it should check that the server implements the minimal required version.

The JSON response body contains an **http_api_version** key which value is
the **MAJOR.MINOR** version.

