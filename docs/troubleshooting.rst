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


kinto.core.storage.exceptions.BackendError: OperationalError [Postgres Service]
===============================================================================

Make sure that postgres server is running properly.


password authentication failed for user "postgres"
==================================================

::


	kinto.core.storage.exceptions.BackendError: OperationalError: (psycopg2.OperationalError) FATAL:  password authentication failed for user "postgres"
	FATAL:  password authentication failed for user "postgres"

By default, the PostgreSQL Debian package does not setup any password for the ``postgres`` user. You can choose one with::

	sudo -u postgres psql postgres

	# \password postgres

	Enter new password:
	...


bind(): No such file or directory [uwsgi error]
===============================================

Make sure that the path you defined for the socket parameter of the uwsgi
configuration exists.

To fix this::

  socket = /var/run/uwsgi/kinto.sock

Make sure the directory exists::

  sudo mkdir -p /var/run/uwsgi

Also, make sure the user that runs uwsgi can access /var/run/uwsgi and can
write in the uwsgi directory.

ERROR: ImportError: No module named .... [uwsgi error]
=========================================================

You might get some error like::

  ImportError: No module named cornice
  unable to load app 0 (mountpoint='') (callable not found or import error)
  *** no app loaded. going in full dynamic mode ***
    File "app.wsgi", line 8, in <module>
      from kinto import main
    File "./kinto/__init__.py", line 4, in <module>
      import kinto.core
    File "./kinto/core/__init__.py", line 5, in <module>
      from cornice import Service as CorniceService
  ImportError: No module named cornice
  unable to load app 0 (mountpoint='') (callable not found or import error)

The reason is that the user/group (``uid`` and ``gid`` specified under [uwsgi] section in kinto.ini) not being able to access the sourcecode.

To fix this, grant ``kinto`` user/group access to the source folder::

  $ chgrp kinto -R .
  $ chown kinto -R .

AssertionError: Unexpected database encoding sql_ascii
======================================================

On some configuration, the default encoding is SQL_ASCII instead of UTF-8. This
can also happen with other database encoding. The encoding expected by kinto is
"UTF-8".

To remediate this, you can issue the following command, once ``pgsql`` open::

  update pg_database set encoding = pg_char_to_encoding('UTF8') where datname = '<your db name>';


bind: address already in use
============================

You will probably have a more precise error message telling you which
port is already in use: ``listen tcp 0.0.0.0:5432: bind: address
already in use``.

This happens when you are trying to start a docker image on the same
port of an existing service running on your machine.

For example, with ``postgresql``, you can either stop the local service::

  sudo service postgresql stop

Or you can run your docker on another port (i.e: ``5433``)::

  postgres=$(sudo docker run -e POSTGRES_PASSWORD=postgres -d -p 5433:5432 postgres)


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
