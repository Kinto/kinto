.. _settings:

Settings
########

.. image:: /images/overview-features.png
    :align: center

If you are looking for installation instructions, please refer to :ref:`install`.

Kinto is built to be highly configurable. As a result, the related
configuration can be verbose, but don't worry, all configuration flags are
listed below.

.. note::

    In order to ease deployment or testing strategies, *Kinto* reads settings
    from environment variables, in addition to ``.ini`` files.

    The environment variables are exactly the same as the settings, but they
    are capitalised and ``.`` are replaced by ``_``.

    For example, ``kinto.storage_backend`` is read from environment variable
    ``KINTO_STORAGE_BACKEND`` if defined.

    All settings are read first from the environment variables, then from
    application ``.ini``, and finally from internal defaults.


.. _configuration-features:

Feature settings
================

+-------------------------------------------------+--------------+--------------------------------------------------------------------------+
| Setting name                                    | Default      | What does it do?                                                         |
+=================================================+==============+==========================================================================+
| kinto.readonly                                  | ``False``    | If set to true, the whole service will reject every write operation.     |
|                                                 |              | Note that with this option, the ``default`` bucket cannot be used and    |
|                                                 |              | request will be rejected with a ``405 Method Not Allowed`` error         |
|                                                 |              | response.                                                                |
+-------------------------------------------------+--------------+--------------------------------------------------------------------------+
| kinto.batch_max_requests                        | ``25``       | The maximum number of requests that can be sent to the batch endpoint.   |
+-------------------------------------------------+--------------+--------------------------------------------------------------------------+
| kinto.paginate_by                               | ``None``     | The maximum number of items to include on a response before enabling     |
|                                                 |              | pagination. If set to ``None``, no pagination will be used.              |
|                                                 |              | It is recommended to set-up pagination if the server is under high load. |
|                                                 |              | If not defined, a collection response cannot contain                     |
|                                                 |              | more elements than defined by the                                        |
|                                                 |              | ``kinto.storage_max_fetch_size`` setting.                                |
+-------------------------------------------------+--------------+--------------------------------------------------------------------------+
| kinto.id_generator                              | ``UUID4``    | The Python *dotted* location of the generator class that should be used  |
|                                                 |              | to generate identifiers on a POST on a records endpoint.                 |
+-------------------------------------------------+--------------+--------------------------------------------------------------------------+
| kinto.experimental_collection_schema_validation | ``False``    | *Experimental*: Allow definition of JSON schema at the collection level, |
|                                                 |              | in order to :ref:`validate submitted records <collection-json-schema>`.  |
|                                                 |              | It is marked as experimental because the API might subjet to changes.    |
+-------------------------------------------------+--------------+--------------------------------------------------------------------------+
| kinto.trailing_slash_redirect_enabled           | ``True``     | Try to redirect resources removing slash or adding it for the root URL   |
|                                                 |              | endpoint: ``/v1`` redirects to ``/v1/`` and ``/buckets/default/``        |
|                                                 |              | to ``/buckets/default``. No redirections are made when turned off.       |
+-------------------------------------------------+--------------+--------------------------------------------------------------------------+


.. _configuration-backends:

Backends
========

Kinto relies on three types of backends: storage, cache and permission. The
settings names have a different prefix for each.

For each of them, the supported services are currently PostgreSQL, Redis, and Memory.

Storage
:::::::

+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| Setting name                 | Default                       | What does it do?                                                         |
+==============================+===============================+==========================================================================+
| kinto.storage_backend        | ``kinto.core.storage.memory`` | The Python *dotted* location of the storage backend to use.              |
|                              |                               |                                                                          |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_url            | ``''``                        | The URL to use to authenticate to the storage backend. e.g.              |
|                              |                               | ``redis://localhost:6378/1`` or ``postgres://user:pass@database/db``     |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_max_fetch_size | ``10000``                     | The maximum number of items that can be returned by one request to the   |
|                              |                               | storage backend. If no pagination is enabled, this is the maximum number |
|                              |                               | of items that can be stored in a collection (otherwise some of them      |
|                              |                               | won't be returned). With pagination enabled, this limitation doesn't     |
|                              |                               | apply.                                                                   |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_pool_size      | ``25``                        | The size of the pool of connections to use for the storage backend.      |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_max_overflow   | ``5``                         | Number of connections that can be opened beyond pool size.               |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_pool_recycle   | ``-1``                        | Recycle connections after the given number of seconds has passed.        |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_pool_timeout   | ``30``                        | Number of seconds to wait before giving up on getting a connection from  |
|                              |                               | the pool.                                                                |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+
| kinto.storage_max_backlog    | ``-1``                        | Number of threads that can be in the queue waiting for a connection.     |
+------------------------------+-------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    kinto.storage_backend = kinto.core.storage.redis
    kinto.storage_url = redis://localhost:6379/1

    # Safety limit while fetching from storage
    # kinto.storage_max_fetch_size = 10000

    # Control number of pooled connections
    # kinto.storage_pool_size = 50


Cache
:::::

+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| Setting name             | Default                     | What does it do?                                                             |
+==========================+=============================+==============================================================================+
| kinto.cache_backend      | ``kinto.core.cache.memory`` | The Python *dotted* location of the cache backend to use.                    |
|                          |                             |                                                                              |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_url          | ``''``                      | The URL to use to authenticate to the cache backend. e.g.                    |
|                          |                             | ``redis://localhost:6378/1`` or ``postgres://user:pass@database/db``         |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_prefix       | ``''``                      | A prefix added to each key. Useful when having multiple Kinto using the same |
|                          |                             | cache database.                                                              |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_pool_size    | ``25``                      | The size of the pool of connections to use for the cache backend.            |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_max_overflow | ``5``                       | Number of connections that can be opened beyond pool size.                   |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_pool_recycle | ``-1``                      | Recycle connections after the given number of seconds has passed.            |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_pool_timeout | ``30``                      | Number of seconds to wait before giving up on getting a connection from      |
|                          |                             | the pool.                                                                    |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+
| kinto.cache_max_backlog  | ``-1``                      | Number of threads that can be in the queue waiting for a connection.         |
+--------------------------+-----------------------------+------------------------------------------------------------------------------+

.. code-block:: ini

    kinto.cache_backend = kinto.core.cache.redis
    kinto.cache_url = redis://localhost:6379/0

    # Control number of pooled connections
    # kinto.cache_pool_size = 50

Permissions
:::::::::::

+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| Setting name                   | Default                          | What does it do?                                                         |
+================================+==================================+==========================================================================+
| kinto.permission_backend       | ``kinto.core.permission.memory`` | The Python *dotted* location of the permission backend to use.           |
|                                |                                  |                                                                          |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_url           | ``''``                           | The URL to use to authenticate to the permission backend. e.g.           |
|                                |                                  | ``redis://localhost:6379/1``                                             |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_pool_size     | ``25``                           | The size of the pool of connections to use for the permission backend.   |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_max_overflow  | ``5``                            | Number of connections that can be opened beyond pool size.               |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_pool_recycle  | ``-1``                           | Recycle connections after the given number of seconds has passed.        |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_pool_timeout  | ``30``                           | Number of seconds to wait before giving up on getting a connection from  |
|                                |                                  | the pool.                                                                |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+
| kinto.permission_max_backlog   | ``-1``                           | Number of threads that can be in the queue waiting for a connection.     |
+--------------------------------+----------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    kinto.permission_backend = kinto.core.permission.redis
    kinto.permission_url = redis://localhost:6379/1

    # Control number of pooled connections
    # kinto.permission_pool_size = 50

Bypass permissions with configuration
:::::::::::::::::::::::::::::::::::::

Permissions are usually retrieved from the permission backend. However, it is
also possible to configure them from settings, and it will **bypass** the
permission backend.

For example, for a resource named "bucket", the following setting will enable
authenticated people to create bucket records:

.. code-block:: ini

    kinto.bucket_create_principals = system.Authenticated

The format of these permission settings is
``<resource_name>_<permission>_principals = comma,separated,principals``.


Scheme, host, and port
======================

By default, Kinto relies on WSGI for underlying details like host, port, or
request scheme. Tuning these settings may be necessary when the application
runs behind proxies or load balancers, but most implementations
(such as uWSGI) provide adequate values automatically.

That said, if ever these items need to be controlled at the application layer,
the following settings are available:

Check the behaviour of the server with the ``url`` value returned in :ref:`the
hello view <api-utilities>`.

+-------------------+----------+--------------------------------------------------------------------------+
| Setting name      | Default  | What does it do?                                                         |
+===================+==========+==========================================================================+
| kinto.http_host   | ``None`` | The HTTP Host used by Kinto to refer to itself. If set to `None`, the    |
|                   |          | HTTP host is read from HTTP headers or WSGI environment.                 |
+-------------------+----------+--------------------------------------------------------------------------+
| kinto.http_scheme | ``None`` | The HTTP scheme used by Kinto to refer to itself. If set to `None`, the  |
|                   |          | HTTP scheme is read from the HTTP headers or WSGI environment.           |
+-------------------+----------+--------------------------------------------------------------------------+

.. code-block :: ini

   # kinto.http_scheme = https
   # kinto.http_host = production.server.com:7777


Logging and Monitoring
======================

+------------------------+----------------------------------------+--------------------------------------------------------------------------+
| Setting name           | Default                                | What does it do?                                                         |
+========================+========================================+==========================================================================+
| kinto.logging_renderer | ``kinto.core.logs.ClassicLogRenderer`` | The Python *dotted* location of the renderer class that should be used   |
|                        |                                        | to render the logs to the standard output.                               |
+------------------------+----------------------------------------+--------------------------------------------------------------------------+
| kinto.statsd_prefix    | ``kinto``                              | The prefix to use when sending data to statsd.                           |
+------------------------+----------------------------------------+--------------------------------------------------------------------------+
| kinto.statsd_url       | ``None``                               | The URL to use to connect to the statsd host. e.g.                       |
|                        |                                        | ``udp://localhost:8125``                                                 |
+------------------------+----------------------------------------+--------------------------------------------------------------------------+

Logging with Heka
:::::::::::::::::

Heka is an open source stream processing software system developed by Mozilla.
Heka is a "Swiss Army Knife" type tool for data processing, and is useful for
a wide variety of different tasks.

For more information, see https://hekad.readthedocs.io/

Heka logging format can be enabled using:

.. code-block:: ini

    kinto.logging_renderer = kinto.core.logs.MozillaHekaRenderer


With the following configuration, all logs are redirected to standard output
(See `12factor app <http://12factor.net/logs>`_):

.. code-block:: ini

    [loggers]
    keys = root

    [handlers]
    keys = console

    [formatters]
    keys = heka

    [logger_root]
    level = INFO
    handlers = console
    formatter = heka

    [handler_console]
    class = StreamHandler
    args = (sys.stdout,)
    level = NOTSET

    [formatter_heka]
    format = %(message)s


Handling exceptions with Sentry
:::::::::::::::::::::::::::::::

Requires the ``raven`` package.

Sentry logging can be enabled `as explained in official documentation
<http://raven.readthedocs.io/en/latest/integrations/pyramid.html#logger-setup>`_.

.. note::

    The application sends an *INFO* message on startup (mainly for setup check).


Monitoring with StatsD
::::::::::::::::::::::

Requires the ``statsd`` package.

StatsD metrics can be enabled (disabled by default):

.. code-block:: ini

    kinto.statsd_url = udp://localhost:8125
    # kinto.statsd_prefix = kinto-prod


Monitoring with New Relic
:::::::::::::::::::::::::

Requires the ``newrelic`` package.

+-----------------------+----------+--------------------------------------------------------------------------+
| Setting name          | Default  | What does it do?                                                         |
+=======================+==========+==========================================================================+
| kinto.newrelic_config | ``None`` | Location of the newrelic configuration file.                             |
+-----------------------+----------+--------------------------------------------------------------------------+
| kinto.newrelic_env    | ``dev``  | The environment the server runs into                                     |
+-----------------------+----------+--------------------------------------------------------------------------+

New Relic can be enabled (disabled by default):

.. code-block:: ini

    kinto.newrelic_config = /location/of/newrelic.ini
    kinto.newrelic_env = prod


.. _configuration-authentication:

Authentication
==============

By default, *Kinto* relies on *Basic Auth* to authenticate users.

User registration is not necessary. A unique user idenfier will be created
for each ``username:password`` pair.

*Kinto* is compatible with any third-party authentication service.

+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+
| Setting name                   | Default                                               | What does it do?                                                         |
+================================+=======================================================+==========================================================================+
| kinto.userid_hmac_secret       | ``''``                                                | The secret used to create the user ID from a ``username:password`` pair. |
|                                |                                                       | This value should be unique to each instance and kept secret.            |
+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+
| multiauth.policies             | ``basicauth``                                         | The list of authentication policies aliases that are enabled.            |
|                                |                                                       | Each alias is configuration using dedicated settings as explained        |
|                                |                                                       | below.                                                                   |
+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+
| multiauth.authorization_policy | ``kinto.authorization.AuthorizationPolicy``           | Python *dotted* path the authorisation policy to use for the permission  |
|                                |                                                       | mecanism.                                                                |
+--------------------------------+-------------------------------------------------------+--------------------------------------------------------------------------+


Authentication setup
::::::::::::::::::::

*Kinto* relies on :github:`pyramid multiauth <mozilla-services/pyramid_multiauth>`
to initialise authentication.

Therefore, any authentication policy can be specified through configuration.

In the following example, Basic Auth, Persona, and IP Auth are all enabled:

.. code-block:: ini

    multiauth.policies = basicauth pyramid_persona ipauth

    multiauth.policy.ipauth.use = pyramid_ipauth.IPAuthentictionPolicy
    multiauth.policy.ipauth.ipaddrs = 192.168.0.*
    multiauth.policy.ipauth.userid = LAN-user
    multiauth.policy.ipauth.principals = trusted

Permission handling and authorisation mechanisms are specified directly via
configuration. This allows for customised solutions ranging from very simple
to highly complex.


Basic Auth
::::::::::

``basicauth`` is enabled via ``multiauth.policies`` by default.

.. code-block:: ini

    multiauth.policies = basicauth

By default an internal *Basic Auth* policy is used, where any `login:password` pair
will be accepted, meaning that no account creation is required.

In order to replace it by another one:

.. code-block:: ini

    multiauth.policies = basicauth
    multiauth.policy.basicauth.use = myproject.authn.BasicAuthPolicy


Custom Authentication
:::::::::::::::::::::

Using the various `Pyramid authentication packages
<https://github.com/ITCase/awesome-pyramid#authentication>`_, it is possible
to plug in any kind of authentication.


Firefox Accounts
::::::::::::::::

Enabling :term:`Firefox Accounts` consists of including ``kinto_fxa`` in
configuration, mentioning ``fxa`` among policies, and providing appropriate
values for OAuth2 client settings.

See :github:`mozilla-services/kinto-fxa`.


.. _configuration-plugins:

Plugins
=======

It is possible to extend the default Kinto behaviors by using "plugins".

The list of plugins to load at startup can be specified in the settings, as a
list of Python modules:

.. code-block:: ini

    kinto.includes = kinto.plugins.default_bucket
                     kinto-attachment
                     custom-myplugin

See also: :ref:`tutorial-write-plugin` for more in-depth informations on how
to create your own plugin.

.. _configuring-notifications:

Notifications
=============

*Kinto* has a notification system, and the event listeners are configured using
the *event_handlers* setting, which takes a list of aliases.

In the example below, the Redis listener is activated and will send events
data in the ``queue`` Redis list.

.. code-block:: ini

    kinto.event_listeners = redis

    kinto.event_listeners.redis.use = kinto.core.listeners.redis
    kinto.event_listeners.redis.url = redis://localhost:6379/0
    kinto.event_listeners.redis.pool_size = 5
    kinto.event_listeners.redis.listname = queue

Filtering
:::::::::

It is possible to filter events by action and/or types of object. By
default actions ``create``, ``update`` and ``delete`` are notified
for every kinds of objects.

.. code-block:: ini

    kinto.event_listeners.redis.actions = create
    kinto.event_listeners.redis.resources = bucket collection

Third-party
:::::::::::

Enabling push notifications to clients consists in enabling an event listener
that will be in charge of forwarding events data to remote clients.

A Kinto plugin was made using the *Pusher* (commercial) service.
See :github:`leplatrem/cliquet-pusher`.


Cross Origin requests (CORS)
============================

Kinto supports `CORS <http://www.w3.org/TR/cors/>`_ out of the box. Use the
`cors_origins` setting to change the list of accepted origins.

+--------------------+---------+--------------------------------------------------------------------------+
| Setting name       | Default | What does it do?                                                         |
+====================+=========+==========================================================================+
| kinto.cors_origins | ``*``   | This List of CORS origins to support on all endpoints. By default allow  |
|                    |         | all cross origin requests.                                               |
+--------------------+---------+--------------------------------------------------------------------------+


.. _configuring-backoff:

Backoff indicators
==================

In order to tell clients to back-off (on heavy load for instance), the
following flags can be used. Read more about this at :ref:`backoff-indicators`.

+---------------------------+----------+--------------------------------------------------------------------------+
| Setting name              | Default  | What does it do?                                                         |
+===========================+==========+==========================================================================+
| kinto.backoff             | ``None`` | The Backoff time to use. If set to `None`, no backoff flag is sent to    |
|                           |          | the clients. If set, provides the client with a number of seconds during |
|                           |          | which it should avoid doing unnecessary requests.                        |
+---------------------------+----------+--------------------------------------------------------------------------+
| kinto.retry_after_seconds | ``30``   | The number of seconds after which the client should issue requests.      |
+---------------------------+----------+--------------------------------------------------------------------------+

.. code-block:: ini

    # kinto.backoff = 10
    kinto.retry_after_seconds = 30

Similarly, the end of service date can be specified by using these settings.

+-------------------+----------+--------------------------------------------------------------------------+
| Setting name      | Default  | What does it do?                                                         |
+===================+==========+==========================================================================+
| kinto.eos         | ``None`` | The End of Service Deprecation date. If the date specified is in the     |
|                   |          | future, an alert will be sent to clients. If it’s in the past, the       |
|                   |          | service will be declared as decomissionned. If set to `None`, no End of  |
|                   |          | Service information will be sent to the client.                          |
+-------------------+----------+--------------------------------------------------------------------------+
| kinto.eos_message | ``None`` | The End of Service message. If set to `None`, no End of Service message  |
|                   |          | will be sent to the clients.                                             |
+-------------------+----------+--------------------------------------------------------------------------+
| kinto.eos_url     | ``None`` | The End of Service information URL.                                      |
+-------------------+----------+--------------------------------------------------------------------------+

.. code-block:: ini

    kinto.eos = 2015-01-22
    kinto.eos_message = "Client is too old"
    kinto.eos_url = http://website/info-shutdown.html


Enabling or disabling endpoints
===============================

Specific resource operations can be disabled.

To do so, a setting key must be defined for the disabled resources endpoints::

    'kinto.{endpoint_type}_{resource_name}_{method}_enabled'

Where:
- **endpoint_type** is either collection or record;
- **resource_name** is the name of the resource (by default, *Kinto* uses the name of the class);
- **method** is the http method (in lower case): For instance ``put``.

For example, to disable the PUT on records for the *Mushrooms* resource, the
following setting should be declared in the ``.ini`` file:

.. code-block:: ini

    # Disable article collection DELETE endpoint
    kinto.collection_article_delete_enabled = false

    # Disable mushroom record PATCH endpoint
    kinto.record_mushroom_patch_enabled = false


Activating the flush endpoint
=============================


The Flush endpoint is used to flush (completely remove) all data from the
database backend. While this can be useful during development, it's too
dangerous to leave on by default, and must therefore be enabled explicitly.

.. code-block :: ini

    kinto.flush_endpoint_enabled = true

Then, issue a `POST` request to the `/__flush__` endpoint to flush all
the data.


.. _configuration-client-caching:

Client caching
==============

In addition to :ref:`per-collection caching <collection-caching>`, it is possible
to add cache control headers for every *Kinto* object.
The client (or cache server or proxy) will use them to cache the collection
records for a certain amount of time, in seconds.

The setting can be set for any kind of object (``bucket``, ``group``, ``collection``, ``record``),
and concerns GET requests (``GET /buckets``, ``GET /buckets/{}/groups``, ``GET /buckets/{}/collections``,
``GET /buckets/{}/collections/{}/records``).

.. code-block:: ini

    # kinto.bucket_cache_expires_seconds = 3600
    # kinto.group_cache_expires_seconds = 3600
    # kinto.collection_cache_expires_seconds = 3600
    kinto.record_cache_expires_seconds = 3600

It can also be specified per bucket or collections for records:

.. code-block:: ini

    kinto.blog_record_cache_expires_seconds = 30
    kinto.blog_articles_record_cache_expires_seconds = 3600

If set to ``0`` then the resource becomes uncacheable (``no-cache``).

.. note::

    In production, :ref:`Nginx can act as a cache-server <production-cache-server>`
    using those client cache control headers.


Project information
===================

+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | Default                                    | What does it do?                                                         |
+=======================================+============================================+==========================================================================+
| kinto.error_info_link                 | ``https://github.com/kinto/kinto/issues/`` | The HTTP link returned when uncaught errors are triggered on the server. |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.project_docs                    | ``http://kinto.readthedocs.io``            | The URL where the documentation of the Kinto instance can be found. Will |
|                                       |                                            | be returned in :ref:`the hello view <api-utilities>`.                    |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.project_version                 | ``''``                                     | The version of the project. Will be returned in :ref:`the hello view     |
|                                       |                                            | <api-utilities>`. By default, this is the major version of Kinto.        |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+
| kinto.version_prefix_redirect_enabled | ``True``                                   | By default, all endpoints exposed by Kinto are prefixed by a             |
|                                       |                                            | :ref:`version number <api-versioning>`. If this flag is enabled, the     |
|                                       |                                            | server will redirect all requests not matching the supported version     |
|                                       |                                            | to the supported one.                                                    |
+---------------------------------------+--------------------------------------------+--------------------------------------------------------------------------+

Example:

.. code-block:: ini

    kinto.project_docs = https://project.rtfd.org/
    # kinto.project_version = 1.0
