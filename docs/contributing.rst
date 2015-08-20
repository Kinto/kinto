.. _contributing:

Contributing
############

Thank you for considering to contribute to *Kinto*!

.. note::

    No contribution is too small; please submit as many fixes for typos and
    grammar bloopers as you can!


How to contribute
=================

Report bugs
-----------

Report bugs at https://github.com/Kinto/kinto/issues/new.

If you are reporting a bug, please include:

* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix bugs
--------

Look through the GitHub issues for bugs. We added a label **[easy-pick]** on bugs
that can be tackled by newcomers.

Implement features
------------------

Look through the GitHub issues for features. Anything tagged with **[enhancement]**
is open to whoever wants to implement it.

Write documentation
-------------------

*Kinto* could always use more documentation, whether as part of the
official docs, in docstrings, or even on the Web in blog posts,
articles, and such.

Submit feedback
---------------

We added a label **[question]** on issues where feedback is required. Don't
be shy and share your thoughts!

Otherwise, the best way to send feedback is to file a new issue on Github.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)


Communication channels
======================

* Questions tagged ``kinto`` on `Stackflow <http://stackoverflow.com/questions/tagged/kinto>`_
* Our IRC channel ``#storage`` on ``irc.mozilla.org``!
* Our team blog http://www.servicedenuages.fr/
* Some ``#Kinto`` mentions on Twitter :)


Hack
====

Ready to contribute? Here's how to set up *Kinto* for local development.

Get started!
------------

1. Fork the *Kinto* repo on GitHub.
2. Clone your fork locally::

    git clone git@github.com:your_name_here/kinto.git

3. Install and run *Kinto* locally::

    make serve

4. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass the tests::

    make test

6. Commit your changes and push yor branch to GitHub::

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
   pass with every supported versions of Python.


Hack core libraries
-------------------

If you want to run *Kinto* with some core libraries under development (like *Cliquet* or *Cornice*),
just install them from your local folder using ``pip``.

For example :

::

    cd ..
    git clone https://github.com/mozilla-services/cliquet.git
    cd kinto/
    .venv/bin/pip install -e ../cliquet/


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


Troubleshooting
===============

*Coming soon* !

