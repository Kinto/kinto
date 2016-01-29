.. _tutorial-notifications-websockets:

How to setup push notifications using WebSockets?
=================================================

This tutorial presents the basic steps to implement live synchronisation of
records between clients.

Currently, it relies on a plugin that sends events through WebSockets using `Pusher.com <https://pusher.com>`_.

.. note::

    Another plugin is under construction for WebPush: :github:`Kinto/kinto-webpush`


Setup a Pusher account
----------------------

* Go to `Pusher.com <https://pusher.com/>`_
* Create a new app
* Get your app credentials (``app_id``, ``key``, ``secret``)


Configure Kinto
---------------

The plugin is already installed in the Docker image. But if you run the
Python version, first install it:

.. code-block:: bash

    $ pip install cliquet-pusher


:ref:`As explained in the settings section <configuring-notifications>`,
add these lines to setup a listener, and be notified of record updates per collection:

.. code-block:: ini

    kinto.includes = cliquet_pusher

    kinto.event_listeners = pusher
    kinto.event_listeners.pusher.use = cliquet_pusher.listener
    kinto.event_listeners.pusher.resources = record
    kinto.event_listeners.pusher.channel = {bucket_id}-{collection_id}-{resource_name}

    pusher.app_id = <pusher-app-id>
    pusher.key = <pusher-key>
    pusher.secret = <pusher-secret>

And (re)start Kinto with this new configuration.


Test Pusher events
------------------

Now that *Kinto* runs locally and is configured to send events to *Pusher*, you
should be able to see them in the *Debug Console* of your *Pusher dashboard*.

For example, create an arbitrary record with `httpie <http://httpie.org>`_

.. code-block:: shell

    $ echo '{"data":{"name":"bob"}}' | \
        http POST http://localhost:8888/v1/buckets/default/collections/tasks/records --auth token:alice-token

This created a record, and you should see the generated event in the dashboard.


Consume events in JavaScript
----------------------------

The Pusher documentation is full of examples for a variety of languages.
For JavaScript, just add the Pusher library to your page:

.. code-block:: html

    <script src="//js.pusher.com/3.0/pusher.min.js"></script>

And listen to the events:

.. code-block:: javascript

    // Pusher credentials
    var pusher_key = 'your key';

    var pusher = new Pusher(pusher_key, {
      encrypted: true
    });

    // The channel name. It should match the setting
    // `kinto.event_listeners.pusher.channel`
    var channelName = bucket_id + '-' + collection_id + '-record';

    var channel = pusher.subscribe(channelName);
    channel.bind('create', function(data) {
      console.log("New records created", data);
    });
    channel.bind('update', function(data) {
      console.log("Records updated", data);
    });
    channel.bind('delete', function(data) {
      console.log("Records deleted", data);
    });


Demos
-----

We've made several demos with live sync.

For example, open these in several browser windows and observe the
live changes:

* `Online map <https://leplatrem.github.io/cliquet-pusher/>`_
* `Calendar <https://leplatrem.github.io/cliquet-pusher/>`_

:ref:`More demos are available. <app-examples>`
