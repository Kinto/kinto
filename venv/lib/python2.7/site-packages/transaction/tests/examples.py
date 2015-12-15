##############################################################################
#
# Copyright (c) 2004 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Sample objects for use in tests

"""


class DataManager(object):
    """Sample data manager

    Used by the 'datamanager' chapter in the Sphinx docs.
    """
    def __init__(self):
        self.state = 0
        self.sp = 0
        self.transaction = None
        self.delta = 0
        self.prepared = False

    def inc(self, n=1):
        self.delta += n

    def prepare(self, transaction):
        if self.prepared:
            raise TypeError('Already prepared')
        self._checkTransaction(transaction)
        self.prepared = True
        self.transaction = transaction
        self.state += self.delta

    def _checkTransaction(self, transaction):
        if (transaction is not self.transaction
            and self.transaction is not None):
            raise TypeError("Transaction missmatch",
                            transaction, self.transaction)

    def abort(self, transaction):
        self._checkTransaction(transaction)
        if self.transaction is not None:
            self.transaction = None

        if self.prepared:
            self.state -= self.delta
            self.prepared = False

        self.delta = 0

    def commit(self, transaction):
        if not self.prepared:
            raise TypeError('Not prepared to commit')
        self._checkTransaction(transaction)
        self.delta = 0
        self.transaction = None
        self.prepared = False

    def savepoint(self, transaction):
        if self.prepared:
            raise TypeError("Can't get savepoint during two-phase commit")
        self._checkTransaction(transaction)
        self.transaction = transaction
        self.sp += 1
        return Rollback(self)


class Rollback(object):

    def __init__(self, dm):
        self.dm = dm
        self.sp = dm.sp
        self.delta = dm.delta
        self.transaction = dm.transaction

    def rollback(self):
        if self.transaction is not self.dm.transaction:
            raise TypeError("Attempt to rollback stale rollback")
        if self.dm.sp < self.sp:
            raise TypeError("Attempt to roll back to invalid save point",
                            self.sp, self.dm.sp)
        self.dm.sp = self.sp
        self.dm.delta = self.delta


class ResourceManager(object):
    """ Sample resource manager.

    Used by the 'resourcemanager' chapter in the Sphinx docs.
    """
    def __init__(self):
        self.state = 0
        self.sp = 0
        self.transaction = None
        self.delta = 0
        self.txn_state = None

    def _check_state(self, *ok_states):
        if self.txn_state not in ok_states:
            raise ValueError("txn in state %r but expected one of %r" %
                             (self.txn_state, ok_states))

    def _checkTransaction(self, transaction):
        if (transaction is not self.transaction
            and self.transaction is not None):
            raise TypeError("Transaction missmatch",
                            transaction, self.transaction)

    def inc(self, n=1):
        self.delta += n

    def tpc_begin(self, transaction):
        self._checkTransaction(transaction)
        self._check_state(None)
        self.transaction = transaction
        self.txn_state = 'tpc_begin'

    def tpc_vote(self, transaction):
        self._checkTransaction(transaction)
        self._check_state('tpc_begin')
        self.state += self.delta
        self.txn_state = 'tpc_vote'

    def tpc_finish(self, transaction):
        self._checkTransaction(transaction)
        self._check_state('tpc_vote')
        self.delta = 0
        self.transaction = None
        self.prepared = False
        self.txn_state = None

    def tpc_abort(self, transaction):
        self._checkTransaction(transaction)
        if self.transaction is not None:
            self.transaction = None

        if self.txn_state == 'tpc_vote':
            self.state -= self.delta

        self.txn_state = None
        self.delta = 0

    def savepoint(self, transaction):
        if self.txn_state is not None:
            raise TypeError("Can't get savepoint during two-phase commit")
        self._checkTransaction(transaction)
        self.transaction = transaction
        self.sp += 1
        return SavePoint(self)

    def discard(self, transaction):
        pass


class SavePoint(object):

    def __init__(self, rm):
        self.rm = rm
        self.sp = rm.sp
        self.delta = rm.delta
        self.transaction = rm.transaction

    def rollback(self):
        if self.transaction is not self.rm.transaction:
            raise TypeError("Attempt to rollback stale rollback")
        if self.rm.sp < self.sp:
            raise TypeError("Attempt to roll back to invalid save point",
                            self.sp, self.rm.sp)
        self.rm.sp = self.sp
        self.rm.delta = self.delta

    def discard(self):
        pass
