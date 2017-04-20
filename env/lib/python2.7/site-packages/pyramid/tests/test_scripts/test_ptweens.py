import unittest
from pyramid.tests.test_scripts import dummy

class TestPTweensCommand(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.scripts.ptweens import PTweensCommand
        return PTweensCommand

    def _makeOne(self):
        cmd = self._getTargetClass()([])
        cmd.bootstrap = (dummy.DummyBootstrap(),)
        cmd.args = ('/foo/bar/myapp.ini#myapp',)
        return cmd

    def test_command_no_tweens(self):
        command = self._makeOne()
        command._get_tweens = lambda *arg: None
        L = []
        command.out = L.append
        result = command.run()
        self.assertEqual(result, 0)
        self.assertEqual(L, [])

    def test_command_implicit_tweens_only(self):
        command = self._makeOne()
        tweens = dummy.DummyTweens([('name', 'item')], None)
        command._get_tweens = lambda *arg: tweens
        L = []
        command.out = L.append
        result = command.run()
        self.assertEqual(result, 0)
        self.assertEqual(
           L[0],
           '"pyramid.tweens" config value NOT set (implicitly ordered tweens '
            'used)')

    def test_command_implicit_and_explicit_tweens(self):
        command = self._makeOne()
        tweens = dummy.DummyTweens([('name', 'item')], [('name2', 'item2')])
        command._get_tweens = lambda *arg: tweens
        L = []
        command.out = L.append
        result = command.run()
        self.assertEqual(result, 0)
        self.assertEqual(
           L[0],
           '"pyramid.tweens" config value set (explicitly ordered tweens used)')

    def test__get_tweens(self):
        command = self._makeOne()
        registry = dummy.DummyRegistry()
        self.assertEqual(command._get_tweens(registry), None)

class Test_main(unittest.TestCase):
    def _callFUT(self, argv):
        from pyramid.scripts.ptweens import main
        return main(argv, quiet=True)

    def test_it(self):
        result = self._callFUT(['ptweens'])
        self.assertEqual(result, 2)
