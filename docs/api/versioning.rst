.. _api-versioning:

##############
API versioning
##############

The API versioning is based on the application version deployed. It follows the
`semver <http://semver.org/>`_ specifications.

During development the server will be 0.X.X, the server endpoint will be
prefixed by ``/v0``.

Each non retro-compatible API change will imply the major version number
to be incremented. Everything will be made to avoid retro incompatible changes.

The ``/`` endpoint will redirect to the last API version.


.. warning::

    The version prefix will be **implied** throughout the rest of the API
    reference, to improve readability. For example, the ``/`` endpoint
    should be understood as ``/v0/``.
