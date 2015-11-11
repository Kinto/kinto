.. _permissions:

Permissions
###########

*Cliquet* provides a mechanism to handle authorization on the stored :term:`objects`.

This section gives details about the behaviour of resources in regards to
:term:`permissions`.

.. _permission-user-resource:

User resource
=============

This is the simplest one, as presented in the :ref:`resource section <resource>`.

When using a :class:`cliquet.resource.UserResource`, every authenticated user
can manipulate and read their own records. There is no way to restrict this or
allow sharing of records.

+------------+--------------------+--------------------+
| Method     | URL                | :term:`permission` |
+============+====================+====================+
| POST       | /{collection}      | *Authenticated*    |
+------------+--------------------+--------------------+
| GET / HEAD | /{collection}      | *Authenticated*    |
+------------+--------------------+--------------------+
| GET / HEAD | /{collection}/{id} | *Authenticated*    |
+------------+--------------------+--------------------+
| PUT        | /{collection}/{id} | *Authenticated*    |
+------------+--------------------+--------------------+
| PATCH      | /{collection}/{id} | *Authenticated*    |
+------------+--------------------+--------------------+
| DELETE     | /{collection}/{id} | *Authenticated*    |
+------------+--------------------+--------------------+

.. note::

    When using only these resource, the permission backend remains unused.
    Its configuration is not necessary.


.. _permission-shareable-resource:

Shareable resource
==================

To introduce more flexibility, the :class:`cliquet.resource.ShareableResource`
can be used instead.

.. code-block:: python

    from cliquet import resource

    @resource.register()
    class Toadstool(resource.ShareableResource):
        mapping = MushroomSchema()


With this alternative resource class, *Cliquet* will register the :term:`endpoints`
with a specific `route factory
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_,
that will take care of checking the appropriate permission for each action.

+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+
| Method     | URL                | :term:`permission`                  | Comments                                                                    |
+============+====================+=====================================+=============================================================================+
| POST       | /{collection}      | ``create``                          | Allowed by setting ``cliquet.{collection}_create_principals``               |
+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+
| GET / HEAD | /{collection}      | ``read``                            | If not allowed by setting ``cliquet.{collection}_read_principals``,         |
|            |                    |                                     | will return list of records where user has ``read`` permission.             |
+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+
| PUT        | /{collection}/{id} | ``create`` if record doesn't exist, | Allowed by setting ``cliquet.{collection}_create_principals``,              |
|            |                    | ``write`` otherwise                 | or ``cliquet.{collection}_create_principals` or existing record permissions |
+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+
| GET / HEAD | /{collection}/{id} | ``read``                            | If not allowed by setting ``cliquet.{collection}_read_principals``,         |
|            |                    |                                     | will check record permissions                                               |
+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+
| PATCH      | /{collection}/{id} | ``write``                           | If not allowed by setting ``cliquet.{collection}_write_principals``,        |
|            |                    |                                     | will check record permissions                                               |
+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+
| DELETE     | /{collection}/{id} | ``write``                           | If not allowed by setting ``cliquet.{collection}_write_principals``,        |
|            |                    |                                     | will check record permissions                                               |
+------------+--------------------+-------------------------------------+-----------------------------------------------------------------------------+

The record permissions can be manipulated via the ``permissions`` attribute in the
JSON payload, aside the ``data`` attribute.
It allows to specify the list of :term:`principals` allowed for each ``permission``,
as detailed in the `API section <resource-permissions-attribute>`_.

The ``write`` permission is required to be able to modify the permissions
of an existing record.

When a record is created or modified, the current user is added to
list of principals for the ``write`` permission. That means that a user is
always able to replace or delete the records she created.

.. note::

    When defining permissions, there are two specific principals:

    * ``system.Authenticated``: any authenticated user
    * ``system.Everyone``: any user


Dynamic permissions
-------------------

In the above section, the list of allowed principals for actions on the collection
(especially ``create``) is specified via settings.

One way of achieving dynamic permissions is to manipulate the permission backend
manually.

.. code-block:: python

    def my_view(request):
        permission = request.registry.permission

        current_user_id = request.prefixed_userid
        perm_object_id = '/{collection}'
        permission.add_principal_to_ace(perm_object_id,
                                        'create'
                                        current_user_id)

Alternatively, since :term:`principals` can be anything, it is also possible to use them to
define groups:

.. code-block:: python

    def my_view(request):
        permission = request.registry.permission

        current_user_id = request.prefixed_userid
        permission.add_user_principal(current_user_id, 'group:admins')


And then refer as ``group:admins`` in the list of allowed principals.


Related/Inherited permissions
-----------------------------

It is possible to extend the previously described behavior with related permissions.

For example, in order to imply that having permission to ``write`` implies
permission to ``read``. Or having permission to ``create`` blog articles also means
permission to ``write`` categories.

To do so, specify the ``get_bound_permissions`` of the *Cliquet* authorization policy.

.. code-block:: python

    def get_bound_permissions(self, permission_object_id, permission):
        related = [(permission_object_id, permission)]
        if permission == 'write':
            related.append((permission_object_id, 'read'))
        return related


.. code-block:: python

    from pyramid.security import IAuthorizationPolicy

    def main(global_settings, **settings):
        ...
        cliquet.initialize(config, __version__)
        ...
        authz = config.registry.queryUtility(IAuthorizationPolicy)
        authz.get_bound_permissions = get_bound_permissions


In :rtd:`Kinto <Kinto/kinto>`, this is leveraged to implement an inheritance tree
of permissions between nested objects. The root objects permissions still have to be specified
via settings though.


It is also possible to subclass the default :class:`cliquet.authorization.AuthorizationPolicy`.

.. code-block:: python

    from cliquet import authorization
    from pyramid.security import IAuthorizationPolicy
    from zope.interface import implementer

    @implementer(IAuthorizationPolicy)
    class MyAuthz(authorization.AuthorizationPolicy):
        def get_bound_permissions(self, permission_object_id, permission):
            related = [(permission_object_id, permission)]
            if permission_object_id.startswith('/articles'):
                related.append((permission_object_id + '/categories', permission))
            return related

This would require forcing the setting ``multiauth.authorization_policy = myapp.authz.MyAuthz``.



.. _permissions-backend:

Backends
========

The :term:`ACLs` are stored in a :term:`permission` backend. Like for
:ref:`storage` and :ref:`cache, it is pluggable from configuration.

PostgreSQL
----------

.. autoclass:: cliquet.permission.postgresql.Permission


Redis
-----

.. autoclass:: cliquet.permission.redis.Permission


Memory
------

.. autoclass:: cliquet.permission.memory.Permission


API
===

Implementing a custom permission backend consists in implementating the following
interface:

.. autoclass:: cliquet.permission.PermissionBase
  :members: