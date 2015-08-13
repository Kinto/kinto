Rationale
#########


Kinto is a lightweight JSON storage service with synchronisation and sharing
abilities baked in. It is meant to be **easy to use** and **easy to self-host**.

Kinto implements modern HTTP best practices making it easy to synchronise
application data between different devices.

Abstractions are provided wherever it makes sense (storage, authentication,
permissions, etc.), which allows Kinto to adapt to many different use-cases.

We believe in open source, collaboration, and consensus - as such, any changes
to the underlying protocol are publically discussed and documented.

Kinto is released under the Apache v2 licence.

Use kinto to
============

- Build collaborative applications with fine grained-permissions;
- Store encrypted data at a location you control;
- Store application state between different devices.
- Create a data wiki

.. _comparison:

Comparison with other solutions
===============================

Before starting to create yet another data storage service, we had a long
look to the existing solutions, to see if that would make sense to extend
the community effort rather than re-inventing the wheel.

It appeared that solutions we looked at weren't solving the problems we had,
especially regarding fine-grained permissions.

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

.. [#] CouchDB uses Map/Reduce as a query mechanism.
.. [#] Notifications support is currently in the work.
.. [#] Remote Storage doesn't define any default implementation (as it is
       a procol) but makes it easy to start with JavaScript and Node.js.

You can also read `a longer explanation of our choices and motivations behind the
creation of Kinto <http://www.servicedenuages.fr/en/generic-storage-ecosystem>`_
on our blog.

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
- Is there a package for my Operating System?
- Why did you chose Python rather than X?
- Is it Web Scale™?
- Can I store files inside Kinto?
- What is Cliquet? What is the difference between Cliquet and Kinto ?
