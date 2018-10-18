.. _community:


Community
#########

You can check out Kinto on GitHub at https://github.com/Kinto/kinto/.

.. _communication_channels:

Communication channels
======================

* Questions tagged ``kinto`` on `Stack Overflow <http://stackoverflow.com/questions/tagged/kinto>`_.
* Our IRC channel ``#kinto`` on ``irc.freenode.net`` —
  `Click here to access the web client <https://kiwiirc.com/client/irc.freenode.net/?#kinto>`_
* If you prefer to use slack, head over to: https://slack.kinto-storage.org/
* Our team blog http://www.servicedenuages.fr/
* `The Kinto mailing list <https://mail.mozilla.org/listinfo/kinto>`_.
* Some `#Kinto <https://twitter.com/search?q=%23Kinto>`_ mentions on Twitter :)

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
for bug fixes and features! See :github:`open issues <Kinto/kinto/labels/documentation>`.


Submit feedback
---------------

Any issue with the |question label|_ is open for feedback, so feel free to
share your thoughts with us!

.. |question label| replace:: **question** label
.. _`question label`: <https://github.com/Kinto/kinto/labels/question>

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

3. Setup a local PostgreSQL database for the tests (:ref:`more details <postgresql-install>`)::

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

    tox -e lint

7. Don't forget to check that your changes pass the tests::

    make tests

8. (Optional) Install a git hook::

    therapist install

9. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

10. Submit a pull request through the GitHub website.


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
3. *TravisCI* integration tests should be *green* :) It will make sure the tests
   pass with `every supported version of Python <https://github.com/Kinto/kinto/blob/master/tox.ini#L2>`_.


Hack core libraries
-------------------

If you want to run *Kinto* with some core libraries under development (like *Cornice*),
just install them from your local folder using ``pip``.

For example:

::

    cd ..
    git clone https://github.com/mozilla-services/cornice.git
    cd kinto/
    .venv/bin/pip install -e ../cornice/


Cleaning your environment
-------------------------

There are three levels of cleaning your environment:

 - ``make clean`` will remove ``*.pyc`` files and ``__pycache__`` directory.
 - ``make distclean`` will also remove ``*.egg-info`` files and ``*.egg``,
   ``build`` and ``dist`` directories.
 - ``make maintainer-clean`` will also remove the ``.tox`` and the
   ``.venv`` directories.


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

.. code-block:: bash

     $ git checkout -b prepare-X.Y.Z
     $ longtest
     $ prerelease

- Merge remaining pull requests
- Update ``CHANGELOG.rst``
- If API was updated, update API changelog in :file:`docs/api/index.rst`
- Make sure ``HTTP_API_VERSION`` is up-to-date in :file:`kinto/__init__.py`
- Update the link in :file:`docs/configuration/production.rst`
- Update the **kinto-admin** version in :file:`kinto/plugins/admin/package.json` if needed
  (`available releases <https://github.com/Kinto/kinto-admin/releases>`_)
- If **kinto-admin** was updated, run ``npm install`` from the `kinto/plugins/admin/` folder in order to refresh the ``package-lock.json`` file

- Update :file:`CONTRIBUTORS.rst`. The following hairy command will output the full list:

.. code-block:: bash

     $ git shortlog -sne | awk '{$1=""; sub(" ", ""); print}' | awk -F'<' '!x[$1]++' | awk -F'<' '!x[$2]++' | sort

- Open a pull-request to release the new version.

.. code-block:: bash

     $ git commit -a --amend
     $ git push origin prepare-X.Y.Z


Step 2
------

Once the pull-request is validated, merge it and do a release.
Use the ``release`` command to invoke the ``setup.py``, which builds and uploads to PyPI.

.. important::

    The Kinto Admin bundle will be built during the release process. Make sure
    a recent version of ``npm`` is available in your shell when running ``release``.

.. code-block:: bash

    $ git checkout master
    $ git merge --no-ff prepare-X.Y.Z
    $ release
    $ postrelease

Step 3
------

As a final step:

- Close the milestone in GitHub
- Create next milestone in GitHub in the case of a major release
- Add entry in GitHub release page
- Check that the version in ReadTheDocs is up-to-date
- Check that a Docker image was built
- Send mail to ML (If major release)
- Tweet about it!

Upgrade:

- Deploy new version on demo server
- Upgrade dependency in ``kinto-dist`` repo
- Upgrade version targetted in ``kinto-heroku`` repo
- Upgrade version of Kinto server for the tests of clients and plugins repos
  (*kinto-http.js, kinto-http.py, kinto-attachment, etc.*)

That's all folks!
