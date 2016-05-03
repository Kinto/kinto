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
  for live updates of your application
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
| <https://kintojs.readthedocs.io>`_          | <Kinto/kinto.py>`                           |
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

Bi-directional synchronisation of records is a very hard topic.

*Kinto* takes some shortcuts by only providing the basics for concurrency control
and polling for changes, and not trying to resolve conflicts automatically.

Basically, each object has a revision number which is guaranteed to be incremented after
each modification. *Kinto* does not keep old revisions of objects.

Clients can retrieve the list of changes that occurred on a collection of records
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

See :ref:`our tutorials <tutorials>` for more in-depth information on
these topics.
