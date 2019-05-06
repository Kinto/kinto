.. _cache:

Cache
#####


PostgreSQL
==========

.. autoclass:: kinto.core.cache.postgresql.Cache


Redis
=====

See `Kinto Redis driver plugin repository <https://github.com/Kinto/kinto-redis>`_
for more information.


Memory
======

.. autoclass:: kinto.core.cache.memory.Cache

Memcached
=========

.. autoclass:: kinto.core.cache.memcached.Cache


API
===

Implementing a custom cache backend consists on implementing the following
interface:

.. autoclass:: kinto.core.cache.CacheBase
    :members:
