Overview
#########

.. image:: images/overview-use-cases.png
    :align: right

*Kinto* is a minimalist JSON storage service with synchronisation and sharing
abilities. It is meant to be **easy to use** and **easy to self-host**.

*Kinto* is used at Mozilla and released under the Apache v2 licence.


.. _why:

Why use Kinto?
==============

We believe data belongs to the users, and not to the application authors. When
writing applications, data should be made available to any device, connected or
offline, and everything should be in sync.

Rather than spending a non-trivial amount of time and expertise on implementing
all that (and then maintaining it!), you could use Kinto, that does all that
for you:

- Expose your data over an HTTP interface, unlike databases like PostgreSQL
- Use simple HTTP requests rather than SQL
- Use `Kinto.js <https://kintojs.readthedocs.io/en/latest/>`_ to easily
  implement offline first clients
- Choose the database you want from those that Kinto supports, and use a
  unified API to access its data
- Manage your data using the handy
  `admin UI <http://kinto.github.io/kinto-admin/>`_
- Easily
  :ref:`set up live push notifications <tutorial-notifications-websockets>`
  for live synchronisation
- Make it possible to
  :ref:`share data between users <api-permissions>`
  (using fine-grained permissions)
- Take advantage of
  :ref:`schema validation <collection-json-schema>`
  if you need it


.. _use-cases:

Use cases
=========

- A generic Web database for frontend applications.
- Build collaborative applications with fine-grained permissions.
- Store encrypted data at a location you control.
- Synchronise application data between different devices.

.. note::

    At Mozilla, *Kinto* is used in *Firefox* and *Firefox OS* for global synchronization
    of settings and assets, as well as a first-class solution for personal data in
    browser extensions and Web apps.


Key features
============

.. |logo-synchronisation| image:: images/logo-synchronisation.svg
   :alt: https://thenounproject.com/search/?q=syncing&i=31170
   :width: 70px

.. |logo-permissions| image:: images/logo-permissions.svg
   :alt: https://thenounproject.com/search/?q=permissions&i=23303
   :width: 70px

.. |logo-multiapps| image:: images/logo-multiapps.svg
   :alt: https://thenounproject.com/search/?q=community&i=189189
   :width: 70px

.. |logo-selfhostable| image:: images/logo-selfhostable.svg
   :alt: https://thenounproject.com/search/?q=free&i=669
   :width: 70px

.. |logo-community| image:: images/logo-community.svg
   :alt: https://thenounproject.com/search/?q=community&i=189189
   :width: 70px

.. |logo-schema| image:: images/logo-jsonschema.svg
   :alt: https://thenounproject.com/search/?q=quality+control&i=170795
   :width: 70px

+---------------------------------------------+---------------------------------------+
| |logo-synchronisation|                      | |logo-permissions|                    |
| Synchronisation                             | Fined grained permissions             |
|                                             |                                       |
+---------------------------------------------+---------------------------------------+
| |logo-schema|                               | |logo-multiapps|                      |
| JSON Schema validation                      | Universal and multi clients           |
+---------------------------------------------+---------------------------------------+
| |logo-selfhostable|                         | |logo-community|                      |
| Open Source and Self-hostable               | Designed in the open                  |
+---------------------------------------------+---------------------------------------+

**Also**

- HTTP best practices
- Pluggable authentication
- :ref:`Pluggable storage, cache, and permission backends
  <configuration-backends>`
- Configuration via a INI file or environment variables
- Built-in monitoring
- Cache control

**Ecosystem**

.. |logo-offline| image:: images/logo-offline.svg
   :alt: https://thenounproject.com/search/?q=offline&i=90580
   :width: 50px

.. |logo-python| image:: images/logo-python.svg
   :alt:
   :width: 50px

.. |logo-attachment| image:: images/logo-attachment.svg
   :alt: https://thenounproject.com/search/?q=attachment&i=169265
   :width: 50px

.. |logo-livesync| image:: images/logo-livesync.svg
   :alt: https://thenounproject.com/search/?q=refresh&i=110628
   :width: 50px

.. |logo-boilerplate| image:: images/logo-react.svg
   :alt: https://commons.wikimedia.org/wiki/File:React.js_logo.svg
   :width: 50px

.. |logo-demos| image:: images/logo-demos.svg
   :alt: https://thenounproject.com/search/?q=tutorial&i=24313
   :width: 50px

+---------------------------------------------+---------------------------------------------+
| |logo-offline|                              | |logo-python|                               |
| Offline-first `JavaScript client            | :github:`Python client                      |
| <https://kintojs.readthedocs.io>`_         | <Kinto/kinto.py>`                           |
+---------------------------------------------+---------------------------------------------+
| |logo-attachment|                           | |logo-livesync|                             |
| :github:`File attachments on records        | Live :ref:`Push notifications               |
| <Kinto/kinto-attachment>`                   | <tutorials>`                                |
+---------------------------------------------+---------------------------------------------+
| |logo-boilerplate|                          | |logo-demos|                                |
| :github:`Kinto+React boilerplate            | :ref:`Example applications <app-examples>`  |
| <Kinto/kinto-react-boilerplate>`            |                                             |
+---------------------------------------------+---------------------------------------------+

**Coming soon**

- Web Administration (:github:`under construction <Kinto/kinto-admin>`)
- Automatic service discovery
- Push notifications using `the Push API <https://developer.mozilla.org/en-US/docs/Web/API/Push_API>`_ (:github:`under construction <Kinto/kinto-webpush>`)

(See `our roadmap <https://github.com/Kinto/kinto/wiki/Roadmap>`_)


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


.. _overview-notifications:

Notifications
=============

*Kinto* can execute some code when a particular event occurs.
For example, when a record is created or updated in a particular collection.

It can send a notification to clients using `WebSockets <https://en.wikipedia.org/wiki/WebSocket>`_
or fill a queue of messages in `Redis <http://redis.io/>`_ or execute any custom code of your choice,
like for sending emails or pinging a third-party.

See :ref:`our tutorials <tutorials>`!


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


===========================  ======  ======  ========  =======  ======= ==============  =======  =========
Project                      Kinto   Parse   Firebase  CouchDB  Kuzzle  Remote-Storage  Hoodie   BrowserFS
---------------------------  ------  ------  --------  -------  ------- --------------  -------  ---------
Offline-first client         ✔       ✔       ✔         ✔        ✔       ✔               ✔
Fine-grained permissions     ✔       ✔       ✔                  ~                       [#]_
Easy query mechanism         ✔       ✔       ✔         [#]_     ✔       [#]_            ✔
Conflict resolution          ✔       ✔       ✔         ✔        ✔       ✔ [#]_          ✔
Validation                   ✔       ✔       ✔         ✔        ✔                       ✔
Revision history                                       ✔                                ✔
File storage                 ✔       ✔                 ✔                ✔               ✔        ✔
Batch/bulk operations        ✔       ✔                 ✔        ✔                       ✔
Changes stream               ✔       ✔       ✔         ✔        ✔                       ✔
Pluggable authentication     ✔                         ✔                [#]_            ✔        ✔
Pluggable storage / cache    ✔                                          ✔
Self-hostable                ✔       ✔                 ✔        ✔       ✔               ✔        ✔
Decentralised discovery      [#]_                                       ✔
Open source                  ✔       ✔                 ✔        ✔       ✔               ✔        ✔
Language                     Python                    Erlang   Node.js Node.js [#]_    Node.js  Node.js
===========================  ======  ======  ========  =======  ======= ==============  =======  =========

.. [#] Currently, user plugin in Hoodie auto-approves users, but they are working on it.
.. [#] CouchDB uses Map/Reduce as a query mechanism, which isn't easy to
       understand for newcomers.
.. [#] Remote Storage allows "ls" on a folder, but items are not sorted or
       paginated.
.. [#] Kinto uses the same mechanisms as Remote storage for conflict handling.
.. [#] Remote Storage supports OAuth2.0 implicit grant flow.
.. [#] Support for decentralised discovery
       `is planned <https://github.com/Kinto/kinto/issues/125>`_ but not
       implemented yet.
.. [#] Remote Storage doesn't define any default implementation (as it is
       a procol) but makes it easy to start with JavaScript and Node.js.

You can also read `a longer explanation of our choices and motivations behind the
creation of Kinto <http://www.servicedenuages.fr/en/generic-storage-ecosystem>`_
on our blog.
