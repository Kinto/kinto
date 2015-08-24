Settings
########

Kinto is built to be highly configurable. As a result, the related
configuration can be verbose, but don't worry, all configuration flags are
listed below.

.. note::

    In order to ease deployment or testing strategies, *Kinto* reads settings
    from environment variables, in addition to ``.ini`` files.

    For example, ``cliquet.storage_backend`` is read from environment variable
    ``CLIQUET_STORAGE_BACKEND`` if defined, else from application ``.ini``, else
    from internal defaults.


Feature settings
================

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.batch_max_requests ``25``     | The Maximum number of requests that can be sent to the batch endpoint.   |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.paginate_by ``None``          | The maximum number of items to include on a response, before enabling    |
|                                       | pagination. If set to `None`, no pagination will be used.                |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.id_generator                  | The Python *dotted* location of the generator class that should be used  |
| ``cliquet.storage.generators.UUID4``  | to generate identifiers on a POST on a collection endpoint.              |
+---------------------------------------+--------------------------------------------------------------------------+

Example:

.. code-block:: ini

    # Limit number of batch operations per request
    # cliquet.batch_max_requests = 25

    # Force pagination *(recommended)*
    # cliquet.paginate_by = 200

    # Custom record id generator class
    # cliquet.id_generator = cliquet.storage.generators.UUID4


Backends
========

In order to configure the backends to use, a number of settings are useful. The
most important ones being `{backend_type}_backend` and `{backend_type}_url`,
where `backend_type` is one of "storage", "permission" or "cache".

Storage
:::::::

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.storage_backend               | The Python *dotted* location of the storage backend to use.              |
| ``cliquet.storage.redis``             |                                                                          |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.storage_max_fetch_size        | The maximum number of items that can be returned by one request to the   |
| ``10000``                             | storage backend. If no pagination is enabled, this is the maximum number |
|                                       | of items that can be stored in a collection (otherwise some of them      |
|                                       | won't be returned). With pagination enabled, this limitation doesn't     |
|                                       | apply.                                                                   |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.storage_pool_size ``10``      | The size of the pool of connections to use for the storage backend.      |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.storage_url  ``''``           | The URL to use to authenticate to the storage backend. e.g.              |
|                                       | ``redis://localhost:6378/1`` or ``postgres://user:pass@database/db``     |
+---------------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    cliquet.storage_backend = cliquet.storage.redis
    cliquet.storage_url = redis://localhost:6379/1

    # Safety limit while fetching from storage
    # cliquet.storage_max_fetch_size = 10000

    # Control number of pooled connections
    # cliquet.storage_pool_size = 50


Cache
:::::

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.cache_backend                 | The Python *dotted* location of the cache backend to use.                |
| ``cliquet.cache.redis``               |                                                                          |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.cache_pool_size ``10``        | The size of the pool of connections to use for the cache backend.        |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.cache_url  ``''``             | The URL to use to authenticate to the cache backend. e.g.                |
|                                       | ``redis://localhost:6378/1`` or ``postgres://user:pass@database/db``     |
+---------------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    cliquet.cache_backend = cliquet.cache.redis
    cliquet.cache_url = redis://localhost:6379/0

    # Control number of pooled connections
    # cliquet.storage_pool_size = 50

Permissions
:::::::::::

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.permission_backend            | The Python *dotted* location of the permission backend to use.           |
| ``cliquet.permission.redis``          |                                                                          |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.permission_url ``''``         | The URL to use to authenticate to the permission backend. e.g.           |
|                                       | ``redis://localhost:6379/1``                                             |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.permission_pool_size ``10``   | The size of the pool of connections to use for the permission backend.   |
+---------------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    cliquet.permission_backend = cliquet.permission.redis
    cliquet.permission_url = redis://localhost:6379/1

    # Control number of pooled connections
    # cliquet.permission_pool_size = 50

Bypass permissions with configuration
:::::::::::::::::::::::::::::::::::::

Permissions are usually retrieved from the permission backend. However, it is
also possible to configure them from settings, and it will **bypass** the
permission backend.

For example, for a resource named "bucket", the following setting will enable
authenticated people to create bucket records:

.. code-block:: ini

    cliquet.bucket_create_principals = system.Authenticated

The format of these permission settings is
``<resource_name>_<permission>_principals = comma,separated,principals``.


Scheme, host and port
=====================

By default *Kinto* does not enforce requests scheme, host and port. It relies
on WSGI specification and the related stack configuration. Tuning this becomes
necessary when the application runs behind proxies or load balancers.

Most implementations, like *uwsgi*, provide configuration variables to adjust it
properly.

However if, for some reasons, this had to be enforced at the application level,
the following settings can be set:

.. code-block :: ini

   # cliquet.http_scheme = https
   # cliquet.http_host = production.server:7777


Check the behaviour of the server with the ``url`` value returned in :ref:`the
hello view <batch>`.

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.http_host ``None``            | The HTTP Host used by Kinto to refer to itself. If set to `None`, the    |
|                                       | HTTP host is read from HTTP headers.                                     |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.http_scheme ``None``          | The HTTP scheme used by Kinto to refer to itself. If set to `None`, the  |
|                                       | HTTP scheme is read from the HTTP headers.                               |
+---------------------------------------+--------------------------------------------------------------------------+

Logging
=======

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.logging_renderer              | The Python *dotted* location of the renderer class that should be used   |
| ``cliquet.logs.ClassicLogRenderer``   | to render the logs to the standard output.                               |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.newrelic_config ``None``      | `None`                                                                   |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.newrelic_env ``dev``          | `dev`                                                                    |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.statsd_prefix ``cliquet``     | The prefix to use when sending data to statsd.                           |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.statsd_url: ``None``          | The URL to use to connect to the statsd host. e.g.                       |
|                                       | ``udp://localhost:8125``                                                 |
+---------------------------------------+--------------------------------------------------------------------------+

Logging with Heka
:::::::::::::::::

Mozilla Services standard logging format can be enabled using:

.. code-block:: ini

    cliquet.logging_renderer = cliquet.logs.MozillaHekaRenderer


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

Requires the ``raven`` package, or *Cliquet* installed with
``pip install cliquet[monitoring]``.

Sentry logging can be enabled, `as explained in official documentation
<http://raven.readthedocs.org/en/latest/integrations/pyramid.html#logger-setup>`_.

.. note::

    The application sends an *INFO* message on startup, mainly for setup check.


Monitoring with StatsD
::::::::::::::::::::::

Requires the ``statsd`` package, or *Cliquet* installed with
``pip install cliquet[monitoring]``.

StatsD metrics can be enabled (disabled by default):

.. code-block:: ini

    cliquet.statsd_url = udp://localhost:8125
    # cliquet.statsd_prefix = cliquet.project_name


Monitoring with New Relic
:::::::::::::::::::::::::

Requires the ``newrelic`` package, or *Cliquet* installed with
``pip install cliquet[monitoring]``.

Enable middlewares as described :ref:`here <configuration-middlewares>`.

New-Relic can be enabled (disabled by default):

.. code-block:: ini

    cliquet.newrelic_config = /location/of/newrelic.ini
    cliquet.newrelic_env = prod

Authentication
==============

By default, *Kinto* relies on *Basic Auth* to authenticate users.

User registration is not necessary. A unique user idenfier will be created
for each couple of ``username:password``.

*Kinto* is compatible with *Firefox Account*.  Install and
configure :github:`mozilla-services/cliquet-fxa`.

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.userid_hmac_secret ``''``     | The secret used by the server to derive the shareable user id. This      |
|                                       | value should be unique to each instance and, of course, kept secret. By  |
|                                       | default, Kinto doesn't define a secret for you, and won't start unless   |
|                                       | you generate one.                                                        |
+---------------------------------------+--------------------------------------------------------------------------+
| multiauth.policies ``["basicauth",    | `MultiAuthenticationPolicy <https://github.com/mozilla-                  |
| ]``                                   | services/pyramid_multiauth>`_ is a Pyramid authentication policy that    |
|                                       | proxies to a stack of other IAuthenticationPolicy objects, to provide a  |
|                                       | combined auth solution from individual pieces. Simply pass it a list of  |
|                                       | policies that should be tried in order.                                  |
+---------------------------------------+--------------------------------------------------------------------------+
| multiauth.policy.basicauth.use        | Python *dotted* path to the authentication policy to use for basicauth.  |
| ``('cliquet.authentication.           | By default, every couple of login / password will be accepted, meaning   |
| BasicAuthAuthenticationPolicy')``     | that no account creation is required.                                    |
+---------------------------------------+--------------------------------------------------------------------------+
| multiauth.authorization_policy        | Python *dotted* path the authorization policy to use for basicAuth.      |
| ``('cliquet.authorization.            | Letting the default value will require the :term:`principal` to have     |
| AuthorizationPolicy')``               | access to the required fields.                                           |
+---------------------------------------+--------------------------------------------------------------------------+

Since user identification is hashed in storage, a secret key is required
in configuration:

.. code-block:: ini

    # cliquet.userid_hmac_secret = b4c96a8692291d88fe5a97dd91846eb4


Authentication setup
::::::::::::::::::::

*Kinto* relies on :github:`pyramid multiauth <mozilla-service/pyramid_multiauth>`_
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

By default, it uses an internal *Basic Auth* policy.

In order to replace it by another one:

.. code-block:: ini

    multiauth.policies = basicauth
    multiauth.policy.basicauth.use = myproject.authn.BasicAuthPolicy


Custom Authentication
:::::::::::::::::::::

Using the various `Pyramid authentication packages
<https://github.com/ITCase/awesome-pyramid#authentication>`_, it is possible
to plug any kind of authentication.


Firefox Accounts
::::::::::::::::

Enabling :term:`Firefox Accounts` consists in including ``cliquet_fxa`` in
configuration, mentioning ``fxa`` among policies and providing appropriate
values for OAuth2 client settings.

See :github:`mozilla-services/cliquet-fxa`.


Cross Origin requests (CORS)
============================

Kinto supports `CORS <http://www.w3.org/TR/cors/>`_ out of the box. Use the
`cors_origins` setting to change the list of accepted origins.

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.cors_origins ``*``            | This List of CORS origins to support on all endpoints. By default allow  |
|                                       | all cross origin requests.                                               |
+---------------------------------------+--------------------------------------------------------------------------+

Backoff indicators
==================

In order to tell clients to back-off (on heavy load for instance), the
following flags can be used. Read more about this at :ref:`backoff-indicators`.

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.backoff ``None``              | The Backoff time to use. If set to `None`, no backoff flag is sent to    |
|                                       | the clients. If set, provides the client with a number of seconds during |
|                                       | which it should avoid doing unnecessary requests.                        |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.retry_after_seconds ``30``    | The number of seconds after which the client should issue requests.      |
+---------------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    # cliquet.backoff = 10
    cliquet.retry_after_seconds = 30

Similarly, the end of service date can be specified by using these settings.

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.eos ``None``                  | The End of Service Deprecation date. If the date specified is in the     |
|                                       | future, an alert will be sent to clients. If it’s in the past, the       |
|                                       | service will be declared as decomissionned. If set to `None`, no End of  |
|                                       | Service information will be sent to the client.                          |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.eos_message ``None``          | The End of Service message. If set to `None`, no End of Service message  |
|                                       | will be sent to the clients.                                             |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.eos_url ``None``              | The End of Service information URL.                                      |
+---------------------------------------+--------------------------------------------------------------------------+

.. code-block:: ini

    cliquet.eos = 2015-01-22
    cliquet.eos_message = "Client is too old"
    cliquet.eos_url = http://website/info-shutdown.html


Enabling or disabling endpoints
===============================

It is possible to deactivate specific resources operations, directly in the
settings.

To do so, a setting key must be defined for the disabled resources endpoints::

    'cliquet.{endpoint_type}_{resource_name}_{method}_enabled'

Where:
- **endpoint_type** is either collection or record;
- **resource_name** is the name of the resource (by default, *Cliquet* uses
  the name of the class);
- **method** is the http method (in lower case): For instance ``put``.

For instance, to disable the PUT on records for the *Mushrooms* resource, the
following setting should be declared in the ``.ini`` file:

.. code-block:: ini

    # Disable article collection DELETE endpoint
    cliquet.collection_article_delete_enabled = false

    # Disable mushroom record PATCH endpoint
    cliquet.record_mushroom_patch_enabled = false

Activating the flush endpoint
=============================

When using Kinto in development mode, it might be helpful to have a way to
flush all the data currently stored in the database.

There is a way to enable this behaviour (it is deactivated by default for
obvious security reasons). In the `.ini` file:

.. code-block :: ini

    kinto.flush_endpoint_enabled = true

Then, issue a `POST` request to the `/__flush__` endpoint to flush all
the data.

Project information
===================

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.error_info_link               | The HTTP link returned when uncaught errors are triggered on the server. |
| ``https://github.com/kinto/kinto/     |                                                                          |
| issues/``                             |                                                                          |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.project_docs                  | The URL where the documentation of the Kinto instance can be found. Will |
| ``'http://kinto.readthedocs.org'``    | be returned in :ref:`the hello view <api-utilities>`.                    |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.project_name ``'kinto'``      | The project name returned in :ref:`the hello view <api- utilities>`.     |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.project_version ``''``        | The version of the project. Will be returned in :ref:`the hello view     |
|                                       | <api-utilities>`. By default, this is the major version of Kinto.        |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.version_prefix_redirect_enab  | By default, all endpoints exposed by Kinto are prefixed by a             |
| led  ``True``                         | :ref:`version number <versioning>`. If this flag is enabled, the server  |
|                                       | will redirect all requests not matching the supported version to the     |
|                                       | supported one.                                                           |
+---------------------------------------+--------------------------------------------------------------------------+

Example:

.. code-block:: ini

    cliquet.project_name = project
    cliquet.project_docs = https://project.rtfd.org/
    # cliquet.project_version = 1.0

Application profiling
=====================

It is possible to profile the application while its running. This is especially
useful when trying to find slowness in the application.

+---------------------------------------+--------------------------------------------------------------------------+
| Setting name                          | What does it do?                                                         |
+=======================================+==========================================================================+
| cliquet.profiler_enabled ``False``    | If enabled, each request will generate an image file with information to |
|                                       | profile the application.                                                 |
+---------------------------------------+--------------------------------------------------------------------------+
| cliquet.profiler_dir ``/tmp``         | The Location where the profiler should output its images.                |
+---------------------------------------+--------------------------------------------------------------------------+

Update the configuration file with the following values:

.. code-block:: ini

    cliquet.profiler_enabled = true
    cliquet.profiler_dir = /tmp/profiling

Render execution graphs using GraphViz:

::

    sudo apt-get install graphviz

::

    pip install gprof2dot
    gprof2dot -f pstats POST.v1.batch.000176ms.1427458675.prof | dot -Tpng -o output.png


Initialization sequence
=======================

In order to control what part of *Kinto* should be run during application
startup, or add custom initialization steps from configuration, it is
possible to change the ``initialization_sequence`` setting.

.. warning::

    This is considered as a dangerous zone and should be used with caution.

    Later, a better formalism should be introduced to easily allow addition
    or removal of steps, without repeating the whole list and without relying
    on internal functions location.


.. code-block:: ini

    cliquet.initialization_sequence = cliquet.initialization.setup_json_serializer
                                      cliquet.initialization.setup_logging
                                      cliquet.initialization.setup_storage
                                      cliquet.initialization.setup_cache
                                      cliquet.initialization.setup_requests_scheme
                                      cliquet.initialization.setup_version_redirection
                                      cliquet.initialization.setup_deprecation
                                      cliquet.initialization.setup_authentication
                                      cliquet.initialization.setup_backoff
                                      cliquet.initialization.setup_stats
