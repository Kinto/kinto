.. _configuration:

Configuration
#############


See `Pyramid settings documentation <http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html>`_.


.. _configuration-environment:

Environment variables
=====================

In order to ease deployment or testing strategies, *Kinto-Core* reads settings
from environment variables, in addition to ``.ini`` files.

For example, ``kinto.storage_backend`` is read from environment variable
``KINTO_STORAGE_BACKEND`` if defined, else from application ``.ini``, else
from internal defaults.


Project info
============

.. code-block:: ini

    kinto.project_name = project
    kinto.project_docs = https://project.rtfd.org/
    # kinto.project_version = 1.3-stable
    # kinto.http_api_version = 1.0

It can be useful to set the ``project_version`` to a custom string, in order
to prevent disclosing information about the currently running version
(when there are known vulnerabilities for example).


Feature settings
================

.. code-block:: ini

    # Limit number of batch operations per request
    # kinto.batch_max_requests = 25

    # Force pagination *(recommended)*
    # kinto.paginate_by = 200

    # Custom record id generator class
    # kinto.id_generator = kinto.core.storage.generators.UUID4


Disabling endpoints
===================

It is possible to deactivate specific resources operations, directly in the
settings.

To do so, a setting key must be defined for the disabled resources endpoints::

    'kinto.{endpoint_type}_{resource_name}_{method}_enabled'

Where:
- **endpoint_type** is either collection or record;
- **resource_name** is the name of the resource (by default, *Kinto-Core* uses the name of the class);
- **method** is the http method (in lower case): For instance ``put``.

For instance, to disable the PUT on records for the *Mushrooms* resource, the
following setting should be declared in the ``.ini`` file:

.. code-block:: ini

    # Disable article collection DELETE endpoint
    kinto.collection_article_delete_enabled = false

    # Disable mushroom record PATCH endpoint
    kinto.record_mushroom_patch_enabled = false


Setting the service in readonly mode
::::::::::::::::::::::::::::::::::::

It is also possible to deploy a *Kinto-Core* service in readonly mode.

Instead of having settings to disable every resource endpoint, the ``readonly`` setting
can be set::

    kinto.readonly = true

This will disable every resources endpoints that are not accessed with one of
``GET``, ``OPTIONS``, or ``HEAD`` methods. Requests will receive a
``405 Method not allowed`` error response.

This setting will also activate readonly heartbeat checks for the
permission and the storage backend.

.. warning::

    The cache backend will still needs read-write privileges, in order to
    cache OAuth authentication states and tokens for example.

    If you do not need cache at all, set the ``kinto.cache_backend`` setting to
    an empty string to disable it.


Deployment
==========

.. code-block:: ini

    # kinto.backoff = 10
    kinto.retry_after_seconds = 30


Scheme, host and port
:::::::::::::::::::::

By default *Kinto-Core* does not enforce requests scheme, host and port. It relies
on WSGI specification and the related stack configuration. Tuning this becomes
necessary when the application runs behind proxies or load balancers.

Most implementations, like *uwsgi*, provide configuration variables to adjust it
properly.

However if, for some reasons, this had to be enforced at the application level,
the following settings can be set:

.. code-block:: ini

    # kinto.http_scheme = https
    # kinto.http_host = production.server:7777


Check the ``url`` value returned in the hello view.


Deprecation
:::::::::::

Activate the :ref:`service deprecation <api-versioning>`. If the date specified
in ``eos`` is in the future, an alert will be sent to clients. If it's in
the past, the service will be declared as decomissionned.

.. code-block:: ini

    # kinto.eos = 2015-01-22
    # kinto.eos_message = "Client is too old"
    # kinto.eos_url = http://website/info-shutdown.html



Logging with Heka
:::::::::::::::::

Mozilla Services standard logging format can be enabled using:

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

Requires the ``raven`` package, or *Kinto-Core* installed with
``pip install kinto[monitoring]``.

Sentry logging can be enabled, `as explained in official documentation
<http://raven.readthedocs.io/en/latest/integrations/pyramid.html#logger-setup>`_.

.. note::

    The application sends an *INFO* message on startup, mainly for setup check.


Monitoring with StatsD
::::::::::::::::::::::

Requires the ``statsd`` package, or *Kinto* installed with
``pip install kinto[monitoring]``.

StatsD metrics can be enabled (disabled by default):

.. code-block:: ini

    kinto.core.statsd_url = udp://localhost:8125
    # kinto.core.statsd_prefix = kinto.project_name


Monitoring with New Relic
:::::::::::::::::::::::::

Requires the ``newrelic`` package, or *Kinto-Core* installed with
``pip install kinto[monitoring]``.

Enable middlewares as described :ref:`here <configuration-middlewares>`.

New-Relic can be enabled (disabled by default):

.. code-block:: ini

    kinto.newrelic_config = /location/of/newrelic.ini
    kinto.newrelic_env = prod


.. _configuration-storage:

Storage
=======

.. code-block:: ini

    kinto.storage_backend = kinto.core.storage.redis
    kinto.storage_url = redis://localhost:6379/1

    # Safety limit while fetching from storage
    # kinto.storage_max_fetch_size = 10000

    # Control number of pooled connections
    # kinto.storage_pool_size = 50

See :ref:`storage backend documentation <storage>` for more details.

.. _configuring-notifications:

Notifications
=============

To activate event listeners, use the *event_handlers* setting,
which takes a list of either:

* aliases (e.g. ``journal``)
* python modules (e.g. ``kinto.core.listeners.redis``)

Each listener will load load its dedicated settings.

In the example below, the Redis listener is activated and will send
data in the ``queue`` Redis list.


.. code-block:: ini

    kinto.event_listeners = redis

    kinto.event_listeners.redis.use = kinto.core.listeners.redis
    kinto.event_listeners.redis.url = redis://localhost:6379/0
    kinto.event_listeners.redis.pool_size = 5
    kinto.event_listeners.redis.listname = queue

Filtering
:::::::::

It is possible to filter events by action and/or resource name. By
default actions ``create``, ``update`` and ``delete`` are notified
for every resources.

.. code-block:: ini

    kinto.event_listeners.redis.actions = create
    kinto.event_listeners.redis.resources = article comment


Cache
=====

Backend
:::::::

.. code-block:: ini

    kinto.cache_backend = kinto.core.cache.redis
    kinto.cache_url = redis://localhost:6379/0
    kinto.cache_prefix = stack1_

    # Control number of pooled connections
    # kinto.storage_pool_size = 50

See :ref:`cache backend documentation <cache>` for more details.


Headers
:::::::

It is possible to add cache control headers on a particular resource
for anonymous requests.
The client (or proxy) will use them to cache the resource responses for a
certain amount of time.

By default, *Kinto-Core* indicates the clients to invalidate their cache
(``Cache-Control: no-cache``).

.. code-block:: ini

    kinto.mushroom_cache_expires_seconds = 3600

Basically, this will add both ``Cache-Control: max-age=3600`` and
``Expire: <server datetime + 1H>`` response headers to the ``GET`` responses.

If setting is set to ``0``, then the resource follows the default behaviour.


CORS
::::

By default, CORS headers are cached by clients during 1H (``Access-Control-Max-Age``).

The duration can be set from settings. If set to empty or to 0, the header
is not sent to clients.

.. code-block:: ini

    kinto.cors_max_age_seconds = 7200



.. _configuration-authentication:

Authentication
==============

Since user identification is hashed in storage, a secret key is required
in configuration:

.. code-block:: ini

    # kinto.userid_hmac_secret = b4c96a8692291d88fe5a97dd91846eb4


Authentication setup
::::::::::::::::::::

*Kinto-Core* relies on :github:`pyramid multiauth <mozilla-service/pyramid_multiauth>`
to initialize authentication.

Therefore, any authentication policy can be specified through configuration.

For example, using the following example, *Basic Auth*, *Persona* and *IP Auth*
are enabled:

.. code-block:: ini

    multiauth.policies = basicauth pyramid_persona ipauth

    multiauth.policy.ipauth.use = pyramid_ipauth.IPAuthentictionPolicy
    multiauth.policy.ipauth.ipaddrs = 192.168.0.*
    multiauth.policy.ipauth.userid = LAN-user
    multiauth.policy.ipauth.principals = trusted


Similarly, any authorization policies and group finder function can be
specified through configuration in order to deeply customize permissions
handling and authorizations.


Basic Auth
::::::::::

``basicauth`` is mentioned among ``multiauth.policies`` by default.

.. code-block:: ini

    multiauth.policies = basicauth

By default, it uses an internal *Basic Auth* policy bundled with *Kinto-Core*.

In order to replace it by another one:

.. code-block:: ini

    multiauth.policies = basicauth
    multiauth.policy.basicauth.use = myproject.authn.BasicAuthPolicy


Custom Authentication
:::::::::::::::::::::

Using the various `Pyramid authentication packages
<https://github.com/ITCase/awesome-pyramid#authentication>`_, it is possible
to plug any kind of authentication.

(*Github/Twitter example to be done*)


Firefox Accounts
::::::::::::::::

Enabling :term:`Firefox Accounts` consists in including ``kinto_fxa`` in
configuration, mentioning ``fxa`` among policies and providing appropriate
values for OAuth2 client settings.

See :github:`mozilla-services/kinto-fxa`.


.. _configuration-permissions:

Permissions
===========

Backend
:::::::

.. code-block:: ini

    kinto.permission_backend = kinto.core.permission.redis
    kinto.permission_url = redis://localhost:6379/1

    # Control number of pooled connections
    # kinto.permission_pool_size = 50

See :ref:`permission backend documentation <permissions-backend>` for more details.

Resources
:::::::::

:term:`ACEs` are usually set on objects using the permission backend.

It is also possible to configure them from settings, and it will **bypass**
the permission backend.

For example, for a resource named "bucket", the following setting will enable
authenticated people to create bucket records:

.. code-block:: ini

    kinto.bucket_create_principals = system.Authenticated

The format of these permission settings is
``<resource_name>_<permission>_principals = comma,separated,principals``.

See :ref:`shareable resource documentation <permission-shareable-resource>` for more details.


Application profiling
=====================

It is possible to profile the application while its running. This is especially
useful when trying to find slowness in the application.

Enable middlewares as described :ref:`here <configuration-middlewares>`.

Update the configuration file with the following values:

.. code-block:: ini

    kinto.profiler_enabled = true
    kinto.profiler_dir = /tmp/profiling

Run a load test (*for example*):

::

    SERVER_URL=http://localhost:8000 make bench -e


Render execution graphs using GraphViz:

::

    sudo apt-get install graphviz

::

    pip install gprof2dot
    gprof2dot -f pstats POST.v1.batch.000176ms.1427458675.prof | dot -Tpng -o output.png


.. _configuration-middlewares:

Enable middleware
=================

In order to enable Kinto-Core middleware, wrap the application in the project ``main`` function:

.. code-block:: python
  :emphasize-lines: 4,5

  def main(global_config, **settings):
      config = Configurator(settings=settings)
      kinto.initialize(config, __version__)
      app = config.make_wsgi_app()
      return kinto.install_middlewares(app, settings)


Initialization sequence
=======================

In order to control what part of *Kinto-Core* should be run during application
startup, or add custom initialization steps from configuration, it is
possible to change the ``initialization_sequence`` setting.

.. warning::

    This is considered as a dangerous zone and should be used with caution.

    Later, a better formalism should be introduced to easily allow addition
    or removal of steps, without repeating the whole list and without relying
    on internal functions location.


.. code-block:: ini

    kinto.core.initialization_sequence = kinto.core.initialization.setup_request_bound_data
                                         kinto.core.initialization.setup_json_serializer
                                         kinto.core.initialization.setup_logging
                                         kinto.core.initialization.setup_storage
                                         kinto.core.initialization.setup_permission
                                         kinto.core.initialization.setup_cache
                                         kinto.core.initialization.setup_requests_scheme
                                         kinto.core.initialization.setup_version_redirection
                                         kinto.core.initialization.setup_deprecation
                                         kinto.core.initialization.setup_authentication
                                         kinto.core.initialization.setup_backoff
                                         kinto.core.initialization.setup_statsd
                                         kinto.core.initialization.setup_listeners
                                         kinto.core.events.setup_transaction_hook
