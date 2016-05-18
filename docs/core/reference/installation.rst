.. _installation:

Installation
############


By default, a *Kinto-Core* application persists the records and cache in a local
`Redis <http://redis.io/>`_.

Using the :ref:`application configuration <configuration-storage>`,
other backends like « in-memory » or `PostgreSQL <http://postgresql.org/>`_
can be enabled afterwards.


Supported Python versions
=========================

Kinto-Core supports Python 2.7, Python 3.4 and PyPy.


Distribute & Pip
================

Installing Kinto-Core with pip:

::

    pip install kinto


For *PostgreSQL* and *monitoring* support:

::

    pip install kinto[postgresql,monitoring]


.. note::

    When installing kinto-core with postgresql support in a virtualenv using the
    `PyPy <http://pypy.org/>`_ interpreter, the
    `psycopg2cffi <https://github.com/chtd/psycopg2cffi>`_ PostgreSQL database
    adapter will be installed, instead of the traditional
    `psycopg2 <https://pythonhosted.org/psycopg2/>`_, as it provides significant
    `performance improvements
    <http://chtd.ru/blog/bystraya-rabota-s-postgres-pod-pypy/?lang=en>`_.


If everything is under control *python*-wise, jump to the next chapter.
Otherwise please find more details below.


Python 3.4
==========

Linux
-----

::

    sudo apt-get install python3.4-dev

OS X
----

::

    brew install python3


Cryptography libraries
======================

Linux
-----

On Debian / Ubuntu based systems::

    apt-get install libffi-dev libssl-dev

On RHEL-derivatives::

    yum install libffi-devel openssl-devel

OS X
----

Assuming `brew <http://brew.sh/>`_ is installed:

::

    brew install libffi openssl pkg-config



Install Redis
=============

Linux
-----

On debian / ubuntu based systems::

    apt-get install redis-server


or::

    yum install redis

OS X
----

Assuming `brew <http://brew.sh/>`_ is installed, Redis installation becomes:

::

    brew install redis

To restart it (Bug after configuration update)::

    brew services restart redis


Install PostgreSQL
==================

Client libraries only
---------------------

Install PostgreSQL client headers::

    sudo apt-get install libpq-dev

Install Kinto-Core with related dependencies::

    pip install kinto[postgresql]


Full server
-----------

PostgreSQL version 9.4 (or higher) is required.

To install PostgreSQL on Ubuntu/Debian use::

    sudo apt-get install postgresql-9.4

If your Ubuntu/Debian distribution doesn't include version 9.4 of PostgreSQL
look at the `PostgreSQL Ubuntu
<http://www.postgresql.org/download/linux/ubuntu/>`_ and `PostgreSQL Debian
<http://www.postgresql.org/download/linux/debian/>`_ pages. The PostgreSQL
project provides an Apt Repository that one can use to install recent
PostgreSQL versions.

By default, the ``postgres`` user has no password and can hence only connect
if ran by the ``postgres`` system user. The following command will assign it:

::

    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

Kinto-Core requires ``UTC`` to be used as the database timezone, and
``UTF-8`` as the database encoding. You can for example use the following
commands to create a database named ``testdb`` with the appropriate timezone
and encoding::

    sudo -u postgres psql -c "ALTER ROLE postgres SET TIMEZONE TO 'UTC';"
    sudo -u postgres psql -c "CREATE DATABASE testdb ENCODING 'UTF-8';"


Server using Docker
-------------------

Install docker, for example on Ubuntu:

::

    sudo apt-get install docker.io

Run the official PostgreSQL container locally:

::

    postgres=$(sudo docker run -d -p 5432:5432 postgres)

(*optional*) Create the test database::

    psql -h localhost -U postgres -W
    #> CREATE DATABASE "testdb";


Tag and save the current state with::

    sudo docker commit $postgres kinto-empty


In the future, run the tagged version of the container ::

    kinto=$(sudo docker run -d -p 5432:5432 kinto-empty)

    ...

    sudo docker stop $kinto
