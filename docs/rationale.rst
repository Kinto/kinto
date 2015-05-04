Rationale
#########

*Cliquet* is a toolkit to ease the implementation of HTTP `microservices`_.
Its mainly focused on resource oriented REST APIs (aka :term:`CRUD`).

.. _microservices: http://en.wikipedia.org/wiki/Microservices


Philosophy
==========

* :term:`KISS`;
* No magic;
* Works with defaults;
* Easy customization;
* Straightforward component substitution.

*Cliquet* doesn't try to be a framework: any project built with *Cliquet* will
expose a well defined HTTP protocol for:

* Collection and records manipulation;
* HTTP status and headers handling;
* API versioning and deprecation;
* Errors formatting.

:ref:`This protocol <api-endpoints>` is an implementation of a series of good
practices (followed at `Mozilla Services`_ and `elsewhere`_).

.. _Mozilla Services: https://wiki.mozilla.org/CloudServices
.. _elsewhere: http://www.vinaysahni.com/best-practices-for-a-pragmatic-restful-api

The goal is to produce standardized APIs, which follow some
well known patterns, encouraging genericity in clients code.

Of course, *Cliquet* can be extended and customized in many ways. It can also
be used in any kind of project, for its tooling, utilities and helpers.


Features
========

It is built around the notion of resources: resources are defined by sub-classing,
and *Cliquet* brings up the HTTP endpoints automatically.

Records and synchronization
---------------------------

* Collection of records by user
* Optional validation from schema
* Sorting and filtering
* Pagination using continuation tokens
* Polling for collection changes
* Record race conditions handling using preconditions headers

Generic endpoints
-----------------

* Hello view at root url
* Heartbeat for monitoring
* Batch operations
* API versioning and deprecation
* Errors formatting
* ``Backoff`` and ``Retry-After`` headers

Toolkit
-------

* Configuration through INI files
* Pluggable storage and cache backends
* Pluggable authentication schemes
* Structured logging
* StatsD metrics (*optional*)
* Sentry reporting (*optional*)
* NewRelic profiling (*optional*)
* Python code profiling (*optional*)


Dependencies
============

*Cliquet* is built on the shoulders of giants:

* :rtd:`Cornice <cornice>` for the REST helpers;
* :rtd:`Pyramid <pyramid>` for the heavy HTTP stuff;
* Redis or PostgreSQL for the cache and/or storage.

Currently, default authentication relies on Firefox Account, but any
:ref:`authentication backend supported by Pyramid can be used <configuration-authentication>`.


Built with Cliquet
==================

Some applications in the wild built with *Cliquet*:

* :rtd:`Reading List <readinglist>`, a service to synchronize articles between
  devices;
* :rtd:`Kinto <kinto>`, a service to store and synchronize schema-less data.

.. note::

    A *Kinto* instance can be used as a storage backend for a *Cliquet*
    application! :ref:`See cloud storage <cloud-storage>`.


Context
=======

(*to be done*)

* Cloud Services team at Mozilla
* :rtd:`ReadingList <readinglist>` project story
* Firefox Sync
* Cloud storage
* Firefox OS User Data synchronization and backup


Long term
=========

General
-------

An offline-first JavaScript library will be published [#]_, with the aim of providing
some reusable code for any client that interacts with a *Cliquet*-based API.

Server applications built with *Cliquet* can store their data in several kinds of
storage backends. Since backends are pluggable, and since *Kinto* is one of
them, storing data «in the cloud» is built-in ! In the long term, we envision
a world where client and server applications are decorrelated from their data [#]_!

Since the protocol is language independant and follows HTTP/REST principles,
in the long term *Cliquet* should become only one among several implementations.
We encourage you to implement a clone of this project using Node.js, Asyncio,
Go, Twisted or even Django !


Roadmap
-------

The future features we plan to implement in *Cliquet* are currently driven by the
use-cases we meet internally at Mozilla. Most notable are:

* Permissions system (e.g. read-only and record sharing)
* Notifications channel (e.g. run asynchronous tasks on events)
* ... come and discuss `enhancements in the issue tracker`_!

.. _enhancements in the issue tracker: https://github.com/mozilla-services/cliquet/issues?q=is%3Aopen+is%3Aissue+label%3Aenhancement


Similar projects
================

* `Python Eve <http://python-eve.org/>`_, built on Flask and MongoDB.


.. [#] Currently, the code was not extracted from the client projects, such as
    `RL Web client`_ (React.js), `Android RL sync`_ (Java) or `Firefox RL client`_ (asm.js).

.. [#] See https://unhosted.org.

.. _RL Web client: https://github.com/n1k0/readinglist-client/
.. _Android RL Sync: https://hg.mozilla.org/releases/mozilla-beta/file/default/mobile/android/base/reading/
.. _Firefox RL client: https://hg.mozilla.org/releases/mozilla-aurora/file/default/browser/components/readinglist
