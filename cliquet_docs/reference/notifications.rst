.. _notifications:

Notifications
#############

Knowing when a bucket or a collection has been modified is very
useful to integrate a Cliquet-based application with other services.

For example, a search service that gets notified everytime something
has changed, can continuously update its indexes.

Cliquet leverages Pyramid's built-in event system and produces
a :class:`cliquet.events.ResourceChanged` event everytime a resource has
been modified. Event listeners can then pick up those events and act upon them.

The :class:`cliquet.events.ResourceChanged` event contains a payload with
the following information:

- **timestamp**: the time of the event
- **action**: what happened. 'create', 'update' or 'delete'
- **uri**: the uri of the impacted resource
- **user_id**: the authenticated user id
- **resource_name**: the name of the impacted resouce. 'bucket', 'collection'
  or 'record'
- **<resource_name>_id**: id of the impacted resouce

We're planning to add a few generic event listeners in Cliquet as
we need them. The first one we're adding is :class:`cliquet.listeners.redis.RedisListener`,
a Redis-based listener that simply pushes the events payload in a Redis
list as they happen.

To activate it, look at :ref:`the dedicated configuration <configuring-events>`.
