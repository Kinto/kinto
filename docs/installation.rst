Installation
############

*Kinto* is based on top of the `cliquet <https://cliquet.rtfd.org>`_ project, and
as such, please refer to cliquet's documentation if details seem to be missing
here.


Run locally
===========

For development
---------------

By default, *Kinto* persists the records and internal cache in a PostgreSQL
database.

The default configuration will connect to the ``postgres`` database on
``localhost:5432``, with user/password ``postgres``/``postgres``.
See more details below about installation and setup of PostgreSQL.

::

    make serve


Using Docker
------------

Kinto uses `Docker Compose <http://docs.docker.com/compose/>`_, which takes
care of running and connecting PostgreSQL:

::

    docker-compose up


Authentication
--------------

By default, Kinto relies on Firefox Account OAuth2 Bearer tokens to authenticate
users.

See `cliquet documentation <http://cliquet.readthedocs.org/en/latest/configuration.html#authentication>`_
to configure authentication options.


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
    refer to `the source code <https://github.com/mozilla-services/cliquet/blob/1.7.0/cliquet/__init__.py#L49-L88>`_.


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



Install and setup PostgreSQL
============================

 (*requires PostgreSQL 9.3 or higher*).

Client libraries only
---------------------

Install PostgreSQL client headers::

    sudo apt-get install libpq-dev


Full server
-----------

In Ubuntu/Debian based::

    sudo apt-get install postgresql


By default, the ``postgres`` user has no password and can hence only connect
if ran by the ``postgres`` system user. The following command will assign it:

::

    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"


Server using Docker
-------------------

Install docker:

On Ubuntu you can do:

::

    sudo apt-get install docker.io

Run the official PostgreSQL container locally:

::

    postgres=$(sudo docker run -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 postgres)

Tag and save the current state with::

    sudo docker commit $postgres kinto-db


In the future, run the tagged version of the container ::

    kinto=$(sudo docker run -e POSTGRES_PASSWORD=postgres -d -p 5432:5432 kinto-db)

    ...

    sudo docker stop $kinto


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew update
    brew install postgresql

Create the initial database:

::

    initdb /usr/local/var/postgres


Cryptography libraries
======================

Linux
-----

On Debian / Ubuntu based systems::

    apt-get install libffi-dev libssl-dev

On RHEL-derivatives::

    apt-get install libffi-devel openssl-devel

OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew install libffi openssl pkg-config
