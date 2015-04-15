.. _storage:

Storage
#######


PostgreSQL
==========

.. autoclass:: cliquet.storage.postgresql.PostgreSQL


Redis
=====

.. autoclass:: cliquet.storage.redis.Redis


Memory
======

.. autoclass:: cliquet.storage.memory.Memory


.. _cloud-storage:

Cloud Storage
=============

.. autoclass:: cliquet.storage.cloud_storage.CloudStorage


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
