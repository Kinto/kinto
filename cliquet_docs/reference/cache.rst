.. _cache:

Cache
#####


PostgreSQL
==========

.. autoclass:: cliquet.cache.postgresql.Cache


Redis
=====

.. autoclass:: cliquet.cache.redis.Cache


Memory
======

.. autoclass:: cliquet.cache.memory.Cache


API
===

Implementing a custom cache backend consists on implementing the following
interface:

.. autoclass:: cliquet.cache.CacheBase
    :members:
