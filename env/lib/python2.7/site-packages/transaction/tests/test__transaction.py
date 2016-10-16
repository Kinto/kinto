##############################################################################
#
# Copyright (c) 2001, 2002, 2005 Zope Foundation and Contributors.
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
"""Test transaction behavior for variety of cases.

I wrote these unittests to investigate some odd transaction
behavior when doing unittests of integrating non sub transaction
aware objects, and to insure proper txn behavior. these
tests test the transaction system independent of the rest of the
zodb.

you can see the method calls to a jar by passing the
keyword arg tracing to the modify method of a dataobject.
the value of the arg is a prefix used for tracing print calls
to that objects jar.

the number of times a jar method was called can be inspected
by looking at an attribute of the jar that is the method
name prefixed with a c (count/check).

i've included some tracing examples for tests that i thought
were illuminating as doc strings below.

TODO

    add in tests for objects which are modified multiple times,
    for example an object that gets modified in multiple sub txns.
"""
import unittest


class TransactionTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import Transaction
        return Transaction

    def _makeOne(self, synchronizers=None, manager=None):
        return self._getTargetClass()(synchronizers, manager)

    def test_ctor_defaults(self):
        from transaction.weakset import WeakSet
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        self.assertTrue(isinstance(txn._synchronizers, WeakSet))
        self.assertEqual(len(txn._synchronizers), 0)
        self.assertTrue(txn._manager is None)
        self.assertEqual(txn.user, "")
        self.assertEqual(txn.description, "")
        self.assertTrue(txn._savepoint2index is None)
        self.assertEqual(txn._savepoint_index, 0)
        self.assertEqual(txn._resources, [])
        self.assertEqual(txn._adapters, {})
        self.assertEqual(txn._voted, {})
        self.assertEqual(txn._extension, {})
        self.assertTrue(txn.log is logger)
        self.assertEqual(len(logger._log), 1)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'new transaction')
        self.assertTrue(txn._failure_traceback is None)
        self.assertEqual(txn._before_commit, [])
        self.assertEqual(txn._after_commit, [])

    def test_ctor_w_syncs(self):
        from transaction.weakset import WeakSet
        synchs = WeakSet()
        txn = self._makeOne(synchronizers=synchs)
        self.assertTrue(txn._synchronizers is synchs)

    def test_isDoomed(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        self.assertFalse(txn.isDoomed())
        txn.status = Status.DOOMED
        self.assertTrue(txn.isDoomed())

    def test_doom_active(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        txn.doom()
        self.assertTrue(txn.isDoomed())
        self.assertEqual(txn.status, Status.DOOMED)

    def test_doom_invalid(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        for status in Status.COMMITTING, Status.COMMITTED, Status.COMMITFAILED:
            txn.status = status
            self.assertRaises(ValueError, txn.doom)

    def test_doom_already_doomed(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        txn.status = Status.DOOMED
        txn.doom()
        self.assertTrue(txn.isDoomed())
        self.assertEqual(txn.status, Status.DOOMED)

    def test__prior_operation_failed(self):
        from transaction.interfaces import TransactionFailedError
        from transaction.tests.common import assertRaisesEx
        class _Traceback(object):
            def getvalue(self):
                return 'TRACEBACK'
        txn = self._makeOne()
        txn._failure_traceback = _Traceback()
        err = assertRaisesEx(TransactionFailedError,
                             txn._prior_operation_failed)
        self.assertTrue(str(err).startswith('An operation previously failed'))
        self.assertTrue(str(err).endswith( "with traceback:\n\nTRACEBACK"))

    def test_join_COMMITFAILED(self):
        from transaction.interfaces import TransactionFailedError
        from transaction._transaction import Status
        class _Traceback(object):
            def getvalue(self):
                return 'TRACEBACK'
        txn = self._makeOne()
        txn.status = Status.COMMITFAILED
        txn._failure_traceback = _Traceback()
        self.assertRaises(TransactionFailedError, txn.join, object())

    def test_join_COMMITTING(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        txn.status = Status.COMMITTING
        self.assertRaises(ValueError, txn.join, object())

    def test_join_COMMITTED(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        txn.status = Status.COMMITTED
        self.assertRaises(ValueError, txn.join, object())

    def test_join_DOOMED_non_preparing_wo_sp2index(self):
        from transaction._transaction import Status
        txn = self._makeOne()
        txn.status = Status.DOOMED
        resource = object()
        txn.join(resource)
        self.assertEqual(txn._resources, [resource])

    def test_join_ACTIVE_w_preparing_w_sp2index(self):
        from transaction._transaction import AbortSavepoint
        from transaction._transaction import DataManagerAdapter
        class _TSP(object):
            def __init__(self):
                self._savepoints = []
        class _DM(object):
            def prepare(self):
                pass
        txn = self._makeOne()
        tsp = _TSP()
        txn._savepoint2index = {tsp: object()}
        dm = _DM
        txn.join(dm)
        self.assertEqual(len(txn._resources), 1)
        dma = txn._resources[0]
        self.assertTrue(isinstance(dma, DataManagerAdapter))
        self.assertTrue(txn._resources[0]._datamanager is dm)
        self.assertEqual(len(tsp._savepoints), 1)
        self.assertTrue(isinstance(tsp._savepoints[0], AbortSavepoint))
        self.assertTrue(tsp._savepoints[0].datamanager is dma)
        self.assertTrue(tsp._savepoints[0].transaction is txn)

    def test__unjoin_miss(self):
        txn = self._makeOne()
        txn._unjoin(object()) #no raise

    def test__unjoin_hit(self):
        txn = self._makeOne()
        resource = object()
        txn._resources.append(resource)
        txn._unjoin(resource)
        self.assertEqual(txn._resources, [])

    def test_savepoint_COMMITFAILED(self):
        from transaction.interfaces import TransactionFailedError
        from transaction._transaction import Status
        class _Traceback(object):
            def getvalue(self):
                return 'TRACEBACK'
        txn = self._makeOne()
        txn.status = Status.COMMITFAILED
        txn._failure_traceback = _Traceback()
        self.assertRaises(TransactionFailedError, txn.savepoint)

    def test_savepoint_empty(self):
        from weakref import WeakKeyDictionary
        from transaction import _transaction
        from transaction._transaction import Savepoint
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        sp = txn.savepoint()
        self.assertTrue(isinstance(sp, Savepoint))
        self.assertTrue(sp.transaction is txn)
        self.assertEqual(sp._savepoints, [])
        self.assertEqual(txn._savepoint_index, 1)
        self.assertTrue(isinstance(txn._savepoint2index, WeakKeyDictionary))
        self.assertEqual(txn._savepoint2index[sp], 1)

    def test_savepoint_non_optimistc_resource_wo_support(self):
        from transaction import _transaction
        from transaction._transaction import Status
        from transaction._compat import StringIO
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        resource = object()
        txn._resources.append(resource)
        self.assertRaises(TypeError, txn.savepoint)
        self.assertEqual(txn.status,  Status.COMMITFAILED)
        self.assertTrue(isinstance(txn._failure_traceback, StringIO))
        self.assertTrue('TypeError' in txn._failure_traceback.getvalue())
        self.assertEqual(len(logger._log), 2)
        self.assertEqual(logger._log[0][0], 'error')
        self.assertTrue(logger._log[0][1].startswith('Error in abort'))
        self.assertEqual(logger._log[1][0], 'error')
        self.assertTrue(logger._log[1][1].startswith('Error in tpc_abort'))

    def test__remove_and_invalidate_after_miss(self):
        from weakref import WeakKeyDictionary
        txn = self._makeOne()
        txn._savepoint2index = WeakKeyDictionary()
        class _SP(object):
            def __init__(self, txn):
                self.transaction = txn
        holdme = []
        for i in range(10):
            sp = _SP(txn)
            holdme.append(sp) #prevent gc
            txn._savepoint2index[sp] = i
        self.assertEqual(len(txn._savepoint2index), 10)
        self.assertRaises(KeyError, txn._remove_and_invalidate_after, _SP(txn))
        self.assertEqual(len(txn._savepoint2index), 10)

    def test__remove_and_invalidate_after_hit(self):
        from weakref import WeakKeyDictionary
        txn = self._makeOne()
        txn._savepoint2index = WeakKeyDictionary()
        class _SP(object):
            def __init__(self, txn, index):
                self.transaction = txn
                self._index = index
            def __lt__(self, other):
                return self._index < other._index
            def __repr__(self):
                return '_SP: %d' % self._index
        holdme = []
        for i in range(10):
            sp = _SP(txn, i)
            holdme.append(sp) #prevent gc
            txn._savepoint2index[sp] = i
        self.assertEqual(len(txn._savepoint2index), 10)
        txn._remove_and_invalidate_after(holdme[1])
        self.assertEqual(sorted(txn._savepoint2index), sorted(holdme[:2]))

    def test__invalidate_all_savepoints(self):
        from weakref import WeakKeyDictionary
        txn = self._makeOne()
        txn._savepoint2index = WeakKeyDictionary()
        class _SP(object):
            def __init__(self, txn, index):
                self.transaction = txn
                self._index = index
            def __repr__(self):
                return '_SP: %d' % self._index
        holdme = []
        for i in range(10):
            sp = _SP(txn, i)
            holdme.append(sp) #prevent gc
            txn._savepoint2index[sp] = i
        self.assertEqual(len(txn._savepoint2index), 10)
        txn._invalidate_all_savepoints()
        self.assertEqual(list(txn._savepoint2index), [])

    def test_register_wo_jar(self):
        class _Dummy(object):
            _p_jar = None
        txn = self._makeOne()
        self.assertRaises(ValueError, txn.register, _Dummy())

    def test_register_w_jar(self):
        class _Manager(object):
            pass
        mgr = _Manager()
        class _Dummy(object):
            _p_jar = mgr
        txn = self._makeOne()
        dummy = _Dummy()
        txn.register(dummy)
        resources = list(txn._resources)
        self.assertEqual(len(resources), 1)
        adapter = resources[0]
        self.assertTrue(adapter.manager is mgr)
        self.assertTrue(dummy in adapter.objects)
        items = list(txn._adapters.items())
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0][0] is mgr)
        self.assertTrue(items[0][1] is adapter)

    def test_register_w_jar_already_adapted(self):
        class _Adapter(object):
            def __init__(self):
                self.objects = []
        class _Manager(object):
            pass
        mgr = _Manager()
        class _Dummy(object):
            _p_jar = mgr
        txn = self._makeOne()
        txn._adapters[mgr] = adapter = _Adapter()
        dummy = _Dummy()
        txn.register(dummy)
        self.assertTrue(dummy in adapter.objects)

    def test_commit_DOOMED(self):
        from transaction.interfaces import DoomedTransaction
        from transaction._transaction import Status
        txn = self._makeOne()
        txn.status = Status.DOOMED
        self.assertRaises(DoomedTransaction, txn.commit)

    def test_commit_COMMITFAILED(self):
        from transaction._transaction import Status
        from transaction.interfaces import TransactionFailedError
        class _Traceback(object):
            def getvalue(self):
                return 'TRACEBACK'
        txn = self._makeOne()
        txn.status = Status.COMMITFAILED
        txn._failure_traceback = _Traceback()
        self.assertRaises(TransactionFailedError, txn.commit)

    def test_commit_wo_savepoints_wo_hooks_wo_synchronizers(self):
        from transaction._transaction import Status
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Mgr(object):
            def __init__(self, txn):
                self._txn = txn
            def free(self, txn):
                assert txn is self._txn
                self._txn = None
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            logger._clear()
            mgr = txn._manager = _Mgr(txn)
            txn.commit()
        self.assertEqual(txn.status, Status.COMMITTED)
        self.assertTrue(mgr._txn is None)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'commit')

    def test_commit_w_savepoints(self):
        from weakref import WeakKeyDictionary
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _SP(object):
            def __init__(self, txn, index):
                self.transaction = txn
                self._index = index
            def __repr__(self):
                return '_SP: %d' % self._index
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._savepoint2index = WeakKeyDictionary()
            holdme = []
            for i in range(10):
                sp = _SP(txn, i)
                holdme.append(sp) #prevent gc
                txn._savepoint2index[sp] = i
            logger._clear()
            txn.commit()
        self.assertEqual(list(txn._savepoint2index), [])

    def test_commit_w_beforeCommitHooks(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        _hooked1, _hooked2 = [], []
        def _hook1(*args, **kw):
            _hooked1.append((args, kw))
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._before_commit.append((_hook1, ('one',), {'uno': 1}))
            txn._before_commit.append((_hook2, (), {}))
            logger._clear()
            txn.commit()
        self.assertEqual(_hooked1, [(('one',), {'uno': 1})])
        self.assertEqual(_hooked2, [((), {})])
        self.assertEqual(txn._before_commit, [])

    def test_commit_w_synchronizers(self):
        from transaction.weakset import WeakSet
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Synch(object):
            _before = _after = False
            def beforeCompletion(self, txn):
                self._before = txn
            def afterCompletion(self, txn):
                self._after = txn
        synchs = [_Synch(), _Synch(), _Synch()]
        ws = WeakSet()
        for synch in synchs:
            ws.add(synch)
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne(synchronizers=ws)
            logger._clear()
            txn.commit()
        for synch in synchs:
            self.assertTrue(synch._before is txn)
            self.assertTrue(synch._after is txn)

    def test_commit_w_afterCommitHooks(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        _hooked1, _hooked2 = [], []
        def _hook1(*args, **kw):
            _hooked1.append((args, kw))
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._after_commit.append((_hook1, ('one',), {'uno': 1}))
            txn._after_commit.append((_hook2, (), {}))
            logger._clear()
            txn.commit()
        self.assertEqual(_hooked1, [((True, 'one',), {'uno': 1})])
        self.assertEqual(_hooked2, [((True,), {})])
        self.assertEqual(txn._after_commit, [])
        self.assertEqual(txn._resources, [])

    def test_commit_error_w_afterCompleteHooks(self):
        from transaction import _transaction
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        class BrokenResource(object):
            def sortKey(self):
                return 'zzz'
            def tpc_begin(self, txn):
                raise ValueError('test')
        broken = BrokenResource()
        resource = Resource('aaa')
        _hooked1, _hooked2 = [], []
        def _hook1(*args, **kw):
            _hooked1.append((args, kw))
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._after_commit.append((_hook1, ('one',), {'uno': 1}))
            txn._after_commit.append((_hook2, (), {}))
            txn._resources.append(broken)
            txn._resources.append(resource)
            logger._clear()
            self.assertRaises(ValueError, txn.commit)
        self.assertEqual(_hooked1, [((False, 'one',), {'uno': 1})])
        self.assertEqual(_hooked2, [((False,), {})])
        self.assertEqual(txn._after_commit, [])
        self.assertTrue(resource._b)
        self.assertFalse(resource._c)
        self.assertFalse(resource._v)
        self.assertFalse(resource._f)
        self.assertTrue(resource._a)
        self.assertTrue(resource._x)

    def test_commit_error_w_synchronizers(self):
        from transaction.weakset import WeakSet
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Synch(object):
            _before = _after = False
            def beforeCompletion(self, txn):
                self._before = txn
            def afterCompletion(self, txn):
                self._after = txn
        synchs = [_Synch(), _Synch(), _Synch()]
        ws = WeakSet()
        for synch in synchs:
            ws.add(synch)
        class BrokenResource(object):
            def sortKey(self):
                return 'zzz'
            def tpc_begin(self, txn):
                raise ValueError('test')
        broken = BrokenResource()
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne(synchronizers=ws)
            logger._clear()
            txn._resources.append(broken)
            self.assertRaises(ValueError, txn.commit)
        for synch in synchs:
            self.assertTrue(synch._before is txn)
            self.assertTrue(synch._after is txn) #called in _cleanup

    def test_commit_clears_resources(self):
        class DM(object):
            tpc_begin = commit = tpc_finish = tpc_vote = lambda s, txn: True

        dm = DM()
        txn = self._makeOne()
        txn.join(dm)
        self.assertEqual(txn._resources, [dm])
        txn.commit()
        self.assertEqual(txn._resources, [])

    def test_getBeforeCommitHooks_empty(self):
        txn = self._makeOne()
        self.assertEqual(list(txn.getBeforeCommitHooks()), [])

    def test_addBeforeCommitHook(self):
        def _hook(*args, **kw):
            pass
        txn = self._makeOne()
        txn.addBeforeCommitHook(_hook, ('one',), dict(uno=1))
        self.assertEqual(list(txn.getBeforeCommitHooks()),
                         [(_hook, ('one',), {'uno': 1})])

    def test_addBeforeCommitHook_w_kws(self):
        def _hook(*args, **kw):
            pass
        txn = self._makeOne()
        txn.addBeforeCommitHook(_hook, ('one',))
        self.assertEqual(list(txn.getBeforeCommitHooks()),
                         [(_hook, ('one',), {})])

    def test_getAfterCommitHooks_empty(self):
        txn = self._makeOne()
        self.assertEqual(list(txn.getAfterCommitHooks()), [])

    def test_addAfterCommitHook(self):
        def _hook(*args, **kw):
            pass
        txn = self._makeOne()
        txn.addAfterCommitHook(_hook, ('one',), dict(uno=1))
        self.assertEqual(list(txn.getAfterCommitHooks()),
                         [(_hook, ('one',), {'uno': 1})])

    def test_addAfterCommitHook_wo_kws(self):
        def _hook(*args, **kw):
            pass
        txn = self._makeOne()
        txn.addAfterCommitHook(_hook, ('one',))
        self.assertEqual(list(txn.getAfterCommitHooks()),
                         [(_hook, ('one',), {})])

    def test_callAfterCommitHook_w_error(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        _hooked2 = []
        def _hook1(*args, **kw):
            raise ValueError()
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn.addAfterCommitHook(_hook1, ('one',))
        txn.addAfterCommitHook(_hook2, ('two',), dict(dos=2))
        txn._callAfterCommitHooks()
        # second hook gets called even if first raises
        self.assertEqual(_hooked2, [((True, 'two',), {'dos': 2})])
        self.assertEqual(len(logger._log), 1)
        self.assertEqual(logger._log[0][0], 'error')
        self.assertTrue(logger._log[0][1].startswith(
                            "Error in after commit hook"))

    def test_callAfterCommitHook_w_abort(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        _hooked2 = []
        def _hook1(*args, **kw):
            raise ValueError()
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn.addAfterCommitHook(_hook1, ('one',))
        txn.addAfterCommitHook(_hook2, ('two',), dict(dos=2))
        txn._callAfterCommitHooks()
        self.assertEqual(logger._log[0][0], 'error')
        self.assertTrue(logger._log[0][1].startswith(
                            "Error in after commit hook"))

    def test__commitResources_normal(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        resources = [Resource('bbb'), Resource('aaa')]
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn._resources.extend(resources)
        txn._commitResources()
        self.assertEqual(len(txn._voted), 2)
        for r in resources:
            self.assertTrue(r._b and r._c and r._v and r._f)
            self.assertFalse(r._a and r._x)
            self.assertTrue(id(r) in txn._voted)
        self.assertEqual(len(logger._log), 2)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'commit Resource: aaa')
        self.assertEqual(logger._log[1][0], 'debug')
        self.assertEqual(logger._log[1][1], 'commit Resource: bbb')

    def test__commitResources_error_in_tpc_begin(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        resources = [Resource('bbb', 'tpc_begin'), Resource('aaa')]
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn._resources.extend(resources)
        self.assertRaises(ValueError, txn._commitResources)
        for r in resources:
            if r._key == 'aaa':
                self.assertTrue(r._b)
            else:
                self.assertFalse(r._b)
            self.assertFalse(r._c and r._v and r._f)
            self.assertTrue(r._a and r._x)
        self.assertEqual(len(logger._log), 0)

    def test__commitResources_error_in_afterCompletion(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Synchrnonizers(object):
            def __init__(self, res):
                self._res = res
            def map(self, func):
                for res in self._res:
                    func(res)
        resources = [Resource('bbb', 'tpc_begin'),
                     Resource('aaa', 'afterCompletion')]
        sync = _Synchrnonizers(resources)
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne(sync)
        logger._clear()
        txn._resources.extend(resources)
        self.assertRaises(ValueError, txn._commitResources)
        for r in resources:
            if r._key == 'aaa':
                self.assertTrue(r._b)
            else:
                self.assertFalse(r._b)
            self.assertFalse(r._c and r._v and r._f)
            self.assertTrue(r._a and r._x)
        self.assertEqual(len(logger._log), 0)
        self.assertTrue(resources[0]._after)
        self.assertFalse(resources[1]._after)

    def test__commitResources_error_in_commit(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        resources = [Resource('bbb', 'commit'), Resource('aaa')]
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn._resources.extend(resources)
        self.assertRaises(ValueError, txn._commitResources)
        for r in resources:
            self.assertTrue(r._b)
            if r._key == 'aaa':
                self.assertTrue(r._c)
            else:
                self.assertFalse(r._c)
            self.assertFalse(r._v and r._f)
            self.assertTrue(r._a and r._x)
        self.assertEqual(len(logger._log), 1)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'commit Resource: aaa')

    def test__commitResources_error_in_tpc_vote(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        resources = [Resource('bbb', 'tpc_vote'), Resource('aaa')]
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn._resources.extend(resources)
        self.assertRaises(ValueError, txn._commitResources)
        self.assertEqual(len(txn._voted), 1)
        for r in resources:
            self.assertTrue(r._b and r._c)
            if r._key == 'aaa':
                self.assertTrue(id(r) in txn._voted)
                self.assertTrue(r._v)
                self.assertFalse(r._f)
                self.assertFalse(r._a)
                self.assertTrue(r._x)
            else:
                self.assertFalse(id(r) in txn._voted)
                self.assertFalse(r._v)
                self.assertFalse(r._f)
                self.assertTrue(r._a and r._x)
        self.assertEqual(len(logger._log), 2)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'commit Resource: aaa')
        self.assertEqual(logger._log[1][0], 'debug')
        self.assertEqual(logger._log[1][1], 'commit Resource: bbb')

    def test__commitResources_error_in_tpc_finish(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        resources = [Resource('bbb', 'tpc_finish'), Resource('aaa')]
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
        logger._clear()
        txn._resources.extend(resources)
        self.assertRaises(ValueError, txn._commitResources)
        for r in resources:
            self.assertTrue(r._b and r._c and r._v)
            self.assertTrue(id(r) in txn._voted)
            if r._key == 'aaa':
                self.assertTrue(r._f)
            else:
                self.assertFalse(r._f)
            self.assertFalse(r._a and r._x) #no cleanup if tpc_finish raises
        self.assertEqual(len(logger._log), 3)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'commit Resource: aaa')
        self.assertEqual(logger._log[1][0], 'debug')
        self.assertEqual(logger._log[1][1], 'commit Resource: bbb')
        self.assertEqual(logger._log[2][0], 'critical')
        self.assertTrue(logger._log[2][1].startswith(
                        'A storage error occurred'))

    def test_abort_wo_savepoints_wo_hooks_wo_synchronizers(self):
        from transaction._transaction import Status
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Mgr(object):
            def __init__(self, txn):
                self._txn = txn
            def free(self, txn):
                assert txn is self._txn
                self._txn = None
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            logger._clear()
            mgr = txn._manager = _Mgr(txn)
            txn.abort()
        self.assertEqual(txn.status, Status.ACTIVE)
        self.assertTrue(mgr._txn is None)
        self.assertEqual(logger._log[0][0], 'debug')
        self.assertEqual(logger._log[0][1], 'abort')

    def test_abort_w_savepoints(self):
        from weakref import WeakKeyDictionary
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _SP(object):
            def __init__(self, txn, index):
                self.transaction = txn
                self._index = index
            def __repr__(self):
                return '_SP: %d' % self._index
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._savepoint2index = WeakKeyDictionary()
            holdme = []
            for i in range(10):
                sp = _SP(txn, i)
                holdme.append(sp) #prevent gc
                txn._savepoint2index[sp] = i
            logger._clear()
            txn.abort()
        self.assertEqual(list(txn._savepoint2index), [])

    def test_abort_w_beforeCommitHooks(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        _hooked1, _hooked2 = [], []
        def _hook1(*args, **kw):
            _hooked1.append((args, kw))
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._before_commit.append((_hook1, ('one',), {'uno': 1}))
            txn._before_commit.append((_hook2, (), {}))
            logger._clear()
            txn.abort()
        self.assertEqual(_hooked1, [])
        self.assertEqual(_hooked2, [])
        # Hooks are neither called nor cleared on abort
        self.assertEqual(list(txn.getBeforeCommitHooks()),
                         [(_hook1, ('one',), {'uno': 1}), (_hook2, (), {})])

    def test_abort_w_synchronizers(self):
        from transaction.weakset import WeakSet
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Synch(object):
            _before = _after = False
            def beforeCompletion(self, txn):
                self._before = txn
            def afterCompletion(self, txn):
                self._after = txn
        synchs = [_Synch(), _Synch(), _Synch()]
        ws = WeakSet()
        for synch in synchs:
            ws.add(synch)
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne(synchronizers=ws)
            logger._clear()
            txn.abort()
        for synch in synchs:
            self.assertTrue(synch._before is txn)
            self.assertTrue(synch._after is txn)

    def test_abort_w_afterCommitHooks(self):
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        _hooked1, _hooked2 = [], []
        def _hook1(*args, **kw):
            _hooked1.append((args, kw))
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._after_commit.append((_hook1, ('one',), {'uno': 1}))
            txn._after_commit.append((_hook2, (), {}))
            logger._clear()
            txn.abort()
        # Hooks are neither called nor cleared on abort
        self.assertEqual(_hooked1, [])
        self.assertEqual(_hooked2, [])
        self.assertEqual(list(txn.getAfterCommitHooks()),
                         [(_hook1, ('one',), {'uno': 1}), (_hook2, (), {})])
        self.assertEqual(txn._resources, [])

    def test_abort_error_w_afterCompleteHooks(self):
        from transaction import _transaction
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        class BrokenResource(object):
            def sortKey(self):
                return 'zzz'
            def abort(self, txn):
                raise ValueError('test')
        broken = BrokenResource()
        aaa = Resource('aaa')
        broken2 = BrokenResource()
        _hooked1, _hooked2 = [], []
        def _hook1(*args, **kw):
            _hooked1.append((args, kw))
        def _hook2(*args, **kw):
            _hooked2.append((args, kw))
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            txn = self._makeOne()
            txn._after_commit.append((_hook1, ('one',), {'uno': 1}))
            txn._after_commit.append((_hook2, (), {}))
            txn._resources.append(aaa)
            txn._resources.append(broken)
            txn._resources.append(broken2)
            logger._clear()
            self.assertRaises(ValueError, txn.abort)
        # Hooks are neither called nor cleared on abort
        self.assertEqual(_hooked1, [])
        self.assertEqual(_hooked2, [])
        self.assertEqual(list(txn.getAfterCommitHooks()),
                         [(_hook1, ('one',), {'uno': 1}), (_hook2, (), {})])
        self.assertTrue(aaa._a)
        self.assertFalse(aaa._x)

    def test_abort_error_w_synchronizers(self):
        from transaction.weakset import WeakSet
        from transaction.tests.common import DummyLogger
        from transaction.tests.common import Monkey
        from transaction import _transaction
        class _Synch(object):
            _before = _after = False
            def beforeCompletion(self, txn):
                self._before = txn
            def afterCompletion(self, txn):
                self._after = txn
        synchs = [_Synch(), _Synch(), _Synch()]
        ws = WeakSet()
        for synch in synchs:
            ws.add(synch)
        class BrokenResource(object):
            def sortKey(self):
                return 'zzz'
            def abort(self, txn):
                raise ValueError('test')
        broken = BrokenResource()
        logger = DummyLogger()
        with Monkey(_transaction, _LOGGER=logger):
            t = self._makeOne(synchronizers=ws)
            logger._clear()
            t._resources.append(broken)
            self.assertRaises(ValueError, t.abort)
        for synch in synchs:
            self.assertTrue(synch._before is t)
            self.assertTrue(synch._after is t) #called in _cleanup

    def test_abort_clears_resources(self):
        class DM(object):
            abort = lambda s, txn: True

        dm = DM()
        txn = self._makeOne()
        txn.join(dm)
        self.assertEqual(txn._resources, [dm])
        txn.abort()
        self.assertEqual(txn._resources, [])

    def test_note(self):
        txn = self._makeOne()
        try:
            txn.note('This is a note.')
            self.assertEqual(txn.description, 'This is a note.')
            txn.note('Another.')
            self.assertEqual(txn.description, 'This is a note.\nAnother.')
        finally:
            txn.abort()

    def test_setUser_default_path(self):
        txn = self._makeOne()
        txn.setUser('phreddy')
        self.assertEqual(txn.user, '/ phreddy')

    def test_setUser_explicit_path(self):
        txn = self._makeOne()
        txn.setUser('phreddy', '/bedrock')
        self.assertEqual(txn.user, '/bedrock phreddy')

    def test_setExtendedInfo_single(self):
        txn = self._makeOne()
        txn.setExtendedInfo('frob', 'qux')
        self.assertEqual(txn._extension, {'frob': 'qux'})

    def test_setExtendedInfo_multiple(self):
        txn = self._makeOne()
        txn.setExtendedInfo('frob', 'qux')
        txn.setExtendedInfo('baz', 'spam')
        txn.setExtendedInfo('frob', 'quxxxx')
        self.assertEqual(txn._extension, {'frob': 'quxxxx', 'baz': 'spam'})

    def test_data(self):
        txn = self._makeOne()

        # Can't get data that wasn't set:
        with self.assertRaises(KeyError) as c:
            txn.data(self)
        self.assertEqual(c.exception.args, (self,))

        data = dict(a=1)
        txn.set_data(self, data)
        self.assertEqual(txn.data(self), data)

        # Can't get something we haven't stored.
        with self.assertRaises(KeyError) as c:
            txn.data(data)
        self.assertEqual(c.exception.args, (data,))

        # When the transaction ends, data are discarded:
        txn.commit()
        with self.assertRaises(KeyError) as c:
            txn.data(self)
        self.assertEqual(c.exception.args, (self,))


class MultiObjectResourceAdapterTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import MultiObjectResourceAdapter
        return MultiObjectResourceAdapter

    def _makeOne(self, jar):
        return self._getTargetClass()(jar)

    def _makeJar(self, key):
        class _Resource(Resource):
            def __init__(self, key):
                super(_Resource, self).__init__(key)
                self._c = []
                self._a = []
            def commit(self, obj, txn):
                self._c.append((obj, txn))
            def abort(self, obj, txn):
                self._a.append((obj, txn))
        return _Resource(key)

    def _makeDummy(self, kind, name):
        class _Dummy(object):
            def __init__(self, kind, name):
                self._kind = kind
                self._name = name
            def __repr__(self):
                return '<%s: %s>' % (self._kind, self._name)
        return _Dummy(kind, name)

    def test_ctor(self):
        jar = self._makeJar('aaa')
        mora = self._makeOne(jar)
        self.assertTrue(mora.manager is jar)
        self.assertEqual(mora.objects, [])
        self.assertEqual(mora.ncommitted, 0)

    def test___repr__(self):
        jar = self._makeJar('bbb')
        mora = self._makeOne(jar)
        self.assertEqual(repr(mora),
                         '<MultiObjectResourceAdapter '
                            'for Resource: bbb at %s>' % id(mora))

    def test_sortKey(self):
        jar = self._makeJar('ccc')
        mora = self._makeOne(jar)
        self.assertEqual(mora.sortKey(), 'ccc')

    def test_tpc_begin(self):
        jar = self._makeJar('ddd')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_begin(txn)
        self.assertTrue(jar._b)

    def test_commit(self):
        jar = self._makeJar('eee')
        objects = [self._makeDummy('obj', 'a'), self._makeDummy('obj', 'b')]
        mora = self._makeOne(jar)
        mora.objects.extend(objects)
        txn = self._makeDummy('txn', 'c')
        mora.commit(txn)
        self.assertEqual(jar._c, [(objects[0], txn), (objects[1], txn)])

    def test_tpc_vote(self):
        jar = self._makeJar('fff')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_vote(txn)
        self.assertTrue(jar._v)

    def test_tpc_finish(self):
        jar = self._makeJar('ggg')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_finish(txn)
        self.assertTrue(jar._f)

    def test_abort(self):
        jar = self._makeJar('hhh')
        objects = [self._makeDummy('obj', 'a'), self._makeDummy('obj', 'b')]
        mora = self._makeOne(jar)
        mora.objects.extend(objects)
        txn = self._makeDummy('txn', 'c')
        mora.abort(txn)
        self.assertEqual(jar._a, [(objects[0], txn), (objects[1], txn)])

    def test_abort_w_error(self):
        from transaction.tests.common import DummyLogger
        jar = self._makeJar('hhh')
        objects = [self._makeDummy('obj', 'a'),
                   self._makeDummy('obj', 'b'),
                   self._makeDummy('obj', 'c'),
                  ]
        _old_abort = jar.abort
        def _abort(obj, txn):
            if obj._name in ('b', 'c'):
                raise ValueError()
            _old_abort(obj, txn)
        jar.abort = _abort
        mora = self._makeOne(jar)
        mora.objects.extend(objects)
        txn = self._makeDummy('txn', 'c')
        txn.log = log = DummyLogger()
        self.assertRaises(ValueError, mora.abort, txn)
        self.assertEqual(jar._a, [(objects[0], txn)])

    def test_tpc_abort(self):
        jar = self._makeJar('iii')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_abort(txn)
        self.assertTrue(jar._x)


class Test_rm_key(unittest.TestCase):

    def _callFUT(self, oid):
        from transaction._transaction import rm_key
        return rm_key(oid)

    def test_miss(self):
        self.assertTrue(self._callFUT(object()) is None)

    def test_hit(self):
        self.assertEqual(self._callFUT(Resource('zzz')), 'zzz')


class Test_object_hint(unittest.TestCase):

    def _callFUT(self, oid):
        from transaction._transaction import object_hint
        return object_hint(oid)

    def test_miss(self):
        class _Test(object):
            pass
        test = _Test()
        self.assertEqual(self._callFUT(test), "_Test oid=None")

    def test_hit(self):
        class _Test(object):
            pass
        test = _Test()
        test._p_oid = 'OID'
        self.assertEqual(self._callFUT(test), "_Test oid='OID'")


class Test_oid_repr(unittest.TestCase):

    def _callFUT(self, oid):
        from transaction._transaction import oid_repr
        return oid_repr(oid)

    def test_as_nonstring(self):
        self.assertEqual(self._callFUT(123), '123')

    def test_as_string_not_8_chars(self):
        self.assertEqual(self._callFUT('a'), "'a'")

    def test_as_string_z64(self):
        s = '\0'*8
        self.assertEqual(self._callFUT(s), '0x00')

    def test_as_string_all_Fs(self):
        s = '\1'*8
        self.assertEqual(self._callFUT(s), '0x0101010101010101')

    def test_as_string_xxx(self):
        s = '\20'*8
        self.assertEqual(self._callFUT(s), '0x1010101010101010')


class DataManagerAdapterTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import DataManagerAdapter
        return DataManagerAdapter

    def _makeOne(self, jar):
        return self._getTargetClass()(jar)

    def _makeJar(self, key):
        class _Resource(Resource):
            _p = False
            def prepare(self, txn):
                self._p = True
        return _Resource(key)

    def _makeDummy(self, kind, name):
        class _Dummy(object):
            def __init__(self, kind, name):
                self._kind = kind
                self._name = name
            def __repr__(self):
                return '<%s: %s>' % (self._kind, self._name)
        return _Dummy(kind, name)

    def test_ctor(self):
        jar = self._makeJar('aaa')
        dma = self._makeOne(jar)
        self.assertTrue(dma._datamanager is jar)

    def test_commit(self):
        jar = self._makeJar('bbb')
        mora = self._makeOne(jar)
        txn = self._makeDummy('txn', 'c')
        mora.commit(txn)
        self.assertFalse(jar._c) #no-op

    def test_abort(self):
        jar = self._makeJar('ccc')
        mora = self._makeOne(jar)
        txn = self._makeDummy('txn', 'c')
        mora.abort(txn)
        self.assertTrue(jar._a)

    def test_tpc_begin(self):
        jar = self._makeJar('ddd')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_begin(txn)
        self.assertFalse(jar._b) #no-op

    def test_tpc_abort(self):
        jar = self._makeJar('eee')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_abort(txn)
        self.assertFalse(jar._f)
        self.assertTrue(jar._a)

    def test_tpc_finish(self):
        jar = self._makeJar('fff')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_finish(txn)
        self.assertFalse(jar._f)
        self.assertTrue(jar._c)

    def test_tpc_vote(self):
        jar = self._makeJar('ggg')
        mora = self._makeOne(jar)
        txn = object()
        mora.tpc_vote(txn)
        self.assertFalse(jar._v)
        self.assertTrue(jar._p)

    def test_sortKey(self):
        jar = self._makeJar('hhh')
        mora = self._makeOne(jar)
        self.assertEqual(mora.sortKey(), 'hhh')


class SavepointTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import Savepoint
        return Savepoint

    def _makeOne(self, txn, optimistic, *resources):
        return self._getTargetClass()(txn, optimistic, *resources)

    def test_ctor_w_savepoint_oblivious_resource_non_optimistic(self):
        txn = object()
        resource = object()
        self.assertRaises(TypeError, self._makeOne, txn, False, resource)

    def test_ctor_w_savepoint_oblivious_resource_optimistic(self):
        from transaction._transaction import NoRollbackSavepoint
        txn = object()
        resource = object()
        sp = self._makeOne(txn, True, resource)
        self.assertEqual(len(sp._savepoints), 1)
        self.assertTrue(isinstance(sp._savepoints[0], NoRollbackSavepoint))
        self.assertTrue(sp._savepoints[0].datamanager is resource)

    def test_ctor_w_savepoint_aware_resources(self):
        class _Aware(object):
            def savepoint(self):
                return self
        txn = object()
        one = _Aware()
        another = _Aware()
        sp = self._makeOne(txn, True, one, another)
        self.assertEqual(len(sp._savepoints), 2)
        self.assertTrue(isinstance(sp._savepoints[0], _Aware))
        self.assertTrue(sp._savepoints[0] is one)
        self.assertTrue(isinstance(sp._savepoints[1], _Aware))
        self.assertTrue(sp._savepoints[1] is another)

    def test_valid_wo_transacction(self):
        sp = self._makeOne(None, True, object())
        self.assertFalse(sp.valid)

    def test_valid_w_transacction(self):
        sp = self._makeOne(object(), True, object())
        self.assertTrue(sp.valid)

    def test_rollback_w_txn_None(self):
        from transaction.interfaces import InvalidSavepointRollbackError
        txn = None
        class _Aware(object):
            def savepoint(self):
                return self
        resource = _Aware()
        sp = self._makeOne(txn, False, resource)
        self.assertRaises(InvalidSavepointRollbackError, sp.rollback)

    def test_rollback_w_sp_error(self):
        class _TXN(object):
            _sarce = False
            _raia = None
            def _saveAndRaiseCommitishError(self):
                import sys
                from transaction._compat import reraise
                self._sarce = True
                reraise(*sys.exc_info())
            def _remove_and_invalidate_after(self, sp):
                self._raia = sp
        class _Broken(object):
            def rollback(self):
                raise ValueError()
        _broken = _Broken()
        class _GonnaRaise(object):
            def savepoint(self):
                return _broken
        txn = _TXN()
        resource = _GonnaRaise()
        sp = self._makeOne(txn, False, resource)
        self.assertRaises(ValueError, sp.rollback)
        self.assertTrue(txn._raia is sp)
        self.assertTrue(txn._sarce)


class AbortSavepointTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import AbortSavepoint
        return AbortSavepoint

    def _makeOne(self, datamanager, transaction):
        return self._getTargetClass()(datamanager, transaction)

    def test_ctor(self):
        dm = object()
        txn = object()
        asp = self._makeOne(dm, txn)
        self.assertTrue(asp.datamanager is dm)
        self.assertTrue(asp.transaction is txn)

    def test_rollback(self):
        class _DM(object):
            _aborted = None
            def abort(self, txn):
                self._aborted = txn
        class _TXN(object):
            _unjoined = None
            def _unjoin(self, datamanager):
                self._unjoin = datamanager
        dm = _DM()
        txn = _TXN()
        asp = self._makeOne(dm, txn)
        asp.rollback()
        self.assertTrue(dm._aborted is txn)
        self.assertTrue(txn._unjoin is dm)


class NoRollbackSavepointTests(unittest.TestCase):

    def _getTargetClass(self):
        from transaction._transaction import NoRollbackSavepoint
        return NoRollbackSavepoint

    def _makeOne(self, datamanager):
        return self._getTargetClass()(datamanager)

    def test_ctor(self):
        dm = object()
        nrsp = self._makeOne(dm)
        self.assertTrue(nrsp.datamanager is dm)

    def test_rollback(self):
        dm = object()
        nrsp = self._makeOne(dm)
        self.assertRaises(TypeError, nrsp.rollback)


class MiscellaneousTests(unittest.TestCase):

    def test_BBB_join(self):
        # The join method is provided for "backward-compatability" with ZODB 4
        # data managers.
        from transaction import Transaction
        from transaction.tests.examples import DataManager
        from transaction._transaction import DataManagerAdapter
        # The argument to join must be a zodb4 data manager,
        # transaction.interfaces.IDataManager.
        txn = Transaction()
        dm = DataManager()
        txn.join(dm)
        # The end result is that a data manager adapter is one of the
        # transaction's objects:
        self.assertTrue(isinstance(txn._resources[0], DataManagerAdapter))
        self.assertTrue(txn._resources[0]._datamanager is dm)

    def test_bug239086(self):
        # The original implementation of thread transaction manager made
        # invalid assumptions about thread ids.
        import threading
        import transaction
        import transaction.tests.savepointsample as SPS
        dm = SPS.SampleSavepointDataManager()
        self.assertEqual(list(dm.keys()), [])

        class Sync:
             def __init__(self, label):
                 self.label = label
                 self.log = []
             def beforeCompletion(self, txn):
                 self.log.append('%s %s' % (self.label, 'before'))
             def afterCompletion(self, txn):
                 self.log.append('%s %s' % (self.label, 'after'))
             def newTransaction(self, txn):
                 self.log.append('%s %s' % (self.label, 'new'))

        def run_in_thread(f):
            txn = threading.Thread(target=f)
            txn.start()
            txn.join()

        sync = Sync(1)
        @run_in_thread
        def first():
            transaction.manager.registerSynch(sync)
            transaction.manager.begin()
            dm['a'] = 1
        self.assertEqual(sync.log, ['1 new'])

        @run_in_thread
        def second():
            transaction.abort() # should do nothing.
        self.assertEqual(sync.log, ['1 new'])
        self.assertEqual(list(dm.keys()), ['a'])

        dm = SPS.SampleSavepointDataManager()
        self.assertEqual(list(dm.keys()), [])

        @run_in_thread
        def third():
            dm['a'] = 1
        self.assertEqual(sync.log, ['1 new'])

        transaction.abort() # should do nothing
        self.assertEqual(list(dm.keys()), ['a'])

class Resource(object):
    _b = _c = _v = _f = _a = _x = _after = False
    def __init__(self, key, error=None):
        self._key = key
        self._error = error
    def __repr__(self):
        return 'Resource: %s' % self._key
    def sortKey(self):
        return self._key
    def tpc_begin(self, txn):
        if self._error == 'tpc_begin':
            raise ValueError()
        self._b = True
    def commit(self, txn):
        if self._error == 'commit':
            raise ValueError()
        self._c = True
    def tpc_vote(self, txn):
        if self._error == 'tpc_vote':
            raise ValueError()
        self._v = True
    def tpc_finish(self, txn):
        if self._error == 'tpc_finish':
            raise ValueError()
        self._f = True
    def abort(self, txn):
        if self._error == 'abort':
            raise ValueError()
        self._a = True
    def tpc_abort(self, txn):
        if self._error == 'tpc_abort':
            raise ValueError()
        self._x = True
    def afterCompletion(self, txn):
        if self._error == 'afterCompletion':
            raise ValueError()
        self._after = True

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TransactionTests),
        unittest.makeSuite(MultiObjectResourceAdapterTests),
        unittest.makeSuite(Test_rm_key),
        unittest.makeSuite(Test_object_hint),
        unittest.makeSuite(Test_oid_repr),
        unittest.makeSuite(DataManagerAdapterTests),
        unittest.makeSuite(SavepointTests),
        unittest.makeSuite(AbortSavepointTests),
        unittest.makeSuite(NoRollbackSavepointTests),
        unittest.makeSuite(MiscellaneousTests),
        ))

if __name__ == '__main__':
    unittest.main()
