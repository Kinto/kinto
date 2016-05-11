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
* Run a PostgreSQL 9.4 ``testdb`` database on ``localhost:5432`` with user
  ``postgres/postgres``. The database encoding should be ``UTF-8``, and the
  database timezone should be ``UTC``.

::

    make tests

Run a single test
-----------------

For Test-Driven Development, it is a possible to run a single test case, in order
to speed-up the execution:

::

    nosetests -s --with-mocha-reporter cliquet.tests.test_views_hello:HelloViewTest.test_returns_info_about_url_and_version


Load tests
----------

A load test is provided in order to run end-to-end tests on *Cliquet* through a sample application,
or prevent regressions in terms of performance.

The following ``make`` command will check briefly the overall sanity of the API,
by running a server and running a very few random HTTP requests on it.

::

    make loadtest-check-simulation

It is possible to customise this load test, by focusing on a single action,
or customise the number of users and hits.

First, run the test application manually in a terminal: ::

    cd loadtests/
    pserve loadtests/testapp.ini

And then, run the test suite against it: ::

    SERVER_URL=http://localhost:8888 make test -e

To run a specific action, specify it with: ::

    LOAD_ACTION=batch_create SERVER_URL=http://localhost:8888 make test -e

Or a specific configuration: ::

    cp test.ini custom.ini
    CONFIG=custom.ini SERVER_URL=http://localhost:8888 make test -e


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


.. _communication_channels:

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


How to release
==============

In order to prepare a new release, we are following the following steps.

The `prerelease` and `postrelease` commands are coming from `zest.releaser
<https://pypi.python.org/pypi/zest.releaser>`_.

Install `zest.releaser` with the `recommended` dependencies. They contain
`wheel` and `twine`, which are required to release a new version.

.. code-block:: bash

    $ pip install "zest.releaser[recommended]"

Step 1
------

- Merge remaining pull requests
- Update ``CHANGELOG.rst``
- Update version in ``cliquet_docs/conf.py``
- Known good versions of dependencies in ``requirements.txt``
- Update ``CONTRIBUTORS.rst`` using: ``git shortlog -sne | awk '{$1=""; sub(" ", ""); print}' | awk -F'<' '!x[$1]++' | awk -F'<' '!x[$2]++' | sort``

.. code-block:: bash

     $ git checkout -b prepare-X.Y.Z
     $ prerelease
     $ vim cliquet_docs/conf.py
     $ make build-requirements
     $ git commit -a --amend
     $ git push origin prepare-X.Y.Z

- Open a pull-request with to release the version.

Step 2
------

Once the pull-request is validated, merge it and do a release.
Use the ``release`` command to invoke the ``setup.py``, which builds and uploads to PyPI

.. code-block:: bash

    $ git checkout master
    $ git merge --no-ff prepare-X.Y.Z
    $ release
    $ postrelease

Step 3
------

As a final step:

- Close the milestone in Github
- Add entry in Github release page
- Create next milestone in Github in the case of a major release
- Configure the version in ReadTheDocs
- Send mail to ML (If major release)

That's all folks!


Cleaning your environment
=========================

There are three levels of cleaning your environment:

 - ``make clean`` will remove ``*.pyc`` files and ``__pycache__`` directory.
 - ``make distclean`` will also remove ``*.egg-info`` files and ``*.egg``,
   ``build`` and ``dist`` directories.
 - ``make maintainer-clean`` will also remove the ``.tox`` and the
   ``.venv`` directories.
