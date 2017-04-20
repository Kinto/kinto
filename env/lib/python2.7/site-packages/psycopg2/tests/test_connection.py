#!/usr/bin/env python

# test_connection.py - unit test for connection attributes
#
# Copyright (C) 2008-2011 James Henstridge  <james@jamesh.id.au>
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

import os
import time
import threading
from operator import attrgetter
from StringIO import StringIO

import psycopg2
import psycopg2.errorcodes
import psycopg2.extensions

from testutils import unittest, decorate_all_tests, skip_if_no_superuser
from testutils import skip_before_postgres, skip_after_postgres
from testutils import ConnectingTestCase, skip_if_tpc_disabled
from testutils import skip_if_windows
from testconfig import dsn, dbname


class ConnectionTests(ConnectingTestCase):
    def test_closed_attribute(self):
        conn = self.conn
        self.assertEqual(conn.closed, False)
        conn.close()
        self.assertEqual(conn.closed, True)

    def test_close_idempotent(self):
        conn = self.conn
        conn.close()
        conn.close()
        self.assert_(conn.closed)

    def test_cursor_closed_attribute(self):
        conn = self.conn
        curs = conn.cursor()
        self.assertEqual(curs.closed, False)
        curs.close()
        self.assertEqual(curs.closed, True)

        # Closing the connection closes the cursor:
        curs = conn.cursor()
        conn.close()
        self.assertEqual(curs.closed, True)

    @skip_before_postgres(8, 4)
    @skip_if_no_superuser
    @skip_if_windows
    def test_cleanup_on_badconn_close(self):
        # ticket #148
        conn = self.conn
        cur = conn.cursor()
        self.assertRaises(psycopg2.OperationalError,
            cur.execute, "select pg_terminate_backend(pg_backend_pid())")

        self.assertEqual(conn.closed, 2)
        conn.close()
        self.assertEqual(conn.closed, 1)

    def test_reset(self):
        conn = self.conn
        # switch isolation level, then reset
        level = conn.isolation_level
        conn.set_isolation_level(0)
        self.assertEqual(conn.isolation_level, 0)
        conn.reset()
        # now the isolation level should be equal to saved one
        self.assertEqual(conn.isolation_level, level)

    def test_notices(self):
        conn = self.conn
        cur = conn.cursor()
        if self.conn.server_version >= 90300:
            cur.execute("set client_min_messages=debug1")
        cur.execute("create temp table chatty (id serial primary key);")
        self.assertEqual("CREATE TABLE", cur.statusmessage)
        self.assert_(conn.notices)

    def test_notices_consistent_order(self):
        conn = self.conn
        cur = conn.cursor()
        if self.conn.server_version >= 90300:
            cur.execute("set client_min_messages=debug1")
        cur.execute("create temp table table1 (id serial); create temp table table2 (id serial);")
        cur.execute("create temp table table3 (id serial); create temp table table4 (id serial);")
        self.assertEqual(4, len(conn.notices))
        self.assert_('table1' in conn.notices[0])
        self.assert_('table2' in conn.notices[1])
        self.assert_('table3' in conn.notices[2])
        self.assert_('table4' in conn.notices[3])

    def test_notices_limited(self):
        conn = self.conn
        cur = conn.cursor()
        if self.conn.server_version >= 90300:
            cur.execute("set client_min_messages=debug1")
        for i in range(0, 100, 10):
            sql = " ".join(["create temp table table%d (id serial);" % j for j in range(i, i+10)])
            cur.execute(sql)

        self.assertEqual(50, len(conn.notices))
        self.assert_('table99' in conn.notices[-1], conn.notices[-1])

    def test_server_version(self):
        self.assert_(self.conn.server_version)

    def test_protocol_version(self):
        self.assert_(self.conn.protocol_version in (2,3),
            self.conn.protocol_version)

    def test_tpc_unsupported(self):
        cnn = self.conn
        if cnn.server_version >= 80100:
            return self.skipTest("tpc is supported")

        self.assertRaises(psycopg2.NotSupportedError,
            cnn.xid, 42, "foo", "bar")

    @skip_before_postgres(8, 2)
    def test_concurrent_execution(self):
        def slave():
            cnn = self.connect()
            cur = cnn.cursor()
            cur.execute("select pg_sleep(4)")
            cur.close()
            cnn.close()

        t1 = threading.Thread(target=slave)
        t2 = threading.Thread(target=slave)
        t0 = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assert_(time.time() - t0 < 7,
            "something broken in concurrency")

    def test_encoding_name(self):
        self.conn.set_client_encoding("EUC_JP")
        # conn.encoding is 'EUCJP' now.
        cur = self.conn.cursor()
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE, cur)
        cur.execute("select 'foo'::text;")
        self.assertEqual(cur.fetchone()[0], u'foo')

    def test_connect_nonnormal_envvar(self):
        # We must perform encoding normalization at connection time
        self.conn.close()
        oldenc = os.environ.get('PGCLIENTENCODING')
        os.environ['PGCLIENTENCODING'] = 'utf-8'    # malformed spelling
        try:
            self.conn = self.connect()
        finally:
            if oldenc is not None:
                os.environ['PGCLIENTENCODING'] = oldenc
            else:
                del os.environ['PGCLIENTENCODING']

    def test_weakref(self):
        from weakref import ref
        import gc
        conn = psycopg2.connect(dsn)
        w = ref(conn)
        conn.close()
        del conn
        gc.collect()
        self.assert_(w() is None)

    def test_commit_concurrency(self):
        # The problem is the one reported in ticket #103. Because of bad
        # status check, we commit even when a commit is already on its way.
        # We can detect this condition by the warnings.
        conn = self.conn
        notices = []
        stop = []

        def committer():
            while not stop:
                conn.commit()
                while conn.notices:
                    notices.append((2, conn.notices.pop()))

        cur = conn.cursor()
        t1 = threading.Thread(target=committer)
        t1.start()
        i = 1
        for i in range(1000):
            cur.execute("select %s;",(i,))
            conn.commit()
            while conn.notices:
                notices.append((1, conn.notices.pop()))

        # Stop the committer thread
        stop.append(True)

        self.assert_(not notices, "%d notices raised" % len(notices))

    def test_connect_cursor_factory(self):
        import psycopg2.extras
        conn = self.connect(cursor_factory=psycopg2.extras.DictCursor)
        cur = conn.cursor()
        cur.execute("select 1 as a")
        self.assertEqual(cur.fetchone()['a'], 1)

    def test_cursor_factory(self):
        self.assertEqual(self.conn.cursor_factory, None)
        cur = self.conn.cursor()
        cur.execute("select 1 as a")
        self.assertRaises(TypeError, (lambda r: r['a']), cur.fetchone())

        self.conn.cursor_factory = psycopg2.extras.DictCursor
        self.assertEqual(self.conn.cursor_factory, psycopg2.extras.DictCursor)
        cur = self.conn.cursor()
        cur.execute("select 1 as a")
        self.assertEqual(cur.fetchone()['a'], 1)

        self.conn.cursor_factory = None
        self.assertEqual(self.conn.cursor_factory, None)
        cur = self.conn.cursor()
        cur.execute("select 1 as a")
        self.assertRaises(TypeError, (lambda r: r['a']), cur.fetchone())

    def test_cursor_factory_none(self):
        # issue #210
        conn = self.connect()
        cur = conn.cursor(cursor_factory=None)
        self.assertEqual(type(cur), psycopg2.extensions.cursor)

        conn = self.connect(cursor_factory=psycopg2.extras.DictCursor)
        cur = conn.cursor(cursor_factory=None)
        self.assertEqual(type(cur), psycopg2.extras.DictCursor)

    def test_failed_init_status(self):
        class SubConnection(psycopg2.extensions.connection):
            def __init__(self, dsn):
                try:
                    super(SubConnection, self).__init__(dsn)
                except Exception:
                    pass

        c = SubConnection("dbname=thereisnosuchdatabasemate password=foobar")
        self.assert_(c.closed, "connection failed so it must be closed")
        self.assert_('foobar' not in c.dsn, "password was not obscured")


class IsolationLevelsTestCase(ConnectingTestCase):

    def setUp(self):
        ConnectingTestCase.setUp(self)

        conn = self.connect()
        cur = conn.cursor()
        try:
            cur.execute("drop table isolevel;")
        except psycopg2.ProgrammingError:
            conn.rollback()
        cur.execute("create table isolevel (id integer);")
        conn.commit()
        conn.close()

    def test_isolation_level(self):
        conn = self.connect()
        self.assertEqual(
            conn.isolation_level,
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def test_encoding(self):
        conn = self.connect()
        self.assert_(conn.encoding in psycopg2.extensions.encodings)

    def test_set_isolation_level(self):
        conn = self.connect()
        curs = conn.cursor()

        levels = [
            (None, psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT),
            ('read uncommitted', psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED),
            ('read committed', psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED),
            ('repeatable read', psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ),
            ('serializable', psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE),
        ]
        for name, level in levels:
            conn.set_isolation_level(level)

            # the only values available on prehistoric PG versions
            if conn.server_version < 80000:
                if level in (
                        psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED,
                        psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ):
                    name, level = levels[levels.index((name, level)) + 1]

            self.assertEqual(conn.isolation_level, level)

            curs.execute('show transaction_isolation;')
            got_name = curs.fetchone()[0]

            if name is None:
                curs.execute('show default_transaction_isolation;')
                name = curs.fetchone()[0]

            self.assertEqual(name, got_name)
            conn.commit()

        self.assertRaises(ValueError, conn.set_isolation_level, -1)
        self.assertRaises(ValueError, conn.set_isolation_level, 5)

    def test_set_isolation_level_abort(self):
        conn = self.connect()
        cur = conn.cursor()

        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("insert into isolevel values (10);")
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_INTRANS,
            conn.get_transaction_status())

        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur.fetchone()[0])

        cur.execute("insert into isolevel values (10);")
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_INTRANS,
            conn.get_transaction_status())
        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur.fetchone()[0])

        cur.execute("insert into isolevel values (10);")
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        self.assertEqual(psycopg2.extensions.TRANSACTION_STATUS_IDLE,
            conn.get_transaction_status())
        cur.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur.fetchone()[0])

    def test_isolation_level_autocommit(self):
        cnn1 = self.connect()
        cnn2 = self.connect()
        cnn2.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cur1 = cnn1.cursor()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur1.fetchone()[0])
        cnn1.commit()

        cur2 = cnn2.cursor()
        cur2.execute("insert into isolevel values (10);")

        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur1.fetchone()[0])

    def test_isolation_level_read_committed(self):
        cnn1 = self.connect()
        cnn2 = self.connect()
        cnn2.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

        cur1 = cnn1.cursor()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur1.fetchone()[0])
        cnn1.commit()

        cur2 = cnn2.cursor()
        cur2.execute("insert into isolevel values (10);")
        cur1.execute("insert into isolevel values (20);")

        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur2.fetchone()[0])
        cnn1.commit()
        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur2.fetchone()[0])

        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur1.fetchone()[0])
        cnn2.commit()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur1.fetchone()[0])

    def test_isolation_level_serializable(self):
        cnn1 = self.connect()
        cnn2 = self.connect()
        cnn2.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

        cur1 = cnn1.cursor()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(0, cur1.fetchone()[0])
        cnn1.commit()

        cur2 = cnn2.cursor()
        cur2.execute("insert into isolevel values (10);")
        cur1.execute("insert into isolevel values (20);")

        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur2.fetchone()[0])
        cnn1.commit()
        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur2.fetchone()[0])

        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(1, cur1.fetchone()[0])
        cnn2.commit()
        cur1.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur1.fetchone()[0])

        cur2.execute("select count(*) from isolevel;")
        self.assertEqual(2, cur2.fetchone()[0])

    def test_isolation_level_closed(self):
        cnn = self.connect()
        cnn.close()
        self.assertRaises(psycopg2.InterfaceError, getattr,
            cnn, 'isolation_level')
        self.assertRaises(psycopg2.InterfaceError,
            cnn.set_isolation_level, 0)
        self.assertRaises(psycopg2.InterfaceError,
            cnn.set_isolation_level, 1)


class ConnectionTwoPhaseTests(ConnectingTestCase):
    def setUp(self):
        ConnectingTestCase.setUp(self)

        self.make_test_table()
        self.clear_test_xacts()

    def tearDown(self):
        self.clear_test_xacts()
        ConnectingTestCase.tearDown(self)

    def clear_test_xacts(self):
        """Rollback all the prepared transaction in the testing db."""
        cnn = self.connect()
        cnn.set_isolation_level(0)
        cur = cnn.cursor()
        try:
            cur.execute(
                "select gid from pg_prepared_xacts where database = %s",
                (dbname,))
        except psycopg2.ProgrammingError:
            cnn.rollback()
            cnn.close()
            return

        gids = [ r[0] for r in cur ]
        for gid in gids:
            cur.execute("rollback prepared %s;", (gid,))
        cnn.close()

    def make_test_table(self):
        cnn = self.connect()
        cur = cnn.cursor()
        try:
            cur.execute("DROP TABLE test_tpc;")
        except psycopg2.ProgrammingError:
            cnn.rollback()
        cur.execute("CREATE TABLE test_tpc (data text);")
        cnn.commit()
        cnn.close()

    def count_xacts(self):
        """Return the number of prepared xacts currently in the test db."""
        cnn = self.connect()
        cur = cnn.cursor()
        cur.execute("""
            select count(*) from pg_prepared_xacts
            where database = %s;""",
            (dbname,))
        rv = cur.fetchone()[0]
        cnn.close()
        return rv

    def count_test_records(self):
        """Return the number of records in the test table."""
        cnn = self.connect()
        cur = cnn.cursor()
        cur.execute("select count(*) from test_tpc;")
        rv = cur.fetchone()[0]
        cnn.close()
        return rv

    def test_tpc_commit(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_PREPARED)
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_commit()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(1, self.count_test_records())

    def test_tpc_commit_one_phase(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit_1p');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_commit()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(1, self.count_test_records())

    def test_tpc_commit_recovered(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit_rec');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        cnn.close()
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        cnn.tpc_commit(xid)

        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(1, self.count_test_records())

    def test_tpc_rollback(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_rollback');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_PREPARED)
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_rollback()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

    def test_tpc_rollback_one_phase(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_rollback_1p');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_rollback()
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

    def test_tpc_rollback_recovered(self):
        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)

        cnn.tpc_begin(xid)
        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_BEGIN)

        cur = cnn.cursor()
        cur.execute("insert into test_tpc values ('test_tpc_commit_rec');")
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn.tpc_prepare()
        cnn.close()
        self.assertEqual(1, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

        cnn = self.connect()
        xid = cnn.xid(1, "gtrid", "bqual")
        cnn.tpc_rollback(xid)

        self.assertEqual(cnn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(0, self.count_xacts())
        self.assertEqual(0, self.count_test_records())

    def test_status_after_recover(self):
        cnn = self.connect()
        self.assertEqual(psycopg2.extensions.STATUS_READY, cnn.status)
        xns = cnn.tpc_recover()
        self.assertEqual(psycopg2.extensions.STATUS_READY, cnn.status)

        cur = cnn.cursor()
        cur.execute("select 1")
        self.assertEqual(psycopg2.extensions.STATUS_BEGIN, cnn.status)
        xns = cnn.tpc_recover()
        self.assertEqual(psycopg2.extensions.STATUS_BEGIN, cnn.status)

    def test_recovered_xids(self):
        # insert a few test xns
        cnn = self.connect()
        cnn.set_isolation_level(0)
        cur = cnn.cursor()
        cur.execute("begin; prepare transaction '1-foo';")
        cur.execute("begin; prepare transaction '2-bar';")

        # read the values to return
        cur.execute("""
            select gid, prepared, owner, database
            from pg_prepared_xacts
            where database = %s;""",
            (dbname,))
        okvals = cur.fetchall()
        okvals.sort()

        cnn = self.connect()
        xids = cnn.tpc_recover()
        xids = [ xid for xid in xids if xid.database == dbname ]
        xids.sort(key=attrgetter('gtrid'))

        # check the values returned
        self.assertEqual(len(okvals), len(xids))
        for (xid, (gid, prepared, owner, database)) in zip (xids, okvals):
            self.assertEqual(xid.gtrid, gid)
            self.assertEqual(xid.prepared, prepared)
            self.assertEqual(xid.owner, owner)
            self.assertEqual(xid.database, database)

    def test_xid_encoding(self):
        cnn = self.connect()
        xid = cnn.xid(42, "gtrid", "bqual")
        cnn.tpc_begin(xid)
        cnn.tpc_prepare()

        cnn = self.connect()
        cur = cnn.cursor()
        cur.execute("select gid from pg_prepared_xacts where database = %s;",
            (dbname,))
        self.assertEqual('42_Z3RyaWQ=_YnF1YWw=', cur.fetchone()[0])

    def test_xid_roundtrip(self):
        for fid, gtrid, bqual in [
            (0, "", ""),
            (42, "gtrid", "bqual"),
            (0x7fffffff, "x" * 64, "y" * 64),
        ]:
            cnn = self.connect()
            xid = cnn.xid(fid, gtrid, bqual)
            cnn.tpc_begin(xid)
            cnn.tpc_prepare()
            cnn.close()

            cnn = self.connect()
            xids = [ xid for xid in cnn.tpc_recover()
                if xid.database == dbname ]
            self.assertEqual(1, len(xids))
            xid = xids[0]
            self.assertEqual(xid.format_id, fid)
            self.assertEqual(xid.gtrid, gtrid)
            self.assertEqual(xid.bqual, bqual)

            cnn.tpc_rollback(xid)

    def test_unparsed_roundtrip(self):
        for tid in [
            '',
            'hello, world!',
            'x' * 199,  # PostgreSQL's limit in transaction id length
        ]:
            cnn = self.connect()
            cnn.tpc_begin(tid)
            cnn.tpc_prepare()
            cnn.close()

            cnn = self.connect()
            xids = [ xid for xid in cnn.tpc_recover()
                if xid.database == dbname ]
            self.assertEqual(1, len(xids))
            xid = xids[0]
            self.assertEqual(xid.format_id, None)
            self.assertEqual(xid.gtrid, tid)
            self.assertEqual(xid.bqual, None)

            cnn.tpc_rollback(xid)

    def test_xid_construction(self):
        from psycopg2.extensions import Xid

        x1 = Xid(74, 'foo', 'bar')
        self.assertEqual(74, x1.format_id)
        self.assertEqual('foo', x1.gtrid)
        self.assertEqual('bar', x1.bqual)

    def test_xid_from_string(self):
        from psycopg2.extensions import Xid

        x2 = Xid.from_string('42_Z3RyaWQ=_YnF1YWw=')
        self.assertEqual(42, x2.format_id)
        self.assertEqual('gtrid', x2.gtrid)
        self.assertEqual('bqual', x2.bqual)

        x3 = Xid.from_string('99_xxx_yyy')
        self.assertEqual(None, x3.format_id)
        self.assertEqual('99_xxx_yyy', x3.gtrid)
        self.assertEqual(None, x3.bqual)

    def test_xid_to_string(self):
        from psycopg2.extensions import Xid

        x1 = Xid.from_string('42_Z3RyaWQ=_YnF1YWw=')
        self.assertEqual(str(x1), '42_Z3RyaWQ=_YnF1YWw=')

        x2 = Xid.from_string('99_xxx_yyy')
        self.assertEqual(str(x2), '99_xxx_yyy')

    def test_xid_unicode(self):
        cnn = self.connect()
        x1 = cnn.xid(10, u'uni', u'code')
        cnn.tpc_begin(x1)
        cnn.tpc_prepare()
        cnn.reset()
        xid = [ xid for xid in cnn.tpc_recover()
            if xid.database == dbname ][0]
        self.assertEqual(10, xid.format_id)
        self.assertEqual('uni', xid.gtrid)
        self.assertEqual('code', xid.bqual)

    def test_xid_unicode_unparsed(self):
        # We don't expect people shooting snowmen as transaction ids,
        # so if something explodes in an encode error I don't mind.
        # Let's just check uniconde is accepted as type.
        cnn = self.connect()
        cnn.set_client_encoding('utf8')
        cnn.tpc_begin(u"transaction-id")
        cnn.tpc_prepare()
        cnn.reset()

        xid = [ xid for xid in cnn.tpc_recover()
            if xid.database == dbname ][0]
        self.assertEqual(None, xid.format_id)
        self.assertEqual('transaction-id', xid.gtrid)
        self.assertEqual(None, xid.bqual)

    def test_cancel_fails_prepared(self):
        cnn = self.connect()
        cnn.tpc_begin('cancel')
        cnn.tpc_prepare()
        self.assertRaises(psycopg2.ProgrammingError, cnn.cancel)

    def test_tpc_recover_non_dbapi_connection(self):
        from psycopg2.extras import RealDictConnection
        cnn = self.connect(connection_factory=RealDictConnection)
        cnn.tpc_begin('dict-connection')
        cnn.tpc_prepare()
        cnn.reset()

        xids = cnn.tpc_recover()
        xid = [ xid for xid in xids if xid.database == dbname ][0]
        self.assertEqual(None, xid.format_id)
        self.assertEqual('dict-connection', xid.gtrid)
        self.assertEqual(None, xid.bqual)


decorate_all_tests(ConnectionTwoPhaseTests, skip_if_tpc_disabled)


class TransactionControlTests(ConnectingTestCase):
    def test_closed(self):
        self.conn.close()
        self.assertRaises(psycopg2.InterfaceError,
            self.conn.set_session,
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

    def test_not_in_transaction(self):
        cur = self.conn.cursor()
        cur.execute("select 1")
        self.assertRaises(psycopg2.ProgrammingError,
            self.conn.set_session,
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)

    def test_set_isolation_level(self):
        cur = self.conn.cursor()
        self.conn.set_session(
            psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
        cur.execute("SHOW default_transaction_isolation;")
        self.assertEqual(cur.fetchone()[0], 'serializable')
        self.conn.rollback()

        self.conn.set_session(
            psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
        cur.execute("SHOW default_transaction_isolation;")
        if self.conn.server_version > 80000:
            self.assertEqual(cur.fetchone()[0], 'repeatable read')
        else:
            self.assertEqual(cur.fetchone()[0], 'serializable')
        self.conn.rollback()

        self.conn.set_session(
            isolation_level=psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        cur.execute("SHOW default_transaction_isolation;")
        self.assertEqual(cur.fetchone()[0], 'read committed')
        self.conn.rollback()

        self.conn.set_session(
            isolation_level=psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED)
        cur.execute("SHOW default_transaction_isolation;")
        if self.conn.server_version > 80000:
            self.assertEqual(cur.fetchone()[0], 'read uncommitted')
        else:
            self.assertEqual(cur.fetchone()[0], 'read committed')
        self.conn.rollback()

    def test_set_isolation_level_str(self):
        cur = self.conn.cursor()
        self.conn.set_session("serializable")
        cur.execute("SHOW default_transaction_isolation;")
        self.assertEqual(cur.fetchone()[0], 'serializable')
        self.conn.rollback()

        self.conn.set_session("repeatable read")
        cur.execute("SHOW default_transaction_isolation;")
        if self.conn.server_version > 80000:
            self.assertEqual(cur.fetchone()[0], 'repeatable read')
        else:
            self.assertEqual(cur.fetchone()[0], 'serializable')
        self.conn.rollback()

        self.conn.set_session("read committed")
        cur.execute("SHOW default_transaction_isolation;")
        self.assertEqual(cur.fetchone()[0], 'read committed')
        self.conn.rollback()

        self.conn.set_session("read uncommitted")
        cur.execute("SHOW default_transaction_isolation;")
        if self.conn.server_version > 80000:
            self.assertEqual(cur.fetchone()[0], 'read uncommitted')
        else:
            self.assertEqual(cur.fetchone()[0], 'read committed')
        self.conn.rollback()

    def test_bad_isolation_level(self):
        self.assertRaises(ValueError, self.conn.set_session, 0)
        self.assertRaises(ValueError, self.conn.set_session, 5)
        self.assertRaises(ValueError, self.conn.set_session, 'whatever')

    def test_set_read_only(self):
        cur = self.conn.cursor()
        self.conn.set_session(readonly=True)
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'on')
        self.conn.rollback()
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'on')
        self.conn.rollback()

        cur = self.conn.cursor()
        self.conn.set_session(readonly=None)
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'on')
        self.conn.rollback()

        self.conn.set_session(readonly=False)
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'off')
        self.conn.rollback()

    def test_set_default(self):
        cur = self.conn.cursor()
        cur.execute("SHOW default_transaction_isolation;")
        default_isolevel = cur.fetchone()[0]
        cur.execute("SHOW default_transaction_read_only;")
        default_readonly = cur.fetchone()[0]
        self.conn.rollback()

        self.conn.set_session(isolation_level='serializable', readonly=True)
        self.conn.set_session(isolation_level='default', readonly='default')

        cur.execute("SHOW default_transaction_isolation;")
        self.assertEqual(cur.fetchone()[0], default_isolevel)
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], default_readonly)

    @skip_before_postgres(9, 1)
    def test_set_deferrable(self):
        cur = self.conn.cursor()
        self.conn.set_session(readonly=True, deferrable=True)
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'on')
        cur.execute("SHOW default_transaction_deferrable;")
        self.assertEqual(cur.fetchone()[0], 'on')
        self.conn.rollback()
        cur.execute("SHOW default_transaction_deferrable;")
        self.assertEqual(cur.fetchone()[0], 'on')
        self.conn.rollback()

        self.conn.set_session(deferrable=False)
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'on')
        cur.execute("SHOW default_transaction_deferrable;")
        self.assertEqual(cur.fetchone()[0], 'off')
        self.conn.rollback()

    @skip_after_postgres(9, 1)
    def test_set_deferrable_error(self):
        self.assertRaises(psycopg2.ProgrammingError,
            self.conn.set_session, readonly=True, deferrable=True)


class AutocommitTests(ConnectingTestCase):
    def test_closed(self):
        self.conn.close()
        self.assertRaises(psycopg2.InterfaceError,
            setattr, self.conn, 'autocommit', True)

        # The getter doesn't have a guard. We may change this in future
        # to make it consistent with other methods; meanwhile let's just check
        # it doesn't explode.
        try:
            self.assert_(self.conn.autocommit in (True, False))
        except psycopg2.InterfaceError:
            pass

    def test_default_no_autocommit(self):
        self.assert_(not self.conn.autocommit)
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        cur = self.conn.cursor()
        cur.execute('select 1;')
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_BEGIN)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_INTRANS)

        self.conn.rollback()
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

    def test_set_autocommit(self):
        self.conn.autocommit = True
        self.assert_(self.conn.autocommit)
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        cur = self.conn.cursor()
        cur.execute('select 1;')
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        self.conn.autocommit = False
        self.assert_(not self.conn.autocommit)
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        cur.execute('select 1;')
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_BEGIN)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_INTRANS)

    def test_set_intrans_error(self):
        cur = self.conn.cursor()
        cur.execute('select 1;')
        self.assertRaises(psycopg2.ProgrammingError,
            setattr, self.conn, 'autocommit', True)

    def test_set_session_autocommit(self):
        self.conn.set_session(autocommit=True)
        self.assert_(self.conn.autocommit)
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        cur = self.conn.cursor()
        cur.execute('select 1;')
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        self.conn.set_session(autocommit=False)
        self.assert_(not self.conn.autocommit)
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)

        cur.execute('select 1;')
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_BEGIN)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_INTRANS)
        self.conn.rollback()

        self.conn.set_session('serializable', readonly=True, autocommit=True)
        self.assert_(self.conn.autocommit)
        cur.execute('select 1;')
        self.assertEqual(self.conn.status, psycopg2.extensions.STATUS_READY)
        self.assertEqual(self.conn.get_transaction_status(),
            psycopg2.extensions.TRANSACTION_STATUS_IDLE)
        cur.execute("SHOW default_transaction_isolation;")
        self.assertEqual(cur.fetchone()[0], 'serializable')
        cur.execute("SHOW default_transaction_read_only;")
        self.assertEqual(cur.fetchone()[0], 'on')


class ReplicationTest(ConnectingTestCase):
    @skip_before_postgres(9, 0)
    def test_replication_not_supported(self):
        conn = self.repl_connect()
        if conn is None: return
        cur = conn.cursor()
        f = StringIO()
        self.assertRaises(psycopg2.NotSupportedError,
            cur.copy_expert, "START_REPLICATION 0/0", f)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
