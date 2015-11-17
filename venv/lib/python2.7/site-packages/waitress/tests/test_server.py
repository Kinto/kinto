import errno
import socket
import unittest

dummy_app = object()

class TestWSGIServer(unittest.TestCase):

    def _makeOne(self, application=dummy_app, host='127.0.0.1', port=0,
                 _dispatcher=None, adj=None, map=None, _start=True,
                 _sock=None, _server=None):
        from waitress.server import create_server
        return create_server(
            application,
            host=host,
            port=port,
            map=map,
            _dispatcher=_dispatcher,
            _start=_start,
            _sock=_sock)

    def _makeOneWithMap(self, adj=None, _start=True, host='127.0.0.1',
                        port=0, app=dummy_app):
        sock = DummySock()
        task_dispatcher = DummyTaskDispatcher()
        map = {}
        return self._makeOne(
            app,
            host=host,
            port=port,
            map=map,
            _sock=sock,
            _dispatcher=task_dispatcher,
            _start=_start,
        )

    def test_ctor_app_is_None(self):
        self.assertRaises(ValueError, self._makeOneWithMap, app=None)


    def test_ctor_start_true(self):
        inst = self._makeOneWithMap(_start=True)
        self.assertEqual(inst.accepting, True)
        self.assertEqual(inst.socket.listened, 1024)

    def test_ctor_makes_dispatcher(self):
        inst = self._makeOne(_start=False, map={})
        self.assertEqual(inst.task_dispatcher.__class__.__name__,
                         'ThreadedTaskDispatcher')

    def test_ctor_start_false(self):
        inst = self._makeOneWithMap(_start=False)
        self.assertEqual(inst.accepting, False)

    def test_get_server_name_empty(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('')
        self.assertTrue(result)

    def test_get_server_name_with_ip(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('127.0.0.1')
        self.assertTrue(result)

    def test_get_server_name_with_hostname(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('fred.flintstone.com')
        self.assertEqual(result, 'fred.flintstone.com')

    def test_get_server_name_0000(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('0.0.0.0')
        self.assertEqual(result, 'localhost')

    def test_run(self):
        inst = self._makeOneWithMap(_start=False)
        inst.asyncore = DummyAsyncore()
        inst.task_dispatcher = DummyTaskDispatcher()
        inst.run()
        self.assertTrue(inst.task_dispatcher.was_shutdown)

    def test_pull_trigger(self):
        inst = self._makeOneWithMap(_start=False)
        inst.trigger = DummyTrigger()
        inst.pull_trigger()
        self.assertEqual(inst.trigger.pulled, True)

    def test_add_task(self):
        task = DummyTask()
        inst = self._makeOneWithMap()
        inst.add_task(task)
        self.assertEqual(inst.task_dispatcher.tasks, [task])
        self.assertFalse(task.serviced)

    def test_readable_not_accepting(self):
        inst = self._makeOneWithMap()
        inst.accepting = False
        self.assertFalse(inst.readable())

    def test_readable_maplen_gt_connection_limit(self):
        inst = self._makeOneWithMap()
        inst.accepting = True
        inst.adj = DummyAdj
        inst._map = {'a': 1, 'b': 2}
        self.assertFalse(inst.readable())

    def test_readable_maplen_lt_connection_limit(self):
        inst = self._makeOneWithMap()
        inst.accepting = True
        inst.adj = DummyAdj
        inst._map = {}
        self.assertTrue(inst.readable())

    def test_readable_maintenance_false(self):
        import time
        inst = self._makeOneWithMap()
        then = time.time() + 1000
        inst.next_channel_cleanup = then
        L = []
        inst.maintenance = lambda t: L.append(t)
        inst.readable()
        self.assertEqual(L, [])
        self.assertEqual(inst.next_channel_cleanup, then)

    def test_readable_maintenance_true(self):
        inst = self._makeOneWithMap()
        inst.next_channel_cleanup = 0
        L = []
        inst.maintenance = lambda t: L.append(t)
        inst.readable()
        self.assertEqual(len(L), 1)
        self.assertNotEqual(inst.next_channel_cleanup, 0)

    def test_writable(self):
        inst = self._makeOneWithMap()
        self.assertFalse(inst.writable())

    def test_handle_read(self):
        inst = self._makeOneWithMap()
        self.assertEqual(inst.handle_read(), None)

    def test_handle_connect(self):
        inst = self._makeOneWithMap()
        self.assertEqual(inst.handle_connect(), None)

    def test_handle_accept_wouldblock_socket_error(self):
        inst = self._makeOneWithMap()
        ewouldblock = socket.error(errno.EWOULDBLOCK)
        inst.socket = DummySock(toraise=ewouldblock)
        inst.handle_accept()
        self.assertEqual(inst.socket.accepted, False)

    def test_handle_accept_other_socket_error(self):
        inst = self._makeOneWithMap()
        eaborted = socket.error(errno.ECONNABORTED)
        inst.socket = DummySock(toraise=eaborted)
        inst.adj = DummyAdj
        def foo():
            raise socket.error
        inst.accept = foo
        inst.logger = DummyLogger()
        inst.handle_accept()
        self.assertEqual(inst.socket.accepted, False)
        self.assertEqual(len(inst.logger.logged), 1)

    def test_handle_accept_noerror(self):
        inst = self._makeOneWithMap()
        innersock = DummySock()
        inst.socket = DummySock(acceptresult=(innersock, None))
        inst.adj = DummyAdj
        L = []
        inst.channel_class = lambda *arg, **kw: L.append(arg)
        inst.handle_accept()
        self.assertEqual(inst.socket.accepted, True)
        self.assertEqual(innersock.opts, [('level', 'optname', 'value')])
        self.assertEqual(L, [(inst, innersock, None, inst.adj)])

    def test_maintenance(self):
        inst = self._makeOneWithMap()

        class DummyChannel(object):
            requests = []
        zombie = DummyChannel()
        zombie.last_activity = 0
        zombie.running_tasks = False
        inst.active_channels[100] = zombie
        inst.maintenance(10000)
        self.assertEqual(zombie.will_close, True)

    def test_backward_compatibility(self):
        from waitress.server import WSGIServer, TcpWSGIServer
        from waitress.adjustments import Adjustments
        self.assertTrue(WSGIServer is TcpWSGIServer)
        inst = WSGIServer(None, _start=False, port=1234)
        # Ensure the adjustment was actually applied.
        self.assertNotEqual(Adjustments.port, 1234)
        self.assertEqual(inst.adj.port, 1234)

if hasattr(socket, 'AF_UNIX'):

    class TestUnixWSGIServer(unittest.TestCase):
        unix_socket = '/tmp/waitress.test.sock'

        def _makeOne(self, _start=True, _sock=None):
            from waitress.server import create_server
            return create_server(
                dummy_app,
                map={},
                _start=_start,
                _sock=_sock,
                _dispatcher=DummyTaskDispatcher(),
                unix_socket=self.unix_socket,
                unix_socket_perms='600'
            )

        def _makeDummy(self, *args, **kwargs):
            sock = DummySock(*args, **kwargs)
            sock.family = socket.AF_UNIX
            return sock

        def test_unix(self):
            inst = self._makeOne(_start=False)
            self.assertEqual(inst.socket.family, socket.AF_UNIX)
            self.assertEqual(inst.socket.getsockname(), self.unix_socket)

        def test_handle_accept(self):
            # Working on the assumption that we only have to test the happy path
            # for Unix domain sockets as the other paths should've been covered
            # by inet sockets.
            client = self._makeDummy()
            listen = self._makeDummy(acceptresult=(client, None))
            inst = self._makeOne(_sock=listen)
            self.assertEqual(inst.accepting, True)
            self.assertEqual(inst.socket.listened, 1024)
            L = []
            inst.channel_class = lambda *arg, **kw: L.append(arg)
            inst.handle_accept()
            self.assertEqual(inst.socket.accepted, True)
            self.assertEqual(client.opts, [])
            self.assertEqual(
                L,
                [(inst, client, ('localhost', None), inst.adj)]
            )

class DummySock(object):
    accepted = False
    blocking = False
    family = socket.AF_INET

    def __init__(self, toraise=None, acceptresult=(None, None)):
        self.toraise = toraise
        self.acceptresult = acceptresult
        self.bound = None
        self.opts = []

    def bind(self, addr):
        self.bound = addr

    def accept(self):
        if self.toraise:
            raise self.toraise
        self.accepted = True
        return self.acceptresult

    def setblocking(self, x):
        self.blocking = True

    def fileno(self):
        return 10

    def getpeername(self):
        return '127.0.0.1'

    def setsockopt(self, *arg):
        self.opts.append(arg)

    def getsockopt(self, *arg):
        return 1

    def listen(self, num):
        self.listened = num

    def getsockname(self):
        return self.bound

class DummyTaskDispatcher(object):

    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def shutdown(self):
        self.was_shutdown = True

class DummyTask(object):
    serviced = False
    start_response_called = False
    wrote_header = False
    status = '200 OK'

    def __init__(self):
        self.response_headers = {}
        self.written = ''

    def service(self): # pragma: no cover
        self.serviced = True

class DummyAdj:
    connection_limit = 1
    log_socket_errors = True
    socket_options = [('level', 'optname', 'value')]
    cleanup_interval = 900
    channel_timeout = 300

class DummyAsyncore(object):

    def loop(self, timeout=30.0, use_poll=False, map=None, count=None):
        raise SystemExit

class DummyTrigger(object):

    def pull_trigger(self):
        self.pulled = True

class DummyLogger(object):

    def __init__(self):
        self.logged = []

    def warning(self, msg, **kw):
        self.logged.append(msg)
