Permissions
###########

.. _permissions:

Objects
=======

There are four kinds of objects that you can have rights on:

- **Buckets**
- **Groups**
- **Collections**
- **Records**


Permissions
===========

They are two kind of permissions on an object:

- **read**: It means that the given user or group of users have
  got read only access to the object
- **write**: It means that the given user or group of users have
  got read and write access to the object.

A **read** access let the user read all the attributes of the object.

A **write** access let the user read, update and delete any attributes
of the object.


Buckets
=======

Permissions to create a bucket are defined in the kinto configuration.
By default **Authenticated users** can create one.

Permission **write_bucket** let the user do anything she want inside
this bucket.

She basically become a bucket owner with full access on it:

- She can manage the bucket's permissions
- She can create and manage any bucket's groups
- She can create and manage any bucket's collections
- She can create and manage any bucket's collections records

There are two other permissions on a bucket:

- **create_group**: It gives the permission for some users to create groups
- **create_collection**: It gives the permission for some users to create collections


Groups
======

A group have got a few permissions:

- **read_group**: It gives read access to the group member list
- **write_group**: It gives write access to update the group member list


Collections
===========

A collection have got a few permissions:

- **read_collection**: It is a read access to the collection
  attributes (schema and permissions)
- **write_collection**: It is a write access to the collection
  attributes (schema and permissions)
- **create_records**: It is a permission that let one create new records
- **read_records**: It is a read access to any collection record
- **write_records**: It is a permission that let one update any collection record


Records
=======

A record have got two permissions:

- **read_record**: Give a read access to this specific record
- **write_record**: Give a write access to this specific record


Examples
========

To better understand how this will work, let's take some common use cases.


The Payments use case
---------------------

For the payment use case we have three players involved:

- The **payment app** that stores payments for users for an app
- The **selling app** that can read records of the given app
- The **user** that can read records of the given user


The ``payments`` bucket
'''''''''''''''''''''''

In that case we will create a bucket **payments** owned by the payment app:

.. code-block:: json

    {
        "id": "payments",
        "permissions": {
            "write_bucket": ["scope:paymentapp"]
        }
    }


The ``operations`` collection
'''''''''''''''''''''''''''''

In this bucket we will create a **operations** collection:

.. code-block:: json

    {
        "id": "operations",
        "permissions": {
            "read_collection": ["Authenticated"]
        }
    }

Records access
''''''''''''''

Finally to give user and sellingapp access to the records they need,
we will add the following permissions on each records:

.. code-block::

    {
        "id": "<record_id>",
        "data": {"records": "data"},
        "permissions": {
            "read_record": ["email:<user_email>", "app:<app_id>"]
        }
    }

By doing this, we will make sure that every app can access all the
records related to it, same for the users that can access their
records and the payment app can administrate everything.


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
