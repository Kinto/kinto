.. _installation:

Installation
############

Depending on the platform, and chosen configuration, some libraries or
extra services are required.

.. note::

    If you are just interesting in trying *Kinto*, a pre-installed and pre-configured
    :ref:`demo instance is publicly available <run-kinto-mozilla-demo>`.


.. _crypto-install:

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


.. _postgresql-install:

Install and setup PostgreSQL
============================

(*requires PostgreSQL 9.4 or higher*).

*Kinto* dependencies do not include *PostgreSQL* tooling and drivers by default.

First, make sure you have PostgreSQL client headers::

    sudo apt-get install libpq-dev

Once done, run ``kinto init`` and select the PostgreSQL option,
the Python dependencies for PostgreSQL will be installed.


Run a PostgreSQL server
-----------------------

The instructions to run local ``postgres``
database on ``localhost:5432``, with user/password ``postgres``/``postgres`` are out of scope here.

A detailed guide is :github:`available on the Kinto Wiki <Kinto/kinto/wiki/How-to-run-a-PostgreSQL-server%3F>`.


