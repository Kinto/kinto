.. _configuration:

Configuration
#############

For an exhaustive list of *Cliquet* settings, see `cliquet settings
documentation
<http://cliquet.readthedocs.org/en/latest/reference/configuration.html>`_.

.. _run-production:

Running in production
=====================

Recommended settings
--------------------

Most default setting values in the application code base are suitable
for production.

Once :ref:`PostgreSQL is installed <postgresql-install>`, the settings about
backends as shown in :file:`config/kinto.ini` can be uncommented in order
to use *PostgreSQL*.

Also, the set of settings mentionned below might deserve some review or
adjustments:

.. code-block :: ini

    kinto.flush_endpoint_enabled = false
    cliquet.http_scheme = https
    cliquet.paginate_by = 100
    cliquet.batch_max_requests = 25
    cliquet.storage_pool_maxconn = 50
    cliquet.cache_pool_maxconn = 50
    cliquet.permission_pool_maxconn = 50
    fxa-oauth.cache_ttl_seconds = 3600

.. note::

    For an exhaustive list of available settings and their default values,
    refer to `the source code <https://github.com/mozilla-services/cliquet/blob/2.3/cliquet/__init__.py#L26-L78>`_.


By default, nobody can read buckets list. You can change that using:

.. code-block :: ini

    cliquet.bucket_read_principals = system.Authenticated

Beware that if you do so, everyone will be able to list bucket
information (including user's personal buckets).


Monitoring
----------

In order to enable *Cliquet* monitoring features like *statsd*, install
extra requirements:

::

    pip install "cliquet[monitoring]"

And configure its URL:

.. code-block :: ini

    # StatsD
    cliquet.statsd_url = udp://carbon.server:8125

The following counters will be enabled:

* ``users`` (unique user ids)
* ``authn_type.basicauth``
* ``authn_type.fxa``

And the following timers:

* ``authentication.permits``
* ``view.hello.GET``
* ``view.heartbeat.GET``
* ``view.batch.POST``
* ``view.bucket-record.[GET|POST|PUT|PATCH|DELETE]``
* ``view.bucket-collection.[GET|POST|PUT|PATCH|DELETE]``
* ``view.collection-record.[GET|POST|PUT|PATCH|DELETE]``
* ``view.collection-collection.[GET|POST|PUT|PATCH|DELETE]``
* ``view.group-record.[GET|POST|PUT|PATCH|DELETE]``
* ``view.group-collection.[GET|POST|PUT|PATCH|DELETE]``
* ``view.record-record.[GET|POST|PUT|PATCH|DELETE]``
* ``view.record-collection.[GET|POST|PUT|PATCH|DELETE]``
* ``cache.[ping|ttl|expire|set|get|delete]``
* ``storage.[ping|collection_timestamp|create|get|update|delete|delete_all|get_all]``
* ``permission.[add_user_principal|remove_user_principal|user_principals|add_principal_to_ace|remove_principal_from_ace|object_permission_principals|check_permission]``


Heka Logging
------------

At Mozilla, applications log files follow a specific JSON schema, that is
processed through `Heka <http://hekad.readthedocs.org>`_.

In order to enable Mozilla *Heka* logging output:

.. code-block :: ini

    # Heka
    cliquet.logging_renderer = cliquet.logs.MozillaHekaRenderer


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

.. note::

    Alternatively the SQL initialization files can be found in the
    *Cliquet* source code (``cliquet/cache/postgresql/schema.sql`` and
    ``cliquet/storage/postgresql/schema.sql``).


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


.. Storage backend
.. ===============

.. In order to use Kinto as a storage backend for an application built with
.. cliquet, some settings must be set carefully.


.. Firefox Account
.. '''''''''''''''

.. In order to avoid double-verification of FxA OAuth tokens, the ``cliquet.cache_url``
.. should be the same in *Kinto* and in the application. This way
.. the verification cache will be shared between the two components.
