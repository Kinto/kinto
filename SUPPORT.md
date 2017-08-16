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
