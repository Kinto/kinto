Concepts
########


Basically, *Kinto* is a service where client applications can store and retrieve JSON data.

In order to provide synchronization and sharing features for these data, *Kinto*
introduces some basic concepts.


.. _concepts-buckets-collections-records:

Buckets, Collections and Records
================================

A **record** is the smallest unit of data. By default, there is no schema,
and the JSON can contain anything.

A **collection** is a group of records. Records are manipulated as a list
and can be filtered or sorted. Clients can obtain the list of changes that
occured on the collection records since a certain revision (e.g. *last synchronization*).

A **bucket** is an abstract notion used to organize collections and their
permissions. A bucket named ``default`` is provided, whose collections and records
are accessible to the current user only.

.. image:: images/concepts-general.jpg

Every kind of object manipulated by *Kinto* shares some common properties:
* a unique identifier;
* a revision number, automatically incremented on change;
* a set of permissions.

Those concepts are very similar to a hard disk, where buckets would be partitions,
collections are folders and records are files!


.. _concepts-groups:

Groups
======

*Kinto* also provides the concept of user groups, in order to define permissions.

A group has a list of members and belongs to a bucket. When defined on objects,
permissions can then refer to a group name instead of individual user identifiers.

It makes it easier to define roles and maintain them, especially if the same set
of permissions is applied to several objects.


.. _concepts-permissions:

Permission inheritance
======================

In order to control who is allowed to read, create, modify or delete the records,
permissions can be defined on buckets, groups, collections and single records.

.. image:: images/concepts-permissions.jpg

Since there is a notion of hierarchy between buckets, collections and records,
*Kinto* consider permissions as inherited from parent objects.
For example, if a bucket defines a permission that allows anonymous users to read,
then every record of every collection in this bucket will becomes readable.

The permission to create new objects is defined in the parent.
For example, the permission to create records is defined in the collection, and the permission
to create collections or groups is defined in the bucket. The permission to create new
buckets is controled from the :ref:`server configuration <configuration>` though.

.. note::

    If a parent defines a permission, it is (*currently*) not possible to restrict
    it in its children objects.
