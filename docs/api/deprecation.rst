.. _deprecation:

###########
Deprecation
###########

A track of the client version will be kept to know after which date each old version can be shutdown.

The date of the end of support is provided in the API root URL (e.g. ``/v0``)

Using the ``Alert`` response header, the server can communicate any potential warning
messages, information, or other alerts.

The value is JSON mapping with the following attributes:

* ``code``: one of the strings ``"soft-eol"`` or ``"hard-eol"``;
* ``message``: a human-readable message (optional);
* ``url``: a URL at which more information is available (optional).

A ``410 Gone`` error response can be returned if the
client version is too old, or the service had been remplaced with
a new and better service using a new protocol version.

See details in :ref:`configuration` to activate deprecation.
