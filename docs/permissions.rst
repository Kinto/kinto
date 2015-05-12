Access Control Lists
####################

.. _acls:

Terminology
===========

Objects:
  Anything that can be interracted with. Collections, records, schemas, buckets
  are all objects.

Principals:
  An entity that can be authenticated.  Principals can be individual people,
  applications, services, or any group of such things.

Groups:
  A group of already existing principals.

Permissions:
  An action that can be done on an object. Example of permissions are "read",
  "write", and "create".

ACLs:
  A list of permissions associated to objects and principals. For instance,
  `write_bucket: [list, of, principals]`.

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
| **schema**      | Validation rules for collection's records               |
+-----------------+---------------------------------------------------------+
| **group**       | A group of other :ref:`principals <principals>`.        |
+-----------------+---------------------------------------------------------+

There is a notion of hierarchy among all these objects:

.. code-block:: text

               +---------------+
               | Buckets       |
               +---------------+
        +----->+ - id          +<--------------------------+
        |      | - acls        |                           |
        |      +---------------+                           |
        |                                                  |
        |                                                  |
        |       +------------------+                       |
        |       |                  |                       |
        |       v                  |                       |
    +---------------+        +----------------+     +----------------+ 
    | Collections   |        | Schema         |     | Groups         | 
    +---------------+        +----------------+     +----------------+ 
    | - id          |        |  - fields      |     |  - id          | 
    | - acls        |        |  - acls        |     |  - members     | 
    +---------------+        +----------------+     |  - acls        | 
           ^                                        +----------------+ 
           |
           |
    +----------------+
    | Records        |
    +----------------+
    |  - id          |
    |  - data        |
    |  - acls        |
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

ACLs are defined with the following formalism:
``{permission}_{object}: {list of principals}``.

For instance, to describe the list of principals which can write to a bucket,
the ``write_bucket`` ACL would be used.

+----------------+------------------------+----------------------------------+
| Object         | Associated permissions | Description                      |
+================+========================+==================================+
| Configuration  | `create_bucket`        | Ability to create a new bucket.  |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| ``bucket``     | `write_bucket`         | Ability to write + read on the   |
|                |                        | bucket and all children objects. |
|                +------------------------+----------------------------------+
|                | `read_bucket`          | Ability to read all objects in   |
|                |                        | the bucket.                      |
|                +------------------------+----------------------------------+
|                | `create_collection`    | Ability to create a new          |
|                |                        | collection in the bucket.        |
|                +------------------------+----------------------------------+
|                | `create_group`         | Ability to create a new group    |
|                |                        | in the bucket.                   |
+----------------+------------------------+----------------------------------+
| ``collection`` | `write_collection`     | Ability to write and read all    |
|                |                        | objects in the collection.       |
|                +------------------------+----------------------------------+
|                | `read_collection`      | Ability to read all objects in   |
|                |                        | the collection.                  |
|                +------------------------+----------------------------------+
|                | `create_record`        | Ability to create a new record   |
|                |                        | in the collection.               |
+----------------+------------------------+----------------------------------+
| ``record``     | `write_record`         |                                  |
|                |                        |                                  |
|                +------------------------+----------------------------------+
|                | `read_record`          |                                  |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| ``schema``     | `write_schema`         |                                  |
|                |                        |                                  |
|                +------------------------+----------------------------------+
|                | `read_schema`          |                                  |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
| ``group``      | `write_group`          |                                  |
|                |                        |                                  |
|                +------------------------+----------------------------------+
|                | `read_group`           |                                  |
|                |                        |                                  |
+----------------+------------------------+----------------------------------+
             
.. note::

  Anyone with the `write` permission on an object can also edit its associated
  permissions.

Principals
==========

XXX Describe how principals are used.


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

In this case, the ``payments`` bucket will be created with the following ACLs:

.. code-block:: json

    {
        "id": "payments",
        "acls": {
            "write_bucket": ["appid:<payment-appid>"]
        }
    }


Receipts will be stored inside a "receipts" collection, stored inside the
"payments" bucket. No specific ACL will be defined for this collection: only
the "payment" app should be able to write receipt records there.

.. code-block:: json

    {
        "id": "receipts",
        "acls": {}
    }


Finally to give buyers and sellers app read access on their related records,
each record should be created with an associated ACL.

.. code-block::

    {
        "id": "<record_id>",
        "data": {"records": "data"},
        "permissions": {
            "read_record": ["userid:<buyer-id>", "appid:<seller-appid>"]
        }
    }

This ensures every app can access its related records, and that each buyer can
also access their receipts. However, only the payment application can create
/ edit new ones.


The Blog use case
-----------------

Consider a blog where:

- A list of administrators can CRUD everything.
- Some moderators can create articles and update existing ones.
- Anybody can read.

Creating a <blogbucket> bucket where the list of admins are defined with the
`write_permission`.

.. code-block:: json

    {
        "id": "<blogname>",
        "acls": {
            "write_bucket": ["email:mathieu@example.com", "email:alexis@example.com"]
        }
    }

Moderators are special persons with special rights. Rather than adding
moderators to each object they can moderate, it is easier to create a group of
such persons:

.. code-block:: json

    {
        "id": "moderators",
        "members": ["email:natim@example.com", "email:nicolas@example.com",
                    "email:tarek@example.com"]
    }
   
The created bucket contains an **article** collection, with a defined set of
ACLs:

.. code-block:: json

    {
        "id": "articles",
        "acls": {
            "read_collection": ["Everyone"],
            "read_record": ["Everyone"],
            "create_record": ["group:moderators"],
            "write_record": ["group:moderators"]
        }
    }


The Twitter use case
--------------------

- Each collection is isolated from the others, and only one person have all
  permissions on all records.
- Anybody can read everything.

A "microblog" bucket is created, where new groups can be created by
authenticated users.

.. code-block:: json

    {
        "id": "twitter",
        "acls": {
            "write_bucket": ["email:sysadmins@twitter.com"],
            "create_groups": ["Authenticated"]
        }
    }


This bucket handles a **tweets** collection where everyone can read and only
authenticated users can create records.

.. code-block:: json

    {
        "id": "tweets",
        "acls": {
            "read_collection": ["Everyone"],
            "create_records": ["Authenticated"]
        }
    }


Each time a user creates a new record, it needs to setup the ACLs attached to
it.

.. code-block::

    {
        "id": "<record_id>",
        "data": {"records": "data"},
        "permissions": {
            "read_record": ["Everyone"],
            "write_record": ["email:<user_email>"]
        }
    }

If one want to restrict read access to its tweets, he can create a
``<username>:authorized_followers`` group and use it like so:

.. code-block:: json

    {
        "id": "<record_id>",
        "data": {"records": "data"},
        "permissions": {
            "read_record": ["group:<username>:authorized_followers"],
            "write_record": ["email:<user_email>"]
        }
    }

With this model it is also possible to setup a shared twitter account
giving ``write_record`` access to a group of users.


The Wiki use case
-----------------

- Authenticated users can create, retrieve, update and delete anything;
- Everyone can read articles.

By default, the creator of the bucket will get write access to the bucket:

.. code-block:: json

    {
        "id": "wiki",
        "acls": {
            "write_bucket": ["email:natim@example.com"]
        }
    }

This bucket contains an **articles** collection, where every

.. code-block:: json

    {
        "id": "articles",
        "acls": {
            "read_collection": ["Everyone"],
            "read_records": ["Everyone"],
            "create_records": ["Authenticated"],
            "write_records": ["Authenticated"]
        }
    }


The Company Wiki use case
-------------------------

- Employees of the company can CRUD anything.
- Managers can add employees to the wiki.
- Other people dont have access.


First, create a "companywiki" bucket:

.. code-block:: json

    {
        "id": "companywiki",
        "acls": {
            "write_bucket": ["email:sysadmin@company.com"]
        }
    }

This bucket contains a **managers** group:

.. code-block:: json

    {
        "id": "managers",
        "members": ["email:tarek@company.com"],
        "acls": {
             "write_group": ["email:cto@company.com"]
        }
    }

In this bucket we have an **employees** group:

.. code-block:: json

    {
        "id": "employees",
        "members": ["group:managers", "email:natim@company.com",
                    "email:nicolas@company.com", "email:mathieu@company.com",
                    "email:alexis@company.com"],
        "acls": {
             "write_group": ["group:managers"]
        }
    }


The bucket contains an **articles** collection:

.. code-block:: json

    {
        "id": "articles",
        "acls": {
            "read_collection": ["group:employees"],
            "create_records": ["group:employees"],
            "write_records": ["group:employees"]
        }
    }
