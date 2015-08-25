.. permission

Permissions
###########

*Cliquet* provides a mechanism to handle authorization on the stored :term:`objects`.

Glossary
========

Authorization isn't complicated, but requires the introduction of a few terms
so that explanations are easier to follow:

**Object**:
    The data that is stored into *Cliquet*. :term:`objects` usually match
    the resources you defined; For one resource there are two :term:`objects`: resource's
    collection and resource's records.
**Principal**:
    An entity that can be authenticated. :term:`principals` can be individual people,
    computers, services, or any group of such things.
**Permission**:
    An action that can be authorized or denied. *read*, *write*, *create* are
    :term:`permissions`.
**Access Control Entity (ACE)**:
    An association of a :term:`principal`, an :term:`object` and a :term:`permission`. For instance,
    (Alexis, article, write).
**Access Control List (ACL)**:
    A list of Access Control Entities (:term:`ACE`).

Overview
========

By default, the resources defined by *Cliquet* are public, and records are
isolated by user. But it is also possible to define *protected resources*,
which will required the user to have access to the requested resource.

.. code-block:: python

    from cliquet import authorization
    from cliquet import resource


    @resource.register(factory=authorization.RouteFactory)
    class Toadstool(resource.ProtectedResource):
        mapping = MushroomSchema()


In this example, a *route factory* is registered. Route factories are explained
in more details below.

A protected resource, in addition to the ``data`` property of request
/ responses, takes a :term:`permissions` property which contains the list of
:term:`principals` that are allowed to access or modify the current :term:`object`.

During the creation of the :term:`object`, the :term:`permissions` property is stored in the
permission backend, and upon access, it checks the current :term:`principal` has
access the the object, with the correct permission.

Route factory
=============

The route factory decides which :term:`permission` is required to access one resource
or another. Here is a summary of the :term:`permissions` that are defined by the
default route factory *Cliquet* defines:

+------------+------------------------------------------------+
| Method     | :term:`permission`                             |
+============+================================================+
| POST       | ``create``                                     |
+------------+------------------------------------------------+
| GET / HEAD | ``read``                                       |
+------------+------------------------------------------------+
| PUT        | ``create`` if it doesn't exist, ``write``      |
|            | otherwise                                      |
+------------+------------------------------------------------+
| PATCH      | ``write``                                      |
+------------+------------------------------------------------+
| DELETE     | ``write``                                      |
+------------+------------------------------------------------+

Route factories are `best described in the pyramid documentation
<http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/urldispatch.html#route-factories>`_

.. autoclass:: cliquet.authorization.RouteFactory
  :members:

Authorization policy
====================

Upon access, the authorization policy is asked if any of the current list of
:term:`principals` has access to the current resource. By default, the authorization
policy *Cliquet* checks in the :term:`permission` backend for the current :term:`object`.

It is possible to extend this behavior, for instance if there is an inheritance
tree between the defined resources (some :term:`ACEs` should give access to its child
:term:`objects`).

In case the application should define its own inheritance tree, it should also
define its own authorization policy.

To do so, subclass the default ``AuthorizationPolicy`` and add a specific
``get_bound_permission`` method.

.. code-block:: python
    
    from cliquet import authorization
    from pyramid.security import IAuthorizationPolicy
    from zope.interface import implementer

    @implementer(IAuthorizationPolicy)
    class AuthorizationPolicy(authorization.AuthorizationPolicy):
        def get_bound_permissions(self, *args, **kwargs):
        """Callable that takes an object ID and a permission and returns
        a list of tuples (<object id>, <permission>)."""
            return build_permissions_set(*args, **kwargs) 


.. autoclass:: cliquet.authorization.AuthorizationPolicy
  :members:

Permissions backend
===================

The :term:`ACLs` are stored in a :term:`permission` backend. Currently, permission backends
exists for Redis and PostgreSQL, as well as a in memory one. It is of course
possible to add you own permission backend, if you whish to store your
:term:`permissions` related data in a different database.

.. autoclass:: cliquet.permission.PermissionBase
  :members:
