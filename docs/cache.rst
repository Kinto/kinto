Cache
#####

.. _cache:


PostgreSQL
==========

.. autoclass:: cliquet.cache.postgresql.PostgreSQL


Redis
=====

.. autoclass:: cliquet.cache.redis.Redis


API
===

Implementing a custom cache backend consists in implementating the following
interface:

.. autoclass:: cliquet.cache.CacheBase
    :members:
