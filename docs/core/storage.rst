.. _storage:

Storage
#######

Backends
========

PostgreSQL
----------

.. autoclass:: kinto.core.storage.postgresql.Storage


Redis
-----

.. autoclass:: kinto_redis.storage.Storage


Memory
------

.. autoclass:: kinto.core.storage.memory.Storage


API
===

Implementing a custom storage backend consists in implementating the following
interface:

.. automodule:: kinto.core.storage
    :members:


Exceptions
----------

.. automodule:: kinto.core.storage.exceptions
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
