.. _configuration:

Configuration
#############

For an exhaustive list of *Cliquet* settings, see `cliquet settings documentation
<http://cliquet.readthedocs.org/en/latest/configuration.html>`_.

.. _run-production:

Running in production
=====================

Recommended settings
--------------------

Most default setting values in the application code base are suitable for production.

But the set of settings mentionned below might deserve some review or adjustments:


.. code-block :: ini

    cliquet.http_scheme = https
    cliquet.paginate_by = 100
    cliquet.batch_max_requests = 25
    cliquet.storage_pool_maxconn = 50
    cliquet.cache_pool_maxconn = 50
    fxa-oauth.cache_ttl_seconds = 3600

:note:

    For an exhaustive list of available settings and their default values,
    refer to `the source code <https://github.com/mozilla-services/cliquet/blob/2.0.0/cliquet/__init__.py#L26-L78>`_.


Monitoring
----------

.. code-block :: ini

    # Heka
    cliquet.logging_renderer = cliquet.logs.MozillaHekaRenderer

    # StatsD
    cliquet.statsd_url = udp://carbon.server:8125


With the following configuration, all logs are structured in JSON and
redirected to standard output (See `12factor app <http://12factor.net/logs>`_).
A `Sentry <https://getsentry.com>`_ logger is also enabled.


.. code-block:: ini

    [loggers]
    keys = root, kinto, cliquet

    [handlers]
    keys = console, sentry

    [formatters]
    keys = generic, heka

    [logger_root]
    level = INFO
    handlers = console, sentry

    [logger_kinto]
    level = INFO
    handlers = console, sentry
    qualname = kinto

    [logger_cliquet]
    level = INFO
    handlers = console, sentry
    qualname = cliquet

    [handler_console]
    class = StreamHandler
    args = (sys.stdout,)
    level = INFO
    formatter = heka

    [handler_sentry]
    class = raven.handlers.logging.SentryHandler
    args = ('http://public:secret@example.com/1',)
    level = INFO
    formatter = generic

    [formatter_generic]
    format = %(asctime)s %(levelname)-5.5s [%(name)s][%(threadName)s] %(message)s

    [formatter_heka]
    format = %(message)s


PostgreSQL setup
----------------

In production, it is wise to run the application with a dedicated database and
user.

::

    postgres=# CREATE USER prod;
    postgres=# CREATE DATABASE prod OWNER prod;
    CREATE DATABASE


Once storage and cache are modified in ``.ini``, the tables need to be created
with the `cliquet` command-line tool:

.. code-block :: bash

    $ cliquet --ini production.ini migrate

:note:

    Alternatively the SQL initialization files can be found in the
    *Cliquet* source code (``cliquet/cache/postgresql/schemal.sql`` and
    ``cliquet/storage/postgresql/schemal.sql``).


Running with uWsgi
------------------

To run the application using uWsgi, an **app.wsgi** file is provided.
This command can be used to run it::

    uwsgi --ini config/kinto.ini

uWsgi configuration can be tweaked in the ini file in the dedicated
``[uwsgi]`` section.

Here's an example:

.. code-block :: ini

    [uwsgi]
    wsgi-file = app.wsgi
    enable-threads = true
    http-socket = 127.0.0.1:8000
    processes =  3
    master = true
    module = kinto
    harakiri = 120
    uid = kinto
    gid = kinto
    virtualenv = .
    lazy = true
    lazy-apps = true
    single-interpreter = true
    buffer-size = 65535
    post-buffering = 65535

To use a different ini file, the ``KINTO_INI`` environment variable
should be present with a path to it.


.. Storage backend
.. ===============

.. In order to use Kinto as a storage backend for an application built with
.. cliquet, some settings must be set carefully.


.. Firefox Account
.. '''''''''''''''

.. In order to avoid double-verification of FxA OAuth tokens, the ``cliquet.cache_url``
.. should be the same in *Kinto* and in the application. This way
.. the verification cache will be shared between the two components.
