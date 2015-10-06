
.. _run-production:

Running in production
=====================

*Kinto* is a standard python application.

Recommended settings for production are listed below. Some :ref:`insights about deployment strategies
<deployment>` are also provided.

Because we use it for most of our deploys, *PostgreSQL* is the recommended
backend for production.

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
    kinto.http_scheme = https
    kinto.paginate_by = 100
    kinto.batch_max_requests = 25
    kinto.storage_pool_maxconn = 50
    kinto.cache_pool_maxconn = 50
    kinto.permission_pool_maxconn = 50
    fxa-oauth.cache_ttl_seconds = 3600

.. note::

    For an exhaustive list of available settings and their default values,
    refer to `the source code <https://github.com/mozilla-services/cliquet/blob/2.7.0/cliquet/__init__.py#L27-L84>`_.


By default, nobody can read buckets list. You can change that using:

.. code-block :: ini

    kinto.bucket_read_principals = system.Authenticated

Beware that if you do so, everyone will be able to list bucket
information (including user's personal buckets).


Monitoring
----------

In order to enable monitoring features like *statsd*, install
extra requirements:

::

    pip install "cliquet[monitoring]"

And configure its URL:

.. code-block :: ini

    # StatsD
    kinto.statsd_url = udp://carbon.server:8125

Counters
::::::::

.. csv-table::
   :header: "Name", "Description"
   :widths: 10, 100

   "``users``", "Number of unique user IDs."
   "``authn_type.basicauth``", "Number of basic authentication requests"
   "``authn_type.fxa``", "Number of FxA authentications"

Timers
::::::

.. csv-table::
   :header: "Name", "Description"
   :widths: 10, 100

   "``authentication.permits``", "Time needed by the permissions backend to allow or reject a request"
   "``view.hello.GET``", "Time needed to return the hello view"
   "``view.heartbeat.GET``", "Time needed to return the heartbeat page"
   "``view.batch.POST``", "Time needed to process a batch request"
   "``view.{resource}-{type}.{method}``", "Time needed to process the specified *{method}* on a *{resource}* (e.g. bucket, collection or record). Different timers exists for the different type of resources (record or collection)"
   "``cache.{method}``", "Time needed to execute a method of the cache backend. Methods are ``ping``, ``ttl``, ``expire``, ``set``, ``get`` and ``delete``"
   "``storage.{method}``", "Time needed to execute a method of the storage backend. Methods are ``ping``, ``collection_timestamp``, ``create``, ``get``, ``update``, ``delete``, ``delete_all``, ``get_all``"
   "``permission.{method}``", "Time needed to execute a method of the permission backend. Methods are ``add_user_principal``, ``remove_user_principal``, ``user_principals``, ``add_principal_to_ace``, ``remove_principal_from_ace``, ``object_permission_principals``, ``check_permission``"


Heka Logging
------------

At Mozilla, applications log files follow a specific JSON schema, that is
processed through `Heka <http://hekad.readthedocs.org>`_.

In order to enable Mozilla *Heka* logging output:

.. code-block :: ini

    # Heka
    kinto.logging_renderer = cliquet.logs.MozillaHekaRenderer


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

.. _production-cache-server:

Nginx as cache server
---------------------

If *Nginx* is used as a reverse proxy, it can also `act as a cache server <https://serversforhackers.com/nginx-caching>`_
by taking advantage of *Kinto* optional cache control response headers
(forced :ref:`in settings <configuration-client-caching>`
or set :ref:`on collections <collection-caching>`).

A sample *Nginx* configuration could look like so:

::

    proxy_cache_path /tmp/nginx levels=1:2 keys_zone=my_zone:100m inactive=200m;
    proxy_cache_key "$scheme$request_method$host$request_uri$";

    server {
        ...

        location / {
            proxy_cache my_zone;

            include proxy_params;
            proxy_pass http://127.0.0.1:8888;
        }
    }
