Settings
########

Kinto is built to be highly configurable and as a result, the related
configuration can be verbose.

All the configuration flags are listed below.





Authentication
--------------

By default, *Kinto* relies on *Basic Auth* to authenticate users.

User registration is not necessary. A unique user idenfier will be created
for each couple of ``username:password``.

*Kinto* is compatible with *Firefox Account*.  Install and
configure :github:`mozilla-services/cliquet-fxa`.


Activating the flush endpoint
=============================

When using Kinto in development mode, it might be helpful to have a way to
flush all the data currently stored in the database.

There is a way to enable this behaviour (it is deactivated by default for
obvious security reasons). In the `.ini` file:

.. code-block :: ini

    kinto.flush_endpoint_enabled = true

Then, issue a `POST` request to the `/__flush__` endpoint to flush all
the data.


.. Storage backend
.. ===============

.. In order to use Kinto as a storage backend for an application built with
.. cliquet, some settings must be set carefully.


.. Firefox Account
.. '''''''''''''''

.. In order to avoid double-verification of FxA OAuth tokens, the ``cliquet.cache_url``
.. should be the same in *Kinto* and in the application. This way
.. the verification cache will be shared between the two components.
