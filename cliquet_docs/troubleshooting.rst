Troubleshooting
###############

.. _troubleshooting:

We are doing the best we can so you do not have to read this section.

That said, we have included solutions (or at least explanations) for
some common problems below.

If you do not find a solution to your problem here, please
:ref:`ask for help <communication_channels>`!


ConnectionError: localhost:6379. nodename nor servname provided, or not known
=============================================================================

Make sure */etc/hosts* has correct mapping to localhost.


IOError: [Errno 24] Too many open files
=======================================

Make sure that max number of connections to redis-server and the max
number of file handlers in operating system have access to required
memory.

To fix this, increase the open file limit for non-root user::

  $ ulimit -n 1024


ERROR: InterpreterNotFound: pypy
================================

You need to install `Pypy <http://pypy.org/>`_ so that it can be found
by tox.
