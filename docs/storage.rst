Storage
#######

.. _storage:


PostgreSQL
==========

.. autoclass:: cliquet.storage.postgresql.PostgreSQL


Redis
=====

.. autoclass:: cliquet.storage.redis.Redis


Memory
======

.. autoclass:: cliquet.storage.memory.Memory

API
===

Implementing a custom storage backend consists in implementating the following
interface:

.. automodule:: cliquet.storage
    :members:
