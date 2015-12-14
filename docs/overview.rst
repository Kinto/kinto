Overview
#########

.. image:: images/overview-use-cases.png
    :align: right

*Kinto* is a lightweight JSON storage service with synchronisation and sharing
abilities. It is meant to be **easy to use** and **easy to self-host**.

*Kinto* is used at Mozilla and released under the Apache v2 licence.


.. _use-cases:

Use cases
=========

- A generic Web database for frontend applications.
- Build collaborative applications with fine-grained permissions.
- Store encrypted data at a location you control.
- Synchronise application data between different devices.


Key features
============

.. |logo-synchronisation| image:: images/logo-synchronisation.svg
   :alt: https://thenounproject.com/search/?q=syncing&i=31170
   :width: 100px

.. |logo-offline| image:: images/logo-offline.svg
   :alt: https://thenounproject.com/search/?q=offline&i=90580
   :width: 100px

.. |logo-permissions| image:: images/logo-permissions.svg
   :alt: https://thenounproject.com/search/?q=permissions&i=23303
   :width: 100px

.. |logo-multiapps| image:: images/logo-multiapps.svg
   :alt: https://thenounproject.com/search/?q=community&i=189189
   :width: 100px

.. |logo-selfhostable| image:: images/logo-selfhostable.svg
   :alt: https://thenounproject.com/search/?q=free&i=669
   :width: 100px

.. |logo-community| image:: images/logo-community.svg
   :alt: https://thenounproject.com/search/?q=community&i=189189
   :width: 100px

+---------------------------------------------+---------------------------------------+
| |logo-synchronisation|                      | |logo-offline|                        |
| :ref:`Synchronisation <api-synchronisation>`| `Offline-first JS client              |
|                                             | <https://kintojs.readthedocs.org>`_   |
+---------------------------------------------+---------------------------------------+
| |logo-permissions|                          | |logo-multiapps|                      |
| **Fined grained permissions**               | **Plug multiple clients**             |
+---------------------------------------------+---------------------------------------+
| |logo-selfhostable|                         | |logo-community|                      |
| **Open Source and Self-hostable**           | **Designed in the open**              |
+---------------------------------------------+---------------------------------------+


**Also**

- HTTP best practices
- Pluggable authentication
- :ref:`Pluggable storage, cache, and permission backends
  <configuration-backends>`
- Configuration via a single INI file
- Built-in monitoring


**Coming soon**

- Schema validation
- Push notifications

.. _overview-synchronisation:

Synchronisation
===============

Bi-directionnal synchronisation of records is a very hard topic.

*Kinto* takes some shortcuts by only providing the basics for concurrency control
and polling for changes, and not trying to resolve conflicts automatically.

Basically, each object has a revision number which is guaranteed to be incremented after
each modification. *Kinto* does not keep old revisions of objects.

Clients can retrieve the list of changes that occured on a collection of records
since a specified revision. *Kinto* can also use it to avoid accidental updates
of objects.

.. image:: images/overview-synchronisation.png
    :align: center

.. note::

    *Kinto* synchronisation was designed and built by the `Mozilla Firefox Sync
    <https://en.wikipedia.org/wiki/Firefox_Sync>`_ team.


.. _comparison:

Comparison with other solutions
===============================

Before we started building our own data storage service, we took a look at what
was already out there. Our initial intent was to use and possibly extend
an existing community project rather than reinventing the wheel.

However, since none of the existing solutions we tried was a perfect fit for the
problems we needed to solve, notably regarding fine-grained permissions, we started
our own stack using the experience we gained from building Firefox Sync.

What follows is a comparison table showing how Kinto stacks up compared to some
other projects in this space.


===========================  ======  ======  ========  =======  ==============  ======  =========
Project                      Kinto   Parse   Firebase  CouchDB  Remote-Storage  Hoodie  BrowserFS
---------------------------  ------  ------  --------  -------  --------------  ------  ---------
Fine-grained permissions     ✔       ✔       ✔                                  [#]_
Easy query mechanism         ✔       ✔       ✔         [#]_     [#]_            ✔
Conflict resolution          ✔       ✔       ✔         ✔        ✔ [#]_          ✔
Validation                   ✔       ✔       ✔         ✔                        ✔
Revision history                                       ✔                        ✔
File storage                         ✔                 ✔        ✔               ✔       ✔
Batch/bulk operations        ✔       ✔                 ✔                        ✔
Changes stream               [#]_    ✔       ✔         ✔                        ✔
Pluggable authentication     ✔                         ✔        [#]_            ✔       ✔
Pluggable storage / cache    ✔                                  ✔              
Self-hostable                ✔                         ✔        ✔               ✔       ✔
Decentralised discovery      [#]_                               ✔               
Open source                  ✔                         ✔        ✔               ✔       ✔
Language                     Python                    Erlang   Node.js [#]_    Node.js Node.js
===========================  ======  ======  ========  =======  ==============  ======  =========

.. [#] Currently, user plugin in Hoodie auto-approves users, but they are working on it.
.. [#] CouchDB uses Map/Reduce as a query mechanism, which isn't easy to
       understand for newcomers.
.. [#] Remote Storage allows "ls" on a folder, but items are not sorted or
       paginated.
.. [#] Kinto uses the same mechanisms as Remote storage for conflict handling.
.. [#] Notifications support is currently in the work.
.. [#] Remote Storage supports OAuth2.0 implicit grant flow.
.. [#] Support for decentralised discovery
       `is planned <https://github.com/Kinto/kinto/issues/125>`_ but not
       implemented yet.
.. [#] Remote Storage doesn't define any default implementation (as it is
       a procol) but makes it easy to start with JavaScript and Node.js.

You can also read `a longer explanation of our choices and motivations behind the
creation of Kinto <http://www.servicedenuages.fr/en/generic-storage-ecosystem>`_
on our blog.


.. _FAQ:

FAQ
===

How does Kinto compares to CouchDB / Remote Storage?
----------------------------------------------------

To see how Kinto compares to CouchDB & Remote Storage, read :ref:`the comparison table <comparison>`.

Can I encrypt my data?
----------------------

Kinto server stores any data you pass to it, whether it's encrypted or not. We believe
encryption should always be done on the client-side, and we make it easy to use encryption in
our Kinto.js client `using transformers <http://kintojs.readthedocs.org/en/latest/api/#transformers>`_.

Is there a package for my Operating System?
-------------------------------------------

No, but it's a great idea. Maintaining packages for several platforms is time-consuming
and we're a small team. At this time we're just making sure it's easy to run our server
using our Makefile or our Dockerfile.

Kinto is :ref:`easy to install with pip <installation>` and
we've got `an image set up <https://hub.docker.com/r/kinto/kinto-server/>`_
on the Docker hub, too.

But if you'd like to help us out by maintaining packages for your favourite OS,
we'd be delighted to collaborate with you!


Why did you chose to use Python rather than X?
----------------------------------------------

We love `Python <python.org>`_ because it's a concise & expressive
language with powerful data structures & easy to learn,
so it was an obvious choice for the development team.

In addition, the Operations team at Mozilla is comfortable with deploying and
managing Python applications in production.

However, Python is just an implementation detail *per se*. Kinto is
defined by an HTTP protocol that could be implemented in any language.


Is it Web Scale?
----------------

YES™. Have a look at the ``/dev/null`` backend. ;-)


Can I store files inside Kinto?
-------------------------------

Not yet, but we've designed a file storage feature and
we're `working on its implementaton <https://github.com/Kinto/kinto-attachment/>`_.
It should land in a release sometimes in 2016.

In the meantime, we're always looking for early feeback if you want to
try our cutting edge version.



What is Cliquet? What is the difference between Cliquet and Kinto ?
-------------------------------------------------------------------

Cliquet is a toolkit for designing micro-services. Kinto is a server built
using that toolkit.

`Read more (in french) about the differences <http://www.servicedenuages.fr/pourquoi-cliquet>`_.


I am seeing an Exception error, what's wrong?
---------------------------------------------

Have a look at the :ref:`Troubleshooting section <troubleshooting>` to
see what to do.
