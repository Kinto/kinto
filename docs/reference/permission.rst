.. _permission:

Permission
##########


Redis
=====

.. autoclass:: cliquet.permission.redis.Redis


Memory
======

.. autoclass:: cliquet.permission.memory.Memory


API
===

Implementing a custom permission backend consists in implementating
the following interface:

.. autoclass:: cliquet.permission.PermissionBase
    :members:
