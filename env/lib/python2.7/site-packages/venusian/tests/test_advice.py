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
"""Tests for advice

This module was adapted from 'protocols.tests.advice', part of the Python
Enterprise Application Kit (PEAK).  Please notify the PEAK authors
(pje@telecommunity.com and tsarna@sarna.org) if bugs are found or
Zope-specific changes are required, so that the PEAK version of this module
can be kept in sync.

PEAK is a Python application framework that interoperates with (but does
not require) Zope 3 and Twisted.  It provides tools for manipulating UML
models, object-relational persistence, aspect-oriented programming, and more.
Visit the PEAK home page at http://peak.telecommunity.com for more information.

$Id: test_advice.py 40836 2005-12-16 22:40:51Z benji_york $
"""

import unittest
import sys
from venusian import advice

PY3 = sys.version_info[0] >= 3

if not PY3:
    class ClassicClass:
        classLevelFrameInfo = advice.getFrameInfo(sys._getframe())

class NewStyleClass(object):
    classLevelFrameInfo = advice.getFrameInfo(sys._getframe())

moduleLevelFrameInfo = advice.getFrameInfo(sys._getframe())

class FrameInfoTest(unittest.TestCase):

    classLevelFrameInfo = advice.getFrameInfo(sys._getframe())

    def testModuleInfo(self):
        kind, module, f_locals, f_globals, codeinfo = moduleLevelFrameInfo
        self.assertEquals(kind, "module")
        for d in module.__dict__, f_locals, f_globals:
            self.assert_(d is globals())
        self.assertEqual(len(codeinfo), 4)

    if not PY3:
        def testClassicClassInfo(self):
            (kind, module, f_locals, f_globals,
             codeinfo) = ClassicClass.classLevelFrameInfo
            self.assertEquals(kind, "class")

            self.assert_(f_locals is ClassicClass.__dict__)  # ???
            for d in module.__dict__, f_globals:
                self.assert_(d is globals())
            self.assertEqual(len(codeinfo), 4)

    def testNewStyleClassInfo(self):
        (kind, module, f_locals,
         f_globals, codeinfo) = NewStyleClass.classLevelFrameInfo
        self.assertEquals(kind, "class")

        for d in module.__dict__, f_globals:
            self.assert_(d is globals())
        self.assertEqual(len(codeinfo), 4)

    def testCallInfo(self):
        (kind, module, f_locals, f_globals,
         codeinfo) = advice.getFrameInfo(sys._getframe())
        self.assertEquals(kind, "function call")
        self.assert_(f_locals is locals()) # ???
        for d in module.__dict__, f_globals:
            self.assert_(d is globals())
        self.assertEqual(len(codeinfo), 4)
