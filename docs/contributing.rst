Contributing
############

Thank you for considering to contribute to *Cliquet*!

.. note::

    No contribution is too small; we welcome fixes about typos and grammar
    bloopers. Don't hesitate to send us a pull request!

.. note::

    Open a pull-request even if your contribution is not ready yet! It can
    be discussed and improved collaboratively, and avoid having you doing a lot
    of work without getting feedback.


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

In order to have your changes incorporated, you need to respect these rules:

* **Tests pass**; Travis-CI will build the tests for you on the branch when you
  push it.
* **Code added comes with tests**; We try to have a 100% coverage on the codebase to avoid
  surprises. No code should be untested :) If you fail to see how to test your
  changes, feel welcome to say so in the pull request, we'll gladly help you to
  find out.
* **Documentation is up to date**;


IRC channel
===========

If you want to discuss with the team behind *Cliquet*, please come and join us
on ``#storage`` on ``irc.mozilla.org``.

* Because of differing time zones, you may not get an immediate response to
  your question, but please be patient and stay logged into IRC — someone will
  almost always respond if you wait long enough (it may take a few hours).
* If you don’t have an IRC client handy, use `the webchat
  <https://kiwiirc.com/client/irc.mozilla.org/?#storage>`_ for quick feedback.
* You can direct your IRC client to the channel using `this IRC link
  <irc://irc.mozilla.org/storage>`_ or you can manually join the #storage IRC
  channel on the mozilla IRC network.
