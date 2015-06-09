Access Control Lists
####################

.. _acls:

Terminology
===========

Objects:
  Anything that can be interracted with. Collections, records, buckets, groups
  are all objects.

Principals:
  An entity that can be authenticated. Principals can be individual people,
  applications, services, or any group of such things.

Groups:
  A group of already existing principals.

Permissions:
  An action that can be done on an object. Permissions are "read",
  "write", and "create".

ACLs:
  A list of permissions associated to objects and principals. For instance,
  `collections:create = [list, of, principals]`.

Objects
=======

Any set of objects defined in Kinto can be given a number of permissions.

+-----------------+---------------------------------------------------------+
| Object          | Description                                             |
+=================+=========================================================+
| **bucket**      | :ref:`Buckets <buckets>` can be seen as namespaces: you |
|                 | can have different collections using the same name, but |
|                 | stored in different buckets, so their names don't       |
|                 | collide.                                                |
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
| **read**   | Any listed :ref:`principal` can read    |
|            | the object.                             |
+------------+-----------------------------------------+
| **write**  | Any listed :ref:`principal` can write   |
|            | the object. Whoever has the permission  |
|            | to write an object can read, update and |
|            | delete it.                              |
+------------+-----------------------------------------+
| **create** | Any listed :ref:`principal` can create  |
|            | a new *child object*.                   |
+------------+-----------------------------------------+

Permissions are defined on an object following formalism:
``{permission}: {list of principals}``.

For the create case, since an object can have different child, a
namespace is used: ``{child_type}:create: {list of principals}``

For instance, to describe the list of principals which can create
collection in a bucket, the ``collections:create`` ACL would be used.

Here is an exaustive list of all the permission that you can manage
and the objet that handle them:

+----------------+------------------------+----------------------------------+
| Object         | Associated permissions | Description                      |
+================+========================+==================================+
| Configuration  | `buckets:create`       | Ability to create a new bucket.  |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| ``bucket``     | `write`                | Ability to write + read on the   |
|                |                        | bucket and all children objects. |
|                +------------------------+----------------------------------+
|                | `read`                 | Ability to read all objects in   |
|                |                        | the bucket.                      |
|                +------------------------+----------------------------------+
|                | `collections:create`   | Ability to create a new          |
|                |                        | collection in the bucket.        |
|                +------------------------+----------------------------------+
|                | `groups:create`        | Ability to create a new group    |
|                |                        | in the bucket.                   |
+----------------+------------------------+----------------------------------+
| ``collection`` | `write`                | Ability to write and read all    |
|                |                        | objects in the collection.       |
|                +------------------------+----------------------------------+
|                | `read`                 | Ability to read all objects in   |
|                |                        | the collection.                  |
|                +------------------------+----------------------------------+
|                | `records:create`       | Ability to create a new record   |
|                |                        | in the collection.               |
+----------------+------------------------+----------------------------------+
| ``record``     | `write`                | Ability to write and read the    |
|                |                        | record.                          |
|                +------------------------+----------------------------------+
|                | `read`                 | Ability to read the record.      |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| ``group``      | `write`                | Ability to write and read the    |
|                |                        | group.                           |
|                +------------------------+----------------------------------+
|                | `read`                 | Ability to read the group.       |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
             
.. note::

  Anyone with the `write` permission on an object can also edit its associated
  permissions and delete it.


Principals
==========

The main principal is set during the login phase, the Authentication
Policy is responsible to generate the user or app principal.

A principal is using the following formalism:
``{type}:{identifier}`` ie for Firefox Account: ``fxa:32aa95a474c984d41d395e2d0b614aa2``

Inside a bucket, groups can be created.. Members of this group will have
it as a principal for the context of the bucket.

When creating the following group, I am adding a new
``group:moderators`` principal for its members:

There are also two other global principals:

- ``Authenticated``: All users that are authenticated.
- ``Everyone``: Anyone that calls the endpoint authenticated or not.


Examples
========

To better understand how this works, here is a handful of examples which expose
how the permission model works.


The Payments use case
---------------------

For the payment use case we have three players involved:

- The **payment app**, storing receipts for buyers and sellers;
- The **selling app**, reading receipts for a given seller.
- The **buyer app** reading receipts for a given buyer.

Users shouldn't be able to write receipts themselves, sellers and users should
only be able to read their owns.

In this case, the ``payments`` bucket will be created with a ``receipts`` collection.


Here are the principals:

- **payment app**: ``hawk:f5c766ab3bf5022ec4776339bf8e197c``
- **seller app**: ``hawk:507e4eb9e3a28ded33ae950d89f61c21``
- **buyer**: ``fxa:32aa95a474c984d41d395e2d0b614aa2``


Here is the permission table:

+---------------------------------------------+-------------+-------------------------------------------+
| Object                                      | Permissions | Principals                                |
+=============================================+=============+===========================================+
| ``bucket:payments``                         | `write`     | ``hawk:f5c766ab3bf5022ec4776339bf8e197c`` |
+---------------------------------------------+-------------+-------------------------------------------+
| ``collection:receipts``                     | None        |                                           |
+---------------------------------------------+-------------+-------------------------------------------+
| ``record:de17f0f24b49f8364187891f8550ffbb`` | `read`      | ``hawk:507e4eb9e3a28ded33ae950d89f61c21`` |
|                                             |             | ``fxa:32aa95a474c984d41d395e2d0b614aa2``  |
+---------------------------------------------+-------------+-------------------------------------------+

This ensures every app can access its related records, and that each
buyer can also access their receipts. However, only the payment
application can create / edit new ones.


The Blog use case
-----------------

Consider a blog where:

- A list of administrators can CRUD everything.
- Some moderators can create articles and update existing ones.
- Anybody can read.

Creating a ``servicedenuages_blog`` bucket with an ``article`` collection.

Our users have the following principals:

- Alexis: ``fxa:<alexis id>``
- Mathieu: ``fxa:<mathieu id>``
- Rémy: ``fxa:<remy id>``
- Tarek: ``fxa:<tarek id>``

Here is the permission table:

+---------------------------------+-------------+-------------------------------------------+
| Object                          | Permissions | Principals                                |
+=================================+=============+===========================================+
| ``bucket:servicedenuages_blog`` | `write`     | ``fxa:<alexis id>``                       |
|                                 |             | ``fxa:<mathieu id>``                      |
+---------------------------------+-------------+-------------------------------------------+
| ``group:moderators``            | members     | ``fxa:<remy id>``                         |
|                                 |             | ``fxa:<tarek id>``                        |
+---------------------------------+-------------+-------------------------------------------+
| ``collection:article``          | `write`     | ``group:moderators``                      |
|                                 +-------------+-------------------------------------------+
|                                 | `read`      | ``Everyone``                              |
+---------------------------------+-------------+-------------------------------------------+


The microblogging use case
--------------------------

A microblog is a service to share short articles with people such as
Twitter, Google+ or Facebook.

- The microblog administrator creates the bucket.
- Each collection is isolated from the others, and only one person have all
  permissions on all records.
- Anybody can read everything.

A ``microblog`` bucket is created, where new groups can be created by authenticated users.
An ``article`` collection is created.

Our users have the following principals:

- Microblog administrator: ``fxa:<microblog administrator id>``
- Alexis: ``fxa:<alexis id>``
- Mathieu: ``fxa:<mathieu id>``
- Rémy: ``fxa:<remy id>``
- Tarek: ``fxa:<tarek id>``

+--------------------------------------------------+---------------------+-------------------------------------------+
| Object                                           | Permissions         | Principals                                |
+==================================================+=====================+===========================================+
| ``bucket:microblog``                             | `write`             | ``fxa:<microblog administrator id>``      |
|                                                  +---------------------+-------------------------------------------+
|                                                  | `group:create`      | ``Authenticated``                         |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``collection:articles``                          | `records:create`    | ``Authenticated``                         |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``group:alexis_buddies``                         | members             | ``fxa:<mathieu id>``                      |
|                                                  |                     | ``fxa:<tarek id>``                        |
|                                                  |                     | ``fxa:<remy id>``                         |
|                                                  +---------------------+-------------------------------------------+
|                                                  | `write`             | ``fxa:<alexis id>``                       |
|                                                  +---------------------+-------------------------------------------+
|                                                  | `read`              | ``Authenticated``                         |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``record:14dc5627-010a-4d39-bd88-c28c28bf37a5``  | `write`             | ``fxa:<alexis id>``                       |
|                                                  +---------------------+-------------------------------------------+
|   In case of a public record                     | `read`              | ``Everyone``                              |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``record:ffdb6deb-111c-40c4-a395-ce669798d72b``  | `write`             | ``fxa:<alexis id>``                       |
|                                                  +---------------------+-------------------------------------------+
|   In case of a direct message for tarek          | `read`              | ``fxa:<tarek id>``                        |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``record:8cc0def1-e19d-4334-9fd4-b968c95d7d0a``  | `write`             | ``fxa:<alexis id>``                       |
|                                                  +---------------------+-------------------------------------------+
|   In case of an article to people alexis follow  | `read`              | ``group:alexis_following``                |
+--------------------------------------------------+---------------------+-------------------------------------------+

Each time a user creates a new record, it needs to setup the ACLs
attached to it.

With this model it is also possible to setup a shared microblogging
account giving record's ``write`` permission to a group of users.


The Wiki use case
-----------------

- Authenticated users can create, retrieve, update and delete anything;
- Everyone can read articles.

A ``wiki`` bucket is created, where new groups can be created by authenticated users.
An ``article`` collection is created.

Our users have the following principals:

- Wiki administrator: ``fxa:<wiki administrator id>``
- Alexis: ``fxa:<alexis id>``
- Mathieu: ``fxa:<mathieu id>``
- Rémy: ``fxa:<remy id>``
- Tarek: ``fxa:<tarek id>``

+--------------------------------------------------+---------------------+-------------------------------------------+
| Object                                           | Permissions         | Principals                                |
+==================================================+=====================+===========================================+
| ``bucket:wiki``                                  | `write`             | ``fxa:<wiki administrator id>``           |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``collection:articles``                          | `write`             | ``Authenticated``                         |
|                                                  +---------------------+-------------------------------------------+
|                                                  | `read`              | ``Everyone``                              |
+--------------------------------------------------+---------------------+-------------------------------------------+

The bias is that kinto doesn't have revision nor history of
modification, but we are just providing a permission setup example.


The Company Wiki use case
-------------------------

- Employees of the company can CRUD anything.
- Managers can add employees to the wiki.
- Other people dont have access.


A ``companywiki`` bucket is created.
An ``article`` collection is created.

Our users have the following principals:

- Wiki administrator: ``fxa:<wiki administrator id>``
- Employees are:
 - Alexis: ``fxa:<alexis id>``
 - Mathieu: ``fxa:<mathieu id>``
 - Rémy: ``fxa:<remy id>``
 - Tarek: ``fxa:<tarek id>``

Tarek is the manager.


+--------------------------------------------------+---------------------+-------------------------------------------+
| Object                                           | Permissions         | Principals                                |
+==================================================+=====================+===========================================+
| ``bucket:companywiki``                           | `write`             | ``fxa:<wiki administrator id>``           |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``group:managers``                               | members             | ``fxa:<tarek id>``                        |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``group:employees``                              | members             | ``fxa:<alexis id>``                       |
|                                                  |                     | ``fxa:<mathieu id>``                      |
|                                                  |                     | ``fxa:<remy id>``                         |
|                                                  |                     | ``group:managers``                        |
|                                                  +---------------------+-------------------------------------------+
|                                                  | `write`             | ``group:managers``                        |
+--------------------------------------------------+---------------------+-------------------------------------------+
| ``collection:articles``                          | `write`             | ``group:employees``                       |
+--------------------------------------------------+---------------------+-------------------------------------------+
