.. _storage:

Storage
#######

Backends
========

PostgreSQL
----------

.. autoclass:: cliquet.storage.postgresql.PostgreSQL


Redis
-----

.. autoclass:: cliquet.storage.redis.Redis


Memory
------

.. autoclass:: cliquet.storage.memory.Memory


.. _cloud-storage:

Cloud Storage
-------------

.. note::

    `Under construction <https://github.com/mozilla-services/kinto/pull/45>`_

If the ``kinto`` package is available, it is possible to store data in
a remote instance of *Kinto*.

::

    cliquet.storage_backend = kinto.storage
    cliquet.storage_url = https://cloud-storage.services.mozilla.com

See :rtd:`Kinto <kinto>` for more details.

.. note::

    In order to avoid double checking of OAuth tokens, the Kinto service
    and the application can share the same cache (``cliquet.cache_url``).


API
===

Implementing a custom storage backend consists in implementating the following
interface:

.. automodule:: cliquet.storage
    :members:


Exceptions
----------

.. automodule:: cliquet.storage.exceptions
    :members:


Store custom data
=================

Storage can be used to store arbitrary data.

.. code-block:: python

    data = {'subscribed': datetime.now()}
    user_id = request.authenticated_userid

    storage = request.registry.storage
    storage.create(collection_id='__custom', parent_id='', record=data)

See the :ref:`collection` class to manipulate collections of records.
