========================================
structlog: Structured Logging for Python
========================================

.. image:: https://travis-ci.org/hynek/structlog.svg?branch=master
   :target: https://travis-ci.org/hynek/structlog

.. image:: https://codecov.io/github/hynek/structlog/coverage.svg?branch=master
   :target: https://codecov.io/github/hynek/structlog?branch=master

.. image:: https://www.irccloud.com/invite-svg?channel=%23structlog&amp;hostname=irc.freenode.net&amp;port=6697&amp;ssl=1
   :target: https://www.irccloud.com/invite?channel=%23structlog&amp;hostname=irc.freenode.net&amp;port=6697&amp;ssl=1

``structlog`` makes structured logging in Python easy by *augmenting* your *existing* logger.
It allows you to split your log entries up into key/value pairs and build them incrementally without annoying boilerplate code.

.. code-block:: pycon

   >>> from structlog import get_logger
   >>> log = get_logger()
   >>> log.info("key_value_logging", out_of_the_box=True, effort=0)
   out_of_the_box=True effort=0 event='key_value_logging'
   >>> log = log.bind(user='anonymous', some_key=23)
   >>> log = log.bind(user='hynek', another_key=42)
   >>> log.info('user.logged_in', happy=True)
   some_key=23 user='hynek' another_key=42 happy=True event='user.logged_in'

.. begin

It's dual-licensed under `Apache License, version 2 <http://choosealicense.com/licenses/apache/>`_ and `MIT <http://choosealicense.com/licenses/mit/>`_, available from `PyPI <https://pypi.python.org/pypi/structlog/>`_, the source code can be found on `GitHub <https://github.com/hynek/structlog>`_, the documentation at http://www.structlog.org/.

``structlog`` targets Python 2.7, 3.4 and newer, and PyPy.

If you need any help, visit us on ``#structlog`` on `Freenode <https://freenode.net>`_!


Release Information
===================

16.1.0 (2016-05-24)
-------------------

Backward-incompatible changes:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Python 3.3 and 2.6 aren't supported anymore.
  They may work by chance but any effort to keep them working has ceased.

  The last Python 2.6 release was on October 29, 2013 and isn't supported by the CPython core team anymore.
  Major Python packages like Django and Twisted dropped Python 2.6 a while ago already.

  Python 3.3 never had a significant user base and wasn't part of any distribution's LTS release.

Changes:
^^^^^^^^

- Add a ``drop_missing`` argument to ``KeyValueRenderer``.
  If ``key_order`` is used and a key is missing a value, it's not rendered at all instead of being rendered as ``None``.
  `#67 <https://github.com/hynek/structlog/pull/67>`_
- Exceptions without a ``__traceback__`` are now also rendered on Python 3.
- Don't cache loggers in lazy proxies returned from ``get_logger()``.
  This lead to in-place mutation of them if used before configuration which in turn lead to the problem that configuration was applied only partially to them later.
  `#72 <https://github.com/hynek/structlog/pull/72>`_

`Full changelog <http://www.structlog.org/en/stable/changelog.html>`_.

Authors
=======

``structlog`` is written and maintained by `Hynek Schlawack <https://hynek.me/>`_.
It’s inspired by previous work done by `Jean-Paul Calderone <http://as.ynchrono.us/>`_ and `David Reid <https://dreid.org/>`_.

The development is kindly supported by `Variomedia AG <https://www.variomedia.de/>`_.

A full list of contributors can be found on GitHub’s `overview <https://github.com/hynek/structlog/graphs/contributors>`_.
Some of them disapprove of the addition of thread local context data. :)


