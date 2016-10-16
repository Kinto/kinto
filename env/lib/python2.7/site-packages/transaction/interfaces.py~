##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
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

from zope.interface import Attribute
from zope.interface import Interface

class ITransactionManager(Interface):
    """An object that manages a sequence of transactions.

    Applications use transaction managers to establish transaction boundaries.
    """

    def begin():
        """Begin a new transaction.

        If an existing transaction is in progress, it will be aborted.

        The newTransaction() method of registered synchronizers is called,
        passing the new transaction object.
        """

    def get():
        """Get the current transaction.
        """

    def commit():
        """Commit the current transaction.
        """

    def abort():
        """Abort the current transaction.
        """

    def doom():
        """Doom the current transaction.
        """

    def isDoomed():
        """Returns True if the current transaction is doomed, otherwise False.
        """

    def savepoint(optimistic=False):
        """Create a savepoint from the current transaction.

        If the optimistic argument is true, then data managers that
        don't support savepoints can be used, but an error will be
        raised if the savepoint is rolled back.

        An ISavepoint object is returned.
        """

    def registerSynch(synch):
        """Register an ISynchronizer.

        Synchronizers are notified about some major events in a transaction's
        life.  See ISynchronizer for details.
        """

    def unregisterSynch(synch):
        """Unregister an ISynchronizer.

        Synchronizers are notified about some major events in a transaction's
        life.  See ISynchronizer for details.
        """

    def clearSynchs():
        """Unregister all registered ISynchronizers.

        This exists to support test cleanup/initialization
        """

    def registeredSynchs():
        """Determine if any ISynchronizers are registered.

        Return true is any are registered, and return False otherwise.

        This exists to support test cleanup/initialization
        """

class ITransaction(Interface):
    """Object representing a running transaction.

    Objects with this interface may represent different transactions
    during their lifetime (.begin() can be called to start a new
    transaction using the same instance, although that example is
    deprecated and will go away in ZODB 3.6).
    """

    user = Attribute(
        """A user name associated with the transaction.

        The format of the user name is defined by the application.  The value
        is of Python type str.  Storages record the user value, as meta-data,
        when a transaction commits.

        A storage may impose a limit on the size of the value; behavior is
        undefined if such a limit is exceeded (for example, a storage may
        raise an exception, or truncate the value).
        """)

    description = Attribute(
        """A textual description of the transaction.

        The value is of Python type str.  Method note() is the intended
        way to set the value.  Storages record the description, as meta-data,
        when a transaction commits.

        A storage may impose a limit on the size of the description; behavior
        is undefined if such a limit is exceeded (for example, a storage may
        raise an exception, or truncate the value).
        """)

    def commit():
        """Finalize the transaction.

        This executes the two-phase commit algorithm for all
        IDataManager objects associated with the transaction.
        """

    def abort():
        """Abort the transaction.

        This is called from the application.  This can only be called
        before the two-phase commit protocol has been started.
        """

    def doom():
        """Doom the transaction.

        Dooms the current transaction. This will cause
        DoomedTransactionException to be raised on any attempt to commit the
        transaction.

        Otherwise the transaction will behave as if it was active.
        """

    def savepoint(optimistic=False):
        """Create a savepoint.

        If the optimistic argument is true, then data managers that don't
        support savepoints can be used, but an error will be raised if the
        savepoint is rolled back.

        An ISavepoint object is returned.
        """

    def join(datamanager):
        """Add a data manager to the transaction.

        `datamanager` must provide the transactions.interfaces.IDataManager
        interface.
        """

    def note(text):
        """Add text to the transaction description.

        This modifies the `.description` attribute; see its docs for more
        detail.  First surrounding whitespace is stripped from `text`.  If
        `.description` is currently an empty string, then the stripped text
        becomes its value, else two newlines and the stripped text are
        appended to `.description`.
        """

    def setUser(user_name, path="/"):
        """Set the user name.

        path should be provided if needed to further qualify the
        identified user.  This is a convenience method used by Zope.
        It sets the .user attribute to str(path) + " " + str(user_name).
        This sets the `.user` attribute; see its docs for more detail.
        """

    def setExtendedInfo(name, value):
        """Add extension data to the transaction.

        name is the name of the extension property to set, of Python type
        str; value must be picklable.  Multiple calls may be made to set
        multiple extension properties, provided the names are distinct.

        Storages record the extension data, as meta-data, when a transaction
        commits.

        A storage may impose a limit on the size of extension data; behavior
        is undefined if such a limit is exceeded (for example, a storage may
        raise an exception, or remove `<name, value>` pairs).
        """

    # deprecated38
    def beforeCommitHook(__hook, *args, **kws):
        """Register a hook to call before the transaction is committed.

        THIS IS DEPRECATED IN ZODB 3.6.  Use addBeforeCommitHook() instead.

        The specified hook function will be called after the transaction's
        commit method has been called, but before the commit process has been
        started.  The hook will be passed the specified positional and keyword
        arguments.

        Multiple hooks can be registered and will be called in the order they
        were registered (first registered, first called).  This method can
        also be called from a hook:  an executing hook can register more
        hooks.  Applications should take care to avoid creating infinite loops
        by recursively registering hooks.

        Hooks are called only for a top-level commit.  A savepoint
        does not call any hooks.  If the transaction is aborted, hooks
        are not called, and are discarded.  Calling a hook "consumes" its
        registration too:  hook registrations do not persist across
        transactions.  If it's desired to call the same hook on every
        transaction commit, then beforeCommitHook() must be called with that
        hook during every transaction; in such a case consider registering a
        synchronizer object via a TransactionManager's registerSynch() method
        instead.
        """

    def addBeforeCommitHook(hook, args=(), kws=None):
        """Register a hook to call before the transaction is committed.

        The specified hook function will be called after the transaction's
        commit method has been called, but before the commit process has been
        started.  The hook will be passed the specified positional (`args`)
        and keyword (`kws`) arguments.  `args` is a sequence of positional
        arguments to be passed, defaulting to an empty tuple (no positional
        arguments are passed).  `kws` is a dictionary of keyword argument
        names and values to be passed, or the default None (no keyword
        arguments are passed).

        Multiple hooks can be registered and will be called in the order they
        were registered (first registered, first called).  This method can
        also be called from a hook:  an executing hook can register more
        hooks.  Applications should take care to avoid creating infinite loops
        by recursively registering hooks.

        Hooks are called only for a top-level commit.  A
        savepoint creation does not call any hooks.  If the
        transaction is aborted, hooks are not called, and are discarded.
        Calling a hook "consumes" its registration too:  hook registrations
        do not persist across transactions.  If it's desired to call the same
        hook on every transaction commit, then addBeforeCommitHook() must be
        called with that hook during every transaction; in such a case
        consider registering a synchronizer object via a TransactionManager's
        registerSynch() method instead.
        """

    def getBeforeCommitHooks():
        """Return iterable producing the registered addBeforeCommit hooks.

        A triple (hook, args, kws) is produced for each registered hook.
        The hooks are produced in the order in which they would be invoked
        by a top-level transaction commit.
        """

    def addAfterCommitHook(hook, args=(), kws=None):
         """Register a hook to call after a transaction commit attempt.

         The specified hook function will be called after the transaction
         commit succeeds or aborts.  The first argument passed to the hook
         is a Boolean value, true if the commit succeeded, or false if the
         commit aborted.  `args` specifies additional positional, and `kws`
         keyword, arguments to pass to the hook.  `args` is a sequence of
         positional arguments to be passed, defaulting to an empty tuple
         (only the true/false success argument is passed).  `kws` is a
         dictionary of keyword argument names and values to be passed, or
         the default None (no keyword arguments are passed).

         Multiple hooks can be registered and will be called in the order they
         were registered (first registered, first called).  This method can
         also be called from a hook:  an executing hook can register more
         hooks.  Applications should take care to avoid creating infinite loops
         by recursively registering hooks.

         Hooks are called only for a top-level commit.  A
         savepoint creation does not call any hooks.  Calling a
         hook "consumes" its registration:  hook registrations do not
         persist across transactions.  If it's desired to call the same
         hook on every transaction commit, then addAfterCommitHook() must be
         called with that hook during every transaction; in such a case
         consider registering a synchronizer object via a TransactionManager's
         registerSynch() method instead.
         """

    def getAfterCommitHooks():
        """Return iterable producing the registered addAfterCommit hooks.

        A triple (hook, args, kws) is produced for each registered hook.
        The hooks are produced in the order in which they would be invoked
        by a top-level transaction commit.
        """

    def set_data(self, object, data):
        """Hold data on behalf of an object

        For objects such as data managers or their subobjects that
        work with multiple transactions, it's convenient to store
        transaction-specific data on the transaction itself.  The
        transaction knows nothing about the data, but simply holds it
        on behalf of the object.

        The object passed should be the object that needs the data, as
        opposed to simple object like a string. (Internally, the id of
        the object is used as the key.)
        """

    def data(self, object):
        """Retrieve data held on behalf of an object.

        See set_data.
        """

class ITransactionDeprecated(Interface):
    """Deprecated parts of the transaction API."""

    def begin(info=None):
        """Begin a new transaction.

        If the transaction is in progress, it is aborted and a new
        transaction is started using the same transaction object.
        """

    # TODO: deprecate this for 3.6.
    def register(object):
        """Register the given object for transaction control."""


class IDataManager(Interface):
    """Objects that manage transactional storage.

    These objects may manage data for other objects, or they may manage
    non-object storages, such as relational databases.  For example,
    a ZODB.Connection.

    Note that when some data is modified, that data's data manager should
    join a transaction so that data can be committed when the user commits
    the transaction.
    """

    transaction_manager = Attribute(
        """The transaction manager (TM) used by this data manager.

        This is a public attribute, intended for read-only use.  The value
        is an instance of ITransactionManager, typically set by the data
        manager's constructor.
        """)

    def abort(transaction):
        """Abort a transaction and forget all changes.

        Abort must be called outside of a two-phase commit.

        Abort is called by the transaction manager to abort
        transactions that are not yet in a two-phase commit.  It may
        also be called when rolling back a savepoint made before the
        data manager joined the transaction.

        In any case, after abort is called, the data manager is no
        longer participating in the transaction.  If there are new
        changes, the data manager must rejoin the transaction.
        """

    # Two-phase commit protocol.  These methods are called by the ITransaction
    # object associated with the transaction being committed.  The sequence
    # of calls normally follows this regular expression:
    #     tpc_begin commit tpc_vote (tpc_finish | tpc_abort)

    def tpc_begin(transaction):
        """Begin commit of a transaction, starting the two-phase commit.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """

    def commit(transaction):
        """Commit modifications to registered objects.

        Save changes to be made persistent if the transaction commits (if
        tpc_finish is called later).  If tpc_abort is called later, changes
        must not persist.

        This includes conflict detection and handling.  If no conflicts or
        errors occur, the data manager should be prepared to make the
        changes persist when tpc_finish is called.
        """

    def tpc_vote(transaction):
        """Verify that a data manager can commit the transaction.

        This is the last chance for a data manager to vote 'no'.  A
        data manager votes 'no' by raising an exception.

        transaction is the ITransaction instance associated with the
        transaction being committed.
        """

    def tpc_finish(transaction):
        """Indicate confirmation that the transaction is done.

        Make all changes to objects modified by this transaction persist.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.  If this raises an exception, the
        database is not expected to maintain consistency; it's a
        serious error.
        """

    def tpc_abort(transaction):
        """Abort a transaction.

        This is called by a transaction manager to end a two-phase commit on
        the data manager.  Abandon all changes to objects modified by this
        transaction.

        transaction is the ITransaction instance associated with the
        transaction being committed.

        This should never fail.
        """

    def sortKey():
        """Return a key to use for ordering registered DataManagers.

        In order to guarantee a total ordering, keys must be strings.

        ZODB uses a global sort order to prevent deadlock when it commits
        transactions involving multiple resource managers.  The resource
        manager must define a sortKey() method that provides a global ordering
        for resource managers.
        """
        # Alternate version:
        #"""Return a consistent sort key for this connection.
        #
        #This allows ordering multiple connections that use the same storage in
        #a consistent manner. This is unique for the lifetime of a connection,
        #which is good enough to avoid ZEO deadlocks.
        #"""

class ISavepointDataManager(IDataManager):

    def savepoint():
        """Return a data-manager savepoint (IDataManagerSavepoint).
        """

class IDataManagerSavepoint(Interface):
    """Savepoint for data-manager changes for use in transaction savepoints.

    Datamanager savepoints are used by, and only by, transaction savepoints.

    Note that data manager savepoints don't have any notion of, or
    responsibility for, validity.  It isn't the responsibility of
    data-manager savepoints to prevent multiple rollbacks or rollbacks after
    transaction termination.  Preventing invalid savepoint rollback is the
    responsibility of transaction rollbacks.  Application code should never
    use data-manager savepoints.
    """

    def rollback():
        """Rollback any work done since the savepoint.
        """

class ISavepoint(Interface):
    """A transaction savepoint.
    """

    def rollback():
        """Rollback any work done since the savepoint.

        InvalidSavepointRollbackError is raised if the savepoint isn't valid.
        """

    valid = Attribute(
        "Boolean indicating whether the savepoint is valid")

class InvalidSavepointRollbackError(Exception):
    """Attempt to rollback an invalid savepoint.

    A savepoint may be invalid because:

    - The surrounding transaction has committed or aborted.

    - An earlier savepoint in the same transaction has been rolled back.
    """

class ISynchronizer(Interface):
    """Objects that participate in the transaction-boundary notification API.
    """

    def beforeCompletion(transaction):
        """Hook that is called by the transaction at the start of a commit.
        """

    def afterCompletion(transaction):
        """Hook that is called by the transaction after completing a commit.
        """

    def newTransaction(transaction):
        """Hook that is called at the start of a transaction.

        This hook is called when, and only when, a transaction manager's
        begin() method is called explictly.
        """

class TransactionError(Exception):
    """An error occurred due to normal transaction processing."""

class TransactionFailedError(TransactionError):
    """Cannot perform an operation on a transaction that previously failed.

    An attempt was made to commit a transaction, or to join a transaction,
    but this transaction previously raised an exception during an attempt
    to commit it.  The transaction must be explicitly aborted, either by
    invoking abort() on the transaction, or begin() on its transaction
    manager.
    """

class DoomedTransaction(TransactionError):
    """A commit was attempted on a transaction that was doomed."""

class TransientError(TransactionError):
    """An error has occured when performing a transaction.

    It's possible that retrying the transaction will succeed.
    """
