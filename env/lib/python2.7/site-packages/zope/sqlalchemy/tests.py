##############################################################################
#
# Copyright (c) 2008 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################

# Much inspiration from z3c.sqlalchemy/trunk/src/z3c/sqlalchemy/tests/testSQLAlchemy.py
#
# You may want to run the tests with your database. To do so set the environment variable
# TEST_DSN to the connection url. e.g.:
# export TEST_DSN=postgres://plone:plone@localhost/test
# export TEST_DSN=mssql://plone:plone@/test?dsn=mydsn
#
# To test in twophase commit mode export TEST_TWOPHASE=True
#
# NOTE: The sqlite that ships with Mac OS X 10.4 is buggy. Install a newer version (3.5.6)
#       and rebuild pysqlite2 against it.

import sys

PY3 = sys.version_info[0] == 3


def u(s):
    if PY3:
        return s
    else:
        return s.decode('utf-8')


def b(s):
    if PY3:
        return s.encode('utf-8')
    else:
        return s

import os
import re
import unittest
import transaction
import threading
import time

from transaction._transaction import Status as ZopeStatus
from transaction.interfaces import TransactionFailedError

import sqlalchemy as sa
from sqlalchemy import orm, sql, exc
from zope.sqlalchemy import datamanager as tx
from zope.sqlalchemy import mark_changed
from zope.testing.renormalizing import RENormalizing

TEST_TWOPHASE = bool(os.environ.get('TEST_TWOPHASE'))
TEST_DSN = os.environ.get('TEST_DSN', 'sqlite:///:memory:')


class SimpleModel(object):
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def asDict(self):
        return dict((k, v) for k, v in self.__dict__.items() if not k.startswith('_'))


class User(SimpleModel):
    pass


class Skill(SimpleModel):
    pass


engine = sa.create_engine(TEST_DSN)
engine2 = sa.create_engine(TEST_DSN)

# See https://code.google.com/p/pysqlite-static-env/
HAS_PATCHED_PYSQLITE = False
if engine.url.drivername == 'sqlite':
    try:
        from pysqlite2.dbapi2 import Connection
    except ImportError:
        pass
    else:
        if hasattr(Connection, 'operation_needs_transaction_callback'):
            HAS_PATCHED_PYSQLITE = True

if HAS_PATCHED_PYSQLITE:
    from sqlalchemy import event
    from zope.sqlalchemy.datamanager import NO_SAVEPOINT_SUPPORT
    NO_SAVEPOINT_SUPPORT.remove('sqlite')

    @event.listens_for(engine, 'connect')
    def connect(dbapi_connection, connection_record):
        dbapi_connection.operation_needs_transaction_callback = lambda x: True


Session = orm.scoped_session(orm.sessionmaker(
    bind=engine,
    extension=tx.ZopeTransactionExtension(),
    twophase=TEST_TWOPHASE,
))

UnboundSession = orm.scoped_session(orm.sessionmaker(
    extension=tx.ZopeTransactionExtension(),
    twophase=TEST_TWOPHASE,
))

EventSession = orm.scoped_session(orm.sessionmaker(
    bind=engine,
    twophase=TEST_TWOPHASE,
))

KeepSession = orm.scoped_session(orm.sessionmaker(
    bind=engine,
    extension=tx.ZopeTransactionExtension(keep_session=True),
    twophase=TEST_TWOPHASE,
))

tx.register(EventSession)

metadata = sa.MetaData()  # best to use unbound metadata


test_users = sa.Table(
    'test_users',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('firstname', sa.VARCHAR(255)),  # mssql cannot do equality on a text type
    sa.Column('lastname', sa.VARCHAR(255)),
)

test_skills = sa.Table(
    'test_skills',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('user_id', sa.Integer),
    sa.Column('name', sa.VARCHAR(255)),
    sa.ForeignKeyConstraint(('user_id',), ('test_users.id',)),
)

bound_metadata1 = sa.MetaData(engine)
bound_metadata2 = sa.MetaData(engine2)

test_one = sa.Table('test_one', bound_metadata1, sa.Column('id', sa.Integer, primary_key=True))
test_two = sa.Table('test_two', bound_metadata2, sa.Column('id', sa.Integer, primary_key=True))


class TestOne(SimpleModel):
    pass


class TestTwo(SimpleModel):
    pass


def setup_mappers():
    orm.clear_mappers()
    # Other tests can clear mappers by calling clear_mappers(),
    # be more robust by setting up mappers in the test setup.
    m1 = orm.mapper(
        User,
        test_users,
        properties={'skills': orm.relation(
            Skill,
            primaryjoin=test_users.columns['id'] == test_skills.columns['user_id']),
        })
    m2 = orm.mapper(Skill, test_skills)

    m3 = orm.mapper(TestOne, test_one)
    m4 = orm.mapper(TestTwo, test_two)
    return [m1, m2, m3, m4]


class DummyException(Exception):
    pass


class DummyTargetRaised(DummyException):
    pass


class DummyTargetResult(DummyException):
    pass


class DummyDataManager(object):
    def __init__(self, key, target=None, args=(), kwargs={}):
        self.key = key
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def abort(self, trans):
        pass

    def tpc_begin(self, trans):
        pass

    def commit(self, trans):
        pass

    def tpc_vote(self, trans):
        if self.target is not None:
            try:
                result = self.target(*self.args, **self.kwargs)
            except Exception as e:
                raise DummyTargetRaised(e)
            raise DummyTargetResult(result)
        else:
            raise DummyException('DummyDataManager cannot commit')

    def tpc_finish(self, trans):
        pass

    def tpc_abort(self, trans):
        pass

    def sortKey(self):
        return self.key


class ZopeSQLAlchemyTests(unittest.TestCase):

    def setUp(self):
        self.mappers = setup_mappers()
        metadata.drop_all(engine)
        metadata.create_all(engine)

    def tearDown(self):
        transaction.abort()
        metadata.drop_all(engine)
        orm.clear_mappers()

    def testMarkUnknownSession(self):
        import zope.sqlalchemy.datamanager
        dummy = DummyDataManager(key='dummy.first')
        session = Session()
        mark_changed(session)
        self.assertTrue(id(session) in zope.sqlalchemy.datamanager._SESSION_STATE)

    def testAbortBeforeCommit(self):
        # Simulate what happens in a conflict error
        dummy = DummyDataManager(key='dummy.first')
        session = Session()
        conn = session.connection()
        mark_changed(session)
        try:
            # Thus we could fail in commit
            transaction.commit()
        except:
            # But abort must succed (and actually rollback the base connection)
            transaction.abort()
            pass
        # Or the next transaction the next transaction will not be able to start!
        transaction.begin()
        session = Session()
        conn = session.connection()
        conn.execute("SELECT 1 FROM test_users")
        mark_changed(session)
        transaction.commit()

    def testAbortAfterCommit(self):
        # This is a regression test which used to wedge the transaction
        # machinery when using PostgreSQL (and perhaps other) connections.
        # Basically, if a commit failed, there was no way to abort the
        # transaction. Leaving the transaction wedged.
        transaction.begin()
        session = Session()
        conn = session.connection()
        # At least PostgresSQL requires a rollback after invalid SQL is executed
        self.assertRaises(Exception, conn.execute, "BAD SQL SYNTAX")
        mark_changed(session)
        try:
            # Thus we could fail in commit
            transaction.commit()
        except:
            # But abort must succed (and actually rollback the base connection)
            transaction.abort()
            pass
        # Or the next transaction the next transaction will not be able to start!
        transaction.begin()
        session = Session()
        conn = session.connection()
        conn.execute("SELECT 1 FROM test_users")
        mark_changed(session)
        transaction.commit()

    def testSimplePopulation(self):
        session = Session()
        query = session.query(User)
        rows = query.all()
        self.assertEqual(len(rows), 0)

        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.flush()

        rows = query.order_by(User.id).all()
        self.assertEqual(len(rows), 2)
        row1 = rows[0]
        d = row1.asDict()
        self.assertEqual(d, {'firstname': 'udo', 'lastname': 'juergens', 'id': 1})

        # bypass the session machinary
        stmt = sql.select(test_users.columns).order_by('id')
        conn = session.connection()
        results = conn.execute(stmt)
        self.assertEqual(results.fetchall(), [(1, 'udo', 'juergens'), (2, 'heino', 'n/a')])

    def testRelations(self):
        session = Session()
        session.add(User(id=1, firstname='foo', lastname='bar'))

        user = session.query(User).filter_by(firstname='foo')[0]
        user.skills.append(Skill(id=1, name='Zope'))
        session.flush()

    def testTransactionJoining(self):
        transaction.abort()  # clean slate
        t = transaction.get()
        self.assertFalse(
            [r for r in t._resources if isinstance(r, tx.SessionDataManager)],
            "Joined transaction too early")
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        t = transaction.get()
        # Expect this to fail with SQLAlchemy 0.4
        self.assertTrue(
            [r for r in t._resources if isinstance(r, tx.SessionDataManager)],
            "Not joined transaction")
        transaction.abort()
        conn = Session().connection()
        self.assertTrue(
            [r for r in t._resources if isinstance(r, tx.SessionDataManager)],
            "Not joined transaction")

    def testTransactionJoiningUsingRegister(self):
        transaction.abort()  # clean slate
        t = transaction.get()
        self.assertFalse(
            [r for r in t._resources if isinstance(r, tx.SessionDataManager)],
            "Joined transaction too early")
        session = EventSession()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        t = transaction.get()
        self.assertTrue(
            [r for r in t._resources if isinstance(r, tx.SessionDataManager)],
            "Not joined transaction")
        transaction.abort()
        conn = EventSession().connection()
        self.assertTrue(
            [r for r in t._resources if isinstance(r, tx.SessionDataManager)],
            "Not joined transaction")

    def testSavepoint(self):
        use_savepoint = not engine.url.drivername in tx.NO_SAVEPOINT_SUPPORT
        t = transaction.get()
        session = Session()
        query = session.query(User)
        self.assertFalse(query.all(), "Users table should be empty")

        s0 = t.savepoint(optimistic=True)  # this should always work

        if not use_savepoint:
            self.assertRaises(TypeError, t.savepoint)
            return  # sqlite databases do not support savepoints

        s1 = t.savepoint()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.flush()
        self.assertTrue(len(query.all()) == 1, "Users table should have one row")

        s2 = t.savepoint()
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.flush()
        self.assertTrue(len(query.all()) == 2, "Users table should have two rows")

        s2.rollback()
        self.assertTrue(len(query.all()) == 1, "Users table should have one row")

        s1.rollback()
        self.assertFalse(query.all(), "Users table should be empty")

    def testRollbackAttributes(self):
        use_savepoint = not engine.url.drivername in tx.NO_SAVEPOINT_SUPPORT
        if not use_savepoint:
            return  # sqlite databases do not support savepoints

        t = transaction.get()
        session = Session()
        query = session.query(User)
        self.assertFalse(query.all(), "Users table should be empty")

        s1 = t.savepoint()
        user = User(id=1, firstname='udo', lastname='juergens')
        session.add(user)
        session.flush()

        s2 = t.savepoint()
        user.firstname = 'heino'
        session.flush()
        s2.rollback()
        self.assertEqual(user.firstname, 'udo', "User firstname attribute should have been rolled back")

    def testCommit(self):
        session = Session()

        use_savepoint = not engine.url.drivername in tx.NO_SAVEPOINT_SUPPORT
        query = session.query(User)
        rows = query.all()
        self.assertEqual(len(rows), 0)

        transaction.commit()  # test a none modifying transaction works

        session = Session()
        query = session.query(User)

        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.flush()

        rows = query.order_by(User.id).all()
        self.assertEqual(len(rows), 2)

        transaction.abort()  # test that the abort really aborts
        session = Session()
        query = session.query(User)
        rows = query.order_by(User.id).all()
        self.assertEqual(len(rows), 0)

        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.flush()
        rows = query.order_by(User.id).all()
        row1 = rows[0]
        d = row1.asDict()
        self.assertEqual(d, {'firstname': 'udo', 'lastname': 'juergens', 'id': 1})

        transaction.commit()

        rows = query.order_by(User.id).all()
        self.assertEqual(len(rows), 2)
        row1 = rows[0]
        d = row1.asDict()
        self.assertEqual(d, {'firstname': 'udo', 'lastname': 'juergens', 'id': 1})

        # bypass the session (and transaction) machinary
        results = engine.connect().execute(test_users.select())
        self.assertEqual(len(results.fetchall()), 2)

    def testCommitWithSavepoint(self):
        if engine.url.drivername in tx.NO_SAVEPOINT_SUPPORT:
            return
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.flush()
        transaction.commit()

        session = Session()
        query = session.query(User)
        # lets just test that savepoints don't affect commits
        t = transaction.get()
        rows = query.order_by(User.id).all()

        s1 = t.savepoint()
        session.delete(rows[1])
        session.flush()
        transaction.commit()

        # bypass the session machinary
        results = engine.connect().execute(test_users.select())
        self.assertEqual(len(results.fetchall()), 1)

    def testNestedSessionCommitAllowed(self):
        # Existing code might use nested transactions
        if engine.url.drivername in tx.NO_SAVEPOINT_SUPPORT:
            return
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.begin_nested()
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.commit()
        transaction.commit()

    def testSessionCommitDisallowed(self):
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        self.assertRaises(AssertionError, session.commit)

    def testTwoPhase(self):
        session = Session()
        if not session.twophase:
            return
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        session.flush()
        transaction.commit()

        # Test that we clean up after a tpc_abort
        t = transaction.get()

        def target():
            return engine.connect().recover_twophase()

        dummy = DummyDataManager(key='~~~dummy.last', target=target)
        t.join(dummy)
        session = Session()
        query = session.query(User)
        rows = query.all()
        session.delete(rows[0])
        session.flush()
        result = None
        try:
            t.commit()
        except DummyTargetResult as e:
            result = e.args[0]
        except DummyTargetRaised as e:
            raise e.args[0]

        self.assertEqual(len(result), 1, "Should have been one prepared transaction when dummy aborted")

        transaction.begin()

        self.assertEqual(len(engine.connect().recover_twophase()), 0, "Test no outstanding prepared transactions")

    def testThread(self):
        transaction.abort()
        global thread_error
        thread_error = None

        def target():
            try:
                session = Session()
                metadata.drop_all(engine)
                metadata.create_all(engine)

                query = session.query(User)
                rows = query.all()
                self.assertEqual(len(rows), 0)

                session.add(User(id=1, firstname='udo', lastname='juergens'))
                session.add(User(id=2, firstname='heino', lastname='n/a'))
                session.flush()

                rows = query.order_by(User.id).all()
                self.assertEqual(len(rows), 2)
                row1 = rows[0]
                d = row1.asDict()
                self.assertEqual(d, {'firstname': 'udo', 'lastname': 'juergens', 'id': 1})
            except Exception as err:
                global thread_error
                thread_error = err
            transaction.abort()

        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        if thread_error is not None:
            raise thread_error  # reraise in current thread

    def testBulkDelete(self):
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        transaction.commit()
        session = Session()
        session.query(User).delete()
        transaction.commit()
        results = engine.connect().execute(test_users.select())
        self.assertEqual(len(results.fetchall()), 0)

    def testBulkUpdate(self):
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        transaction.commit()
        session = Session()
        session.query(User).update(dict(lastname="smith"))
        transaction.commit()
        results = engine.connect().execute(test_users.select(test_users.c.lastname == "smith"))
        self.assertEqual(len(results.fetchall()), 2)

    def testBulkDeleteUsingRegister(self):
        session = EventSession()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        transaction.commit()
        session = EventSession()
        session.query(User).delete()
        transaction.commit()
        results = engine.connect().execute(test_users.select())
        self.assertEqual(len(results.fetchall()), 0)

    def testBulkUpdateUsingRegister(self):
        session = EventSession()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        session.add(User(id=2, firstname='heino', lastname='n/a'))
        transaction.commit()
        session = EventSession()
        session.query(User).update(dict(lastname="smith"))
        transaction.commit()
        results = engine.connect().execute(test_users.select(test_users.c.lastname == "smith"))
        self.assertEqual(len(results.fetchall()), 2)

    def testFailedJoin(self):
        # When a join is issued while the transaction is in COMMITFAILED, the
        # session is never closed and the session id stays in _SESSION_STATE,
        # which means the session won't be joined in the future either. This
        # causes the session to stay open forever, potentially accumulating
        # data, but never issuing a commit.
        dummy = DummyDataManager(key='dummy.first')
        transaction.get().join(dummy)
        try:
            transaction.commit()
        except DummyException:
            # Commit raised an error, we are now in COMMITFAILED
            pass
        self.assertEqual(transaction.get().status, ZopeStatus.COMMITFAILED)

        session = Session()
        # try to interact with the session while the transaction is still
        # in COMMITFAILED
        self.assertRaises(TransactionFailedError,
                          session.query(User).all)
        transaction.abort()

        # start a new transaction everything should be ok now
        transaction.begin()
        session = Session()
        self.assertEqual([], session.query(User).all())
        session.add(User(id=1, firstname='udo', lastname='juergens'))

        # abort transaction, session should be closed without commit
        transaction.abort()
        self.assertEqual([], session.query(User).all())

    def testKeepSession(self):
        session = KeepSession()

        try:
            with transaction.manager:
                session.add(User(id=1, firstname='foo', lastname='bar'))

            user = session.query(User).get(1)

            # if the keep_session works correctly, this transaction will not close
            # the session after commit
            with transaction.manager:
                user.firstname = 'super'
                session.flush()

            # make sure the session is still attached to user
            self.assertEqual(user.firstname, 'super')

        finally:
            # KeepSession does not rollback on transaction abort
            session.rollback()

    def testExpireAll(self):
        session = Session()
        session.add(User(id=1, firstname='udo', lastname='juergens'))
        transaction.commit()

        session = Session()
        instance = session.query(User).get(1)
        transaction.commit()  # No work, session.close()

        self.assertEqual(sa.inspect(instance).expired, True)


class RetryTests(unittest.TestCase):

    def setUp(self):
        self.mappers = setup_mappers()
        metadata.drop_all(engine)
        metadata.create_all(engine)
        self.tm1 = transaction.TransactionManager()
        self.tm2 = transaction.TransactionManager()
        # With psycopg2 you might supply isolation_level='SERIALIZABLE' here,
        # unfortunately that is not supported by cx_Oracle.
        e1 = sa.create_engine(TEST_DSN)
        e2 = sa.create_engine(TEST_DSN)
        self.s1 = orm.sessionmaker(
            bind=e1,
            extension=tx.ZopeTransactionExtension(transaction_manager=self.tm1),
            twophase=TEST_TWOPHASE,
        )()
        self.s2 = orm.sessionmaker(
            bind=e2,
            extension=tx.ZopeTransactionExtension(transaction_manager=self.tm2),
            twophase=TEST_TWOPHASE,
        )()
        self.tm1.begin()
        self.s1.add(User(id=1, firstname='udo', lastname='juergens'))
        self.tm1.commit()

    def tearDown(self):
        self.tm1.abort()
        self.tm2.abort()
        metadata.drop_all(engine)
        orm.clear_mappers()

    def testRetry(self):
        # sqlite is unable to run this test as the databse is locked
        tm1, tm2, s1, s2 = self.tm1, self.tm2, self.s1, self.s2
        # make sure we actually start a session.
        tm1.begin()
        self.assertTrue(len(s1.query(User).all()) == 1, "Users table should have one row")
        tm2.begin()
        self.assertTrue(len(s2.query(User).all()) == 1, "Users table should have one row")
        s1.query(User).delete()
        user = s2.query(User).get(1)
        user.lastname = u('smith')
        tm1.commit()
        raised = False
        try:
            s2.flush()
        except orm.exc.ConcurrentModificationError as e:
            # This error is thrown when the number of updated rows is not as expected
            raised = True
            self.assertTrue(tm2._retryable(type(e), e), "Error should be retryable")
        self.assertTrue(raised, "Did not raise expected error")

    def testRetryThread(self):
        tm1, tm2, s1, s2 = self.tm1, self.tm2, self.s1, self.s2
        # make sure we actually start a session.
        tm1.begin()
        self.assertTrue(len(s1.query(User).all()) == 1, "Users table should have one row")
        tm2.begin()
        s2.connection().execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        self.assertTrue(len(s2.query(User).all()) == 1, "Users table should have one row")
        s1.query(User).delete()
        raised = False

        def target():
            time.sleep(0.2)
            tm1.commit()

        thread = threading.Thread(target=target)
        thread.start()
        try:
            user = s2.query(User).with_lockmode('update').get(1)
        except exc.DBAPIError as e:
            # This error wraps the underlying DBAPI module error, some of which are retryable
            raised = True
            retryable = tm2._retryable(type(e), e)
            self.assertTrue(retryable, "Error should be retryable")
        self.assertTrue(raised, "Did not raise expected error")
        thread.join()  # well, we must have joined by now


class MultipleEngineTests(unittest.TestCase):

    def setUp(self):
        self.mappers = setup_mappers()
        bound_metadata1.drop_all()
        bound_metadata1.create_all()
        bound_metadata2.drop_all()
        bound_metadata2.create_all()

    def tearDown(self):
        transaction.abort()
        bound_metadata1.drop_all()
        bound_metadata2.drop_all()
        orm.clear_mappers()

    def testTwoEngines(self):
        session = UnboundSession()
        session.add(TestOne(id=1))
        session.add(TestTwo(id=2))
        session.flush()
        transaction.commit()
        session = UnboundSession()
        rows = session.query(TestOne).all()
        self.assertEqual(len(rows), 1)
        rows = session.query(TestTwo).all()
        self.assertEqual(len(rows), 1)


def tearDownReadMe(test):
    Base = test.globs['Base']
    engine = test.globs['engine']
    Base.metadata.drop_all(engine)


def test_suite():
    from unittest import TestSuite, makeSuite
    import doctest
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    checker = RENormalizing([
        # Python 3 includes module name in exceptions
        (re.compile(r"sqlalchemy.orm.exc.DetachedInstanceError:"),
         "DetachedInstanceError:"),
        # Python 3 drops the u'' prefix on unicode strings
        (re.compile(r"u('[^']*')"), r"\1"),
        # PyPy includes __builtin__ in front of classes defined in doctests
        (re.compile(r"__builtin__[.]Address"), "Address"),
    ])
    suite = TestSuite()
    suite.addTest(makeSuite(ZopeSQLAlchemyTests))
    suite.addTest(makeSuite(MultipleEngineTests))
    if TEST_DSN.startswith('postgres') or TEST_DSN.startswith('oracle'):
        suite.addTest(makeSuite(RetryTests))
    suite.addTest(doctest.DocFileSuite('README.txt', optionflags=optionflags,
                  checker=checker, tearDown=tearDownReadMe,
                  globs={'TEST_DSN': TEST_DSN, 'TEST_TWOPHASE': TEST_TWOPHASE}))
    return suite
