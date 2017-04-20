import unittest
import os
import sys

if not sys.platform.startswith("win"):

    class Test_trigger(unittest.TestCase):

        def _makeOne(self, map):
            from waitress.trigger import trigger
            return trigger(map)

        def test__close(self):
            map = {}
            inst = self._makeOne(map)
            fd = os.open(os.path.abspath(__file__), os.O_RDONLY)
            inst._fds = (fd,)
            inst.close()
            self.assertRaises(OSError, os.read, fd, 1)

        def test__physical_pull(self):
            map = {}
            inst = self._makeOne(map)
            inst._physical_pull()
            r = os.read(inst._fds[0], 1)
            self.assertEqual(r, b'x')

        def test_readable(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.readable(), True)

        def test_writable(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.writable(), False)

        def test_handle_connect(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.handle_connect(), None)

        def test_close(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.close(), None)
            self.assertEqual(inst._closed, True)

        def test_handle_close(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.handle_close(), None)
            self.assertEqual(inst._closed, True)

        def test_pull_trigger_nothunk(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.pull_trigger(), None)
            r = os.read(inst._fds[0], 1)
            self.assertEqual(r, b'x')

        def test_pull_trigger_thunk(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.pull_trigger(True), None)
            self.assertEqual(len(inst.thunks), 1)
            r = os.read(inst._fds[0], 1)
            self.assertEqual(r, b'x')

        def test_handle_read_socket_error(self):
            map = {}
            inst = self._makeOne(map)
            result = inst.handle_read()
            self.assertEqual(result, None)

        def test_handle_read_no_socket_error(self):
            map = {}
            inst = self._makeOne(map)
            inst.pull_trigger()
            result = inst.handle_read()
            self.assertEqual(result, None)

        def test_handle_read_thunk(self):
            map = {}
            inst = self._makeOne(map)
            inst.pull_trigger()
            L = []
            inst.thunks = [lambda: L.append(True)]
            result = inst.handle_read()
            self.assertEqual(result, None)
            self.assertEqual(L, [True])
            self.assertEqual(inst.thunks, [])

        def test_handle_read_thunk_error(self):
            map = {}
            inst = self._makeOne(map)
            def errorthunk():
                raise ValueError
            inst.pull_trigger(errorthunk)
            L = []
            inst.log_info = lambda *arg: L.append(arg)
            result = inst.handle_read()
            self.assertEqual(result, None)
            self.assertEqual(len(L), 1)
            self.assertEqual(inst.thunks, [])
