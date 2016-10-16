############################################################################
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
############################################################################
import binascii
import logging
import sys
import weakref
import traceback

from zope.interface import implementer

from transaction.weakset import WeakSet
from transaction.interfaces import TransactionFailedError
from transaction import interfaces
from transaction._compat import reraise
from transaction._compat import get_thread_ident
from transaction._compat import native_
from transaction._compat import bytes_
from transaction._compat import StringIO

_marker = object()

_TB_BUFFER = None #unittests may hook
def _makeTracebackBuffer(): #pragma NO COVER
    if _TB_BUFFER is not None:
        return _TB_BUFFER
    return StringIO()

_LOGGER = None #unittests may hook
def _makeLogger(): #pragma NO COVER
    if _LOGGER is not None:
        return _LOGGER
    return logging.getLogger("txn.%d" % get_thread_ident())


# The point of this is to avoid hiding exceptions (which the builtin
# hasattr() does).
def myhasattr(obj, attr):
    return getattr(obj, attr, _marker) is not _marker

class Status:
    # ACTIVE is the initial state.
    ACTIVE       = "Active"

    COMMITTING   = "Committing"
    COMMITTED    = "Committed"

    DOOMED = "Doomed"

    # commit() or commit(True) raised an exception.  All further attempts
    # to commit or join this transaction will raise TransactionFailedError.
    COMMITFAILED = "Commit failed"

@implementer(interfaces.ITransaction,
             interfaces.ITransactionDeprecated)
class Transaction(object):



    # Assign an index to each savepoint so we can invalidate later savepoints
    # on rollback.  The first index assigned is 1, and it goes up by 1 each
    # time.
    _savepoint_index = 0

    # If savepoints are used, keep a weak key dict of them.  This maps a
    # savepoint to its index (see above).
    _savepoint2index = None

    # Meta data.  ._extension is also metadata, but is initialized to an
    # emtpy dict in __init__.
    user = ""
    description = ""

    def __init__(self, synchronizers=None, manager=None):
        self.status = Status.ACTIVE
        # List of resource managers, e.g. MultiObjectResourceAdapters.
        self._resources = []

        # Weak set of synchronizer objects to call.
        if synchronizers is None:
            synchronizers = WeakSet()
        self._synchronizers = synchronizers

        self._manager = manager

        # _adapters: Connection/_p_jar -> MultiObjectResourceAdapter[Sub]
        self._adapters = {}
        self._voted = {} # id(Connection) -> boolean, True if voted
        # _voted and other dictionaries use the id() of the resource
        # manager as a key, because we can't guess whether the actual
        # resource managers will be safe to use as dict keys.

        # The user, description, and _extension attributes are accessed
        # directly by storages, leading underscore notwithstanding.
        self._extension = {}

        self.log = _makeLogger()
        self.log.debug("new transaction")

        # If a commit fails, the traceback is saved in _failure_traceback.
        # If another attempt is made to commit, TransactionFailedError is
        # raised, incorporating this traceback.
        self._failure_traceback = None

        # List of (hook, args, kws) tuples added by addBeforeCommitHook().
        self._before_commit = []

        # List of (hook, args, kws) tuples added by addAfterCommitHook().
        self._after_commit = []

    def isDoomed(self):
        """ See ITransaction.
        """
        return self.status is Status.DOOMED

    def doom(self):
        """ See ITransaction.
        """
        if self.status is not Status.DOOMED:
            if self.status is not Status.ACTIVE:
                # should not doom transactions in the middle,
                # or after, a commit
                raise ValueError('non-doomable')
            self.status = Status.DOOMED

    # Raise TransactionFailedError, due to commit()/join()/register()
    # getting called when the current transaction has already suffered
    # a commit/savepoint failure.
    def _prior_operation_failed(self):
        assert self._failure_traceback is not None
        raise TransactionFailedError("An operation previously failed, "
                "with traceback:\n\n%s" %
                self._failure_traceback.getvalue())

    def join(self, resource):
        """ See ITransaction.
        """
        if self.status is Status.COMMITFAILED:
            self._prior_operation_failed() # doesn't return

        if (self.status is not Status.ACTIVE and
                self.status is not Status.DOOMED):
            # TODO: Should it be possible to join a committing transaction?
            # I think some users want it.
            raise ValueError("expected txn status %r or %r, but it's %r" % (
                             Status.ACTIVE, Status.DOOMED, self.status))
        # TODO: the prepare check is a bit of a hack, perhaps it would
        # be better to use interfaces.  If this is a ZODB4-style
        # resource manager, it needs to be adapted, too.
        if myhasattr(resource, "prepare"):
            # TODO: deprecate 3.6
            resource = DataManagerAdapter(resource)
        self._resources.append(resource)

        if self._savepoint2index:
            # A data manager has joined a transaction *after* a savepoint
            # was created.  A couple of things are different in this case:
            #
            # 1. We need to add its savepoint to all previous savepoints.
            # so that if they are rolled back, we roll this one back too.
            #
            # 2. We don't actually need to ask the data manager for a
            # savepoint:  because it's just joining, we can just abort it to
            # roll back to the current state, so we simply use an
            # AbortSavepoint.
            datamanager_savepoint = AbortSavepoint(resource, self)
            for transaction_savepoint in self._savepoint2index.keys():
                transaction_savepoint._savepoints.append(
                    datamanager_savepoint)

    def _unjoin(self, resource):
        # Leave a transaction because a savepoint was rolled back on a resource
        # that joined later.

        # Don't use remove.  We don't want to assume anything about __eq__.
        self._resources = [r for r in self._resources if r is not resource]

    def savepoint(self, optimistic=False):
        """ See ITransaction.
        """
        if self.status is Status.COMMITFAILED:
            self._prior_operation_failed() # doesn't return, it raises

        try:
            savepoint = Savepoint(self, optimistic, *self._resources)
        except:
            self._cleanup(self._resources)
            self._saveAndRaiseCommitishError() # reraises!

        if self._savepoint2index is None:
            self._savepoint2index = weakref.WeakKeyDictionary()
        self._savepoint_index += 1
        self._savepoint2index[savepoint] = self._savepoint_index

        return savepoint

    # Remove and invalidate all savepoints we know about with an index
    # larger than `savepoint`'s.  This is what's needed when a rollback
    # _to_ `savepoint` is done.
    def _remove_and_invalidate_after(self, savepoint):
        savepoint2index = self._savepoint2index
        index = savepoint2index[savepoint]
        # use list(items()) to make copy to avoid mutating while iterating
        for savepoint, i in list(savepoint2index.items()):
            if i > index:
                savepoint.transaction = None # invalidate
                del savepoint2index[savepoint]

    # Invalidate and forget about all savepoints.
    def _invalidate_all_savepoints(self):
        for savepoint in self._savepoint2index.keys():
            savepoint.transaction = None # invalidate
        self._savepoint2index.clear()


    def register(self, obj):
        """ See ITransaction.
        """
        # The old way of registering transaction participants.
        #
        # register() is passed either a persisent object or a
        # resource manager like the ones defined in ZODB.DB.
        # If it is passed a persistent object, that object should
        # be stored when the transaction commits.  For other
        # objects, the object implements the standard two-phase
        # commit protocol.
        manager = getattr(obj, "_p_jar", obj)
        if manager is None:
            raise ValueError("Register with no manager")
        adapter = self._adapters.get(manager)
        if adapter is None:
            adapter = MultiObjectResourceAdapter(manager)
            adapter.objects.append(obj)
            self._adapters[manager] = adapter
            self.join(adapter)
        else:
            # TODO: comment out this expensive assert later
            # Use id() to guard against proxies.
            assert id(obj) not in map(id, adapter.objects)
            adapter.objects.append(obj)

    def commit(self):
        """ See ITransaction.
        """
        if self.status is Status.DOOMED:
            raise interfaces.DoomedTransaction(
                'transaction doomed, cannot commit')

        if self._savepoint2index:
            self._invalidate_all_savepoints()

        if self.status is Status.COMMITFAILED:
            self._prior_operation_failed() # doesn't return

        self._callBeforeCommitHooks()

        self._synchronizers.map(lambda s: s.beforeCompletion(self))
        self.status = Status.COMMITTING

        try:
            self._commitResources()
            self.status = Status.COMMITTED
        except:
            t = None
            v = None
            tb = None
            try:
                t, v, tb = self._saveAndGetCommitishError()
                self._callAfterCommitHooks(status=False)
                reraise(t, v, tb)
            finally:
                del t, v, tb
        else:
            self._free()
            self._synchronizers.map(lambda s: s.afterCompletion(self))
            self._callAfterCommitHooks(status=True)
        self.log.debug("commit")

    def _saveAndGetCommitishError(self):
        self.status = Status.COMMITFAILED
        # Save the traceback for TransactionFailedError.
        ft = self._failure_traceback = _makeTracebackBuffer()
        t = None
        v = None
        tb = None
        try:
            t, v, tb = sys.exc_info()
            # Record how we got into commit().
            traceback.print_stack(sys._getframe(1), None, ft)
            # Append the stack entries from here down to the exception.
            traceback.print_tb(tb, None, ft)
            # Append the exception type and value.
            ft.writelines(traceback.format_exception_only(t, v))
            return t, v, tb
        finally:
            del t, v, tb

    def _saveAndRaiseCommitishError(self):
        t = None
        v = None
        tb = None
        try:
            t, v, tb = self._saveAndGetCommitishError()
            reraise(t, v, tb)
        finally:
            del t, v, tb

    def getBeforeCommitHooks(self):
        """ See ITransaction.
        """
        return iter(self._before_commit)

    def addBeforeCommitHook(self, hook, args=(), kws=None):
        """ See ITransaction.
        """
        if kws is None:
            kws = {}
        self._before_commit.append((hook, tuple(args), kws))

    def _callBeforeCommitHooks(self):
        # Call all hooks registered, allowing further registrations
        # during processing.  Note that calls to addBeforeCommitHook() may
        # add additional hooks while hooks are running, and iterating over a
        # growing list is well-defined in Python.
        for hook, args, kws in self._before_commit:
            hook(*args, **kws)
        self._before_commit = []

    def getAfterCommitHooks(self):
        """ See ITransaction.
        """
        return iter(self._after_commit)

    def addAfterCommitHook(self, hook, args=(), kws=None):
        """ See ITransaction.
        """
        if kws is None:
            kws = {}
        self._after_commit.append((hook, tuple(args), kws))

    def _callAfterCommitHooks(self, status=True):
        # Avoid to abort anything at the end if no hooks are registred.
        if not self._after_commit:
            return
        # Call all hooks registered, allowing further registrations
        # during processing.  Note that calls to addAterCommitHook() may
        # add additional hooks while hooks are running, and iterating over a
        # growing list is well-defined in Python.
        for hook, args, kws in self._after_commit:
            # The first argument passed to the hook is a Boolean value,
            # true if the commit succeeded, or false if the commit aborted.
            try:
                hook(status, *args, **kws)
            except:
                # We need to catch the exceptions if we want all hooks
                # to be called
                self.log.error("Error in after commit hook exec in %s ",
                               hook, exc_info=sys.exc_info())
        # The transaction is already committed. It must not have
        # further effects after the commit.
        for rm in self._resources:
            try:
                rm.abort(self)
            except:
                # XXX should we take further actions here ?
                self.log.error("Error in abort() on manager %s",
                               rm, exc_info=sys.exc_info())
        self._after_commit = []
        self._before_commit = []

    def _commitResources(self):
        # Execute the two-phase commit protocol.

        L = list(self._resources)
        L.sort(key=rm_key)
        try:
            for rm in L:
                rm.tpc_begin(self)
            for rm in L:
                rm.commit(self)
                self.log.debug("commit %r", rm)
            for rm in L:
                rm.tpc_vote(self)
                self._voted[id(rm)] = True

            try:
                for rm in L:
                    rm.tpc_finish(self)
            except:
                # TODO: do we need to make this warning stronger?
                # TODO: It would be nice if the system could be configured
                # to stop committing transactions at this point.
                self.log.critical("A storage error occurred during the second "
                                  "phase of the two-phase commit.  Resources "
                                  "may be in an inconsistent state.")
                raise
        except:
            # If an error occurs committing a transaction, we try
            # to revert the changes in each of the resource managers.
            t, v, tb = sys.exc_info()
            try:
                try:
                    self._cleanup(L)
                finally:
                    self._synchronizers.map(lambda s: s.afterCompletion(self))
                reraise(t, v, tb)
            finally:
                del t, v, tb

    def _cleanup(self, L):
        # Called when an exception occurs during tpc_vote or tpc_finish.
        for rm in L:
            if id(rm) not in self._voted:
                try:
                    rm.abort(self)
                except Exception:
                    self.log.error("Error in abort() on manager %s",
                                   rm, exc_info=sys.exc_info())
        for rm in L:
            try:
                rm.tpc_abort(self)
            except Exception:
                self.log.error("Error in tpc_abort() on manager %s",
                               rm, exc_info=sys.exc_info())

    def _free(self):
        # Called when the transaction has been committed or aborted
        # to break references---this transaction object will not be returned
        # as the current transaction from its manager after this, and all
        # IDatamanager objects joined to it will forgotten
        if self._manager:
            self._manager.free(self)

        if hasattr(self, '_data'):
            delattr(self, '_data')

        del self._resources[:]

    def data(self, ob):
        try:
            data = self._data
        except AttributeError:
            raise KeyError(ob)

        try:
            return data[id(ob)]
        except KeyError:
            raise KeyError(ob)

    def set_data(self, ob, ob_data):
        try:
            data = self._data
        except AttributeError:
            data = self._data = {}

        data[id(ob)] = ob_data

    def abort(self):
        """ See ITransaction.
        """
        if self._savepoint2index:
            self._invalidate_all_savepoints()

        self._synchronizers.map(lambda s: s.beforeCompletion(self))

        try:

            t = None
            v = None
            tb = None

            for rm in self._resources:
                try:
                    rm.abort(self)
                except:
                    if tb is None:
                        t, v, tb = sys.exc_info()
                    self.log.error("Failed to abort resource manager: %s",
                                   rm, exc_info=sys.exc_info())

            self._free()

            self._synchronizers.map(lambda s: s.afterCompletion(self))

            self.log.debug("abort")

            if tb is not None:
                reraise(t, v, tb)
        finally:
            del t, v, tb

    def note(self, text):
        """ See ITransaction.
        """
        text = text.strip()
        if self.description:
            self.description += "\n" + text
        else:
            self.description = text

    def setUser(self, user_name, path="/"):
        """ See ITransaction.
        """
        self.user = "%s %s" % (path, user_name)

    def setExtendedInfo(self, name, value):
        """ See ITransaction.
        """
        self._extension[name] = value


# TODO: We need a better name for the adapters.


class MultiObjectResourceAdapter(object):
    """Adapt the old-style register() call to the new-style join().

    With join(), a resource manager like a Connection registers with
    the transaction manager.  With register(), an individual object
    is passed to register().
    """
    def __init__(self, jar):
        self.manager = jar
        self.objects = []
        self.ncommitted = 0

    def __repr__(self):
        return "<%s for %s at %s>" % (self.__class__.__name__,
                                      self.manager, id(self))

    def sortKey(self):
        return self.manager.sortKey()

    def tpc_begin(self, txn):
        self.manager.tpc_begin(txn)

    def tpc_finish(self, txn):
        self.manager.tpc_finish(txn)

    def tpc_abort(self, txn):
        self.manager.tpc_abort(txn)

    def commit(self, txn):
        for o in self.objects:
            self.manager.commit(o, txn)
            self.ncommitted += 1

    def tpc_vote(self, txn):
        self.manager.tpc_vote(txn)

    def abort(self, txn):
        t = None
        v = None
        tb = None
        try:
            for o in self.objects:
                try:
                    self.manager.abort(o, txn)
                except:
                    # Capture the first exception and re-raise it after
                    # aborting all the other objects.
                    if tb is None:
                        t, v, tb = sys.exc_info()
                    txn.log.error("Failed to abort object: %s",
                                  object_hint(o), exc_info=sys.exc_info())

            if tb is not None:
                reraise(t, v, tb)
        finally:
            del t, v, tb


def rm_key(rm):
    func = getattr(rm, 'sortKey', None)
    if func is not None:
        return func()

def object_hint(o):
    """Return a string describing the object.

    This function does not raise an exception.
    """
    # We should always be able to get __class__.
    klass = o.__class__.__name__
    # oid would be great, but maybe this isn't a persistent object.
    oid = getattr(o, "_p_oid", _marker)
    if oid is not _marker:
        oid = oid_repr(oid)
    else:
        oid = 'None'
    return "%s oid=%s" % (klass, oid)

def oid_repr(oid):
    if isinstance(oid, str) and len(oid) == 8:
        # Convert to hex and strip leading zeroes.
        as_hex = native_(
            binascii.hexlify(bytes_(oid, 'ascii')), 'ascii').lstrip('0')
        # Ensure two characters per input byte.
        if len(as_hex) & 1:
            as_hex = '0' + as_hex
        elif as_hex == '':
            as_hex = '00'
        return '0x' + as_hex
    else:
        return repr(oid)


# TODO: deprecate for 3.6.
class DataManagerAdapter(object):
    """Adapt zodb 4-style data managers to zodb3 style

    Adapt transaction.interfaces.IDataManager to
    ZODB.interfaces.IPureDatamanager
    """

    # Note that it is pretty important that this does not have a _p_jar
    # attribute. This object will be registered with a zodb3 TM, which
    # will then try to get a _p_jar from it, using it as the default.
    # (Objects without a _p_jar are their own data managers.)

    def __init__(self, datamanager):
        self._datamanager = datamanager

    # TODO: I'm not sure why commit() doesn't do anything

    def commit(self, transaction):
        # We don't do anything here because ZODB4-style data managers
        # didn't have a separate commit step
        pass

    def abort(self, transaction):
        self._datamanager.abort(transaction)

    def tpc_begin(self, transaction):
        # We don't do anything here because ZODB4-style data managers
        # didn't have a separate tpc_begin step
        pass

    def tpc_abort(self, transaction):
        self._datamanager.abort(transaction)

    def tpc_finish(self, transaction):
        self._datamanager.commit(transaction)

    def tpc_vote(self, transaction):
        self._datamanager.prepare(transaction)

    def sortKey(self):
        return self._datamanager.sortKey()


@implementer(interfaces.ISavepoint)
class Savepoint:
    """Transaction savepoint.

    Transaction savepoints coordinate savepoints for data managers
    participating in a transaction.
    """

    def __init__(self, transaction, optimistic, *resources):
        self.transaction = transaction
        self._savepoints = savepoints = []

        for datamanager in resources:
            try:
                savepoint = datamanager.savepoint
            except AttributeError:
                if not optimistic:
                    raise TypeError("Savepoints unsupported", datamanager)
                savepoint = NoRollbackSavepoint(datamanager)
            else:
                savepoint = savepoint()

            savepoints.append(savepoint)

    @property
    def valid(self):
        return self.transaction is not None

    def rollback(self):
        """ See ISavepoint.
        """
        transaction = self.transaction
        if transaction is None:
            raise interfaces.InvalidSavepointRollbackError(
                'invalidated by a later savepoint')
        transaction._remove_and_invalidate_after(self)

        try:
            for savepoint in self._savepoints:
                savepoint.rollback()
        except:
            # Mark the transaction as failed.
            transaction._saveAndRaiseCommitishError() # reraises!


class AbortSavepoint:

    def __init__(self, datamanager, transaction):
        self.datamanager = datamanager
        self.transaction = transaction

    def rollback(self):
        self.datamanager.abort(self.transaction)
        self.transaction._unjoin(self.datamanager)


class NoRollbackSavepoint:

    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        raise TypeError("Savepoints unsupported", self.datamanager)
