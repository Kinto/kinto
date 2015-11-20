.. _run-kinto:

Run Kinto
#########

.. _run-kinto-mozilla-demo:

Mozilla demo server
===================

A Kinto instance is running at https://kinto.dev.mozaws.net/v1/

It should be enough to get started, but the records are flushed every day
at 7:00 AM UTC.


Using Docker
============

If you have `Docker <https://docker.com/>`_, *Kinto* can be started locally with a single command:

::

    sudo docker run -p 8888:8888 kinto/kinto-server

The server should now be running on http://localhost:8888

It is possible to specify every Kinto setting through environment variables.
For example, using an environment file:

.. code-block:: shell

    # kinto.env
    KINTO_USERID_HMAC_SECRET = tr0ub4d@ur
    KINTO_BATCH_MAX_REQUESTS = 200
    # KINTO_STORAGE_BACKEND = cliquet.storage.postgresql
    # KINTO_STORAGE_URL = postgres://user:pass@localhost/kintodb

And running the container with:

::

    docker run --env-file ./kinto.env -p 8888:8888 kinto/kinto-server

The server should now be running on http://localhost:8888


Using Docker Compose
--------------------

A sample configuration for `Docker Compose <http://docs.docker.com/compose/>`_
is provided in the Kinto repository. It pulls the *Kinto* container and run it
with a *PostgreSQL* container.

::

    wget https://raw.githubusercontent.com/Kinto/kinto/master/docker-compose.yml
    sudo docker-compose up


Using Python package
====================

Python tooling
--------------

The following tools are necessary to initiate the local installation and use
our helpers:

* `Virtualenv <https://virtualenv.pypa.io/>`_

On Ubuntu/Debian, ``sudo apt-get install python-virtualenv`` is enough.


Quick start
-----------

By default, for convenience, *Kinto* persists the records, permissions and
internal cache in a **volatile** memory backend. On every restart, the server
will lose its data, and multiple processes are not handled properly.

But it should be enough to get started!


Create a Python isolated environment (*optional*):

::

    virtualenv env/
    source env/bin/activate

Then install the package using the default configuration:

::

    pip install kinto
    kinto init
    kinto start

The server should now be running on http://localhost:8888


.. _run-kinto-from-source:

From sources
============

If you plan on contributing, this is the way to go!

This will install every necessary packages to run the tests, build the
documentation etc.

::

    git clone https://github.com/Kinto/kinto.git
    cd kinto/

    make serve


The server should now be running with the default configuration on http://localhost:8888

In order to specify a particular settings file: ::

    make serve SERVER_CONFIG=config/dev.ini

With `make`, it is also possible to specify arguments from environment variables: ::

    export SERVER_CONFIG=config/dev.ini

    make serve -e


See :ref:`dedicated section about contributing <contributing>` !


Go further
==========

Some suggestions for the next steps:

* :rtd:`Follow the Kinto.js tutorial <kintojs>`
* :ref:`Configure PostgreSQL <postgresql-install>`
* :ref:`Play with the HTTP API <tutorial-first-steps>`
* :ref:`Run in production <run-production>`
