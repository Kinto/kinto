Buckets
#######

.. _buckets:

:ref:`Buckets <buckets>` enables the creation of collections handled by
a group of ref:`User identifiers <user-identifiers>`.

All collections are created in a bucket. By default, it uses the connected
user's bucket (bucket only the connected user has access to).

:ref:`Buckets <buckets>` can be seen as namespaces: you can have different
collections using the same name, but stored in different buckets, so their
names don't collide.

Data (everything stored in a bucket: collections, groups and records) is
not anymore linked to a specific user that only has access to her private data
but is linked to the bucket and managed by bucket's owners (those who have the
``write_bucket`` permission on the bucket.

Access to buckets, groups, collections and records are granted using
:ref:`permissions <permissions>`.

To understand objects imbrication and properties, here is a little schema.

.. code-block:: text

               +---------------+
               | Buckets       |
               +---------------+
        +----->+ - id          +<-----+
        |      | - permissions |      |
        |      +---------------+      |
        |                             |
        |                             |
        |                             |
        |                             |
        |                             |
    +---------------+        +----------------+
    | Collections   |        | Groups         |
    +---------------+        +----------------+
    | - id          |        |  - id          |
    | - permissions |        |  - members     |
    +---------------+        |  - permissions |
           ^                 +----------------+
           |
           |
    +----------------+
    | Records        |
    +----------------+
    |  - id          |
    |  - data        |
    |  - permissions |
    +----------------+


Creating a bucket
=================

A bucket can be created using a PUT on the desired bucket URI, optionally
specifying the list of attached permissions.

Arguments:

- ``permissions``: A mapping object that defines the list of users for each of
  the following permissions defined in the table below.  In any case (even if
  not specified), the current logged-in user will get access to the bucket.

Here is the list of possible permissions on a bucket:

+------------------------+---------------------------------+
| Permission             | Description                     |
+========================+=================================+
| ``write_bucket``       | The list of users principals    |
|                        | that have administration        |
|                        | permissions on the bucket, the  |
|                        | creator is automatically added  |
|                        | to the owner list.              |
+------------------------+---------------------------------+
| ``create_groups``      | Permission to create new groups |
+------------------------+---------------------------------+
| ``create_collections`` | Permission to create new        |
|                        | collections                     |
+------------------------+---------------------------------+

.. code-block:: http

    $ http PUT http://localhost:8000/v1/buckets/{bucket_id} --auth "admin:"

    POST /v1/buckets{bucket_id} HTTP/1.1
    Authorization: Basic YWRtaW46

    HTTP/1.1 201 Created
    Content-Type: application/json; charset=UTF-8

    {
        "id": "{bucket_id}",
        "permissions": {
            "write_bucket": ["uid:basicauth_5d127220922673e346c0ebee46c23e6739dfa756"],
            "create_groups": [],
            "create_collections": [],
        }
    }

There are two kinds of data linked to a bucket: **collections** and **groups**.


Collections
===========

Creating a collection inside a bucket enables all buckets users with
the ``write_bucket`` permission to have all permissions on all bucket's
collections and associated records.

.. code-block:: http

    > PUT /buckets/servicedenuages/collections/mushrooms HTTP/1.1
    < 201 Created


Groups
======

Creating a group inside a bucket eases user permission management.

.. code-block:: http

    > PUT /buckets/servicedenuages/groups/moderators HTTP/1.1

    { "members": ["email:alexis@example.com"] }

    < 201 Created

    {
      "id": "moderators",
      "members": ["email:alexis@example.com"]
    }

It is now possible to use the ``groups:moderators`` principal to describe
permissions inside the ``servicedenuages`` bucket.

