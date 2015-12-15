##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
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
"""Class advice.

This module was adapted from 'protocols.advice', part of the Python
Enterprise Application Kit (PEAK).  Please notify the PEAK authors
(pje@telecommunity.com and tsarna@sarna.org) if bugs are found or
Zope-specific changes are required, so that the PEAK version of this module
can be kept in sync.

PEAK is a Python application framework that interoperates with (but does
not require) Zope 3 and Twisted.  It provides tools for manipulating UML
models, object-relational persistence, aspect-oriented programming, and more.
Visit the PEAK home page at http://peak.telecommunity.com for more information.

$Id: advice.py 25177 2004-06-02 13:17:31Z jim $
"""

import inspect
import sys

def getFrameInfo(frame):
    """Return (kind,module,locals,globals) for a frame

    'kind' is one of "exec", "module", "class", "function call", or "unknown".
    """

    f_locals = frame.f_locals
    f_globals = frame.f_globals

    sameNamespace = f_locals is f_globals
    hasModule = '__module__' in f_locals
    hasName = '__name__' in f_globals

    sameName = hasModule and hasName
    sameName = sameName and f_globals['__name__']==f_locals['__module__']

    module = hasName and sys.modules.get(f_globals['__name__']) or None

    namespaceIsModule = module and module.__dict__ is f_globals

    frameinfo = inspect.getframeinfo(frame)
    try:
        sourceline = frameinfo[3][0].strip()
    except: #pragma NO COVER
        # dont understand circumstance here, 3rdparty code without comment
        sourceline = frameinfo[3]

    codeinfo = frameinfo[0], frameinfo[1], frameinfo[2], sourceline

    if not namespaceIsModule: #pragma no COVER
        # some kind of funky exec
        kind = "exec" # don't know how to repeat this scenario
    elif sameNamespace and not hasModule:
        kind = "module"
    elif sameName and not sameNamespace:
        kind = "class"
    elif not sameNamespace:
        kind = "function call"
    else: #pragma NO COVER
        # How can you have f_locals is f_globals, and have '__module__' set?
        # This is probably module-level code, but with a '__module__' variable.
        kind = "unknown"
    return kind, module, f_locals, f_globals, codeinfo
