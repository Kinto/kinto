.. _run-production:

Running in production
#####################

*Kinto* is a standard Python application.

Recommended settings for production are listed below. Some :ref:`general insights about deployment strategies
<deployment>` are also provided.

Because we use it for most of our deploys, *PostgreSQL* is the recommended
backend for production.


.. _postgresql-install:

Install and setup PostgreSQL
============================

(*requires PostgreSQL 9.4 or higher*).

*Kinto* dependencies do not include *PostgreSQL* tooling and drivers by default.


PostgreSQL client
-----------------

On Debian / Ubuntu based systems::

    $ sudo apt-get install libpq-dev

On Mac OS X, `install a server or use port <http://superuser.com/questions/296873/install-libpq-dev-on-mac-os>`_.


Run a PostgreSQL server
-----------------------

The instructions to run a local PostgreSQL database are out of scope here.

A detailed guide is :github:`available on the Kinto Wiki <Kinto/kinto/wiki/How-to-run-a-PostgreSQL-server%3F>`.


Initialization
--------------

Once a PostgreSQL is up and running somewhere, select the Postgresql option when
running the ``init`` command:

.. code-block :: bash

    $ kinto --ini production.ini init

By default, the generated configuration refers to a ``postgres`` database on
``localhost:5432``, with user/password ``postgres``/``postgres``.

The last step consists in creating the necessary tables and indices, run the ``migrate`` command:

.. code-block :: bash

    $ kinto --ini production.ini migrate

.. note::

    Alternatively the SQL initialization files can be found in the
    *Cliquet* :github:`source code <mozilla-services/cliquet>`.


Production checklist
====================

Recommended settings
--------------------

Most default setting values in the application code base are suitable
for production.

Also, the set of settings mentionned below might deserve some review or
adjustments:

.. code-block :: ini

    kinto.flush_endpoint_enabled = false
    kinto.http_scheme = https
    kinto.paginate_by = 100
    kinto.batch_max_requests = 25
    kinto.storage_pool_size = 50
    kinto.cache_pool_size = 50
    kinto.permission_pool_size = 50
    fxa-oauth.cache_ttl_seconds = 3600

.. note::

    For an exhaustive list of available settings and their default values,
    refer to the *Cliquet* :github:`source code <mozilla-services/cliquet/blob/2.15.0/cliquet/__init__.py#L26-L89>`.


By default, nobody can read buckets list. You can change that using:

.. code-block :: ini

    kinto.bucket_read_principals = system.Authenticated

Beware that if you do so, everyone will be able to list bucket
information (including user's personal buckets).


Handling CDN
------------

If you want to put your Kinto behind a CDN you must make sure to define the
right host or you will leak the main server host.

.. code-block:: ini

    kinto.http_host = cdn.firefox.com

You can make sure your service is correctly configured by looking at the service URL
returned on the service home page. It should be your CDN service URL.

It might also be relevant to set your main server :ref:`as readonly <configuration-features>`_.

In the configuration of the CDN service, you should also:

- Allow ``OPTIONS`` requests (CORS)
- Pass through cache and concurrency control headers: ``ETag``, ``Last-Modified``, ``Expire``
- Cached responses should depend on querystring parameters (e.g. try with different ``?_limit=`` values)


Monitoring
----------

In order to enable monitoring features like *statsd*, install
extra requirements:

::

    make install-monitoring

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



Run the Kinto application
=========================

Using Apache mod wsgi
---------------------

This is probably the easiest way to setup a production server.

With the following configuration for the site, Apache should be able to
run the Kinto application:

::

    WSGIScriptAlias /         /path/to/kinto/app.wsgi
    WSGIPythonPath            /path/to/kinto
    SetEnv          KINTO_INI /path/to/kinto.ini

    <Directory /path/to/kinto>
      <Files app.wsgi>
        Require all granted
      </Files>
    </Directory>


Using nginx
-----------

nginx can act as a *reverse proxy* in front of :rtd:`uWSGI <uwsgi-docs>`
(or any other wsgi server like `Gunicorn <http://gunicorn.org>`_ or :rtd:`Circus <circus>`).

Download the ``uwsgi_params`` file:

::

    wget https://raw.githubusercontent.com/nginx/nginx/master/conf/uwsgi_params


Configure nginx to listen to a uwsgi running:

::

    upstream kinto {
        server unix:///var/run/uwsgi/kinto.sock;
    }

    server {
        listen      8000;
        server_name .my-kinto.org; # substitute your machine's IP address or FQDN
        charset     utf-8;

        # max upload size
        client_max_body_size 75M;   # adjust to taste

        location / {
            uwsgi_pass  kinto;
            include     /path/to/uwsgi_params; # the uwsgi_params file previously downloaded
        }
    }


It is also wise to restrict the private URLs (like for ``__heartbeat__``):

::

    location ~ /v1/__(.+)__ {
        allow 127.0.0.1;
        allow 172.31.17.16;
        deny all;
    }


Running with uWSGI
------------------

::

    pip install uwsgi

To run the application using uWSGI, an **app.wsgi** file is provided.
This command can be used to run it::

    uwsgi --ini config/kinto.ini

uWSGI configuration can be tweaked in the ini file in the dedicated
``[uwsgi]`` section.

Here's an example:

.. code-block :: ini

    [uwsgi]
    wsgi-file = app.wsgi
    enable-threads = true
    socket = /var/run/uwsgi/kinto.sock
    chmod-socket = 666
    processes =  3
    master = true
    module = kinto
    harakiri = 120
    uid = kinto
    gid = kinto
    virtualenv = .venv
    lazy = true
    lazy-apps = true
    single-interpreter = true
    buffer-size = 65535
    post-buffering = 65535
    plugin = python

To use a different ini file, the ``KINTO_INI`` environment variable
should be present with a path to it.

.. _production-cache-server:

Nginx as cache server
---------------------

If *Nginx* is used as a reverse proxy, it can also `act as a cache server <https://serversforhackers.com/nginx-caching>`_
by taking advantage of *Kinto* optional cache control response headers
(forced :ref:`in settings <configuration-client-caching>`
or set :ref:`on collections <collection-caching>`).

The sample *Nginx* configuration file shown above will look like so:

.. code-block:: javascript
    :emphasize-lines: 1,2,8

    proxy_cache_path /tmp/nginx levels=1:2 keys_zone=my_zone:100m inactive=200m;
    proxy_cache_key "$scheme$request_method$host$request_uri$";

    server {
        ...

        location / {
            proxy_cache my_zone;

            uwsgi_pass  kinto;
            include     /path/to/uwsgi_params; # the uwsgi_params file previously downloaded
        }
    }
