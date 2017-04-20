import unittest
import io

class TestHTTPChannel(unittest.TestCase):

    def _makeOne(self, sock, addr, adj, map=None):
        from waitress.channel import HTTPChannel
        server = DummyServer()
        return HTTPChannel(server, sock, addr, adj=adj, map=map)

    def _makeOneWithMap(self, adj=None):
        if adj is None:
            adj = DummyAdjustments()
        sock = DummySock()
        map = {}
        inst = self._makeOne(sock, '127.0.0.1', adj, map=map)
        inst.outbuf_lock = DummyLock()
        return inst, sock, map

    def test_ctor(self):
        inst, _, map = self._makeOneWithMap()
        self.assertEqual(inst.addr, '127.0.0.1')
        self.assertEqual(map[100], inst)

    def test_total_outbufs_len_an_outbuf_size_gt_sys_maxint(self):
        from waitress.compat import MAXINT
        inst, _, map = self._makeOneWithMap()
        class DummyHugeBuffer(object):
            def __len__(self):
                return MAXINT + 1
        inst.outbufs = [DummyHugeBuffer()]
        result = inst.total_outbufs_len()
        # we are testing that this method does not raise an OverflowError
        # (see https://github.com/Pylons/waitress/issues/47)
        self.assertEqual(result, MAXINT+1)

    def test_writable_something_in_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        inst.outbufs[0].append(b'abc')
        self.assertTrue(inst.writable())

    def test_writable_nothing_in_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        self.assertFalse(inst.writable())

    def test_writable_nothing_in_outbuf_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.will_close = True
        self.assertTrue(inst.writable())

    def test_handle_write_not_connected(self):
        inst, sock, map = self._makeOneWithMap()
        inst.connected = False
        self.assertFalse(inst.handle_write())

    def test_handle_write_with_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)

    def test_handle_write_no_request_with_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.outbufs = [DummyBuffer(b'abc')]
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertNotEqual(inst.last_activity, 0)
        self.assertEqual(sock.sent, b'abc')

    def test_handle_write_outbuf_raises_socketerror(self):
        import socket
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        outbuf = DummyBuffer(b'abc', socket.error)
        inst.outbufs = [outbuf]
        inst.last_activity = 0
        inst.logger = DummyLogger()
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)
        self.assertEqual(sock.sent, b'')
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(outbuf.closed)

    def test_handle_write_outbuf_raises_othererror(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        outbuf = DummyBuffer(b'abc', IOError)
        inst.outbufs = [outbuf]
        inst.last_activity = 0
        inst.logger = DummyLogger()
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)
        self.assertEqual(sock.sent, b'')
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(outbuf.closed)

    def test_handle_write_no_requests_no_outbuf_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        outbuf = DummyBuffer(b'')
        inst.outbufs = [outbuf]
        inst.will_close = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.connected, False)
        self.assertEqual(sock.closed, True)
        self.assertEqual(inst.last_activity, 0)
        self.assertTrue(outbuf.closed)

    def test_handle_write_no_requests_force_flush(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = [True]
        inst.outbufs = [DummyBuffer(b'abc')]
        inst.will_close = False
        inst.force_flush = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.will_close, False)
        self.assertTrue(inst.outbuf_lock.acquired)
        self.assertEqual(inst.force_flush, False)
        self.assertEqual(sock.sent, b'abc')

    def test_handle_write_no_requests_outbuf_gt_send_bytes(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = [True]
        inst.outbufs = [DummyBuffer(b'abc')]
        inst.adj.send_bytes = 2
        inst.will_close = False
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.will_close, False)
        self.assertTrue(inst.outbuf_lock.acquired)
        self.assertEqual(sock.sent, b'abc')

    def test_handle_write_close_when_flushed(self):
        inst, sock, map = self._makeOneWithMap()
        outbuf = DummyBuffer(b'abc')
        inst.outbufs = [outbuf]
        inst.will_close = False
        inst.close_when_flushed = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.will_close, True)
        self.assertEqual(inst.close_when_flushed, False)
        self.assertEqual(sock.sent, b'abc')
        self.assertTrue(outbuf.closed)

    def test_readable_no_requests_not_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.will_close = False
        self.assertEqual(inst.readable(), True)

    def test_readable_no_requests_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.will_close = True
        self.assertEqual(inst.readable(), False)

    def test_readable_with_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = True
        self.assertEqual(inst.readable(), False)

    def test_handle_read_no_error(self):
        inst, sock, map = self._makeOneWithMap()
        inst.will_close = False
        inst.recv = lambda *arg: b'abc'
        inst.last_activity = 0
        L = []
        inst.received = lambda x: L.append(x)
        result = inst.handle_read()
        self.assertEqual(result, None)
        self.assertNotEqual(inst.last_activity, 0)
        self.assertEqual(L, [b'abc'])

    def test_handle_read_error(self):
        import socket
        inst, sock, map = self._makeOneWithMap()
        inst.will_close = False
        def recv(b):
            raise socket.error
        inst.recv = recv
        inst.last_activity = 0
        inst.logger = DummyLogger()
        result = inst.handle_read()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)
        self.assertEqual(len(inst.logger.exceptions), 1)

    def test_write_soon_empty_byte(self):
        inst, sock, map = self._makeOneWithMap()
        wrote = inst.write_soon(b'')
        self.assertEqual(wrote, 0)
        self.assertEqual(len(inst.outbufs[0]), 0)

    def test_write_soon_nonempty_byte(self):
        inst, sock, map = self._makeOneWithMap()
        wrote = inst.write_soon(b'a')
        self.assertEqual(wrote, 1)
        self.assertEqual(len(inst.outbufs[0]), 1)

    def test_write_soon_filewrapper(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        wrapper = ReadOnlyFileBasedBuffer(f, 8192)
        wrapper.prepare()
        inst, sock, map = self._makeOneWithMap()
        outbufs = inst.outbufs
        orig_outbuf = outbufs[0]
        wrote = inst.write_soon(wrapper)
        self.assertEqual(wrote, 3)
        self.assertEqual(len(outbufs), 3)
        self.assertEqual(outbufs[0], orig_outbuf)
        self.assertEqual(outbufs[1], wrapper)
        self.assertEqual(outbufs[2].__class__.__name__, 'OverflowableBuffer')

    def test__flush_some_empty_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        result = inst._flush_some()
        self.assertEqual(result, False)

    def test__flush_some_full_outbuf_socket_returns_nonzero(self):
        inst, sock, map = self._makeOneWithMap()
        inst.outbufs[0].append(b'abc')
        result = inst._flush_some()
        self.assertEqual(result, True)

    def test__flush_some_full_outbuf_socket_returns_zero(self):
        inst, sock, map = self._makeOneWithMap()
        sock.send = lambda x: False
        inst.outbufs[0].append(b'abc')
        result = inst._flush_some()
        self.assertEqual(result, False)

    def test_flush_some_multiple_buffers_first_empty(self):
        inst, sock, map = self._makeOneWithMap()
        sock.send = lambda x: len(x)
        buffer = DummyBuffer(b'abc')
        inst.outbufs.append(buffer)
        result = inst._flush_some()
        self.assertEqual(result, True)
        self.assertEqual(buffer.skipped, 3)
        self.assertEqual(inst.outbufs, [buffer])

    def test_flush_some_multiple_buffers_close_raises(self):
        inst, sock, map = self._makeOneWithMap()
        sock.send = lambda x: len(x)
        buffer = DummyBuffer(b'abc')
        inst.outbufs.append(buffer)
        inst.logger = DummyLogger()
        def doraise():
            raise NotImplementedError
        inst.outbufs[0].close = doraise
        result = inst._flush_some()
        self.assertEqual(result, True)
        self.assertEqual(buffer.skipped, 3)
        self.assertEqual(inst.outbufs, [buffer])
        self.assertEqual(len(inst.logger.exceptions), 1)

    def test__flush_some_outbuf_len_gt_sys_maxint(self):
        from waitress.compat import MAXINT
        inst, sock, map = self._makeOneWithMap()
        class DummyHugeOutbuffer(object):
            def __init__(self):
                self.length = MAXINT + 1
            def __len__(self):
                return self.length
            def get(self, numbytes):
                self.length = 0
                return b'123'
            def skip(self, *args): pass
        buf = DummyHugeOutbuffer()
        inst.outbufs = [buf]
        inst.send = lambda *arg: 0
        result = inst._flush_some()
        # we are testing that _flush_some doesn't raise an OverflowError
        # when one of its outbufs has a __len__ that returns gt sys.maxint
        self.assertEqual(result, False)
        
    def test_handle_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.handle_close()
        self.assertEqual(inst.connected, False)
        self.assertEqual(sock.closed, True)

    def test_handle_close_outbuf_raises_on_close(self):
        inst, sock, map = self._makeOneWithMap()
        def doraise():
            raise NotImplementedError
        inst.outbufs[0].close = doraise
        inst.logger = DummyLogger()
        inst.handle_close()
        self.assertEqual(inst.connected, False)
        self.assertEqual(sock.closed, True)
        self.assertEqual(len(inst.logger.exceptions), 1)

    def test_add_channel(self):
        inst, sock, map = self._makeOneWithMap()
        fileno = inst._fileno
        inst.add_channel(map)
        self.assertEqual(map[fileno], inst)
        self.assertEqual(inst.server.active_channels[fileno], inst)

    def test_del_channel(self):
        inst, sock, map = self._makeOneWithMap()
        fileno = inst._fileno
        inst.server.active_channels[fileno] = True
        inst.del_channel(map)
        self.assertEqual(map.get(fileno), None)
        self.assertEqual(inst.server.active_channels.get(fileno), None)

    def test_received(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.server.tasks, [inst])
        self.assertTrue(inst.requests)

    def test_received_no_chunk(self):
        inst, sock, map = self._makeOneWithMap()
        self.assertEqual(inst.received(b''), False)

    def test_received_preq_not_completed(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = False
        preq.empty = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.requests, ())
        self.assertEqual(inst.server.tasks, [])

    def test_received_preq_completed_empty(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.empty = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, None)
        self.assertEqual(inst.server.tasks, [])

    def test_received_preq_error(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.error = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, None)
        self.assertEqual(len(inst.server.tasks), 1)
        self.assertTrue(inst.requests)

    def test_received_preq_completed_connection_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.empty = True
        preq.connection_close = True
        inst.received(b'GET / HTTP/1.1\n\n' + b'a' * 50000)
        self.assertEqual(inst.request, None)
        self.assertEqual(inst.server.tasks, [])

    def test_received_preq_completed_n_lt_data(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.empty = False
        line = b'GET / HTTP/1.1\n\n'
        preq.retval = len(line)
        inst.received(line + line)
        self.assertEqual(inst.request, None)
        self.assertEqual(len(inst.requests), 2)
        self.assertEqual(len(inst.server.tasks), 1)

    def test_received_headers_finished_expect_continue_false(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.expect_continue = False
        preq.headers_finished = True
        preq.completed = False
        preq.empty = False
        preq.retval = 1
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, preq)
        self.assertEqual(inst.server.tasks, [])
        self.assertEqual(inst.outbufs[0].get(100), b'')

    def test_received_headers_finished_expect_continue_true(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.expect_continue = True
        preq.headers_finished = True
        preq.completed = False
        preq.empty = False
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, preq)
        self.assertEqual(inst.server.tasks, [])
        self.assertEqual(sock.sent, b'HTTP/1.1 100 Continue\r\n\r\n')
        self.assertEqual(inst.sent_continue, True)
        self.assertEqual(preq.completed, False)

    def test_received_headers_finished_expect_continue_true_sent_true(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.expect_continue = True
        preq.headers_finished = True
        preq.completed = False
        preq.empty = False
        inst.sent_continue = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, preq)
        self.assertEqual(inst.server.tasks, [])
        self.assertEqual(sock.sent, b'')
        self.assertEqual(inst.sent_continue, True)
        self.assertEqual(preq.completed, False)

    def test_service_no_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)

    def test_service_with_one_request(self):
        inst, sock, map = self._makeOneWithMap()
        request = DummyRequest()
        inst.task_class = DummyTaskClass()
        inst.requests = [request]
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(request.serviced)
        self.assertTrue(request.closed)

    def test_service_with_one_error_request(self):
        inst, sock, map = self._makeOneWithMap()
        request = DummyRequest()
        request.error = DummyError()
        inst.error_task_class = DummyTaskClass()
        inst.requests = [request]
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(request.serviced)
        self.assertTrue(request.closed)

    def test_service_with_multiple_requests(self):
        inst, sock, map = self._makeOneWithMap()
        request1 = DummyRequest()
        request2 = DummyRequest()
        inst.task_class = DummyTaskClass()
        inst.requests = [request1, request2]
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(request1.serviced)
        self.assertTrue(request2.serviced)
        self.assertTrue(request1.closed)
        self.assertTrue(request2.closed)

    def test_service_with_request_raises(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = False
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.task_class.wrote_header = False
        inst.error_task_class = DummyTaskClass()
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertFalse(inst.will_close)
        self.assertEqual(inst.error_task_class.serviced, True)
        self.assertTrue(request.closed)

    def test_service_with_requests_raises_already_wrote_header(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = False
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.error_task_class = DummyTaskClass()
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertTrue(inst.close_when_flushed)
        self.assertEqual(inst.error_task_class.serviced, False)
        self.assertTrue(request.closed)

    def test_service_with_requests_raises_didnt_write_header_expose_tbs(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = True
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.task_class.wrote_header = False
        inst.error_task_class = DummyTaskClass()
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertFalse(inst.will_close)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertEqual(inst.error_task_class.serviced, True)
        self.assertTrue(request.closed)

    def test_service_with_requests_raises_didnt_write_header(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = False
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.task_class.wrote_header = False
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertTrue(inst.close_when_flushed)
        self.assertTrue(request.closed)

    def test_cancel_no_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = ()
        inst.cancel()
        self.assertEqual(inst.requests, [])

    def test_cancel_with_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = [None]
        inst.cancel()
        self.assertEqual(inst.requests, [])

    def test_defer(self):
        inst, sock, map = self._makeOneWithMap()
        self.assertEqual(inst.defer(), None)

class DummySock(object):
    blocking = False
    closed = False

    def __init__(self):
        self.sent = b''

    def setblocking(self, *arg):
        self.blocking = True

    def fileno(self):
        return 100

    def getpeername(self):
        return '127.0.0.1'

    def close(self):
        self.closed = True

    def send(self, data):
        self.sent += data
        return len(data)

class DummyLock(object):

    def __init__(self, acquirable=True):
        self.acquirable = acquirable

    def acquire(self, val):
        self.val = val
        self.acquired = True
        return self.acquirable

    def release(self):
        self.released = True

    def __exit__(self, type, val, traceback):
        self.acquire(True)

    def __enter__(self):
        pass

class DummyBuffer(object):
    closed = False

    def __init__(self, data, toraise=None):
        self.data = data
        self.toraise = toraise

    def get(self, *arg):
        if self.toraise:
            raise self.toraise
        data = self.data
        self.data = b''
        return data

    def skip(self, num, x):
        self.skipped = num

    def __len__(self):
        return len(self.data)

    def close(self):
        self.closed = True

class DummyAdjustments(object):
    outbuf_overflow = 1048576
    inbuf_overflow = 512000
    cleanup_interval = 900
    send_bytes = 9000
    url_scheme = 'http'
    channel_timeout = 300
    log_socket_errors = True
    recv_bytes = 8192
    expose_tracebacks = True
    ident = 'waitress'
    max_request_header_size = 10000

class DummyServer(object):
    trigger_pulled = False
    adj = DummyAdjustments()

    def __init__(self):
        self.tasks = []
        self.active_channels = {}

    def add_task(self, task):
        self.tasks.append(task)

    def pull_trigger(self):
        self.trigger_pulled = True

class DummyParser(object):
    version = 1
    data = None
    completed = True
    empty = False
    headers_finished = False
    expect_continue = False
    retval = None
    error = None
    connection_close = False

    def received(self, data):
        self.data = data
        if self.retval is not None:
            return self.retval
        return len(data)

class DummyRequest(object):
    error = None
    path = '/'
    version = '1.0'
    closed = False

    def __init__(self):
        self.headers = {}

    def close(self):
        self.closed = True

class DummyLogger(object):

    def __init__(self):
        self.exceptions = []

    def exception(self, msg):
        self.exceptions.append(msg)

class DummyError(object):
    code = '431'
    reason = 'Bleh'
    body = 'My body'

class DummyTaskClass(object):
    wrote_header = True
    close_on_finish = False
    serviced = False

    def __init__(self, toraise=None):
        self.toraise = toraise

    def __call__(self, channel, request):
        self.request = request
        return self

    def service(self):
        self.serviced = True
        self.request.serviced = True
        if self.toraise:
            raise self.toraise
