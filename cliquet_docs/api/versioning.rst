.. _api-versioning:

##############
API versioning
##############

The :term:`HTTP API` exposed by the service will be consumed by clients, like
JavaScript application for example.

It is described :ref:`here <api-endpoints>` and is subject to changes.

When the :term:`HTTP API` is changed, its version is incremented.
The :term:`HTTP API` version follows a `Semantic Versioning <http://semver.org/>`_
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

A client that interacts with the service can query the server to know what
is its :term:`HTTP API` version. This is done with a query on the root view,
as described in :ref:`the root API description <api-utilities>`.

If a client relies on a feature that was introduced at a particular version,
it should check that the server implements the minimal required version.

The URL will be prefixed by the major version of the API (e.g ``/v1`` for ``1.4``).

The ``/`` endpoint will redirect to the last API version.

.. warning::

    The version prefix will be **implied** throughout the rest of the API
    reference, to improve readability. For example, the ``/`` endpoint
    should be understood as ``/vX/``.
