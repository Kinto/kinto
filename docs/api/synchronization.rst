.. _api-synchronization:

Synchronization
###############

This section describes the basic aspects of synchronization using *Kinto*.

.. note::

    If you are looking for a ready-to-use synchronization solution,
    jump to :ref:`sync-implementations`.


The main idea consists in maintaining a local database up-to-date
with the *Kinto* server. Remote changes are downloaded and applied
on the local data. Local changes are uploaded using HTTP headers to control
concurrency and overwrite.

In short:

#. Poll for remote changes using ``?_since=<timestamp>``
#. Apply changes locally
#. Post creations
#. Use concurrency control to send updates and deletes


Polling for changes
===================

When fetching the collection records with ``?_since=<timestamp>``, *Kinto* returns
every records that were created/updated/deleted **after** this timestamp.

#. Cold sync → no ``?_since``.
#. ``GET /buckets/default/collections/articles?_since=<timestamp>`` (with header ``If-Unmodified-Since = <timestamp>``)
#. If response is ``304 Not modified``, done → up to date, nothing to do.
#. If response is ``200 OK`` store ``ETag`` response header value for next
   synchronization and handle the obtained list of changes.

.. note::

    * Deleted records have an attribute ``delete: true``
    * Created/updated records are both returned in their new version
    * Since *Kinto* does not keep any history, there is no *diff* for updates


Paginated changes
-----------------

By default, *Kinto* does not paginate the records list. If an explicit limit is
set in the server settings or using the ``?_limit=<nb>`` parameter, then polling for
changes will be paginated.

It basically consists in fetching the list until the ``Next-Page`` is present.

Since changes can occur between the first and the last page, the synchronization
process is a bit more complex.

#. Cold sync → no ``?_since``.
#. ``GET /buckets/default/collections/articles?_since=<timestamp>`` (with header ``If-Unmodified-Since = <timestamp>``)
#. If response is ``304 Not modified``, done → up to date, nothing to do.
#. If no ``Next-Page`` response header, done → store ``ETag`` response header valuè for next
   synchronization.
#. If ``Next-Page`` response header is present → store the ``ETag`` response header value into a variable ``timestamp``
   and go on to it (it's an url) using a ``If-Match: <timestamp>`` request header.
#. If response is ``200 OK`` → repeat previous step.
#. If response is ``412 Precondition Failed``, some changes occured since the last
   page → Store the ``ETag``response header into ``before``
#. Fetch and handle the changes using ``GET collections?_since=<timestamp>&_before=<before>``,
   and store the ``ETag``response header in to ``timestamp``
#. Go back to step 5 (follow the ``Next-Page``)


Apply changes
=============

Applying remote changes to the local database consists in adding new records,
updating changed records and remove deleted records.

From the client perspective, *Kinto* does not distinguish creations from updates.
In the *polling for changes* response, created records are simply the records
unknown by the client (using ``id`` field).

If the records to be updated or deleted had also been modified locally then
the developper must choose a relevant strategy. For example, merge fields or
ignore deletion.


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
record exists on the server with this id.

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

The **current implementation of reference** for offline-first records synchronization is
:rtd:`Kinto.js <kintojs>`_.


Before that, some other clients were implemented in the context of the
*ReadingList* project, such as `RL Web client`_ (React.js), `Android RL sync`_ (Java) or `Firefox RL client`_ (asm.js).

.. _RL Web client: https://github.com/n1k0/readinglist-client/
.. _Android RL Sync: https://hg.mozilla.org/releases/mozilla-beta/file/default/mobile/android/base/reading/
.. _Firefox RL client: https://hg.mozilla.org/releases/mozilla-aurora/file/default/browser/components/readinglist



.. [#]  After generating **1 billion** UUIDs **every second** for the next **100 years**,
        the probability of creating just **one duplicate** would
        be about **50%**.
        `Source <https://en.wikipedia.org/wiki/Universally_unique_identifier#Random_UUID_probability_of_duplicates>`_

