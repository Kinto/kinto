.. _command-line:

Command Line
============

When Kinto is installed, a command ``kinto`` becomes available.

It accepts a ``--ini`` parameter, whose default value is
``config/kinto.ini`` or the ``KINTO_INI`` env variable if defined.

A set of «sub commands» are available.

::

    usage: kinto [-h] {init,start,migrate,version,rename} ...

    Kinto Command-Line Interface

    optional arguments:
      -h, --help            show this help message and exit

    subcommands:
      Main Kinto CLI commands

      {init,start,migrate,version,rename}
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


Purge Deleted
-------------

Delete tombstones from the database, and keep a certain number of them per collection.

This is **not** recommended in production, unless you really know what you are doing.

It will break partial synchronization on clients that didn't have the chance to apply these deletions locally.

::

    usage: kinto purge-deleted [-h] [--ini INI_FILE] [-q] [-v] resources [resources ...] max-retained

For example:

::

    kinto purge-deleted --ini=config/postgresql.ini bucket collection record 10000


Rename Collection
-----------------

Move and/or rename a collection to a different location, optionally in a different bucket.

This command copies the collection object, all its records (including deleted ones),
and all associated permissions to a new location, then removes the original.

.. warning::

    Ensure you have a backup before running this command in production.
    The source collection will be deleted after the move completes.

::

    usage: kinto rename [-h] [--ini INI_FILE] [-q] [-v] [--dry-run] [--force] SRC DST

    positional arguments:
      SRC               Source collection path (e.g. /buckets/old/collections/data)
      DST               Destination collection path (e.g. /buckets/new/collections/data)

    optional arguments:
      -h, --help        show this help message and exit
      --dry-run         Preview the operation without making changes
      --force           Overwrite destination if it already exists
      -q, --quiet       Show only critical errors
      -v, --debug       Show all messages, including debug messages

Examples:

Rename a collection within the same bucket:

::

    kinto rename --ini config/kinto.ini \
      /buckets/mybucket/collections/articles \
      /buckets/mybucket/collections/blog-posts

Move a collection to a different bucket:

::

    kinto rename --ini config/kinto.ini \
      /buckets/v1/collections/items \
      /buckets/v2/collections/items

Preview changes without modifying data:

::

    kinto rename --ini config/kinto.ini --dry-run \
      /buckets/old/collections/data \
      /buckets/new/collections/data

Overwrite an existing destination collection:

::

    kinto rename --ini config/kinto.ini --force \
      /buckets/source/collections/items \
      /buckets/dest/collections/items

.. note::

    The destination bucket must exist before running this command.
    All records, tombstones, and permissions associated with the collection are moved.
