.. _community:


Community
#########

You can check out Kinto on GitHub at https://github.com/Kinto/kinto/.

.. _how-to-contribute:

How to contribute
=================

Thanks for your interest in contributing to *Kinto*!

.. note::

    We love community feedback and are glad to review contributions of any
    size - from typos in the documentation to critical bug fixes - so don't be
    shy!

Report bugs
-----------

Report bugs at https://github.com/Kinto/kinto/issues/new

If you are reporting a bug, please include:

* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix bugs
--------

Check out the `open bugs <https://github.com/Kinto/kinto/issues>`_ - anything
tagged with the |easy-pick label|_ could be a good choice for newcomers.

.. |easy-pick label| replace:: **easy-pick** label
.. _`easy-pick label`: https://github.com/Kinto/kinto/labels/easy-pick


Implement features
------------------

Look through the GitHub issues for features. Anything tagged with |enhancement|_
is open to whoever wants to implement it.

.. |enhancement| replace:: **enhancement**
.. _enhancement:  https://github.com/Kinto/kinto/labels/enhancement

Write documentation
-------------------

*Kinto* could always use more documentation, whether as part of the
official docs, in docstrings, or even on the Web in blog posts,
articles, and such.

This official documentation is maintained in `GitHub
<https://github.com/Kinto/kinto/>`_. The ``docs`` folder contains the documentation sources in `reStructuredText <https://en.wikipedia.org/wiki/ReStructuredText>`_ format. And you can generate the docs locally with::

    make docs

Output is written at ``docs/_build/html/index.html``.

We obviously accept pull requests for this documentation, just as we accept them
for bug fixes and features! See `open issues <https://github.com/Kinto/kinto/labels/documentation>`_.


Submit feedback
---------------

Any issue with the |question label|_ is open for feedback, so feel free to
share your thoughts with us!

.. |question label| replace:: **question** label
.. _`question label`: https://github.com/Kinto/kinto/labels/question

The best way to send feedback is to
`file a new issue <https://github.com/Kinto/kinto/issues/new>`_ on GitHub.

If you are proposing a feature:

* Explain how you envision it working. Try to be as detailed as you can.
* Try to keep the scope as narrow as possible. This will help make it easier
  to implement.
* Feel free to include any code you might already have, even if it's just a
  rough idea. This is a volunteer-driven project, and contributions
  are welcome :)

Contribute.json
---------------

*Kinto* implements the ``GET /contribute.json`` endpoint which provides
structured open source contribution information.

See :ref:`API docs <api-utilities-contribute>`.


Hack
====

Ready to contribute? Here's how to set up *Kinto* for local development.

Get started!
------------

1. Fork the *Kinto* repo on GitHub.
2. Clone your fork locally::

    git clone git@github.com:your_name_here/kinto.git

3. Run ``make test-deps``, or setup a local PostgreSQL database (:ref:`more details <postgresql-install>`)::

    sudo apt-get install postgresql
    sudo -n -u postgres -s -- psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" -U postgres
    sudo -n -u postgres -s -- psql -c "CREATE DATABASE testdb ENCODING 'UTF8' TEMPLATE template0;" -U postgres
    sudo -n -u postgres -s -- psql -c "ALTER DATABASE testdb SET TIMEZONE TO UTC;" -U postgres

4. Install and run *Kinto* locally (:ref:`more details <run-kinto-from-source>`)::

    make serve

5. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

6. When you're done making changes, check that your changes pass linting (requires python >= 3.6)::

    make lint

7. Don't forget to check that your changes pass the tests::

    make tests

8. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

9. Submit a pull request through the GitHub website.


Testing methodology
-------------------

The `tests are the specifications <http://blog.mathieu-leplatre.info/your-tests-as-your-specs.html>`_.

* Each test class represents a situation or feature (e.g. ``class AnonymousCreationTest(unittest.TestCase):``)
* Each test method represents an aspect of the specification (e.g. ``def test_creation_is_allowed_if_enabled_in_settings(self):``)
* Each test method is independant
* The assertions should only correspond to the aspect of the specification that this method targets
* The ``setUp()`` method contains some initialization steps that are shared among the methods
* If the methods have different initialization steps, they should probably be split into different test classes

When contributing a **bug fix**:

1. Write a test that reproduces the problem: it should fail because of the bug
2. Fix the faulty piece of code
3. The test should now pass

When contributing a **new feature**:

* Do not rush on the code
* Step by step, you'll write tests for each aspect and each edge case of the feature
* Start very small: one simple test for the simplest situation

Once you get that simple bit working, you can iterate like this, `a.k.a TDD <https://en.wikipedia.org/wiki/Test-driven_development>`_:

1. Add a new test that will fail because the code does not handle the new case
2. Make the test pass with some new code
3. Track your changes: ``git add -A``
4. Refactor and clean-up if necessary. If you're lost, go back to the previous step with ``git checkout <file>``
5. Commit the changes: ``git commit -am "feature X"``
6. Go to step 1


Pull request guidelines
-----------------------

.. note::

    Open a pull-request even if your contribution is not ready yet! It can
    be discussed and improved collaboratively!

Before we merge a pull request, we check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated.
3. *CI* integration tests should be *green* :)

Hack core libraries
-------------------

If you want to run *Kinto* with some core libraries under development,
just install them from your local folder using ``pip``.

For example:

::

    cd ..
    git clone https://github.com/Kinto/kinto-attachment.git
    cd kinto/
    .venv/bin/pip install -e ../kinto-attachment/


Functional Tests
----------------

In a terminal, run an instance with the provided ``functional.ini`` configuration:

::

    make runkinto

In another terminal, run the end-to-end tests with:

::

    make functional


Browser Tests
-------------
We use `playwright <https://playwright.dev/>`_ for browser testing. The tests included in this repo are very simple and verify the admin UI can at least authenticate with the current kinto back-end. Comprehensive unit tests are maintained in the kinto-admin repo.


In a terminal, run an instance with the provided ``browser.ini`` configuration:

::

    kinto start --ini tests/browser.ini

In another terminal, run the end-to-end tests with:

::

    make browser-test


Cleaning your environment
-------------------------

 - ``make clean``

How to release
==============

In order to prepare a new release, follow these steps:

Step 1
------

- Merge remaining pull requests
- Make sure supported version is up-to-date in :file:`SECURITY.md`
- If API was updated, update API changelog in :file:`docs/api/index.rst`
- Make sure ``HTTP_API_VERSION`` is up-to-date in :file:`kinto/__init__.py`
- Make sure the list of contributors is up-to-date in :file:`CONTRIBUTORS.rst`. The following hairy command will output the full list:

.. code-block:: bash

     $ git shortlog -sne | awk '{$1=""; sub(" ", ""); print}' | awk -F'<' '!x[$1]++' | awk -F'<' '!x[$2]++' | sort

Step 2
------

1. Create a release on Github on https://github.com/Kinto/kinto-attachment/releases/new
2. Create a new tag `X.Y.Z` (*This tag will be created from the target when you publish this release.*)
3. Generate release notes
4. Publish release

Step 3
------

- Check that the version in ReadTheDocs was published
- Check that a Pypi package was published
