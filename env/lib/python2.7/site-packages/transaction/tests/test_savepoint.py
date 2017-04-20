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
import unittest


class SavepointTests(unittest.TestCase):

    def testRollbackRollsbackDataManagersThatJoinedLater(self):
        # A savepoint needs to not just rollback it's savepoints, but needs
        # to # rollback savepoints for data managers that joined savepoints
        # after the savepoint:
        import transaction
        from transaction.tests import savepointsample
        dm = savepointsample.SampleSavepointDataManager()
        dm['name'] = 'bob'
        sp1 = transaction.savepoint()
        dm['job'] = 'geek'
        sp2 = transaction.savepoint()
        dm['salary'] = 'fun'
        dm2 = savepointsample.SampleSavepointDataManager()
        dm2['name'] = 'sally'

        self.assertTrue('name' in dm)
        self.assertTrue('job' in dm)
        self.assertTrue('salary' in dm)
        self.assertTrue('name' in dm2)

        sp1.rollback()

        self.assertTrue('name' in dm)
        self.assertFalse('job' in dm)
        self.assertFalse('salary' in dm)
        self.assertFalse('name' in dm2)

    def test_commit_after_rollback_for_dm_that_joins_after_savepoint(self):
        # There was a problem handling data managers that joined after a
        # savepoint.  If the savepoint was rolled back and then changes
        # made, the dm would end up being joined twice, leading to extra
        # tpc calls and pain.
        import transaction
        from transaction.tests import savepointsample
        sp = transaction.savepoint()
        dm = savepointsample.SampleSavepointDataManager()
        dm['name'] = 'bob'
        sp.rollback()
        dm['name'] = 'Bob'
        transaction.commit()
        self.assertEqual(dm['name'], 'Bob')



def test_suite():
    return unittest.TestSuite((
            unittest.makeSuite(SavepointTests),
        ))
