.. _notifications:

Notifications
#############

Knowing collection has been modified is very
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

        if resource_name == 'user' and action == 'create':
            send_welcome_email(event.payload['user_id'])

    config.add_subscriber(on_resource_changed, ResourceChanged)


The :class:`cliquet.events.ResourceChanged` event contains a ``payload`` attribute with
the following information:

- **timestamp**: the time of the event
- **action**: what happened. 'create', 'update' or 'delete'
- **uri**: the uri of the impacted resource
- **user_id**: the authenticated user id
- **resource_name**: the name of the impacted resouce (e.g. 'mushroom', 'bucket',
  etc.)
- **<resource_name>_id**: id of the impacted record
- **<match-dict value>**: every matchdict values of the URL pattern


Event listeners
---------------

It is possible for an application or a plugin to listen to the events and execute
some code. In this case, the notifications are synchronous.

In addition to this low-level events handling, *Cliquet* provides some generic
listeners that are pluggable from configuration.

Currently, a simple built-in listener is available, that just consists in delivering the
events into a Redis queue, allowing asynchronous event handling:

.. autoclass:: cliquet.listeners.redis.Listener

To activate it, look at :ref:`the dedicated configuration <configuring-notifications>`.

Implementing a custom listener consists on implementing the following
interface:

.. autoclass:: cliquet.listeners.ListenerBase
    :members: __call__