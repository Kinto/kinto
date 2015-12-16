import atexit
import os
import tempfile
import unittest

from pyramid.compat import PY3
if PY3: # pragma: no cover
    import builtins as __builtin__
else:
    import __builtin__

class TestPServeCommand(unittest.TestCase):
    def setUp(self):
        from pyramid.compat import NativeIO
        self.out_ = NativeIO()
        self.pid_file = None

    def tearDown(self):
        if self.pid_file and os.path.exists(self.pid_file):
            os.remove(self.pid_file)

    def out(self, msg):
        self.out_.write(msg)

    def _get_server(*args, **kwargs):
        def server(app):
            return ''

        return server

    def _getTargetClass(self):
        from pyramid.scripts.pserve import PServeCommand
        return PServeCommand

    def _makeOne(self, *args):
        effargs = ['pserve']
        effargs.extend(args)
        cmd = self._getTargetClass()(effargs)
        cmd.out = self.out
        return cmd

    def _makeOneWithPidFile(self, pid):
        self.pid_file = tempfile.mktemp()
        inst = self._makeOne()
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))
        return inst

    def test_remove_pid_file_verbose(self):
        inst = self._makeOneWithPidFile(os.getpid())
        inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=1)
        self._assert_pid_file_removed(verbose=True)

    def test_remove_pid_file_not_verbose(self):
        inst = self._makeOneWithPidFile(os.getpid())
        inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=0)
        self._assert_pid_file_removed(verbose=False)

    def test_remove_pid_not_a_number(self):
        inst = self._makeOneWithPidFile('not a number')
        inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=1)
        self._assert_pid_file_removed(verbose=True)

    def test_remove_pid_current_pid_is_not_written_pid(self):
        inst = self._makeOneWithPidFile(os.getpid())
        inst._remove_pid_file('99999', self.pid_file, verbosity=1)
        self._assert_pid_file_not_removed('')

    def test_remove_pid_current_pid_is_not_pid_in_file(self):
        inst = self._makeOneWithPidFile('99999')
        inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=1)
        msg = 'PID file %s contains 99999, not expected PID %s'
        self._assert_pid_file_not_removed(msg % (self.pid_file, os.getpid()))

    def test_remove_pid_no_pid_file(self):
        inst = self._makeOne()
        self.pid_file = 'some unknown path'
        inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=1)
        self._assert_pid_file_removed(verbose=False)

    def test_remove_pid_file_unlink_exception(self):
        inst = self._makeOneWithPidFile(os.getpid())
        self._remove_pid_unlink_exception(inst)
        msg = [
            'Removing PID file %s' % (self.pid_file),
            'Cannot remove PID file: (Some OSError - unlink)',
            'Stale PID removed']
        self._assert_pid_file_not_removed(msg=''.join(msg))
        with open(self.pid_file) as f:
            self.assertEqual(f.read(), '')

    def test_remove_pid_file_stale_pid_write_exception(self):
        inst = self._makeOneWithPidFile(os.getpid())
        self._remove_pid_unlink_and_write_exceptions(inst)
        msg = [
            'Removing PID file %s' % (self.pid_file),
            'Cannot remove PID file: (Some OSError - unlink)',
            'Stale PID left in file: %s ' % (self.pid_file),
            '(Some OSError - open)']
        self._assert_pid_file_not_removed(msg=''.join(msg))
        with open(self.pid_file) as f:
            self.assertEqual(int(f.read()), os.getpid())

    def test_record_pid_verbose(self):
        self._assert_record_pid(verbosity=2, msg='Writing PID %d to %s')

    def test_record_pid_not_verbose(self):
        self._assert_record_pid(verbosity=1, msg='')

    def _remove_pid_unlink_exception(self, inst):
        old_unlink = os.unlink
        def fake_unlink(filename):
            raise OSError('Some OSError - unlink')

        try:
            os.unlink = fake_unlink
            inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=1)
        finally:
            os.unlink = old_unlink

    def _remove_pid_unlink_and_write_exceptions(self, inst):
        old_unlink = os.unlink
        def fake_unlink(filename):
            raise OSError('Some OSError - unlink')

        run_already = []
        old_open = __builtin__.open
        def fake_open(*args):
            if not run_already:
                run_already.append(True)
                return old_open(*args)
            raise OSError('Some OSError - open')

        try:
            os.unlink = fake_unlink
            __builtin__.open = fake_open
            inst._remove_pid_file(os.getpid(), self.pid_file, verbosity=1)
        finally:
            os.unlink = old_unlink
            __builtin__.open = old_open

    def _assert_pid_file_removed(self, verbose=False):
        self.assertFalse(os.path.exists(self.pid_file))
        msg = 'Removing PID file %s' % (self.pid_file) if verbose else ''
        self.assertEqual(self.out_.getvalue(), msg)

    def _assert_pid_file_not_removed(self, msg):
        self.assertTrue(os.path.exists(self.pid_file))
        self.assertEqual(self.out_.getvalue(), msg)

    def _assert_record_pid(self, verbosity, msg):
        old_atexit = atexit.register
        def fake_atexit(*args):
            pass

        self.pid_file = tempfile.mktemp()
        pid = os.getpid()
        inst = self._makeOne()
        inst.options.verbose = verbosity

        try:
            atexit.register = fake_atexit
            inst.record_pid(self.pid_file)
        finally:
            atexit.register = old_atexit

        msg = msg % (pid, self.pid_file) if msg else ''
        self.assertEqual(self.out_.getvalue(), msg)
        with open(self.pid_file) as f:
            self.assertEqual(int(f.read()), pid)

    def test_run_no_args(self):
        inst = self._makeOne()
        result = inst.run()
        self.assertEqual(result, 2)
        self.assertEqual(self.out_.getvalue(), 'You must give a config file')

    def test_run_stop_daemon_no_such_pid_file(self):
        path = os.path.join(os.path.dirname(__file__), 'wontexist.pid')
        inst = self._makeOne('--stop-daemon', '--pid-file=%s' % path)
        inst.run()
        msg = 'No PID file exists in %s' % path
        self.assertEqual(self.out_.getvalue(), msg)

    def test_run_stop_daemon_bad_pid_file(self):
        path = __file__
        inst = self._makeOne('--stop-daemon', '--pid-file=%s' % path)
        inst.run()
        msg = 'Not a valid PID file in %s' % path
        self.assertEqual(self.out_.getvalue(), msg)

    def test_run_stop_daemon_invalid_pid_in_file(self):
        fn = tempfile.mktemp()
        with open(fn, 'wb') as tmp:
            tmp.write(b'9999999')
        tmp.close()
        inst = self._makeOne('--stop-daemon', '--pid-file=%s' % fn)
        inst.run()
        msg = 'PID in %s is not valid (deleting)' % fn
        self.assertEqual(self.out_.getvalue(), msg)

    def test_get_options_with_command(self):
        inst = self._makeOne()
        inst.args = ['foo', 'stop', 'a=1', 'b=2']
        result = inst.get_options()
        self.assertEqual(result, {'a': '1', 'b': '2'})

    def test_get_options_no_command(self):
        inst = self._makeOne()
        inst.args = ['foo', 'a=1', 'b=2']
        result = inst.get_options()
        self.assertEqual(result, {'a': '1', 'b': '2'})

    def test_parse_vars_good(self):
        from pyramid.tests.test_scripts.dummy import DummyApp

        inst = self._makeOne('development.ini', 'a=1', 'b=2')
        inst.loadserver = self._get_server


        app = DummyApp()

        def get_app(*args, **kwargs):
            app.global_conf = kwargs.get('global_conf', None)

        inst.loadapp = get_app
        inst.run()

        self.assertEqual(app.global_conf, {'a': '1', 'b': '2'})

    def test_parse_vars_bad(self):
        inst = self._makeOne('development.ini', 'a')
        inst.loadserver = self._get_server
        self.assertRaises(ValueError, inst.run)

class Test_read_pidfile(unittest.TestCase):
    def _callFUT(self, filename):
        from pyramid.scripts.pserve import read_pidfile
        return read_pidfile(filename)

    def test_read_pidfile(self):
        filename = tempfile.mktemp()
        try:
            with open(filename, 'w') as f:
                f.write('12345')
            result = self._callFUT(filename)
            self.assertEqual(result, 12345)
        finally:
            os.remove(filename)

    def test_read_pidfile_no_pid_file(self):
        result = self._callFUT('some unknown path')
        self.assertEqual(result, None)

    def test_read_pidfile_not_a_number(self):
        result = self._callFUT(__file__)
        self.assertEqual(result, None)

class Test_main(unittest.TestCase):
    def _callFUT(self, argv):
        from pyramid.scripts.pserve import main
        return main(argv, quiet=True)

    def test_it(self):
        result = self._callFUT(['pserve'])
        self.assertEqual(result, 2)

class TestLazyWriter(unittest.TestCase):
    def _makeOne(self, filename, mode='w'):
        from pyramid.scripts.pserve import LazyWriter
        return LazyWriter(filename, mode)

    def test_open(self):
        filename = tempfile.mktemp()
        try:
            inst = self._makeOne(filename)
            fp = inst.open()
            self.assertEqual(fp.name, filename)
        finally:
            fp.close()
            os.remove(filename)

    def test_write(self):
        filename = tempfile.mktemp()
        try:
            inst = self._makeOne(filename)
            inst.write('hello')
        finally:
            with open(filename) as f:
                data = f.read()
                self.assertEqual(data, 'hello')
            inst.close()
            os.remove(filename)

    def test_writeline(self):
        filename = tempfile.mktemp()
        try:
            inst = self._makeOne(filename)
            inst.writelines('hello')
        finally:
            with open(filename) as f:
                data = f.read()
                self.assertEqual(data, 'hello')
            inst.close()
            os.remove(filename)

    def test_flush(self):
        filename = tempfile.mktemp()
        try:
            inst = self._makeOne(filename)
            inst.flush()
            fp = inst.fileobj
            self.assertEqual(fp.name, filename)
        finally:
            fp.close()
            os.remove(filename)

class Test__methodwrapper(unittest.TestCase):
    def _makeOne(self, func, obj, type):
        from pyramid.scripts.pserve import _methodwrapper
        return _methodwrapper(func, obj, type)

    def test___call__succeed(self):
        def foo(self, cls, a=1): return 1
        class Bar(object): pass
        wrapper = self._makeOne(foo, Bar, None)
        result = wrapper(a=1)
        self.assertEqual(result, 1)

    def test___call__fail(self):
        def foo(self, cls, a=1): return 1
        class Bar(object): pass
        wrapper = self._makeOne(foo, Bar, None)
        self.assertRaises(AssertionError, wrapper, cls=1)
