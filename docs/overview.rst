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

    Don't build silos. Redecentralize the Web!

It's hard for frontend developers to respect users privacy when building applications
that work offline, store data remotely, and synchronise accross devices.
Existing solutions either rely on big corporations that crave for user data, or require
a non-trivial amount of time and expertise to setup a new server for every new project.

We want to help developers focus on the frontend, and we don't want the challenge
of storing user data to get in their way! The path between a new idea and starting into
production should be short!

Also, we believe data belongs to the users, and not to the application authors.
Applications should be decoupled from the storage location, and users should be
able to choose where their personal data are stored.

We envision mutualisation and self-hosting: the backend is deployed, secured and scaled
only once and efforts are capitalized.


.. _use-cases:

Use cases
=========

- **A generic Web database**: for mobile and Web apps, games, or IoT...
- **Quickly prototype frontend applications**: don't loose time with server stuff.
- **Applications as static files**: just host your apps on Github pages, your storage backend
  is elsewhere!
- **Offline-first applications**: data can also be stored locally and published later.
- **Build collaborative applications** with real time updates and fine-grained permissions.
- **Synchronise application data** between different devices.
- **Store encrypted data** at a location users can control.

.. note::

    At Mozilla, *Kinto* is used in *Firefox* for global synchronization
    of frequently changed settings like blocklists, and the Web Extensions storage.sync API.
    It is also used in *Firefox for Android* for A/B testing and delivering extra
    assets like fonts or hyphenation dictionnaries.


How ?
=====

Kinto is an HTTP API in front of a database. Interactions with the server are simple HTTP requests
rather than complex SQL or map-reduce queries. It is meant to be minimalist and simple.

Permissions can be set on the stored objects, making it possible to share data between users.

We provide a demo server to start immediately, a one-click installer on Heroku for long
term hosting or a Docker image to even run it yourself.

The JavaScript and Python development kits (SDK) provide basic abstractions to store
and retrieve data from your applications. Our offline client for browsers will leverage
IndexedDB to synchronize data locally when back online.

Storing encrypted records on the server with client-side encryption is optional.

The ecosystem is growing and some plugins provide advanced features like history tracking,
push notifications, file attachments, or schema validation...


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
- Optional :ref:`JSON schema validation <collection-json-schema>`
- Built-in monitoring
- Cache control

**Ecosystem**

.. |logo-javascript| image:: images/logo-javascript.svg
   :alt:
   :width: 50px

.. |logo-python| image:: images/logo-python.svg
   :alt:
   :width: 50px

.. |logo-offline| image:: images/logo-offline.svg
   :alt: https://thenounproject.com/search/?q=offline&i=90580
   :width: 50px

.. |logo-admin| image:: images/logo-admin.svg
   :alt: control panel by Gregor Črešnar from the Noun Project
   :width: 50px

.. |logo-history| image:: images/logo-history.svg
   :alt: restore by Francesco Terzini from the Noun Project
   :width: 50px

.. |logo-livesync| image:: images/logo-livesync.svg
   :alt: https://thenounproject.com/search/?q=refresh&i=110628
   :width: 50px

.. |logo-attachment| image:: images/logo-attachment.svg
   :alt: https://thenounproject.com/search/?q=attachment&i=169265
   :width: 50px

.. |logo-signature| image:: images/logo-signature.svg
   :alt: approved by Gregor Črešnar from the Noun Project
   :width: 50px

.. |logo-boilerplate| image:: images/logo-react.svg
   :alt: https://commons.wikimedia.org/wiki/File:React.js_logo.svg
   :width: 50px

.. |logo-quotas| image:: images/logo-quotas.svg
   :alt: Mobile Cloud by Thays Malcher from the Noun Project
   :width: 50px

.. |logo-demos| image:: images/logo-demos.svg
   :alt: https://thenounproject.com/search/?q=tutorial&i=24313
   :width: 50px

+---------------------------------------------+---------------------------------------------+
| |logo-javascript|                           | |logo-python|                               |
| :github:`JavaScript HTTP API client         | :github:`Python HTTP API client             |
| <Kinto/kinto-http.js/>`                     | <Kinto/kinto.py>`                           |
+---------------------------------------------+---------------------------------------------+
| |logo-offline|                              | |logo-admin|                                |
| Offline-first `JavaScript client            | :github:`Web Admin UI                       |
| <https://kintojs.readthedocs.io>`_          | <Kinto/kinto-admin>`                        |
+---------------------------------------------+---------------------------------------------+
| |logo-history|                              | |logo-livesync|                             |
| :ref:`History of changes and authorship     | Live :ref:`Push notifications               |
| <api-history>`                              | <tutorials>`                                |
+---------------------------------------------+---------------------------------------------+
| |logo-attachment|                           | |logo-signature|                            |
| :github:`File attachments on records        | :github:`Digital signature and review       |
| <Kinto/kinto-attachment>`                   | workflows <Kinto/kinto-signer>`             |
+---------------------------------------------+---------------------------------------------+
| |logo-quotas|                               | |logo-boilerplate|                          |
| :ref:`Storage quotas                        | :github:`Kinto+React boilerplate            |
| <api-quotas>`                               | <Kinto/kinto-react-boilerplate>`            |
+---------------------------------------------+---------------------------------------------+

**Learn from examples**

|logo-demos| Check out :ref:`the list of example applications <app-examples>`,
or our :ref:`tutorials <tutorials>`!


**Coming soon**

- Push notifications using `the Push API <https://developer.mozilla.org/en-US/docs/Web/API/Push_API>`_ (:github:`under construction <Kinto/kinto-webpush>`)

(See `our roadmap <https://github.com/Kinto/kinto/wiki/Roadmap>`_)


.. _overview-synchronisation:

Synchronisation
===============

Bi-directional synchronisation of records is a very hard topic.

*Kinto* takes some shortcuts by only providing the basics for concurrency control
and polling for changes, and not trying to resolve conflicts automatically.

Basically, each object has a revision number which is guaranteed to be incremented after
each modification. Unless the :ref:`history plugin <api-history>` is activated,
*Kinto* does not keep old revisions of objects.

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
