Contributing
############


Setup your development environment
==================================

To prepare your system with Postgres and Redis please refer to the Installation guide.

Make sure you have python3.4 installed on your system.

To install, on linux run:

::
    $ sudo apt-get install python3.4-dev

On OSX run:

::
    $ brew install python3.4

Prepare your project environment by running:

::

    $ make install-dev

You might need to install curl. On linux run:

::

    $ sudo apt-get install curl

On OSX, you should have curl installed already. If for some reasons you don't, run:

::

    $ brew install curl

Install packages as usual, for example install needed packages with:

::

    $ pip install -r dev-requirements.txt
    $ pip install tox

Prepare and run Kinto:

::

    $ make runkinto

On OSX especially you might get the following error when running tests:

::
    $ ValueError: unknown locale: UTF-8

If this is the case add the following to your ~/.bash_profile:

::
    export LC_ALL=en_US.UTF-8
    export LANG=en_US.UTF-8

Then run:

::
    $ source ~/.bash_profile


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
