.. _notifications:

Notifications
#############

Knowing some records have been modified in a resource is very
useful to integrate a Kinto-Core-based application with other services.

For example, a search service that gets notified everytime something
has changed, can continuously update its index.

Kinto-Core leverages Pyramid's built-in event system and produces the following
events:

- :class:`kinto.core.events.ResourceRead`: a read operation occured on the resource.

- :class:`kinto.core.events.ResourceChanged`: a resource **is being changed**. This
  event occurs synchronously within the transaction and within the
  request/response cycle. Commit is not yet done and rollback is still possible.

  Subscribers of this event are likely to perform database operations,
  alter the server response, or cancel the transaction (by raising an HTTP
  exception for example).
  Do not subscribe to this event for operations that will not be rolled-back
  automatically.

- :class:`kinto.core.events.AfterResourceChanged`: a resource **was changed** and
  **committed**.

  Subscribers of this event can fail, errors are swallowed and logged. The
  final transaction result (or response) cannot be altered.

  Subscribers of this event are likely to perform irreversible actions that
  requires data to be committed in database
  (like sending messages, deleting files on disk, or run asynchronous tasks).


Event subscribers can then pick up those events and act upon them.

.. code-block:: python

    from kinto.core.events import AfterResourceChanged


    def on_resource_changed(event):
        for change in event.impacted_records:
            start_download(change['new']['url'])

    config.add_subscriber(on_resource_changed, AfterResourceChanged)


Transactions
------------

Only one event is sent per transaction, per resource and per action.

In other words, if every requests of a :ref:`batch requests <batch>`
perform the same action on the same resource, only one event will be sent.

The ``AfterResourceChanged`` is sent only if the transaction was comitted
successfully.

It is possible to cancel the current transaction by raising an HTTP Exception
from a ``ResourceChanged`` event. For example:

.. code-block:: python

    from kinto.core.events import ResourceChanged
    from pyramid import httpexceptions

    def check_quota(event):
         max_quota = event.request.registry.settings['max_quota']
         if check_quota(event, max_quota):
            raise httpexceptions.HTTPInsufficientStorage()

    config.add_subscriber(check_quota, ResourceChanged)


Filtering
---------

It is possible to filter events based on its action or the name of the resource where
it occured.

For example:

.. code-block:: python

    from kinto.core.events import ResourceChanged, ACTIONS

    config.add_subscriber(on_mushroom_changed, ResourceChanged, for_resources=('mushroom',))
    config.add_subscriber(on_record_deleted, ResourceChanged, for_actions=(ACTIONS.DELETE,))


Payload
-------

The :class:`kinto.core.events.ResourceChanged` and :class:`kinto.core.events.AfterResourceChanged`
events contain a ``payload`` attribute with the following information:

- **timestamp**: the time of the event
- **action**: what happened. 'create', 'update' or 'delete'
- **uri**: the uri of the impacted resource
- **user_id**: the authenticated user id
- **resource_name**: the name of the impacted resouce (e.g. 'article', 'bookmark', bucket',
  'group' etc.)
- **<resource_name>_id**: id of the impacted record
- **<matchdict value>**: every value matched by each URL pattern name (see
  `Pyramid request matchdict <http://docs.pylonsproject.org/projects/pyramid/en/latest/glossary.html#term-matchdict>`_)

And provides the list of affected records in the ``impacted_records`` attribute.
This list contains dictionnaries with ``new`` and ``old`` keys. For creation
events, only ``new`` is provided. For deletion events, only ``old`` is provided.
This also allows listeners to react on particular field change or handle *diff*
between versions.

Example, when deleting a collection with two records:

::

    >>> event.impacted_records
    [{'old': {'deleted': True, 'last_modified': 1447240896769, 'id': u'a1f4af60-ddf5-4c49-933f-4cfeff18ad07'}},
     {'old': {'deleted': True, 'last_modified': 1447240896770, 'id': u'7a6916aa-0ea1-42a7-9741-c24fe13cb70b'}}]


Event listeners
---------------

It is possible for an application or a plugin to listen to events and execute
some code. Triggered code on events is synchronously called when a request is handled.

*Kinto-Core* offers custom listeners that can be activated through configuration,
so that every Kinto-Core-based application can benefit from **pluggable listeners**
without using `config.add_event_subscriber()` explicitely.

Currently, a simple built-in listener is available, that just delivers the
events into a Redis queue, allowing asynchronous event handling:

.. autoclass:: kinto.core.listeners.redis.Listener

To activate it, look at :ref:`the dedicated configuration <configuring-notifications>`.

Implementing a custom listener consists on implementing the following
interface:

.. autoclass:: kinto.core.listeners.ListenerBase
    :members: __call__
