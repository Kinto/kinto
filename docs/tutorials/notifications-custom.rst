.. _tutorial-notifications-custom-code:

How to run custom code on notifications?
========================================

Kinto is able to execute some custom code when a particular event occurs.
For example, when a record is created or updated in a particular collection.

Kinto uses the same thread to trigger notifications on events, so any custom
code that is executed through a notification will block the incoming 
request until it's done. 

This design is useful when we want to ensure that something is done on the 
server before we send back the result to the client. But sometimes it's 
preferrable to run the notifications asynchronously.

For the latter, the simplest way to run our custom code asynchronously
is to use separate process workers that are notified via a job queue

This tutorial presents the basic steps to run code both ways:

* synchronously in Python;
* asynchronously using a Redis queue, consumed via any third-party application.

    

Run synchronous code
--------------------

In this example, we will send an email to an administrator every time
a new bucket is created.

To run this in production, we would rely on a local email server acting as a relay
in order to avoid bottlenecks. Or use the asynchronous approach otherwise.


Implement a listener
''''''''''''''''''''

Create a file :file:`kinto_email.py` with the following scaffold:

.. code-block:: python

    from kinto.core.listeners import ListenerBase

    class Listener(ListenerBase):
        def __call__(self, event):
            print(event.payload)

    def load_from_config(config, prefix=''):
        return Listener()

Then, we will read the email server configuration and recipients from
the settings.


.. code-block:: python
    :emphasize-lines: 2,5-11,17-26

    from kinto.core.listeners import ListenerBase
    from pyramid.settings import aslist, asbool

    class Listener(ListenerBase):
        def __init__(self, server, tls, username, password, sender, recipients):
            self.server = server
            self.tls = tls
            self.username = username
            self.password = password
            self.sender = sender
            self.recipients = recipients

        def __call__(self, event):
            print(event.payload)

    def load_from_config(config, prefix=''):
        settings = config.get_settings()

        server = settings[prefix + 'server']
        tls = asbool(settings[prefix + 'tls'])
        username = settings[prefix + 'username']
        password = settings[prefix + 'password']
        sender = settings[prefix + 'from']
        recipients = aslist(settings[prefix + 'recipients'])

        return Listener(server, tls, username, password, sender, recipients)


Now, every time a new event occurs, we send an email:


.. code-block:: python
    :emphasize-lines: 1,2,17-32

    import smtplib
    from email.mime.text import MIMEText

    from kinto.core.listeners import ListenerBase
    from pyramid.settings import aslist, asbool

    class Listener(ListenerBase):
        def __init__(self, server, tls, username, password, sender, recipients):
            self.server = server
            self.tls = tls
            self.username = username
            self.password = password
            self.sender = sender
            self.recipients = recipients

        def __call__(self, event):
            subject = "%s %sd" % (event.payload['resource_name'],
                                  event.payload['action'])
            text = "User id: %s" % event.request.prefixed_userid

            message = MIMEText(text)
            message['Subject'] = subject
            message['From'] = self.sender
            message['To'] = ", ".join(self.recipients)

            server = smtplib.SMTP(self.server)
            if self.tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(self.sender, self.recipients, message.as_string())
            server.quit()

    def load_from_config(config, prefix=''):
        settings = config.get_settings()

        server = settings[prefix + 'server']
        tls = asbool(settings[prefix + 'tls'])
        username = settings[prefix + 'username']
        password = settings[prefix + 'password']
        sender = settings[prefix + 'from']
        recipients = aslist(settings[prefix + 'recipients'])

        return Listener(server, tls, username, password, sender, recipients)


Add it to Python path
'''''''''''''''''''''

For the simplicity in this tutorial, we will just alter the ``PYTHONPATH`` system
environment variable. Specify the path to the folder containing the :file:`kinto_email.py`:

::

    $ export PYTHONPATH="/path/to/folder:${PYTHONPATH}"


In order to test that it works, simply try to import it from a ``python`` script:

.. code-block:: shell
    :emphasize-lines: 5

    $ python
    Python 2.7.9 (default, Apr  2 2015, 15:33:21)
    [GCC 4.9.2] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import kinto_email
    >>>


Enable in configuration
'''''''''''''''''''''''

:ref:`As explained in the settings section <configuring-notifications>`, just
enable a new listener pointing to your python module:

.. code-block:: ini

    kinto.event_listeners = send_email

    kinto.event_listeners.send_email.use = kinto_email
    kinto.event_listeners.send_email.server = localhost:1025
    kinto.event_listeners.send_email.tls = false
    kinto.event_listeners.send_email.username =
    kinto.event_listeners.send_email.password =
    kinto.event_listeners.send_email.from = postmaster@localhost
    kinto.event_listeners.send_email.recipients = kinto@yopmail.com

Kinto should load the listeners without errors:

.. code-block:: shell
    :emphasize-lines: 3

    $ kinto start
    Starting subprocess with file monitor
    2016-01-21 16:21:59,941 INFO  [kinto.core.initialization][MainThread] Setting up 'send_email' listener


Test it
'''''''

In a separate terminal, run a fake SMTP server on ``localhost:1025``:

::

    $ python -m smtpd -n -c DebuggingServer localhost:1025

Create a record (using `HTTPie <http://httpie.org>`_):

.. code-block:: shell

    $ echo '{"data": {"note": "kinto"}}' | \
        http --auth token:alice-token --verbose POST http://localhost:8888/v1/buckets/default/collections/notes/records

And observe the fake server output:

::

    ---------- MESSAGE FOLLOWS ----------
    Content-Type: text/plain; charset="us-ascii"
    MIME-Version: 1.0
    Content-Transfer-Encoding: 7bit
    Subject: record created
    From: postmaster@localhost
    To: kinto@yopmail.com
    X-Peer: 127.0.0.1

    User id: basicauth:fea1e21d339299506d89e60f048cefd5b424ea641ba48267c35a4ce921439fa4
    ------------ END MESSAGE ------------

It worked!



Run asynchronous code
---------------------

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

    kinto.event_listeners.redis.use = kinto.core.listeners.redis
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
        http --auth token:alice-token --verbose POST http://localhost:8888/v1/buckets/default/collections/notes/records

The server response is returned immediately.

But 2 seconds later, look at the worker output:

::

    {u'resource_name': u'record', u'user_id': u'basicauth:fea1e21d339299506d89e60f048cefd5b424ea641ba48267c35a4ce921439fa4', u'timestamp': 1453459942672, u'uri': u'/buckets/c8c94a74-5bf6-9fb0-5b72-b0777da6718e/collections/assets/records', u'bucket_id': u'c8c94a74-5bf6-9fb0-5b72-b0777da6718e', u'action': u'create', u'collection_id': u'assets'}

It worked!
