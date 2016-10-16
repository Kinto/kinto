import unittest

class TestPyramidTemplate(unittest.TestCase):
    def _makeOne(self):
        from pyramid.scaffolds import PyramidTemplate
        return PyramidTemplate('name')

    def test_pre(self):
        inst = self._makeOne()
        vars = {'package':'one'}
        inst.pre('command', 'output dir', vars)
        self.assertTrue(vars['random_string'])
        self.assertEqual(vars['package_logger'], 'one')

    def test_pre_root(self):
        inst = self._makeOne()
        vars = {'package':'root'}
        inst.pre('command', 'output dir', vars)
        self.assertTrue(vars['random_string'])
        self.assertEqual(vars['package_logger'], 'app')

