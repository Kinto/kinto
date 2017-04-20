############################################################################
#
# Copyright (c) 2001, 2002, 2004 Zope Foundation and Contributors.
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
"""Exported transaction functions.

$Id$
"""

from transaction._transaction import Transaction
from transaction._manager import TransactionManager
from transaction._manager import ThreadTransactionManager

# NB: "with transaction:" does not work under Python 3 because they worked
# really hard to break looking up special methods like __enter__ and __exit__
# via getattr and getattribute; see http://bugs.python.org/issue12022.  On
# Python 3, you must use ``with transaction.manager`` instead.

manager = ThreadTransactionManager()
get = __enter__ = manager.get
begin = manager.begin
commit = manager.commit
abort = manager.abort
__exit__ = manager.__exit__
doom = manager.doom
isDoomed = manager.isDoomed
savepoint = manager.savepoint
attempts = manager.attempts
