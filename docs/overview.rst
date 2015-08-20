Overview
#########


*Kinto* is a lightweight JSON storage service with synchronisation and sharing
abilities. It is meant to be **easy to use** and **easy to self-host**.

Kinto is released under the Apache v2 licence.

.. _use-cases:

Use cases
=========

- Build collaborative applications with fine grained-permissions;
- Store encrypted data at a location you control;
- Store application state between different devices.
- Create a data wiki


Key features
============

*Kinto* implements modern HTTP best practices making it easy to synchronise
application data between different devices.

Abstractions are provided wherever it makes sense (storage, authentication,
permissions, etc.), which allows Kinto to adapt to many different use-cases.

We believe in open source, collaboration, and consensus - as such, any changes
to the underlying protocol are publically discussed and documented.


.. _overview-synchronization:

Synchronization
===============

Bi-directionnal synchronization of records is a very hard topic.

*Kinto* takes some shortcuts by only providing the basics for concurrency control
and polling for changes, and not trying to resolve conflicts automatically.

Basically, each object has a revision number which is guaranteed to be incremented after
each modification. *Kinto* does not keep any history.

Clients can retrieve the list of changes that occured on a collection of records
since a specified revision. *Kinto* can also use it to avoid accidental updates
of objects.

.. note::

    *Kinto* synchronization was designed and built by the `Mozilla Firefox Sync
    <https://en.wikipedia.org/wiki/Firefox_Sync>`_ team.


.. _comparison:

Comparison with other solutions
===============================

Before starting to create yet another data storage service, we had a long
look to the existing solutions, to see if that would make sense to extend
the community effort rather than re-inventing the wheel.

It appeared that solutions we looked at weren't solving the problems we had,
especially regarding fine-grained permissions.

Here is a comparison table we put together with existing alternative
technologies.

===========================  ======  ======  ========  =======  ==============
Project                      Kinto   Parse   Firebase  CouchDB  Remote-Storage
---------------------------  ------  ------  --------  -------  --------------
Fine-grained permissions     ✔       ✔       ✔
Easy query mechanism         ✔       ✔       ✔         [#]_     N/A
Conflict resolution          ✔       ✔       ✔         ✔        N/A
Validation                   ✔       ✔       ✔         ✔        N/A
Revision history                                       ✔        N/A
File storage                         ✔                 ✔
Batch/bulk operations        ✔       ✔                 ✔
Changes stream               [#]_    ✔       ✔         ✔        N/A
Pluggable authentication     ✔                         ✔        N/A
Pluggable storage / cache    ✔                                  ✔
Self-hostable                ✔                         ✔        N/A
Open source                  ✔                         ✔        ✔
Language                     Python                    Erlang   Node.js [#]_
===========================  ======  ======  ========  =======  ==============

.. [#] CouchDB uses Map/Reduce as a query mechanism, which isn't easy to
       understand for newcomers.
.. [#] Notifications support is currently in the work.
.. [#] Remote Storage doesn't define any default implementation (as it is
       a procol) but makes it easy to start with JavaScript and Node.js.

You can also read `a longer explanation of our choices and motivations behind the
creation of Kinto <http://www.servicedenuages.fr/en/generic-storage-ecosystem>`_
on our blog.

.. _FAQ:

FAQ
===

- How does Kinto compares to CouchDB / Remote Storage?

    Before starting to create yet another data storage service, we had a long
    look to the existing solutions, to see if that would make sense to extend
    the community effort rather than re-inventing the wheel.

    It appeared that solutions we looked at weren't solving the problems we had,
    especially regarding fine-grained permissions.

    To see how Kinto compares to these solutions,
    read :ref:`the comparison table <comparison>`.

- Can I encrypt my data?

    Kinto server stores any data you pass to it, be it encrypted or not.
    We make it easy to use encryption in our Kinto.js client
    `using transformers <http://kintojs.readthedocs.org/en/latest/api/#transformers>`_.

- Is there a package for my Operating System?

    Not at the moment. We want to make it very easy to integrate with existing
    operating systems, and this item is on our priority list.

    However, we are not there just yet. We are `already integrated with docker <https://hub.docker.com/r/kinto/kinto-server/>`
    and :ref:`easy to install with pip <installation>`.

- Why did you chose to use Python rather than X?

    We know and love `Python <python.org>`_ for its simplicity and ease to
    learn, so it was an obvious choice the development team. In addition, the
    operational team at Mozilla has good recipes and a lot of knowledge about
    how to deploy python.

    However, the protocol and concepts behind Kinto don't rely on Python *per se*,
    so it is possible to have other Kinto implementations using other languages.

- Is it Web Scale?

    YES™.

- Can I store files inside Kinto?

    No. At the moment, Kinto is meant to be used as a JSON storage service, and
    differs with file storage solutions. We might add this in the future if
    the use-case appears, but it is not on our radar so far.


- What is Cliquet? What is the difference between Cliquet and Kinto ?

    Kinto is a server built upon a toolkit named Cliquet. All of the reusable
    parts have been factorised inside the toolkit, whereas what makes Kinto
    unique is not.

    `Read more (in french) about the differences <http://www.servicedenuages.fr/pourquoi-cliquet>`_.
