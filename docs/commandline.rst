.. _command-line:

Command Line
============

When Kinto is installed, a command ``kinto`` becomes available.

It accepts a ``--ini`` parameter, whose default value is
``config/kinto.ini`` or the ``KINTO_INI`` env variable if defined.

A set of «sub commands» are available.

::

    usage: kinto [-h] {init,start,migrate,version} ...

    Kinto Command-Line Interface

    optional arguments:
      -h, --help            show this help message and exit

    subcommands:
      Main Kinto CLI commands

      {init,start,migrate,version}
                            Choose and run with --help


Configuration file
------------------

Creates a configuration file that works out of the box.

::

    usage: kinto init [-h] [--backend BACKEND]

    optional arguments:
      -h, --help         show this help message and exit
      --backend BACKEND  {memory,postgresql}


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

Flush Cache
-----------

Clears the content of the cache backend. This can be useful for debugging.

::

    usage: kinto flush-cache [--ini INI_FILE]

For example:

::

    kinto flush-cache --ini kinto.ini
