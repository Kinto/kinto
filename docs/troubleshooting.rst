Troubleshooting
###############

.. _troubleshooting:

We are doing the best we can so you do not have to read this section.

That said, we have included solutions (or at least explanations) for
some common problems below.

If you do not find a solution to your problem here, please
:ref:`ask for help <communication_channels>`!


Module object has no attribute 'register_json'
==============================================

Kinto uses the ``JSONBin`` feature of PostgreSQL, which is used to
store native ``JSON objects`` efficiently. Support for this feature
was added in PostgreSQL 9.4.

This is a hard requirement for postgresql backends, therefore you
will either need to **use PostgreSQL 9.4 (or greater)**, or
:ref:`use a different backend <configuration-backends>` entirely.


No module named functools
=========================

With some old version of pip, the jsonschema package does not install properly
because one if its dependencies is missing.

To fix this, you can either install it locally or upgrade your version of pip::

  $ pip install --upgrade pip


socket.error: [Errno 48] Address already in use
===============================================

Another process has occupied Kinto's default port 8888.

To fix this, see which service is running on port 8888::

$ sudo lsof -i :8888

and kill the process using PID from output::

$ kill -kill [PID]


cliquet.storage.exceptions.BackendError: OperationalError [Postgres Service]
============================================================================

Make sure that postgres server is running properly.