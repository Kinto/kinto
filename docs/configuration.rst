.. _configuration:

Configuration
#############


See `Pyramid settings documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/environment.html>`_.


Environment variables
=====================

In order to ease deployment or testing strategies, cliquet reads settings
from environment variables, in addition to ``.ini`` files.

For example, ``cliquet.storage_backend`` is read from environment variable
``CLIQUET_STORAGE_BACKEND`` if defined, else from application ``.ini``, else
from internal defaults.


Project info
============

.. code-block :: ini

    cliquet.project_name = project
    cliquet.project_docs = https://project.rtfd.org/
    # cliquet.project_version = 1.0


Feature settings
================

.. code-block :: ini

    # Limit number of batch operations per request
    # cliquet.batch_max_requests = 25

    # Disable DELETE on collection
    # cliquet.delete_collection_enabled = false

    # Force pagination *(recommended)*
    # cliquet.paginate_by = 200

Deployment
==========

.. code-block :: ini

    # cliquet.backoff = 10
    cliquet.retry_after_seconds = 30


Scheme, host and port
:::::::::::::::::::::

By default *cliquet* does not enforce requests scheme, host and port. It relies
on WSGI specification and the related stack configuration. Tuning this becomes
necessary when the application runs behind proxies or load balancers.

Most implementations, like *uwsgi*, provide configuration variables to adjust it
properly.

However if, for some reasons, this had to be enforced at the application level,
the following settings can be set:

.. code-block :: ini

    # cliquet.http_scheme = https
    # cliquet.http_host = production.server:7777


Check the ``url`` value returned in the hello view.


Deprecation
:::::::::::

Activate the :ref:`service deprecation <versioning>`. If the date specified
in ``eos`` is in the future, an alert will be sent to clients. If it's in
the past, the service will be declared as decomissionned.

.. code-block :: ini

    # cliquet.eos = 2015-01-22
    # cliquet.eos_message = "Client is too old"
    # cliquet.eos_url = http://website/info-shutdown.html



Logging with Heka
:::::::::::::::::

Mozilla Services standard logging format can be enabled using:

.. code-block :: ini

    cliquet.logging_renderer = cliquet.logs.MozillaHekaRenderer


With the following configuration, all logs are redirected to standard output
(See `12factor app <http://12factor.net/logs>`_):

.. code-block :: ini

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

Requires the ``raven`` package, or *cliquet* installed with
``pip install cliquet[monitoring]``.

Sentry logging can be enabled, `as explained in official documentation
<http://raven.readthedocs.org/en/latest/integrations/pyramid.html#logger-setup>`_.

:note:

    The application sends an *INFO* message on startup, mainly for setup check.


Monitoring with StatsD
::::::::::::::::::::::

Requires the ``statsd`` package, or *cliquet* installed with
``pip install cliquet[monitoring]``.

StatsD metrics can be enabled (disabled by default):

.. code-block :: ini

    cliquet.statsd_url = udp://localhost:8125
    # cliquet.statsd_prefix = cliquet.project_name

Monitoring with New Relic
:::::::::::::::::::::::::

Requires the ``newrelic`` package, or *cliquet* installed with
``pip install cliquet[monitoring]``.

New-Relic can be enabled (disabled by default):

.. code-block :: ini

    cliquet.newrelic_config = /location/of/newrelic.ini
    cliquet.newrelic_env = prod

This also requires your wsgi application to be wrapped by cliquet.
In your project ``main`` function:

.. code-block :: python
  :emphasize-lines: 4,5

  def main(global_config, **settings):
      config = Configurator(settings=settings)
      cliquet.initialize(config, __version__)
      app = config.make_wsgi_app()
      return cliquet.install_middlewares(app)


Storage
=======

.. code-block :: ini

    cliquet.storage_backend = cliquet.storage.redis
    cliquet.storage_url = redis://localhost:6379/1

    # Safety limit while fetching from storage
    # cliquet.storage_max_fetch_size = 10000

    # Control number of pooled connections
    # cliquet.storage_pool_maxconn = 50

See :ref:`storage backend documentation <storage>` for more details.


Cache
=====

.. code-block :: ini

    cliquet.cache_backend = cliquet.cache.redis
    cliquet.cache_url = redis://localhost:6379/0

    # Control number of pooled connections
    # cliquet.cache_pool_maxconn = 50

See :ref:`cache backend documentation <cache>` for more details.


Authentication
==============

Since user identification is hashed in storage, a secret key is required
in configuration:

.. code-block :: ini

    # cliquet.userid_hmac_secret = b4c96a8692291d88fe5a97dd91846eb4


Basic Auth
::::::::::

.. code-block :: ini

    # cliquet.basic_auth_enabled = true


Custom Authentication
:::::::::::::::::::::

Is is possible to overwrite the Cliquet initialization in order to replace
the default authentication backend.

Internally, Cliquet relies on Pyramid ``authenticated_userid`` request
attribute to associate users to records.


.. code-block :: python

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize(config, __version__)

        config.include('velruse.providers.github')


Or set it up manually:

.. code-block :: python

    import pyramid_multiauth

    #
    # ... (see quickstart example)
    #

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        cliquet.initialize(config, __version__)

        policies = [
            cliquet.authentication.BasicAuthAuthenticationPolicy(),
            myproject.authentication.MyPolicy()
        ]
        authn_policy = pyramid_multiauth.MultiAuthenticationPolicy(policies)

        config.set_authentication_policy(authn_policy)


Firefox Accounts
::::::::::::::::

As `stated in the official documentation <https://developer.mozilla.org/en-US/Firefox_Accounts>`_,
Firefox Accounts OAuth integration is currently limited to Mozilla relying services.

If you're a Mozilla service, fill the settings with the values you were provided:

.. code-block :: ini

    fxa-oauth.relier.enabled = true
    fxa-oauth.client_id = 89513028159972bc
    fxa-oauth.client_secret = 9aced230585cc0aaea0a3467dd800
    fxa-oauth.oauth_uri = https://oauth-stable.dev.lcip.org
    fxa-oauth.scope = profile
    fxa-oauth.webapp.authorized_domains = *.firefox.com
    # fxa-oauth.cache_ttl_seconds = 300
    # fxa-oauth.state.ttl_seconds = 3600


Application profiling
=====================

It is possible to profile the application while its running. This is especially
useful when trying to find slowness in the application.

Update your configuration file with the following values:

.. code-block :: ini

    cliquet.profiler_enabled = true
    cliquet.profiler_dir = /tmp/profiling

Run a load test (*for example*):

::

    SERVER_URL=http://localhost:8000 make bench -e


Render execution graphs using GraphViz:

::

    sudo apt-get install graphviz

::

    pip install gprof2dot
    gprof2dot -f pstats POST.v1.batch.000176ms.1427458675.prof | dot -Tpng -o output.png
