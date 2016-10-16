"""A Python driver for PostgreSQL

psycopg is a PostgreSQL_ database adapter for the Python_ programming
language. This is version 2, a complete rewrite of the original code to
provide new-style classes for connection and cursor objects and other sweet
candies. Like the original, psycopg 2 was written with the aim of being very
small and fast, and stable as a rock.

Homepage: http://initd.org/projects/psycopg2

.. _PostgreSQL: http://www.postgresql.org/
.. _Python: http://www.python.org/

:Groups:
  * `Connections creation`: connect
  * `Value objects constructors`: Binary, Date, DateFromTicks, Time,
    TimeFromTicks, Timestamp, TimestampFromTicks
"""
# psycopg/__init__.py - initialization of the psycopg module
#
# Copyright (C) 2003-2010 Federico Di Gregorio  <fog@debian.org>
#
# psycopg2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# In addition, as a special exception, the copyright holders give
# permission to link this program with the OpenSSL library (or with
# modified versions of OpenSSL that use the same license as OpenSSL),
# and distribute linked combinations including the two.
#
# You must obey the GNU Lesser General Public License in all respects for
# all of the code used other than OpenSSL.
#
# psycopg2 is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
# License for more details.

# Import modules needed by _psycopg to allow tools like py2exe to do
# their work without bothering about the module dependencies.

# Note: the first internal import should be _psycopg, otherwise the real cause
# of a failed loading of the C module may get hidden, see
# http://archives.postgresql.org/psycopg/2011-02/msg00044.php

# Import the DBAPI-2.0 stuff into top-level module.

from psycopg2._psycopg import BINARY, NUMBER, STRING, DATETIME, ROWID

from psycopg2._psycopg import Binary, Date, Time, Timestamp
from psycopg2._psycopg import DateFromTicks, TimeFromTicks, TimestampFromTicks

from psycopg2._psycopg import Error, Warning, DataError, DatabaseError, ProgrammingError
from psycopg2._psycopg import IntegrityError, InterfaceError, InternalError
from psycopg2._psycopg import NotSupportedError, OperationalError

from psycopg2._psycopg import _connect, apilevel, threadsafety, paramstyle
from psycopg2._psycopg import __version__

from psycopg2 import tz


# Register default adapters.

import psycopg2.extensions as _ext
_ext.register_adapter(tuple, _ext.SQL_IN)
_ext.register_adapter(type(None), _ext.NoneAdapter)

# Register the Decimal adapter here instead of in the C layer.
# This way a new class is registered for each sub-interpreter.
# See ticket #52
try:
    from decimal import Decimal
except ImportError:
    pass
else:
    from psycopg2._psycopg import Decimal as Adapter
    _ext.register_adapter(Decimal, Adapter)
    del Decimal, Adapter

import re

def _param_escape(s,
        re_escape=re.compile(r"([\\'])"),
        re_space=re.compile(r'\s')):
    """
    Apply the escaping rule required by PQconnectdb
    """
    if not s: return "''"

    s = re_escape.sub(r'\\\1', s)
    if re_space.search(s):
        s = "'" + s + "'"

    return s

del re


def connect(dsn=None,
        database=None, user=None, password=None, host=None, port=None,
        connection_factory=None, cursor_factory=None, async=False, **kwargs):
    """
    Create a new database connection.

    The connection parameters can be specified either as a string:

        conn = psycopg2.connect("dbname=test user=postgres password=secret")

    or using a set of keyword arguments:

        conn = psycopg2.connect(database="test", user="postgres", password="secret")

    The basic connection parameters are:

    - *dbname*: the database name (only in dsn string)
    - *database*: the database name (only as keyword argument)
    - *user*: user name used to authenticate
    - *password*: password used to authenticate
    - *host*: database host address (defaults to UNIX socket if not provided)
    - *port*: connection port number (defaults to 5432 if not provided)

    Using the *connection_factory* parameter a different class or connections
    factory can be specified. It should be a callable object taking a dsn
    argument.

    Using the *cursor_factory* parameter, a new default cursor factory will be
    used by cursor().

    Using *async*=True an asynchronous connection will be created.

    Any other keyword parameter will be passed to the underlying client
    library: the list of supported parameters depends on the library version.

    """
    items = []
    if database is not None:
        items.append(('dbname', database))
    if user is not None:
        items.append(('user', user))
    if password is not None:
        items.append(('password', password))
    if host is not None:
        items.append(('host', host))
    if port is not None:
        items.append(('port', port))

    items.extend([(k, v) for (k, v) in kwargs.iteritems() if v is not None])

    if dsn is not None and items:
        raise TypeError(
            "'%s' is an invalid keyword argument when the dsn is specified"
                % items[0][0])

    if dsn is None:
        if not items:
            raise TypeError('missing dsn and no parameters')
        else:
            dsn = " ".join(["%s=%s" % (k, _param_escape(str(v)))
                for (k, v) in items])

    conn = _connect(dsn, connection_factory=connection_factory, async=async)
    if cursor_factory is not None:
        conn.cursor_factory = cursor_factory

    return conn
