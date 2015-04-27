Contributing
############

Thank you for considering to contribute to *Cliquet*!

.. note::

    No contribution is too small; please submit as many fixes for typos and
    grammar bloopers as you can!

.. note::

    Open a pull-request even if your contribution is not ready yet! It can
    be discussed and improved collaboratively!


Setup your development environment
==================================

To prepare your system with Python 3.4, PostgreSQL and Redis, please refer to the
:ref:`installation` guide.

You might need to install `curl <http://curl.haxx.se>`_, if you don't have it already.

Prepare your project environment by running:

::

    $ make install-dev

::

    $ pip install tox

Prepare and run Kinto:

::

    $ make runkinto


OS X
----

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
* Run a Kinto instance using ``make runkinto``

::

    make tests

Run a single test
-----------------

For Test-Driven Development, it is a possible to run a single test case, in order
to speed-up the execution:

::

    nosetests -s --with-mocha-reporter cliquet.tests.test_views_hello:HelloViewTest.test_returns_info_about_url_and_version


Definition of done
==================

* Tests pass;
* Code added comes with tests;
* Documentation is up to date.


IRC channel
===========

Join ``#storage`` on ``irc.mozilla.org``!
