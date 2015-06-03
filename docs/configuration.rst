.. _configuration:

Configuration
#############

See `cliquet settings documentation <http://cliquet.readthedocs.org/en/latest/configuration.html>`_.


Storage backend
===============

In order to use *Kinto* as a storage backend for an application built with
*cliquet*, just set the following settings:

.. code-block:: ini

        cliquet.storage_backend = kinto.storage
        cliquet.storage_url = https://cloud-storage.services.mozilla.com

Authentication
--------------

Authentication is shared between the two components. In other words, the
``Authorization`` request header is passed through from *cliquet* to
*Kinto*.

Firefox Account
'''''''''''''''

In order to avoid double-verification of FxA OAuth tokens, the ``cliquet.cache_url``
should be the same in *Kinto* and in the application. This way
the verification cache will be shared between the two components.
