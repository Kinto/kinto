.. _command-line:

Command Line
============

When Kinto is installed, a command ``kinto`` becomes available.

It accepts a ``--ini`` parameter, whose default value is
``config/kinto.ini`` or the ``KINTO_INI`` env variable if defined.

A set of «sub commands» are available.

::

    usage: kinto [-h] {init,start,migrate,version,rebuild-quotas} ...

    Kinto Command-Line Interface

    optional arguments:
      -h, --help            show this help message and exit

    subcommands:
      Main Kinto CLI commands

      {init,start,migrate,version,rebuild-quotas}
                            Choose and run with --help


Configuration file
------------------

Creates a configuration file that works out of the box.

::

    usage: kinto init [-h] [--backend BACKEND]

    optional arguments:
      -h, --help         show this help message and exit
      --backend BACKEND  {memory,redis,postgresql}


.. note::

    When choosing ``postgresql``, the PostgreSQL Python dependencies will be
    installed if not available.

Database schemas
----------------

Installs the last database schemas in the configured backends.

::

    usage: kinto migrate [-h] [--dry-run]

    optional arguments:
      -h, --help  show this help message and exit
      --dry-run   Simulate the migration operations and show information

.. note::

    Running this on PostgreSQL requires the configured user to have certain
    privileges (table creation etc.).


Local server
------------

Starts Kinto locally using a simple HTTP server.

::

    usage: kinto start [-h] [--reload] [--port PORT]

    optional arguments:
      -h, --help   show this help message and exit
      --reload     Restart when code or config changes
      --port PORT  Listening port number

.. note::

    This **not** recommended for production. :ref:`See more details <run-production>`.


Rebuild quotas
--------------

Recalculate the amount of storage taken up by buckets and collections
and update quota records to match reality. This can be useful if
you've been bitten by `bug #1226
<https://github.com/Kinto/kinto/issues/1226>`_. However, this isn't
intended to be a reoccurring maintenance task -- if your quota records
are regularly becoming inaccurate, please file a bug!

::

    usage: kinto rebuild-quotas [-h] [--ini INI_FILE] [-q] [-v] [--dry-run]

    optional arguments:
      -h, --help      show this help message and exit
      --ini INI_FILE  Application configuration file
      -q, --quiet     Show only critical errors.
      -v, --debug     Show all messages, including debug messages.
      --dry-run       Simulate the rebuild operation and show information

For example:

::

    kinto rebuild-quotas --ini=config/postgresql.ini

Flush Cache
-----------

Clears the content of the cache backend. This can be useful for debugging.

::

    usage: kinto flush-cache [--ini INI_FILE]

For example:

::

    kinto flush-cache --ini kinto.ini
