.. _community:

Community
#########

You can check out Kinto on Github at https://github.com/Kinto/kinto/.

.. _communication_channels:

Communication channels
======================

* Questions tagged ``kinto`` on `Stack Overflow <http://stackoverflow.com/questions/tagged/kinto>`_.
* Our IRC channel ``#kinto`` on ``irc.freenode.net`` —
  `Click here to access the web client <https://kiwiirc.com/client/irc.freenode.net/?#kinto>`_
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

This official documentation is maintained in `Github
<https://github.com/Kinto/kinto/>`_, in the ``docs`` directory. Just
run ``make docs`` from the project root to convert the RST source
files into HTML output (in the ``docs/_build/html`` directory). We
accept pull requests for this documentation, just as we accept them
for bug fixes and features!

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


Hack
====

Ready to contribute? Here's how to set up *Kinto* for local development.

Get started!
------------

1. Fork the *Kinto* repo on GitHub.
2. Clone your fork locally::

    git clone git@github.com:your_name_here/kinto.git

3. Install and run *Kinto* locally (:ref:`more details <run-kinto-from-source>`)::

    make serve

4. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass the tests::

    make tests

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.


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


Run load tests
--------------

From the :file:`loadtests` folder:

::

    make test SERVER_URL=http://localhost:8888


Run a particular type of action instead of random:

::

    LOAD_ACTION=batch_create make test SERVER_URL=http://localhost:8888

(*See loadtests source code for an exhaustive list of available actions and
their respective randomness.*)


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
     $ prerelease
     $ vim docs/conf.py

- Merge remaining pull requests
- Update ``CHANGELOG.rst``
- If API was updated, update API changelog in :file:`docs/api/index.rst`
- Update the link in :file:`docs/configuration/production.rst`
- Update :file:`CONTRIBUTORS.rst`. The following hairy command will output the full list:

.. code-block:: bash

     $ git shortlog -sne | awk '{$1=""; sub(" ", ""); print}' | awk -F'<' '!x[$1]++' | awk -F'<' '!x[$2]++' | sort

- Update known good versions of dependencies in ``requirements.txt`` with this command:

.. code-block:: bash

     $ make build-requirements

- Open a pull-request to release the new version.

.. code-block:: bash

     $ git commit -a --amend
     $ git push origin prepare-X.Y.Z


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
- Create next milestone in Github in the case of a major release
- Add entry in Github release page
- Configure the version in ReadTheDocs
- Send mail to ML (If major release)

That's all folks!
