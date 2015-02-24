Rationale
#########

Philosophy
==========

Cliquet doesn't try to be a framework: the generated APIs are well defined and
follow a specific protocol.

This protocol is an implementation of a series of opinionated good practices
we follow at Mozilla. The goal is to produce APIs which are easy to consume
for the clients and follow some well known patterns.

Cliquet handles:

* Records validation
* Storage by user
* Pagination
* Sorting and filtering
* Preconditions headers
* Batch operations
* Polling for collection changes
* Errors formatting
* API versioning and deprecation

It is built around the notion of resources: resources are defined by sub-classing,
and Cliquet handles the APIs out of that.

* KISS
* No magic
* Works with defaults

Cliquet is built on the shoulders of giants: Pyramid is doing all the heavy
HTTP stuff and PostgreSQL for the storage.

Currently, default authentication relies on Firefox Account, but any
authentication backend supported by Pyramid can be used.


Context
=======

* Cloud Services team at Mozilla
* Reading list project story
* Firefox Sync
* Cloud storage


Vision
======

General:

* A global protocol : Cliquet as the implementation of reference in python
* JavaScript client: implementation of reference

Features:

* Notifications channel
* Pluggable authentication backends (from configuration, just like storage)


Built with Cliquet
==================

Some applications in the wild built with Cliquet:

* `Reading List <https://github.com/mozilla-services/readinglist/>`_


Similar projects
================

* `Python Eve <http://python-eve.org/>`_
