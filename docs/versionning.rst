##############
API versioning
##############

.. _versioning:

Versionning
===========

The API versioning is based on the application version deployed. It follows `semver <http://semver.org/>`_.

During development the server will be 0.X.X, the server endpoint will be prefixed by ``/v0``.

Each non retro-compatible API change will imply the major version number to be incremented.
Everything will be made to avoid retro incompatible changes.

The ``/`` endpoint will redirect to the last API version.


Deprecation
===========

A track of the client version will be kept to know after which date each old version can be shutdown.
The date of the end of support is provided in the API root URL (e.g. ``/v0``)

.. Using the ``Alert`` header, the server can communicate any potential warning
.. messages, information, or other alerts.
.. The value is JSON mapping with the following attributes:

.. * ``code``: one of the strings ``"deprecated-client"``, ``"soft-eol"`` or ``"hard-eol"``
.. * ``message``: a human-readable message
.. * ``url``: a URL at which more information is available

.. A ``503 Service Unavailable`` error response can be returned if the
.. client version is too old.

.. A ``513 Service Decommissioned`` error response can be returned
.. indicating that the service has been replaced with a new and better
.. service using some as-yet-undesigned protocol.
