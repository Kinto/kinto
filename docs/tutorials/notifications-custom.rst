.. _tutorial-notifications-custom-code:

How to run custom code on notifications?
========================================

Kinto is able to execute some custom code when a particular event occurs.
For example, when a record is created or updated in a particular collection.

Kinto uses the same thread to trigger notifications on events, so any custom
code that is executed through a notification will block the incoming
request until it's done.

This design is useful when we want to ensure that something is done on the
server before we send back the result to the client, and within the database
transaction. But it's usually preferrable to run the notifications asynchronously.

For the latter, the simplest way to run our custom code asynchronously
is to use separate process workers that are notified via a job queue.

This tutorial presents the basic steps to run code both ways:

* synchronously in Python;
* asynchronously using a Redis queue, consumed via any third-party application.



Run synchronous code
--------------------

In this example, we will track the creation of new buckets.


Implement a listener
''''''''''''''''''''

Create a file :file:`tracker.py` with the following scaffold:

.. code-block:: python

    from kinto.core.listeners import ListenerBase

    class Listener(ListenerBase):
        def __call__(self, event):
            print(event.payload)

    def load_from_config(config, prefix=''):
        return Listener()

Now, every time a new event occurs, we create a record in a tracker collection.

.. code-block:: python
    :emphasize-lines: 5-7

    from kinto.core.listeners import ListenerBase

    class Listener(ListenerBase):
        def __call__(self, event):
            backend = event.request.registry.storage
            userid = event.request.prefixed_userid
            backend.create(obj={'userid': userid}, resource_name='tracker')

    def load_from_config(config, prefix=''):
        return Listener()

In order to keep advantage of what we've just tracked and show it into the
response:

.. code-block:: python
    :emphasize-lines: 1-5,13-19,22

    from pyramid.events import NewRequest, NewResponse

    from kinto.core import utils as core_utils
    from kinto.core.listeners import ListenerBase
    from kinto.core.storage import Filter

    class Listener(ListenerBase):
        def __call__(self, event):
            backend = event.request.registry.storage
            userid = event.request.prefixed_userid
            backend.create(obj={'userid': userid}, resource_name='tracker')

    def count_created_buckets(event):
        userid = event.request.prefixed_userid
        if userid:
            backend = event.request.registry.storage
            filters = [Filter('userid', userid, core_utils.COMPARISON.EQ)]
            _, count = backend.get_all(resource_name='tracker', filters=filters)
            event.response.headers['Buckets-Created'] = str(count)

    def load_from_config(config, prefix=''):
        config.add_subscriber(count_created_buckets, NewResponse)
        return Listener()


Add it to Python path
'''''''''''''''''''''

For the simplicity in this tutorial, we will just alter the ``PYTHONPATH`` system
environment variable. Specify the path to the folder containing the :file:`tracker.py`:

::

    $ export PYTHONPATH="/path/to/folder:${PYTHONPATH}"


In order to test that it works, simply try to import it from a ``python`` script:

.. code-block:: shell
    :emphasize-lines: 5

    $ python
    Python 2.7.9 (default, Apr  2 2015, 15:33:21)
    [GCC 4.9.2] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import tracker
    >>>


Enable in configuration
'''''''''''''''''''''''

:ref:`As explained in the settings section <configuring-notifications>`, just
enable a new listener pointing to your python module:

.. code-block:: ini

    kinto.event_listeners = tracker

    kinto.event_listeners.tracker.use = tracker
    kinto.event_listeners.tracker.actions = create
    kinto.event_listeners.tracker.resources = bucket

Kinto should load the listeners without errors:

.. code-block:: shell
    :emphasize-lines: 3

    $ kinto start
    Starting subprocess with file monitor
    2016-01-21 16:21:59,941 INFO  [kinto.core.initialization][MainThread] Setting up 'tracker' listener


Test it
'''''''

Create a bucket (using `HTTPie <http://httpie.org>`_):

.. code-block:: shell

    $ http --auth alice:s3cr3t --verbose PUT http://localhost:8888/v1/buckets/bid1
    $ http --auth alice:s3cr3t --verbose PUT http://localhost:8888/v1/buckets/bid2

Now, every response has a ``Buckets-Created`` header:

.. code-block:: shell
    :emphasize-lines: 6

    $ http --auth alice:s3cr3t --verbose GET http://localhost:8888/v1/

    HTTP/1.1 200 OK
    Content-Length: 66
    Content-Type: application/json
    Buckets-Created: 2
    ...

It worked!



Run asynchronous code
---------------------

.. note::

   You will need to install ``kinto-redis`` to use this listener.

In this part, we will take advantage of the built-in listener that delivers the events
into a Redis queue. Separate scripts, also as known as “workers”, then consume
the queue to execute custom asynchronous code.


Run Redis
'''''''''

Redis is available in most Linux distributions or Mac OS brew. Using Docker it
is also very easy to run a server on ``localhost:6379``:

::

    $ sudo docker run -p 6379:6379 redis


Setup Kinto queue
'''''''''''''''''

In configuration, we setup the listener to post the message to a queue named
``eventqueue``:

.. code-block:: ini

    kinto.event_listeners = redis

    kinto.event_listeners.redis.use = kinto_redis.listeners
    kinto.event_listeners.redis.url = redis://localhost:6379/0
    kinto.event_listeners.redis.pool_size = 5
    kinto.event_listeners.redis.listname = eventqueue

Kinto should load the listeners without errors:

.. code-block:: shell
    :emphasize-lines: 3

    $ kinto start
    Starting subprocess with file monitor
    2016-01-21 16:21:59,941 INFO  [kinto.core.initialization][MainThread] Setting up 'redis' listener


Run worker(s)
'''''''''''''

The simplest worker would look like that:

.. code-block:: python

    import time
    import json

    import redis

    def main():
        db = redis.Redis()
        # Run indefinitely.
        while True:
            # Wait for new messages (blocking).
            key, payload = db.blpop("eventqueue")
            # Decode JSON payload.
            message = json.loads(payload)
            # Simulate long task.
            time.sleep(2)
            print(message)

    if __name__ == "__main__":
        main()

Run it in a separate terminal: ::

    $ python worker.py


Test it!
''''''''

Create a record (using `HTTPie <http://httpie.org>`_):

.. code-block:: shell

    $ echo '{"data": {"note": "kinto"}}' | \
        http --auth alice:s3cr3t --verbose POST http://localhost:8888/v1/buckets/default/collections/notes/records

The server response is returned immediately.

But 2 seconds later, look at the worker output:

::

    {'resource_name': 'record', 'user_id': 'account:alice', 'timestamp': 1453459942672, 'uri': '/buckets/c8c94a74-5bf6-9fb0-5b72-b0777da6718e/collections/assets/records', 'bucket_id': 'c8c94a74-5bf6-9fb0-5b72-b0777da6718e', 'action': 'create', 'collection_id': 'assets'}

It worked!
