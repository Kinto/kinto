Permissions examples
====================

In order to better understand how the *Kinto* permission model works, it is
possible to refer to this set of examples:

+---------------+-------------------------------------------------------------------------+
| Example       | Description                                                             |
+===============+=========================================================================+
| Blog          | Everyone can read; Authors can write / read / create articles           |
+---------------+-------------------------------------------------------------------------+
| Wiki          | Authenticated users can write / read / create; Everyone can read.       |
+---------------+-------------------------------------------------------------------------+
| Company Wiki  | Employees can write / read /create anything; Managers can add employees |
+---------------+-------------------------------------------------------------------------+
| Microblogging | A micro blogging platform like twitter                                  |
+---------------+-------------------------------------------------------------------------+

.. _permissions-setups-blog:

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

+---------------------------------+-------------+----------------------------------------------------+
| Object                          | Permissions | Principals                                         |
+=================================+=============+====================================================+
| Bucket ``servicedenuages_blog`` | ``write``   | ``account:<alexis id>``                            |
|                                 |             | ``account:<mathieu id>``                           |
+---------------------------------+-------------+----------------------------------------------------+
| Collection ``article``          | ``write``   | ``/bucket/servicedenuages_blog/groups/moderators`` |
|                                 +-------------+----------------------------------------------------+
|                                 | ``read``    | ``system.Everyone``                                |
+---------------------------------+-------------+----------------------------------------------------+


A Wiki
------

- Authenticated users can create, retrieve, update and delete anything;
- Everyone can read articles.

The following objects are created:

- A ``wiki`` bucket, where new groups can be created by authenticated users;
- An ``article`` collection is created.

+-------------------------+---------------------+-------------------------------------+
| Object                  | Permissions         | Principals                          |
+=========================+=====================+=====================================+
| Bucket ``wiki``         | ``write``           | ``account:<wiki administrator id>`` |
+-------------------------+---------------------+-------------------------------------+
| Collection ``articles`` | ``write``           | ``system.Authenticated``            |
|                         +---------------------+-------------------------------------+
|                         | ``read``            | ``system.Everyone``                 |
+-------------------------+---------------------+-------------------------------------+


A Company Wiki
--------------

- Employees of the company can CRUD anything;
- Managers can add employees to the wiki;
- Other people don't have access.

The following objects are created:

- A ``companywiki`` bucket;
- An ``articles`` collection;
- An ``employees`` group.

+--------------------------+--------------+-------------------------------------------+
| Object                   | Permissions  | Principals                                |
+==========================+==============+===========================================+
| Bucket ``companywiki``   | ``write``    | ``account:<wiki administrator id>``       |
+--------------------------+--------------+-------------------------------------------+
| Group ``employees``      | ``write``    | ``/buckets/companywiki/groups/managers``  |
+--------------------------+--------------+-------------------------------------------+
| Collection ``articles``  | ``write``    | ``/buckets/companywiki/groups/employees`` |
|                          |              | ``/buckets/companywiki/groups/managers``  |
+--------------------------+--------------+-------------------------------------------+


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

+------------------------------------------+---------------------+------------------------------------------------+
| Object                                   | Permissions         | Principals                                     |
+==========================================+=====================+================================================+
| Bucket ``microblog``                     | ``write``           | ``account:<microblog administrator id>``       |
|                                          +---------------------+------------------------------------------------+
|                                          | ``group:create``    | ``system.Authenticated``                       |
+------------------------------------------+---------------------+------------------------------------------------+
| Collection ``articles``                  | ``record:create``   | ``system.Authenticated``                       |
+------------------------------------------+---------------------+------------------------------------------------+
| Group ``alexis_buddies``                 | ``write``           | ``account:<alexis id>``                        |
+------------------------------------------+---------------------+------------------------------------------------+
| A public message                         | ``write``           | ``account:<alexis id>``                        |
|                                          +---------------------+------------------------------------------------+
|                                          | ``read``            | ``system.Everyone``                            |
+------------------------------------------+---------------------+------------------------------------------------+
| A direct message for a user              | ``write``           | ``account:<alexis id>``                        |
|                                          +---------------------+------------------------------------------------+
|                                          | ``read``            | ``account:<tarek id>``                         |
+------------------------------------------+---------------------+------------------------------------------------+
| A private message for a group            | ``write``           | ``account:<alexis id>``                        |
|                                          +---------------------+------------------------------------------------+
|                                          | ``read``            | ``/buckets/microblog/groups/alexis_following`` |
+------------------------------------------+---------------------+------------------------------------------------+

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
|                      |             | ``account:<buyer id>``  |
+----------------------+-------------+-------------------------+

This ensures every app can list the receipts of every buyer, and that each
buyer can also list their receipts. However, only the payment
application can create / edit new ones.
