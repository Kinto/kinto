Contributing
############


Setup your development environment
==================================

To prepare your system with Postgres and Redis please refer to the Installation guide.

Prepare your project virtualenv:

::

    $ pip install virtualenv
    $ virtualenv .venv
    $ source .venv/bin/activate

(deactivate when finished)

Install packages as usual, for example install needed packages:

::

    $ pip install cliquet
    $ pip install waitress
    $ pip install tox

Clone Kinto:

::

    $ git clone https://github.com/mozilla-services/kinto.git


Prepare Kinto to run:

::

    $ cd kinto
    $ make serve


Run tests
=========

Currently, running the complete test suite implies to run every type of backend.

That means:

* Run Redis on ``localhost:6379``
* Run a PostgreSQL ``testdb`` database on ``localhost:5432`` with user ``postgres/postgres``
* Run a Kinto instance on ``localhost:8888``

::

    make tests


.. note ::

    For Kinto, a sample config file is provided in :file:`cliquet/tests/config/kinto.ini`.


Run a single test
'''''''''''''''''

For Test-Driven Development, it is a possible to run a single test case, in order
to speed-up the execution:

::

    nosetests -s --with-mocha-reporter cliquet.tests.test_views_hello:HelloViewTest.test_returns_info_about_url_and_version



Definition of done
==================

* Tests pass;
* Code added comes with tests;
* Documentation is up to date.
