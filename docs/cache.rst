.. _cache:

Cache
#####


PostgreSQL
==========

.. autoclass:: cliquet.cache.postgresql.PostgreSQL


Redis
=====

.. autoclass:: cliquet.cache.redis.Redis


Memory
======

.. autoclass:: cliquet.cache.memory.Memory


API
===

Implementing a custom cache backend consists in implementating the following
interface:

.. autoclass:: cliquet.cache.CacheBase
    :members:
