.. _command-line:

Command Line
============

When Kinto is installed, a command ``kinto`` becomes available.

It accepts a ``--ini`` parameter, whose default value is ``config/kinto.ini``,
and a set of «sub commands» are available.

::

    usage: kinto [-h] {init,start,migrate,delete-collection,version} ...

    Kinto Command-Line Interface

    optional arguments:
      -h, --help            show this help message and exit

    subcommands:
      Main Kinto CLI commands

      {init,start,migrate,delete-collection,version}
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


Delete a collection
-------------------

Deletes a collection and its underlying objects from the ``storage`` and ``permission`` backends.

.. warning::

    Objects are permanently deleted, and there is no way to cancel the operation.

::

    usage: kinto delete-collection [-h] --bucket BUCKET --collection COLLECTION

    optional arguments:
      -h, --help            show this help message and exit
      --bucket BUCKET       The bucket where the collection belongs to.
      --collection COLLECTION
                            The collection to remove.

For example:

::

    kinto delete-collection --ini=config/postgresql.ini --bucket=source --collection=source

.. note::

    This command does not go through the HTTP API and won't trigger
    :class:`kinto.core.events.ResourceChanged` events.
