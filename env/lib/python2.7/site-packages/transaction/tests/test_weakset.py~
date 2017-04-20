##############################################################################
#
# Copyright (c) 2007 Zope Foundation and Contributors.
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
import unittest
from transaction._compat import JYTHON

class WeakSetTests(unittest.TestCase):
    def test_contains(self):
        from transaction.weakset import WeakSet
        w = WeakSet()
        dummy = Dummy()
        w.add(dummy)
        self.assertEqual(dummy in w, True)
        dummy2 = Dummy()
        self.assertEqual(dummy2 in w, False)

    def test_len(self):
        import gc
        from transaction.weakset import WeakSet
        w = WeakSet()
        d1 = Dummy()
        d2 = Dummy()
        w.add(d1)
        w.add(d2)
        self.assertEqual(len(w), 2)
        del d1
        gc.collect()
        if not JYTHON:
            # The Jython GC is non deterministic
            self.assertEqual(len(w), 1)

    def test_remove(self):
        from transaction.weakset import WeakSet
        w = WeakSet()
        dummy = Dummy()
        w.add(dummy)
        self.assertEqual(dummy in w, True)
        w.remove(dummy)
        self.assertEqual(dummy in w, False)

    def test_as_weakref_list(self):
        import gc
        from transaction.weakset import WeakSet
        w = WeakSet()
        dummy = Dummy()
        dummy2 = Dummy()
        dummy3 = Dummy()
        w.add(dummy)
        w.add(dummy2)
        w.add(dummy3)
        del dummy3
        gc.collect()
        refs = w.as_weakref_list()
        self.assertTrue(isinstance(refs, list))
        L = [x() for x in refs]
        # L is a list, but it does not have a guaranteed order.
        self.assertTrue(list, type(L))
        self.assertEqual(set(L), set([dummy, dummy2]))

    def test_map(self):
        from transaction.weakset import WeakSet
        w = WeakSet()
        dummy = Dummy()
        dummy2 = Dummy()
        dummy3 = Dummy()
        w.add(dummy)
        w.add(dummy2)
        w.add(dummy3)
        def poker(x):
            x.poked = 1
        w.map(poker)
        for thing in dummy, dummy2, dummy3:
            self.assertEqual(thing.poked, 1)

    def test_map_w_gced_element(self):
        import gc
        from transaction.weakset import WeakSet
        w = WeakSet()
        dummy = Dummy()
        dummy2 = Dummy()
        dummy3 = [Dummy()]
        w.add(dummy)
        w.add(dummy2)
        w.add(dummy3[0])

        _orig = w.as_weakref_list
        def _as_weakref_list():
            # simulate race condition during iteration of list
            # object is collected after being iterated.
            result = _orig()
            del dummy3[:]
            gc.collect()
            return result
        w.as_weakref_list = _as_weakref_list

        def poker(x):
            x.poked = 1
        w.map(poker)
        for thing in dummy, dummy2:
            self.assertEqual(thing.poked, 1)


class Dummy:
    pass


def test_suite():
    return unittest.makeSuite(WeakSetTests)
