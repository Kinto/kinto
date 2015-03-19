Installation
############


By default, Cliquet persists the records and cache in `Redis <http://redis.io/>`_.

In-memory or `PostgreSQL <http://postgresql.org/>`_ storage backend can be enabled in
:ref:`configuration`.

See dedicated paragraphs below for more details about installation of these
services.


Distribute & Pip
================

Installing Cliquet with pip:

::

    pip install cliquet


Install libffi
==============

Linux
-----

On debian / ubuntu based systems::

    apt-get install libffi-dev


OS X
----

Assuming `brew <http://brew.sh/>`_ is installed, libffi installation becomes:

::

    brew install libffi pkg-config



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

Install Cliquet with related dependencies::

    pip install cliquet[postgresql]


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

    postgres=$(sudo docker run -d -p 5432:5432 postgres)

(*optional*) Create the test database::

    psql -h localhost -U postgres -W
    #> CREATE DATABASE "testdb";


Tag and save the current state with::

    sudo docker commit $postgres cliquet-empty


In the future, run the tagged version of the container ::

    cliquet=$(sudo docker run -d -p 5432:5432 cliquet-empty)

    ...

    sudo docker stop $cliquet
