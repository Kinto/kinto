.. _notifications:

Notifications
#############

Knowing some records have been modified in a resource is very
useful to integrate a Cliquet-based application with other services.

For example, a search service that gets notified everytime something
has changed, can continuously update its indexes.

Cliquet leverages Pyramid's built-in event system and produces
a :class:`cliquet.events.ResourceChanged` event everytime a record in a
:ref:`resource` has been modified.

Event listeners can then pick up those events and act upon them.

.. code-block:: python

    from cliquet.events import ResourceChanged


    def on_resource_changed(event):
        resource_name = event.payload['resource_name']
        action = event.payload['action']

        if resource_name == 'article' and action == 'create':
            start_download(event.payload['article_id'])

    config.add_subscriber(on_resource_changed, ResourceChanged)


The :class:`cliquet.events.ResourceChanged` event contains a ``payload`` attribute with
the following information:

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

Example, when deleting a collection:

::

    >>> event.impacted_records
    [{'old': {'deleted': True, 'last_modified': 1447240896769, 'id': u'a1f4af60-ddf5-4c49-933f-4cfeff18ad07'}},
     {'old': {'deleted': True, 'last_modified': 1447240896770, 'id': u'7a6916aa-0ea1-42a7-9741-c24fe13cb70b'}}]


Event listeners
---------------

It is possible for an application or a plugin to listen to events and execute
some code. Triggered code on events is synchronously called when a request is handled.

*Cliquet* offers custom listeners that can be activated through configuration,
so that every Cliquet-based application can benefit from **pluggable listeners**
without using `config.add_event_subscriber()` explicitely.

Currently, a simple built-in listener is available, that just delivers the
events into a Redis queue, allowing asynchronous event handling:

.. autoclass:: cliquet.listeners.redis.Listener

To activate it, look at :ref:`the dedicated configuration <configuring-notifications>`.

Implementing a custom listener consists on implementing the following
interface:

.. autoclass:: cliquet.listeners.ListenerBase
    :members: __call__