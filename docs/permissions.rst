Access Control Lists
####################

.. _acls:

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
| **group**       | A group of other principals.                            |
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


Examples
========

To better understand how this will work, let's take some common use cases.


The Payments use case
---------------------

For the payment use case we have three players involved:

- The **payment app**, storing receipts for buyers and sellers;
- The **selling app**, reading receipts for a given seller.
- The **buyer app** reading receipts for a given buyer.

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

What do we want?
''''''''''''''''

- A list of administrators can CRUD everything.
- Some moderators can create_articles and update existing ones.
- Anybody can read.


The ``servicedenuages_blog`` bucket
''''''''''''''''''''''''''''''''''

In that case we will create a bucket for the blog
**servicedenuages_blog** owned by the blog administrators:

.. code-block:: json

    {
        "id": "servicedenuages_blog",
        "permissions": {
            "write_bucket": ["email:mathieu@example.com", "email:alexis@example.com"]
        }
    }


The ``moderators`` group
''''''''''''''''''''''''

We will create a moderators group with the list of people having the
ability to create and manage content.

.. code-block:: json

    {
        "id": "moderators",
        "members": ["email:natim@example.com", "email:nicolas@example.com",
                    "email:tarek@example.com"]
    }
   


The ``articles`` collection
'''''''''''''''''''''''''''

In this bucket we will create an **articles** collection:

.. code-block:: json

    {
        "id": "articles",
        "permissions": {
            "read_collection": ["Everyone"],
            "read_records": ["Everyone"],
            "create_records": ["group:moderators"],
            "write_records": ["group:moderators"]
        }
    }

And we don't need to setup specific records access.


The Twitter use case
--------------------

What do we want?
''''''''''''''''

- Collection is isolated (CRUD your own records).
- Anybody can read anything.


The ``twitter`` bucket
''''''''''''''''''''''

.. code-block:: json

    {
        "id": "twitter",
        "permissions": {
            "write_bucket": ["email:sysadmins@twitter.com"],
            "create_groups": ["Authenticated"]
        }
    }


The ``tweets`` collection
'''''''''''''''''''''''''

In this bucket we will create a **tweets** collection:

.. code-block:: json

    {
        "id": "tweets",
        "permissions": {
            "read_collection": ["Everyone"],
            "create_records": ["Authenticated"]
        }
    }


Record access
'''''''''''''

Finally to let users manage their tweets we will add the following
permissions on each records:

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

What do we want?
''''''''''''''''

- Authenticated users can CRUD anything.


The ``wiki`` bucket
'''''''''''''''''''

.. code-block:: json

    {
        "id": "wiki",
        "permissions": {
            "write_bucket": ["email:natim@example.com"]
        }
    }


The ``articles`` collection
'''''''''''''''''''''''''

In this bucket we will create an **articles** collection:

.. code-block:: json

    {
        "id": "articles",
        "permissions": {
            "read_collection": ["Everyone"],
            "read_records": ["Everyone"],
            "create_records": ["Authenticated"],
            "write_records": ["Authenticated"]
        }
    }

And that's about all.


The Company Wiki use case
-------------------------

What do we want?
''''''''''''''''

- Employee of the company to users can CRUD anything.
- Managers can add employees to the wiki.
- Other people doesn't have access.


The ``companywiki`` bucket
'''''''''''''''''''

.. code-block:: json

    {
        "id": "companywiki",
        "permissions": {
            "write_bucket": ["email:sysadmin@company.com"]
        }
    }

The ``managers`` group
''''''''''''''''''''''

In this bucket we will create a **managers** group:

.. code-block:: json

    {
        "id": "managers",
        "members": ["email:tarek@company.com"],
        "permissions": {
             "write_group": ["email:cto@company.com"]
        }
    }



The ``employees`` group
'''''''''''''''''''''''

In this bucket we will create an **employees** group:

.. code-block:: json

    {
        "id": "employees",
        "members": ["group:managers", "email:natim@company.com",
                     "email:nicolas@company.com", "email:mathieu@company.com",
                     "email:alexis@company.com"],
        "permissions": {
             "write_group": ["group:managers"]
        }
    }


The ``articles`` collection
'''''''''''''''''''''''''

In this bucket we will create an **articles** collection:

.. code-block:: json

    {
        "id": "articles",
        "permissions": {
            "read_collection": ["group:employees"],
            "create_records": ["group:employees"],
            "write_records": ["group:employees"]
        }
    }

And that's about all.
