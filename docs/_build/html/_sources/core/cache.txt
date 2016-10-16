.. _cache:

Cache
#####


PostgreSQL
==========

.. autoclass:: kinto.core.cache.postgresql.Cache


Redis
=====

.. autoclass:: kinto_redis.cache.Cache


Memory
======

.. autoclass:: kinto.core.cache.memory.Cache


API
===

Implementing a custom cache backend consists on implementing the following
interface:

.. autoclass:: kinto.core.cache.CacheBase
    :members:
