"""
This module is a release hook for `zest.releaser <https://zestreleaser.readthedocs.io>`_
in order to build the Kinto Admin UI bundle just before it is packaged.

* See hooks in :file:`setup.cfg`
* `Documentation <http://zestreleaser.readthedocs.io/en/latest/entrypoints.html>`_
"""

import subprocess


def after_checkout(data):
    """
    During the ``release`` process, the current tag is checked out in a
    temporary folder. We build the Kinto Admin at this step, just before
    the files are gathered for the final Python package.

    .. note::

        The ``node_modules`` folder is excluded using :file:`MANIFEST.in`.
    """
    subprocess.run(["make", "build-kinto-admin"])
