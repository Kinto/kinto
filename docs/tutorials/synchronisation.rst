.. _api-synchronisation:

Synchronisation
###############

This section describes the basic aspects of synchronisation using *Kinto*.

.. note::

    If you are looking for a ready-to-use synchronisation solution,
    jump to :ref:`sync-implementations`.




The basic idea is to keep a local database up to date with the Kinto server:

* Remote changes are downloaded and applied on the local data.
* Local changes are uploaded using HTTP headers to control concurrency and overwrites.


In short:

#. Poll for remote changes using ``?_since=<timestamp>``
#. Apply changes locally
#. Send local creations
#. Use concurrency control to send local updates and deletes


Polling for remote changes
==========================

*Kinto* supports range queries for timestamps. Combining them with the sort parameter
allows to fetch changes in a particular order.

Depending on the context (latest first, readonly, etc.), there are several
strategies to poll the server for changes.

.. important::

    * Timestamps are unique.
    * Deleted records have an attribute ``delete: true``.
    * Created/updated records are both returned in their new version.
    * Since *Kinto* does not keep any history, there is no *diff* for updates.


Pagination
----------

By default, *Kinto* does not paginate the records list. Since an explicit limit can
be set in the server settings, clients must handle pagination when polling for
changes.

In order to reduce the size of response payloads, the client can also force the
pagination using the ``?_limit=<nb>`` querystring parameter.

Pagination basically consists in fetching the list while the ``Next-Page`` response header
is present. The ``Next-Page`` header is the **full** URL of the next page.

.. note::

    Pagination requests carry every necessary parameter to be reproduced in case
    of connectivity error.


Strategy #1 — Oldest first
--------------------------

The simplest way to obtain the changes is to sort the records by timestamp
ascending.

We will use ``sort=last_modified`` and ``_since=<timestamp>``:

#. First sync: ``timestamp := 0``
#. Next sync: ``timestamp := MAX(local_records['last_modified'])``
#. Fetch ``GET /buckets/<bid>/collections/<cid>/records?_sort=last_modified&_since=<timestamp>``
#. If response is ``200 OK``, handle the list of remote changes.
#. If response has ``Next-Page`` header, follow full URL in header.
#. If list of changes is empty, **done** → up-to-date.

.. image:: ../../images/sync-oldest.svg

If an error occurs during the retrieval of pages,
the synchronisation can be resumed transparently, since the pages are obtained
with ascending timestamps, and the next sync relies on the highest
timestamp successfully stored locally.


Strategy #2 — Newest first
--------------------------

In order to populate a UI, it might be relevant to obtain the latest changes first.

Syncing newest records first is a bit more complex since changes can occur between
the retrieval of the first and the last pages.

We will use ``sort=-last_modified`` (desc), ``_before`` to omit later changes,
and ``_since`` to include changes after last sync:

#. First sync: ``timestamp := 0``
#. Next sync: use ``timestamp`` stored in last successful sync.
#. Fetch current collection timestamp ``HEAD /buckets/<bid>/collections/<cid>/records``
   in ``ETag`` response header and store its value in ``start``.
#. Fetch ``GET /buckets/<bid>/collections/<cid>/records?_sort=-last_modified&_before=<start>&_since=<timestamp>``
#. If response is ``200 OK``, stack the obtained list of remote changes.
#. If response has ``Next-Page`` header, follow full URL in header.
#. If list of changes is empty, **done** → handle the stack of remote changes
   and update the timestamp: ``timestamp := MAX(local_records['last_modified'])``

.. image:: ../../images/sync-newest.svg

With this approach, the main algorithm is rather simple but since we track the
*last sync timestamp* when the last page is done, if an error occurs
between the first and the last step, the client must redownload every page obtained
from *step 1* until it succeeds to fetch every page of the sync.

In order to avoid that, the algorithm should slightly be complexified in order to
track additional info obtained from the page that failed. The upper and lower
values of timestamps (``_before`` and ``_since``) can then
be specified manually to resume the synchronisation.


Strategy #3 — Newest first, partially
-------------------------------------

For very large collections, it could be interesting to perform a first *partial*
synchronisation, and then fetch old records in background.

When a new client wants to sync, instead of syncing hundreds of pages on the
first synchronization, two distinct synchronization processes can be combined.

For example, start with some recent records in order to populate a UI,
and then fetch older records in background.

#. Obtain a few pages of recent records using the *newest first* strategy from above
#. In background, fetch old records using ``_sort=-last_modified`` and ``_before=MIN(local_records[last_modified])``
#. Recent changes can be obtained using ``_sort=-last_modified`` and ``_since=MAX(local_records[last_modified])``

.. image:: ../../images/sync-both.svg


Apply changes locally
=====================

Applying remote changes to the local database consists in adding new records,
updating changed records and remove deleted records.

From the client perspective, *Kinto* does not distinguish creations from updates.
In the *polling for changes* response, created records are simply the records
unknown by the client (using ``id`` field).

If the records to be updated or deleted had also been modified locally then
the developper must choose a relevant strategy. For example, merge fields or
ignore deletion.

.. _api-concurrency-control:

Concurrency control
===================

As described in :ref:`server-timestamps`, *Kinto* uses *ETag* for concurrency
control.

ETags are provided in response headers, for the collection as well as individual
records.

Even though it is recommended to consider them as opaque and abstract, it can still
be useful to notice that ETags are a string with the quoted record last modified value
(``"<record.last_modified>"``)


Protected creation with PUT
---------------------------

Add a ``If-None-Match: *`` request header to the ``PUT`` to make sure no
record exists on the server with this ID.

This can be useful to avoid overwrites when creating records with ``PUT``
instead of ``POST``.


Protected update and delete
---------------------------

Add a ``If-Match: "<record.last_modified>"`` request header to the ``PUT``, ``PATCH``
or ``DELETE`` request.

*Kinto* will reject the request with a ``412 Precondition Failed`` response if
the record was modified in the interim.

If the remote record was already deleted, a ``404 Not found`` response will be
returned. The client can choose to ignore it.


Offline-first
=============

Since the server won't be available to assign record identifiers while offline,
it is recommended to generate them on the client.

Record identifiers are `UUID <https://en.wikipedia.org/wiki/Universally_unique_identifier>`_,
a very common format for unique strings with almost zero [#]_ collision probability.

When going back online, the set of changes can be sent to the server using a
:ref:`batch` request.


.. _sync-implementations:

Implementations
===============

The **current implementation of reference** for offline-first records synchronisation is
:rtd:`Kinto.js <kintojs>`.


Before that, some other clients were implemented in the context of the
*ReadingList* project. That project was abandoned, but you can still
see the implementation of the `RL Web client`_ (React.js), `Android RL
sync`_ (Java) or `Firefox RL client`_ (asm.js).

.. _RL Web client: https://github.com/n1k0/readinglist-client/
.. _Android RL Sync: https://hg.mozilla.org/releases/mozilla-beta/file/FIREFOX_BETA_42_END/mobile/android/base/reading
.. _Firefox RL client: https://hg.mozilla.org/releases/mozilla-aurora/file/FIREFOX_AURORA_41_END/browser/components/readinglist



.. [#]  After generating **1 billion** UUIDs **every second** for the next **100 years**,
        the probability of creating just **one duplicate** would
        be about **50%**.
        `Source <https://en.wikipedia.org/wiki/Universally_unique_identifier#Random_UUID_probability_of_duplicates>`_
