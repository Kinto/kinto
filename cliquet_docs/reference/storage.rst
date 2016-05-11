.. _storage:

Storage
#######

Backends
========

PostgreSQL
----------

.. autoclass:: cliquet.storage.postgresql.Storage


Redis
-----

.. autoclass:: cliquet.storage.redis.Storage


Memory
------

.. autoclass:: cliquet.storage.memory.Storage


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

See the :ref:`resource-model` class to manipulate collections of records.
