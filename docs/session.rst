Session
#######

.. _session:


PostgreSQL
==========

.. autoclass:: cliquet.session.postgresql.PostgreSQL


Redis
=====

.. autoclass:: cliquet.session.redis.Redis


API
===

Implementing a custom session backend consists in implementating the following
interface:

.. autoclass:: cliquet.session.SessionStorageBase
    :members:
