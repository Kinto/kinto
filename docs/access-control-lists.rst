Access Control Lists
####################

.. _acls:

Terminology
===========

Objects:
  Anything that can be interacted with. Collections, records, buckets, groups
  are all objects.

Principals:
  An entity that can be authenticated. Principals can be individual people,
  applications, services, or any group of such things.

Groups:
  A group of already existing principals.

Permissions:
  An action that can be done on an object. Examples of permissions are "read",
  "write", and "create".

ACLs:
  A list of permissions associated to objects and principals. For instance,
  ``collections:create = [list, of, principals]``.

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
| **group**       | A group of other :ref:`principals <principals>`.        |
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

Permissions are associated on objects.

For the create case, since an object can several kinds of children, the
permission is prefixed (``groups:create``, ``collections:create``).

The following table gives every permissions that can be associated by object
to build ACLs.

+----------------+------------------------+----------------------------------+
| Object         | Associated permissions | Description                      |
+================+========================+==================================+
| Configuration  | ``buckets:create``     | Ability to create new buckets.   |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| Bucket         | ``write``              | Ability to write + read on the   |
|                |                        | bucket and all children objects. |
|                +------------------------+----------------------------------+
|                | ``reade``              | Ability to read all objects in   |
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

  Anyone with the ``write`` permission on an object can also edit its associated
  permissions and delete it.


Principals
==========

During the login phase, the main principal of the user is bound to the request.

Using default authentication, a principal is using the following formalism:
``{type}:{identifier}`` (i.e. for Firefox Account: ``fxa:32aa95a474c984d41d395e2d0b614aa2``).

.. note::

    A user can be another application (*service to service*).


Groups can be created in buckets, whose members are referenced using principals.

When a user is a member of a group, she will have ``group:<name>`` among her
principals.

There are two specific principals:

- ``system.Authenticated``: All users that are authenticated.
- ``system.Everyone``: Anyone (authenticated or anonymous).


Examples
========

In order to better understand how permission model works, here is a handful of
use-cases examples.

A Blog
------

Consider a blog where:

- A list of administrators can CRUD everything;
- Some moderators can create articles and update existing ones;
- Anybody can read.

The following objects are created:

- A bucket ``servicedenuages_blog``;
- A collection ``articles``;
- A group ``moderators`` with members ``fxa:<remy id>`` and ``fxa:<tarek id>``.

+---------------------------------+-------------+-------------------------------------------+
| Object                          | Permissions | Principals                                |
+=================================+=============+===========================================+
| Bucket ``servicedenuages_blog`` | ``write``   | ``fxa:<alexis id>``                       |
|                                 |             | ``fxa:<mathieu id>``                      |
+---------------------------------+-------------+-------------------------------------------+
| Collection ``article``          | ``write``   | ``group:moderators``                      |
|                                 +-------------+-------------------------------------------+
|                                 | ``read``    | ``Everyone``                              |
+---------------------------------+-------------+-------------------------------------------+


A Wiki
------

- Authenticated users can create, retrieve, update and delete anything;
- Everyone can read articles.

The following objects are created:

- A ``wiki`` bucket, where new groups can be created by authenticated users;
- An ``article`` collection is created.

+-------------------------+---------------------+---------------------------------+
| Object                  | Permissions         | Principals                      |
+=========================+=====================+=================================+
| Bucket ``wiki``         | ``write``           | ``fxa:<wiki administrator id>`` |
+-------------------------+---------------------+---------------------------------+
| Collection ``articles`` | ``write``           | ``Authenticated``               |
|                         +---------------------+---------------------------------+
|                         | ``read``            | ``Everyone``                    |
+-------------------------+---------------------+---------------------------------+


A Company Wiki
--------------

- Employees of the company can CRUD anything;
- Managers can add employees to the wiki;
- Other people don't have access.

The following objects are created:
- A ``companywiki`` bucket;
- An ``articles`` collection;
- An ``employees`` group.

+--------------------------+--------------+-----------------------------------+
| Object                   | Permissions  | Principals                        |
+==========================+==============+===================================+
| Bucket ``companywiki``   | ``write``    | ``fxa:<wiki administrator id>``   |
+--------------------------+--------------+-----------------------------------+
| Group ``employees``      | ``write``    | ``group:managers``                |
+--------------------------+--------------+-----------------------------------+
| Collection ``articles``  | ``write``    | ``group:employees``               |
|                          |              | ``group:managers``                |
+--------------------------+--------------+-----------------------------------+


A microblogging
---------------

A microblog is a service to share short articles with people such as
Twitter, Google+ or Facebook.

- The microblog administrator creates the bucket;
- Each collection is isolated from the others, and only one person have all
  permissions on all records;
- Records are private by default, and published to specific audiences.

The following objects are created:
- A ``microblog`` bucket, where groups can be created by authenticated users;
- A single ``article`` collection;
- A group ``alexis_buddies``, whose members are chosen by *Alexis* (a.k.a circle);
- Some records (messages) with specific visibility (public, direct message, private
  for a group)

+------------------------------------------+---------------------+-------------------------------------------+
| Object                                   | Permissions         | Principals                                |
+==========================================+=====================+===========================================+
| Bucket ``microblog``                     | ``write``           | ``fxa:<microblog administrator id>``      |
|                                          +---------------------+-------------------------------------------+
|                                          | ``group:create``    | ``Authenticated``                         |
+------------------------------------------+---------------------+-------------------------------------------+
| Collection ``articles``                  | ``records:create``  | ``Authenticated``                         |
+------------------------------------------+---------------------+-------------------------------------------+
| Group ``alexis_buddies``                 | ``write``           | ``fxa:<alexis id>``                       |
+------------------------------------------+---------------------+-------------------------------------------+
| A public message                         | ``write``           | ``fxa:<alexis id>``                       |
|                                          +---------------------+-------------------------------------------+
|                                          | ``read``            | ``Everyone``                              |
+------------------------------------------+---------------------+-------------------------------------------+
| A direct message for a user              | ``write``           | ``fxa:<alexis id>``                       |
|                                          +---------------------+-------------------------------------------+
|                                          | ``read``            | ``fxa:<tarek id>``                        |
+------------------------------------------+---------------------+-------------------------------------------+
| A private message for a group            | ``write``           | ``fxa:<alexis id>``                       |
|                                          +---------------------+-------------------------------------------+
|                                          | ``read``            | ``group:alexis_following``                |
+------------------------------------------+---------------------+-------------------------------------------+

Each time a user creates a new record, it needs to setup the ACLs
attached to it.

With this model it is also possible to setup a shared microblogging
account giving record's ``write`` permission to a group of users.

.. note::

    Another model could be to let users create their own collections of
    records.


Mozilla Payments tracking
-------------------------

For the payment tracking use case, three players are involved:

- The **payment app**, storing receipts for buyers and sellers;
- The **selling app**, reading receipts for a given seller;
- The **buyer app** reading receipts for a given buyer.

Users shouldn't be able to write receipts themselves, sellers and users should
only be able to read their owns.

The following objects are created:
- the ``mozilla`` bucket;
- the ``payment`` collection.

+----------------------+-------------+-------------------------+
| Object               | Permissions | Principals              |
+======================+=============+=========================+
| Bucket ``payments``  | ``write``   | ``hawk:<payment app>``  |
+----------------------+-------------+-------------------------+
| On every record      | ``read``    | ``hawk:<selling app>``  |
|                      |             | ``fxa:<buyer id>``      |
+----------------------+-------------+-------------------------+

This ensures every app can list the receipts of every buyer, and that each
buyer can also list their receipts. However, only the payment
application can create / edit new ones.
