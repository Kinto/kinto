.. _permissions:

Permissions
###########

*Kinto-Core* provides a mechanism to handle authorization on the stored :term:`objects`.

This section gives details about the behaviour of resources in regards to
:term:`permissions`.


.. _permission-user-resource:

User resource
=============

This is the simplest one, as presented in the :ref:`resource section <resource>`.

When using a :class:`kinto.core.resource.UserResource`, every authenticated user
can manipulate and read their own records. There is no way to restrict this or
allow sharing of records.

+------------+--------------------+--------------------+
| Method     | URL                | :term:`permission` |
+============+====================+====================+
| GET / HEAD | /{collection}      | *Authenticated*    |
+------------+--------------------+--------------------+
| POST       | /{collection}      | *Authenticated*    |
+------------+--------------------+--------------------+
| DELETE     | /{collection}      | *Authenticated*    |
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


Public BasicAuth
----------------

If *Basic Auth* authentication is enabled, private user resources can become semi-private or public
if the ``user:pass`` is publicly known and shared (for example ``public:`` is a valid user:pass combination).
That's how most simple demos of *Kinto* — a *Kinto-Core*-based application — are built by the way!


.. _permission-shareable-resource:

Shareable resource
==================

.. warning::

    When using this kind of resource, the ``permission_backend`` setting must be
    set, :ref:`as described in the configuration section <configuration-permissions>`.

To introduce more flexibility, the :class:`kinto.core.resource.ShareableResource`
can be used instead.

.. code-block:: python

    from kinto.core import resource

    @resource.register()
    class Toadstool(resource.ShareableResource):
        mapping = MushroomSchema()


With this alternative resource class, *Kinto-Core* will register the :term:`endpoints`
with a specific `route factory
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_,
that will take care of checking the appropriate permission for each action.

+------------+--------------------+----------------------+-----------------------------------------------+
| Method     | URL                | :term:`permission`   | Comments                                      |
+============+====================+======================+===============================================+
| GET / HEAD | /{collection}      | ``read``             | If not allowed by setting                     |
|            |                    |                      | ``kinto.{collection}_read_principals``,       |
|            |                    |                      | will return list of records where user        |
|            |                    |                      | has ``read`` permission.                      |
+------------+--------------------+----------------------+-----------------------------------------------+
| POST       | /{collection}      | ``create``           | Allowed by setting                            |
|            |                    |                      | ``kinto.{collection}_create_principals``      |
+------------+--------------------+----------------------+-----------------------------------------------+
| DELETE     | /{collection}      | ``write``            | If not allowed by setting                     |
|            |                    |                      | ``kinto.{collection}_write_principals``,      |
|            |                    |                      | will delete the list of records where         |
|            |                    |                      | user has ``write`` permission.                |
+------------+--------------------+----------------------+-----------------------------------------------+
| GET / HEAD | /{collection}/{id} | ``read``             | If not allowed by setting                     |
|            |                    |                      | ``kinto.{collection}_read_principals``,       |
|            |                    |                      | will check record permissions                 |
+------------+--------------------+----------------------+-----------------------------------------------+
| PUT        | /{collection}/{id} | ``create`` if record | Allowed by setting                            |
|            |                    | doesn't exist,       | ``kinto.{collection}_create_principals``,     |
|            |                    | ``write`` otherwise  | or ``kinto.{collection}_create_principals``   |
|            |                    |                      | or existing record permissions                |
+------------+--------------------+----------------------+-----------------------------------------------+
| PATCH      | /{collection}/{id} | ``write``            | If not allowed by setting                     |
|            |                    |                      | ``kinto.{collection}_write_principals``,      |
|            |                    |                      | will check record permissions                 |
|            |                    |                      |                                               |
+------------+--------------------+----------------------+-----------------------------------------------+
| DELETE     | /{collection}/{id} | ``write``            | If not allowed by setting                     |
|            |                    |                      | ``kinto.{collection}_write_principals``,      |
|            |                    |                      | will check record permissions                 |
+------------+--------------------+----------------------+-----------------------------------------------+

The record permissions can be manipulated via the ``permissions`` attribute in the
JSON payload, aside the ``data`` attribute.
It allows to specify the list of :term:`principals` allowed for each ``permission``,
as detailed in the `API section <resource-permissions-attribute>`_.

.. important::

    When defining permissions, there are two specific principals:

    * ``system.Authenticated``: any authenticated user
    * ``system.Everyone``: any user


The ``write`` permission is required to be able to modify the permissions
of an existing record.

When a record is created or modified, the **current user is added to
list of principals** for the ``write`` permission on this object.
That means that a user is always able to replace or delete the records she created.

.. note::

    Don't hesitate to submit a contribution to introduce a way to control the
    current behaviour instead of always granting ``write`` on current user!


BasicAuth trickery
------------------

Like for user resources, if *Basic Auth* authentication is enabled, the predictable
user id can be used to define semi-private or public if the ``user:pass`` is
known and shared (for example ``public:`` is a valid user:pass combination).

For example, get the user id obtained in the hello :ref:`root view <api-utilities>` with a
user:pass combination and use it in the permissions JSON payloads, or settings:

::

    kinto.{collection}_read_principals = basicauth:631c2d625ee5726172cf67c6750de10a3e1a04bcd603bc9ad6d6b196fa8257a6



Related/Inherited permissions
-----------------------------

In the above section, the list of allowed principals for actions on the collection
(especially ``create``) is specified via settings.

It is possible to extend the previously described behavior with related permissions.

For example, in order to imply that having permission to ``write`` implies
permission to ``read``. Or having permission to ``create`` blog articles also means
permission to ``write`` categories.

To do so, specify the ``get_bound_permissions`` of the *Kinto-Core* authorization policy.

.. code-block:: python

    def get_bound_permissions(self, permission_object_id, permission):
        related = [(permission_object_id, permission)]
        # Grant `read` if user can `write`
        if permission == 'write':
            related.append((permission_object_id, 'read'))
        return related


.. code-block:: python
    :emphasize-lines: 7,8

    from pyramid.security import IAuthorizationPolicy

    def main(global_settings, **settings):
        ...
        kinto.core.initialize(config, __version__)
        ...
        authz = config.registry.queryUtility(IAuthorizationPolicy)
        authz.get_bound_permissions = get_bound_permissions


In :rtd:`Kinto <Kinto/kinto>`, this is leveraged to implement an inheritance tree
of permissions between nested objects. The root objects permissions still have to be specified
via settings though.


It is also possible to subclass the default :class:`kinto.core.authorization.AuthorizationPolicy`.

.. code-block:: python

    from kinto.core import authorization
    from pyramid.security import IAuthorizationPolicy
    from zope.interface import implementer

    @implementer(IAuthorizationPolicy)
    class MyAuthz(authorization.AuthorizationPolicy):
        def get_bound_permissions(self, permission_object_id, permission):
            related = [(permission_object_id, permission)]
            # Grant permission on `categories` if permission on `articles`
            if permission_object_id.startswith('/articles'):
                related.append((permission_object_id + '/categories', permission))
            return related

This would require forcing the setting ``multiauth.authorization_policy = myapp.authz.MyAuthz``.


Manipulate permissions
----------------------

One way of achieving dynamic permissions is to manipulate the permission backend
manually.

For example, in some imaginary admin view:

.. code-block:: python

    def admin_view(request):
        # Custom Pyramid view.
        permission = request.registry.permission

        # Give `create` permission to `user_id` in POST
        some_user_id = request.POST['user_id']
        permission_object_id = '/articles'
        permission = 'create'
        permission.add_principal_to_ace(permission_object_id,
                                        permission,
                                        some_user_id)

Or during application init (or scripts):

.. code-block:: python
    :emphasize-lines: 6-11

    def main(global_config, **settings):
        # ...
        kinto.core.initialize(config, __version__)
        # ...

        some_user_id = 'basicauth:ut082jghnrgnjnj'
        permission_object_id = '/articles'
        permission = 'create'
        config.registry.permission.add_principal_to_ace(permission_object_id,
                                                        permission,
                                                        some_user_id)

Since :term:`principals` can be anything, it is also possible to use them to
define groups:

.. code-block:: python

    def add_to_admins(request):
        # Custom Pyramid view.
        permission = request.registry.permission

        some_user_id = request.POST['user_id']
        group_name = 'group:admins'
        permission.add_user_principal(some_user_id, group_name)


And then refer as ``group:admins`` in the list of allowed principals.


Custom permission checking
--------------------------

The permissions verification in *Kinto-Core* is done with usual Pyramid authorization
abstractions. Most notably using an implementation of a `RootFactory in conjonction with an Authorization policy
<http://docs.pylonsproject.org/projects/pyramid/en/latest/quick_tutorial/authorization.html>`_.

In order to completely override (or mimic) the defaults, a custom
*RootFactory* and a custom *Authorization policy* can be plugged
on the resource during registration.


.. code-block:: python
    :emphasize-lines: 10,15

    from kinto.core import resource

    class MyViewSet(resource.ViewSet):

        def get_view_arguments(self, endpoint_type, resource_cls, method):
            args = super(MyViewSet, self).get_view_arguments(endpoint_type,
                                                             resource_cls,
                                                             method)
            if method.lower() not in ('get', 'head'):
                args['permission'] = 'publish'
            return args

        def get_service_arguments(self):
            args = super(MyViewSet, self).get_service_arguments()
            args['factory'] = myapp.MyRootFactory
            return args


    @resource.register(viewset=MyViewSet())
    class Resource(resource.UserResource):
        mapping = BookmarkSchema()


See more details about available customization in the :ref:`viewset section <viewset>`.

A custom RootFactory and AuthorizationPolicy should implement the permission
checking `using Pyramid mecanisms <http://docs.pylonsproject.org/projects/pyramid/en/latest/tutorials/wiki2/authorization.html>`_.

For example, a simplistic example with the previous resource viewset:

.. code-block:: python

    from pyramid.security import IAuthorizationPolicy

    class MyRootFactory(object):
        def __init__(self, request):
            self.current_resource = None
            service = request.current_service
            if service and hasattr(service, 'resource'):
                self.current_resource = service.resource


    @implementer(IAuthorizationPolicy)
    class AuthorizationPolicy(object):
        def permits(self, context, principals, permission):
            if context.current_resource == BlogArticle:
                if permission == 'publish':
                    return ('group:publishers' in principals)
            return False



.. _permissions-backend:

Backends
========

The :term:`ACLs` are stored in a :term:`permission` backend. Like for
:ref:`storage` and :ref:`cache`, it is pluggable from configuration.

PostgreSQL
----------

.. autoclass:: kinto.core.permission.postgresql.Permission


Redis
-----

.. autoclass:: kinto.core.permission.redis.Permission


Memory
------

.. autoclass:: kinto.core.permission.memory.Permission


API
===

Implementing a custom permission backend consists in implementating the following
interface:

.. autoclass:: kinto.core.permission.PermissionBase
  :members: