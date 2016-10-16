# testutils.py - utility module for psycopg2 testing.

#
# Copyright (C) 2010-2011 Daniele Varrazzo  <daniele.varrazzo@gmail.com>
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


# Use unittest2 if available. Otherwise mock a skip facility with warnings.

import os
import platform
import sys
from functools import wraps
from testconfig import dsn, repl_dsn

try:
    import unittest2
    unittest = unittest2
except ImportError:
    import unittest
    unittest2 = None

if hasattr(unittest, 'skipIf'):
    skip = unittest.skip
    skipIf = unittest.skipIf

else:
    import warnings

    def skipIf(cond, msg):
        def skipIf_(f):
            @wraps(f)
            def skipIf__(self):
                if cond:
                    warnings.warn(msg)
                    return
                else:
                    return f(self)
            return skipIf__
        return skipIf_

    def skip(msg):
        return skipIf(True, msg)

    def skipTest(self, msg):
        warnings.warn(msg)
        return

    unittest.TestCase.skipTest = skipTest

# Silence warnings caused by the stubbornness of the Python unittest
# maintainers
# http://bugs.python.org/issue9424
if not hasattr(unittest.TestCase, 'assert_') \
or unittest.TestCase.assert_ is not unittest.TestCase.assertTrue:
    # mavaff...
    unittest.TestCase.assert_ = unittest.TestCase.assertTrue
    unittest.TestCase.failUnless = unittest.TestCase.assertTrue
    unittest.TestCase.assertEquals = unittest.TestCase.assertEqual
    unittest.TestCase.failUnlessEqual = unittest.TestCase.assertEqual


class ConnectingTestCase(unittest.TestCase):
    """A test case providing connections for tests.

    A connection for the test is always available as `self.conn`. Others can be
    created with `self.connect()`. All are closed on tearDown.

    Subclasses needing to customize setUp and tearDown should remember to call
    the base class implementations.
    """
    def setUp(self):
        self._conns = []

    def tearDown(self):
        # close the connections used in the test
        for conn in self._conns:
            if not conn.closed:
                conn.close()

    def connect(self, **kwargs):
        try:
            self._conns
        except AttributeError, e:
            raise AttributeError(
                "%s (did you forget to call ConnectingTestCase.setUp()?)"
                % e)

        if 'dsn' in kwargs:
            conninfo = kwargs.pop('dsn')
        else:
            conninfo = dsn
        import psycopg2
        conn = psycopg2.connect(conninfo, **kwargs)
        self._conns.append(conn)
        return conn

    def repl_connect(self, **kwargs):
        """Return a connection set up for replication

        The connection is on "PSYCOPG2_TEST_REPL_DSN" unless overridden by
        a *dsn* kwarg.

        Should raise a skip test if not available, but guard for None on
        old Python versions.
        """
        if 'dsn' not in kwargs:
            kwargs['dsn'] = repl_dsn
        import psycopg2
        try:
            conn = self.connect(**kwargs)
        except psycopg2.OperationalError, e:
            return self.skipTest("replication db not configured: %s" % e)

        conn.autocommit = True
        return conn

    def _get_conn(self):
        if not hasattr(self, '_the_conn'):
            self._the_conn = self.connect()

        return self._the_conn

    def _set_conn(self, conn):
        self._the_conn = conn

    conn = property(_get_conn, _set_conn)


def decorate_all_tests(cls, *decorators):
    """
    Apply all the *decorators* to all the tests defined in the TestCase *cls*.
    """
    for n in dir(cls):
        if n.startswith('test'):
            for d in decorators:
                setattr(cls, n, d(getattr(cls, n)))


def skip_if_no_uuid(f):
    """Decorator to skip a test if uuid is not supported by Py/PG."""
    @wraps(f)
    def skip_if_no_uuid_(self):
        try:
            import uuid
        except ImportError:
            return self.skipTest("uuid not available in this Python version")

        try:
            cur = self.conn.cursor()
            cur.execute("select typname from pg_type where typname = 'uuid'")
            has = cur.fetchone()
        finally:
            self.conn.rollback()

        if has:
            return f(self)
        else:
            return self.skipTest("uuid type not available on the server")

    return skip_if_no_uuid_


def skip_if_tpc_disabled(f):
    """Skip a test if the server has tpc support disabled."""
    @wraps(f)
    def skip_if_tpc_disabled_(self):
        from psycopg2 import ProgrammingError
        cnn = self.connect()
        cur = cnn.cursor()
        try:
            cur.execute("SHOW max_prepared_transactions;")
        except ProgrammingError:
            return self.skipTest(
                "server too old: two phase transactions not supported.")
        else:
            mtp = int(cur.fetchone()[0])
        cnn.close()

        if not mtp:
            return self.skipTest(
                "server not configured for two phase transactions. "
                "set max_prepared_transactions to > 0 to run the test")
        return f(self)

    return skip_if_tpc_disabled_


def skip_if_no_namedtuple(f):
    @wraps(f)
    def skip_if_no_namedtuple_(self):
        try:
            from collections import namedtuple
        except ImportError:
            return self.skipTest("collections.namedtuple not available")
        else:
            return f(self)

    return skip_if_no_namedtuple_


def skip_if_no_iobase(f):
    """Skip a test if io.TextIOBase is not available."""
    @wraps(f)
    def skip_if_no_iobase_(self):
        try:
            from io import TextIOBase
        except ImportError:
            return self.skipTest("io.TextIOBase not found.")
        else:
            return f(self)

    return skip_if_no_iobase_


def skip_before_postgres(*ver):
    """Skip a test on PostgreSQL before a certain version."""
    ver = ver + (0,) * (3 - len(ver))
    def skip_before_postgres_(f):
        @wraps(f)
        def skip_before_postgres__(self):
            if self.conn.server_version < int("%d%02d%02d" % ver):
                return self.skipTest("skipped because PostgreSQL %s"
                    % self.conn.server_version)
            else:
                return f(self)

        return skip_before_postgres__
    return skip_before_postgres_

def skip_after_postgres(*ver):
    """Skip a test on PostgreSQL after (including) a certain version."""
    ver = ver + (0,) * (3 - len(ver))
    def skip_after_postgres_(f):
        @wraps(f)
        def skip_after_postgres__(self):
            if self.conn.server_version >= int("%d%02d%02d" % ver):
                return self.skipTest("skipped because PostgreSQL %s"
                    % self.conn.server_version)
            else:
                return f(self)

        return skip_after_postgres__
    return skip_after_postgres_

def skip_before_python(*ver):
    """Skip a test on Python before a certain version."""
    def skip_before_python_(f):
        @wraps(f)
        def skip_before_python__(self):
            if sys.version_info[:len(ver)] < ver:
                return self.skipTest("skipped because Python %s"
                    % ".".join(map(str, sys.version_info[:len(ver)])))
            else:
                return f(self)

        return skip_before_python__
    return skip_before_python_

def skip_from_python(*ver):
    """Skip a test on Python after (including) a certain version."""
    def skip_from_python_(f):
        @wraps(f)
        def skip_from_python__(self):
            if sys.version_info[:len(ver)] >= ver:
                return self.skipTest("skipped because Python %s"
                    % ".".join(map(str, sys.version_info[:len(ver)])))
            else:
                return f(self)

        return skip_from_python__
    return skip_from_python_

def skip_if_no_superuser(f):
    """Skip a test if the database user running the test is not a superuser"""
    @wraps(f)
    def skip_if_no_superuser_(self):
        from psycopg2 import ProgrammingError
        try:
            return f(self)
        except ProgrammingError, e:
            import psycopg2.errorcodes
            if e.pgcode == psycopg2.errorcodes.INSUFFICIENT_PRIVILEGE:
                self.skipTest("skipped because not superuser")
            else:
                raise

    return skip_if_no_superuser_

def skip_if_green(reason):
    def skip_if_green_(f):
        @wraps(f)
        def skip_if_green__(self):
            from testconfig import green
            if green:
                return self.skipTest(reason)
            else:
                return f(self)

        return skip_if_green__
    return skip_if_green_

skip_copy_if_green = skip_if_green("copy in async mode currently not supported")

def skip_if_no_getrefcount(f):
    @wraps(f)
    def skip_if_no_getrefcount_(self):
        if not hasattr(sys, 'getrefcount'):
            return self.skipTest('skipped, no sys.getrefcount()')
        else:
            return f(self)
    return skip_if_no_getrefcount_

def skip_if_windows(f):
    """Skip a test if run on windows"""
    @wraps(f)
    def skip_if_windows_(self):
        if platform.system() == 'Windows':
            return self.skipTest("Not supported on Windows")
        else:
            return f(self)
    return skip_if_windows_


def script_to_py3(script):
    """Convert a script to Python3 syntax if required."""
    if sys.version_info[0] < 3:
        return script

    import tempfile
    f = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    f.write(script.encode())
    f.flush()
    filename = f.name
    f.close()

    # 2to3 is way too chatty
    import logging
    logging.basicConfig(filename=os.devnull)

    from lib2to3.main import main
    if main("lib2to3.fixes", ['--no-diffs', '-w', '-n', filename]):
        raise Exception('py3 conversion failed')

    f2 = open(filename)
    try:
        return f2.read()
    finally:
        f2.close()
        os.remove(filename)

class py3_raises_typeerror(object):

    def __enter__(self):
        pass

    def __exit__(self, type, exc, tb):
        if sys.version_info[0] >= 3:
            assert type is TypeError
            return True
