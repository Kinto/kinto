.. _api-permissions:

Permissions
###########


Terminology
===========

.. glossary::

    Object
        Anything that can be interacted with. Collections, records, buckets, groups
        are all objects.

    Principal
        An entity that can be authenticated. Principals can be individual people,
        applications, services, or any group of such things.

    Group
        A group associates a name to a list of principals.

    Permission
    Permissions
        A permission is an action that can be performed on an object.
        Examples of permissions are «read», «write», or «create».

    ACE
    Access Control Entity
        An ACE associates a permission to objects and principals, and allows
        to describe rules like «*Members of group admins can create collections*».
        Using #a pseudo-code syntax: ``collections:create = ['group:admins',]``.

    ACL
        A list of ACEs

Objects
=======

Any set of objects defined in *Kinto* can be given a number of permissions.

+-----------------+---------------------------------------------------------+
| Object          | Description                                             |
+=================+=========================================================+
| **bucket**      | :ref:`Buckets <buckets>` can be seen as namespaces:     |
|                 | collections names won't collide if stored in different  |
|                 | buckets.                                                |
+-----------------+---------------------------------------------------------+
| **collection**  | A collection of records                                 |
+-----------------+---------------------------------------------------------+
| **record**      | The data handled by the server                          |
+-----------------+---------------------------------------------------------+
| **group**       | A group of other :term:`principals <principal>`.        |
+-----------------+---------------------------------------------------------+

There is a notion of hierarchy among all these objects:

.. code-block:: text

               +---------------+
               | Buckets       |
               +---------------+
        +----->+ - id          +<---+
        |      | - permissions |    |
        |      +---------------+    |
        |                           |
        |                           |
        |                           |
        |                           |
        |                           |
    +---+-----------+        +------+---------+
    | Collections   |        | Groups         |
    +---------------+        +----------------+
    | - id          |        |  - id          |
    | - permissions |        |  - members     |
    +------+--------+        |  - permissions |
           ^                 +----------------+
           |
           |
    +------+---------+
    | Records        |
    +----------------+
    |  - id          |
    |  - data        |
    |  - permissions |
    +----------------+


Permissions
===========

On each of these objects, the set of permissions can be:

+------------+-----------------------------------------+
| Permission | Description                             |
+============+=========================================+
| **read**   | Any listed :term:`principal` can read   |
|            | the object.                             |
+------------+-----------------------------------------+
| **write**  | Any listed :term:`principal` can write  |
|            | the object. Whoever has the permission  |
|            | to write an object can read, update and |
|            | delete it.                              |
+------------+-----------------------------------------+
| **create** | Any listed :term:`principal` can create |
|            | a new *child object*.                   |
+------------+-----------------------------------------+

Permissions are associated to objects.

In the case of a creation, since an object can have several kinds of children, the
permission is prefixed (for instance ``groups:create``, ``collections:create``).

The following table lists all permissions that can be associated to each kind
of object.

+----------------+------------------------+----------------------------------+
| Object         | Associated permissions | Description                      |
+================+========================+==================================+
| Configuration  | ``buckets:create``     | Ability to create new buckets.   |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| Bucket         | ``write``              | Ability to write + read on the   |
|                |                        | bucket and all children objects. |
|                +------------------------+----------------------------------+
|                | ``read``               | Ability to read all objects in   |
|                |                        | the bucket.                      |
|                +------------------------+----------------------------------+
|                | ``collections:create`` | Ability to create new            |
|                |                        | collections in the bucket.       |
|                +------------------------+----------------------------------+
|                | ``groups:create``      | Ability to create new groups     |
|                |                        | in the bucket.                   |
+----------------+------------------------+----------------------------------+
| Collection     | ``write``              | Ability to write and read all    |
|                |                        | objects in the collection.       |
|                +------------------------+----------------------------------+
|                | ``read``               | Ability to read all objects in   |
|                |                        | the collection.                  |
|                +------------------------+----------------------------------+
|                | ``records:create``     | Ability to create new records    |
|                |                        | in the collection.               |
+----------------+------------------------+----------------------------------+
| Record         | ``write``              | Ability to write and read the    |
|                |                        | record.                          |
|                +------------------------+----------------------------------+
|                | ``read``               | Ability to read the record.      |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| Group          | ``write``              | Ability to write and read the    |
|                |                        | group.                           |
|                +------------------------+----------------------------------+
|                | ``read``               | Ability to read the group.       |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+

.. note::

  There is no ``delete`` permission: Anyone with the ``write`` permission on an
  object can also edit its associated permissions and delete it.


Principals
==========

During the authentication phase, the main :term:`principal` of the user is
bound to the request.

A principal is described with the following formalism:
``{type}:{identifier}`` (i.e. for Firefox Account: ``fxa:32aa95a474c984d41d395e2d0b614aa2``).

.. note::

    A user can also be another application (in order to provide *service to
    service* authentication).

Groups
======

A group associates a name to a list of :term:`principals <principal>`.

There are two special principals:

- ``system.Authenticated``: All users that are authenticated, no matter the
  authentication mean.
- ``system.Everyone``: Anyone (authenticated or anonymous). Using this
  principal is useful when a rule should apply to all users.

