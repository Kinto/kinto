Buckets
#######

Buckets are a group of collections, shared between users, with fined
permissions on the data stored inside.

Basically a bucket have got an id and a list of people identifier that
can administrate it.

A bucket can be created using a PUT on the bucket URI:

.. code-block:: http

   > PUT /buckets/servicedenuages HTTP/1.1
   < 201 Created

    {
      "id": "servicedenuages",
      "owners": ["email:natim@example.com"]
    }


There are two kinds of data linked to a bucket:

 - collections
 - groups


Collections
===========

Creating a collection inside a bucket enable all buckets owners to
administrate the collection.

The collection is not linked to a user anymore but to the bucket.


.. code-block:: http

    > PUT /buckets/servicedenuages/collections/mushrooms HTTP/1.1
    < 201 Created


Groups
======

Creating a group inside a bucket ease user permission management.

.. code-block:: http

    > PUT /buckets/servicedenuages/groups/seekers HTTP/1.1

    { "members": ["email:alexis@example.com"] }

    < 201 Created

    {
      "id": "seekers",
      "members": ["email:alexis@example.com"]
    }

It is now possible to use the ``groups:seekers`` principal to describe
permissions inside the ``servicedenuages`` bucket.


Schema
======

To understand objects imbrication and properties we have the following:

.. code-block:: text

               +--------------+
               | Buckets      |
               +--------------+
        +----->+ - id         +<-----+
        |      | - owners     |      |
        |      +--------------+      |
        |                            |
        |                            |
        |                            |
        |                            |
        |                            |
    +---------------+       +---------------+
    | Collections   |       | Groups        |
    +---------------+       +---------------+
    | - id          |       |  - id         |
    | - permissions |       |  - members    |
    +---------------+       +---------------+
           ^
           |
           |
    +---------------+
    | Records       |
    +---------------+
    |  - id         |
    |  - data       |
    |  - members    |
    +---------------+
