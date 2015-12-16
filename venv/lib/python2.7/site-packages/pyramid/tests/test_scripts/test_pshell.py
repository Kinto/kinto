import unittest
from pyramid.tests.test_scripts import dummy

class TestPShellCommand(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.scripts.pshell import PShellCommand
        return PShellCommand

    def _makeOne(self, patch_bootstrap=True, patch_config=True,
                 patch_args=True, patch_options=True):
        cmd = self._getTargetClass()([])
        if patch_bootstrap:
            self.bootstrap = dummy.DummyBootstrap()
            cmd.bootstrap = (self.bootstrap,)
        if patch_config:
            self.config_factory = dummy.DummyConfigParserFactory()
            cmd.ConfigParser = self.config_factory
        if patch_args:
            self.args = ('/foo/bar/myapp.ini#myapp',)
            cmd.args = self.args
        if patch_options:
            class Options(object): pass
            self.options = Options()
            self.options.python_shell = ''
            self.options.setup = None
            cmd.options = self.options
        return cmd

    def test_make_default_shell(self):
        command = self._makeOne()
        interact = dummy.DummyInteractor()
        shell = command.make_default_shell(interact)
        shell({'foo': 'bar'}, 'a help message')
        self.assertEqual(interact.local, {'foo': 'bar'})
        self.assertTrue('a help message' in interact.banner)

    def test_make_bpython_shell(self):
        command = self._makeOne()
        bpython = dummy.DummyBPythonShell()
        shell = command.make_bpython_shell(bpython)
        shell({'foo': 'bar'}, 'a help message')
        self.assertEqual(bpython.locals_, {'foo': 'bar'})
        self.assertTrue('a help message' in bpython.banner)

    def test_make_ipython_v1_1_shell(self):
        command = self._makeOne()
        ipshell_factory = dummy.DummyIPShellFactory()
        shell = command.make_ipython_v1_1_shell(ipshell_factory)
        shell({'foo': 'bar'}, 'a help message')
        self.assertEqual(ipshell_factory.kw['user_ns'], {'foo': 'bar'})
        self.assertTrue('a help message' in ipshell_factory.kw['banner2'])
        self.assertTrue(ipshell_factory.shell.called)

    def test_make_ipython_v0_11_shell(self):
        command = self._makeOne()
        ipshell_factory = dummy.DummyIPShellFactory()
        shell = command.make_ipython_v0_11_shell(ipshell_factory)
        shell({'foo': 'bar'}, 'a help message')
        self.assertEqual(ipshell_factory.kw['user_ns'], {'foo': 'bar'})
        self.assertTrue('a help message' in ipshell_factory.kw['banner2'])
        self.assertTrue(ipshell_factory.shell.called)

    def test_make_ipython_v0_10_shell(self):
        command = self._makeOne()
        ipshell_factory = dummy.DummyIPShellFactory()
        shell = command.make_ipython_v0_10_shell(ipshell_factory)
        shell({'foo': 'bar'}, 'a help message')
        self.assertEqual(ipshell_factory.kw['argv'], [])
        self.assertEqual(ipshell_factory.kw['user_ns'], {'foo': 'bar'})
        self.assertTrue('a help message' in ipshell_factory.shell.banner)
        self.assertTrue(ipshell_factory.shell.called)

    def test_command_loads_default_shell(self):
        command = self._makeOne()
        shell = dummy.DummyShell()
        command.make_ipython_shell = lambda: None
        command.make_bpython_shell = lambda: None
        command.make_default_shell = lambda: shell
        command.run()
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_default_shell_with_unknown_shell(self):
        command = self._makeOne()
        shell = dummy.DummyShell()
        bad_shell = dummy.DummyShell()
        command.make_ipython_shell = lambda: bad_shell
        command.make_bpython_shell = lambda: bad_shell
        command.make_default_shell = lambda: shell
        command.options.python_shell = 'unknow_python_shell'
        command.run()
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertEqual(bad_shell.env, {})
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_ipython_v1_1(self):
        command = self._makeOne()
        shell = dummy.DummyShell()
        command.make_ipython_v1_1_shell = lambda: shell
        command.make_ipython_v0_11_shell = lambda: None
        command.make_ipython_v0_10_shell = lambda: None
        command.make_bpython_shell = lambda: None
        command.make_default_shell = lambda: None
        command.options.python_shell = 'ipython'
        command.run()
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_ipython_v0_11(self):
        command = self._makeOne()
        shell = dummy.DummyShell()
        command.make_ipython_v1_1_shell = lambda: None
        command.make_ipython_v0_11_shell = lambda: shell
        command.make_ipython_v0_10_shell = lambda: None
        command.make_bpython_shell = lambda: None
        command.make_default_shell = lambda: None
        command.options.python_shell = 'ipython'
        command.run()
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_ipython_v0_10(self):
        command = self._makeOne()
        shell = dummy.DummyShell()
        command.make_ipython_v1_1_shell = lambda: None
        command.make_ipython_v0_11_shell = lambda: None
        command.make_ipython_v0_10_shell = lambda: shell
        command.make_bpython_shell = lambda: None
        command.make_default_shell = lambda: None
        command.options.python_shell = 'ipython'
        command.run()
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_bpython_shell(self):
        command = self._makeOne()
        shell = dummy.DummyBPythonShell()
        command.make_ipython_shell = lambda: None
        command.make_bpython_shell = lambda: shell
        command.options.python_shell = 'bpython'
        command.run()
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.locals_, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.banner)

    def test_shell_ipython_ordering(self):
        command = self._makeOne()
        shell1_1 = dummy.DummyShell()
        shell0_11 = dummy.DummyShell()
        shell0_10 = dummy.DummyShell()
        command.make_ipython_v1_1_shell = lambda: shell1_1
        shell = command.make_shell()
        self.assertEqual(shell, shell1_1)

        command.make_ipython_v1_1_shell = lambda: None
        command.make_ipython_v0_11_shell = lambda: shell0_11
        shell = command.make_shell()
        self.assertEqual(shell, shell0_11)

        command.make_ipython_v0_11_shell = lambda: None
        command.make_ipython_v0_10_shell = lambda: shell0_10
        shell = command.make_shell()
        self.assertEqual(shell, shell0_10)

        command.options.python_shell = 'ipython'
        command.make_ipython_v1_1_shell = lambda: shell1_1
        shell = command.make_shell()
        self.assertEqual(shell, shell1_1)

    def test_shell_ordering(self):
        command = self._makeOne()
        ipshell = dummy.DummyShell()
        bpshell = dummy.DummyShell()
        dshell = dummy.DummyShell()
        command.make_ipython_shell = lambda: None
        command.make_bpython_shell = lambda: None
        command.make_default_shell = lambda: dshell

        shell = command.make_shell()
        self.assertEqual(shell, dshell)

        command.options.python_shell = 'ipython'
        shell = command.make_shell()
        self.assertEqual(shell, dshell)

        command.options.python_shell = 'bpython'
        shell = command.make_shell()
        self.assertEqual(shell, dshell)

        command.make_ipython_shell = lambda: ipshell
        command.make_bpython_shell = lambda: bpshell
        command.options.python_shell = 'ipython'
        shell = command.make_shell()
        self.assertEqual(shell, ipshell)

        command.options.python_shell = 'bpython'
        shell = command.make_shell()
        self.assertEqual(shell, bpshell)

        command.options.python_shell = 'python'
        shell = command.make_shell()
        self.assertEqual(shell, dshell)

    def test_command_loads_custom_items(self):
        command = self._makeOne()
        model = dummy.Dummy()
        self.config_factory.items = [('m', model)]
        shell = dummy.DummyShell()
        command.run(shell)
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':self.bootstrap.root,
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
            'm':model,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_setup(self):
        command = self._makeOne()
        def setup(env):
            env['a'] = 1
            env['root'] = 'root override'
        self.config_factory.items = [('setup', setup)]
        shell = dummy.DummyShell()
        command.run(shell)
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':'root override',
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
            'a':1,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_check_variable_override_order(self):
        command = self._makeOne()
        model = dummy.Dummy()
        def setup(env):
            env['a'] = 1
            env['m'] = 'model override'
            env['root'] = 'root override'
        self.config_factory.items = [('setup', setup), ('m', model)]
        shell = dummy.DummyShell()
        command.run(shell)
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':'root override',
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
            'a':1, 'm':model,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_loads_setup_from_options(self):
        command = self._makeOne()
        def setup(env):
            env['a'] = 1
            env['root'] = 'root override'
        model = dummy.Dummy()
        self.config_factory.items = [('setup', 'abc'),
                                     ('m', model)]
        command.options.setup = setup
        shell = dummy.DummyShell()
        command.run(shell)
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':self.bootstrap.app, 'root':'root override',
            'registry':self.bootstrap.registry,
            'request':self.bootstrap.request,
            'root_factory':self.bootstrap.root_factory,
            'a':1, 'm':model,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)

    def test_command_custom_section_override(self):
        command = self._makeOne()
        dummy_ = dummy.Dummy()
        self.config_factory.items = [('app', dummy_), ('root', dummy_),
                                     ('registry', dummy_), ('request', dummy_)]
        shell = dummy.DummyShell()
        command.run(shell)
        self.assertTrue(self.config_factory.parser)
        self.assertEqual(self.config_factory.parser.filename,
                         '/foo/bar/myapp.ini')
        self.assertEqual(self.bootstrap.a[0], '/foo/bar/myapp.ini#myapp')
        self.assertEqual(shell.env, {
            'app':dummy_, 'root':dummy_, 'registry':dummy_, 'request':dummy_,
            'root_factory':self.bootstrap.root_factory,
        })
        self.assertTrue(self.bootstrap.closer.called)
        self.assertTrue(shell.help)


class Test_main(unittest.TestCase):
    def _callFUT(self, argv):
        from pyramid.scripts.pshell import main
        return main(argv, quiet=True)

    def test_it(self):
        result = self._callFUT(['pshell'])
        self.assertEqual(result, 2)

