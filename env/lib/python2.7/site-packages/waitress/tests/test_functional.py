import errno
import logging
import multiprocessing
import os
import socket
import string
import subprocess
import sys
import time
import unittest
from waitress import server
from waitress.compat import (
    httplib,
    tobytes
)
from waitress.utilities import cleanup_unix_socket

dn = os.path.dirname
here = dn(__file__)

class NullHandler(logging.Handler): # pragma: no cover
    """A logging handler that swallows all emitted messages.
    """
    def emit(self, record):
        pass

def start_server(app, svr, queue, **kwargs): # pragma: no cover
    """Run a fixture application.
    """
    logging.getLogger('waitress').addHandler(NullHandler())
    svr(app, queue, **kwargs).run()

class FixtureTcpWSGIServer(server.TcpWSGIServer):
    """A version of TcpWSGIServer that relays back what it's bound to.
    """

    family = socket.AF_INET # Testing

    def __init__(self, application, queue, **kw): # pragma: no cover
        # Coverage doesn't see this as it's ran in a separate process.
        kw['port'] = 0 # Bind to any available port.
        super(FixtureTcpWSGIServer, self).__init__(application, **kw)
        host, port = self.socket.getsockname()
        if os.name == 'nt':
            host = '127.0.0.1'
        queue.put((host, port))

class SubprocessTests(object):

    # For nose: all tests may be ran in separate processes.
    _multiprocess_can_split_ = True

    exe = sys.executable

    server = None

    def start_subprocess(self, target, **kw):
        # Spawn a server process.
        self.queue = multiprocessing.Queue()
        self.proc = multiprocessing.Process(
            target=start_server,
            args=(target, self.server, self.queue),
            kwargs=kw,
        )
        self.proc.start()
        if self.proc.exitcode is not None: # pragma: no cover
            raise RuntimeError("%s didn't start" % str(target))
        # Get the socket the server is listening on.
        self.bound_to = self.queue.get(timeout=5)
        self.sock = self.create_socket()

    def stop_subprocess(self):
        if self.proc.exitcode is None:
            self.proc.terminate()
        self.sock.close()
        # This give us one FD back ...
        self.queue.close()

    def assertline(self, line, status, reason, version):
        v, s, r = (x.strip() for x in line.split(None, 2))
        self.assertEqual(s, tobytes(status))
        self.assertEqual(r, tobytes(reason))
        self.assertEqual(v, tobytes(version))

    def create_socket(self):
        return socket.socket(self.server.family, socket.SOCK_STREAM)

    def connect(self):
        self.sock.connect(self.bound_to)

    def make_http_connection(self):
        raise NotImplementedError # pragma: no cover

    def send_check_error(self, to_send):
        self.sock.send(to_send)

class TcpTests(SubprocessTests):

    server = FixtureTcpWSGIServer

    def make_http_connection(self):
        return httplib.HTTPConnection(*self.bound_to)

class SleepyThreadTests(TcpTests, unittest.TestCase):
    # test that sleepy thread doesnt block other requests

    def setUp(self):
        from waitress.tests.fixtureapps import sleepy
        self.start_subprocess(sleepy.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_it(self):
        getline = os.path.join(here, 'fixtureapps', 'getline.py')
        cmds = (
            [self.exe, getline, 'http://%s:%d/sleepy' % self.bound_to],
            [self.exe, getline, 'http://%s:%d/' % self.bound_to]
        )
        r, w = os.pipe()
        procs = []
        for cmd in cmds:
            procs.append(subprocess.Popen(cmd, stdout=w))
        time.sleep(3)
        for proc in procs:
            if proc.returncode is not None: # pragma: no cover
                proc.terminate()
        # the notsleepy response should always be first returned (it sleeps
        # for 2 seconds, then returns; the notsleepy response should be
        # processed in the meantime)
        result = os.read(r, 10000)
        os.close(r)
        os.close(w)
        self.assertEqual(result, b'notsleepy returnedsleepy returned')

class EchoTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import echo
        self.start_subprocess(echo.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_date_and_server(self):
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 0\n\n")
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('server'), 'waitress')
        self.assertTrue(headers.get('date'))

    def test_bad_host_header(self):
        # http://corte.si/posts/code/pathod/pythonservers/index.html
        to_send = ("GET / HTTP/1.0\n"
                   " Host: 0\n\n")
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '400', 'Bad Request', 'HTTP/1.0')
        self.assertEqual(headers.get('server'), 'waitress')
        self.assertTrue(headers.get('date'))

    def test_send_with_body(self):
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 5\n\n")
        to_send += 'hello'
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), '5')
        self.assertEqual(response_body, b'hello')

    def test_send_empty_body(self):
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 0\n\n")
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), '0')
        self.assertEqual(response_body, b'')

    def test_multiple_requests_with_body(self):
        for x in range(3):
            self.sock = self.create_socket()
            self.test_send_with_body()
            self.sock.close()

    def test_multiple_requests_without_body(self):
        for x in range(3):
            self.sock = self.create_socket()
            self.test_send_empty_body()
            self.sock.close()

    def test_without_crlf(self):
        data = "Echo\nthis\r\nplease"
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Connection: close\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(int(headers['content-length']), len(data))
        self.assertEqual(len(response_body), len(data))
        self.assertEqual(response_body, tobytes(data))

    def test_large_body(self):
        # 1024 characters.
        body = 'This string has 32 characters.\r\n' * 32
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(body), body)
        )
        self.connect()
        self.sock.send(s)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), '1024')
        self.assertEqual(response_body, tobytes(body))

    def test_many_clients(self):
        conns = []
        for n in range(50):
            h = self.make_http_connection()
            h.request("GET", "/", headers={"Accept": "text/plain"})
            conns.append(h)
        responses = []
        for h in conns:
            response = h.getresponse()
            self.assertEqual(response.status, 200)
            responses.append(response)
        for response in responses:
            response.read()

    def test_chunking_request_without_content(self):
        header = tobytes(
            "GET / HTTP/1.1\n"
            "Transfer-Encoding: chunked\n\n"
        )
        self.connect()
        self.sock.send(header)
        self.sock.send(b"0\r\n\r\n")
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, b'')
        self.assertEqual(headers['content-length'], '0')
        self.assertFalse('transfer-encoding' in headers)

    def test_chunking_request_with_content(self):
        control_line = b"20;\r\n" # 20 hex = 32 dec
        s = b'This string has 32 characters.\r\n'
        expected = s * 12
        header = tobytes(
            "GET / HTTP/1.1\n"
            "Transfer-Encoding: chunked\n\n"
        )
        self.connect()
        self.sock.send(header)
        fp = self.sock.makefile('rb', 0)
        for n in range(12):
            self.sock.send(control_line)
            self.sock.send(s)
        self.sock.send(b"0\r\n\r\n")
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, expected)
        self.assertEqual(headers['content-length'], str(len(expected)))
        self.assertFalse('transfer-encoding' in headers)

    def test_broken_chunked_encoding(self):
        control_line = "20;\r\n" # 20 hex = 32 dec
        s = 'This string has 32 characters.\r\n'
        to_send = "GET / HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        to_send += (control_line + s)
        # garbage in input
        to_send += "GET / HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        to_send += (control_line + s)
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # receiver caught garbage and turned it into a 400
        self.assertline(line, '400', 'Bad Request', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertEqual(sorted(headers.keys()),
            ['content-length', 'content-type', 'date', 'server'])
        self.assertEqual(headers['content-type'], 'text/plain')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_keepalive_http_10(self):
        # Handling of Keep-Alive within HTTP 1.0
        data = "Default: Don't keep me alive"
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        connection = response.getheader('Connection', '')
        # We sent no Connection: Keep-Alive header
        # Connection: close (or no header) is default.
        self.assertTrue(connection != 'Keep-Alive')

    def test_keepalive_http10_explicit(self):
        # If header Connection: Keep-Alive is explicitly sent,
        # we want to keept the connection open, we also need to return
        # the corresponding header
        data = "Keep me alive"
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        connection = response.getheader('Connection', '')
        self.assertEqual(connection, 'Keep-Alive')

    def test_keepalive_http_11(self):
        # Handling of Keep-Alive within HTTP 1.1

        # All connections are kept alive, unless stated otherwise
        data = "Default: Keep me alive"
        s = tobytes(
            "GET / HTTP/1.1\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data))
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        self.assertTrue(response.getheader('connection') != 'close')

    def test_keepalive_http11_explicit(self):
        # Explicitly set keep-alive
        data = "Default: Keep me alive"
        s = tobytes(
            "GET / HTTP/1.1\n"
            "Connection: keep-alive\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        self.assertTrue(response.getheader('connection') != 'close')

    def test_keepalive_http11_connclose(self):
        # specifying Connection: close explicitly
        data = "Don't keep me alive"
        s = tobytes(
            "GET / HTTP/1.1\n"
            "Connection: close\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        self.assertEqual(response.getheader('connection'), 'close')

class PipeliningTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import echo
        self.start_subprocess(echo.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_pipelining(self):
        s = ("GET / HTTP/1.0\r\n"
             "Connection: %s\r\n"
             "Content-Length: %d\r\n"
             "\r\n"
             "%s")
        to_send = b''
        count = 25
        for n in range(count):
            body = "Response #%d\r\n" % (n + 1)
            if n + 1 < count:
                conn = 'keep-alive'
            else:
                conn = 'close'
            to_send += tobytes(s % (conn, len(body), body))

        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        for n in range(count):
            expect_body = tobytes("Response #%d\r\n" % (n + 1))
            line = fp.readline() # status line
            version, status, reason = (x.strip() for x in line.split(None, 2))
            headers = parse_headers(fp)
            length = int(headers.get('content-length')) or None
            response_body = fp.read(length)
            self.assertEqual(int(status), 200)
            self.assertEqual(length, len(response_body))
            self.assertEqual(response_body, expect_body)

class ExpectContinueTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import echo
        self.start_subprocess(echo.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_expect_continue(self):
        # specifying Connection: close explicitly
        data = "I have expectations"
        to_send = tobytes(
            "GET / HTTP/1.1\n"
            "Connection: close\n"
            "Content-Length: %d\n"
            "Expect: 100-continue\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # continue status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        self.assertEqual(int(status), 100)
        self.assertEqual(reason, b'Continue')
        self.assertEqual(version, b'HTTP/1.1')
        fp.readline() # blank line
        line = fp.readline() # next status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        length = int(headers.get('content-length')) or None
        response_body = fp.read(length)
        self.assertEqual(int(status), 200)
        self.assertEqual(length, len(response_body))
        self.assertEqual(response_body, tobytes(data))

class BadContentLengthTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import badcl
        self.start_subprocess(badcl.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_short_body(self):
        # check to see if server closes connection when body is too short
        # for cl header
        to_send = tobytes(
            "GET /short_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        content_length = int(headers.get('content-length'))
        response_body = fp.read(content_length)
        self.assertEqual(int(status), 200)
        self.assertNotEqual(content_length, len(response_body))
        self.assertEqual(len(response_body), content_length - 1)
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote closed connection (despite keepalive header); not sure why
        # first send succeeds
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_long_body(self):
        # check server doesnt close connection when body is too short
        # for cl header
        to_send = tobytes(
            "GET /long_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        content_length = int(headers.get('content-length')) or None
        response_body = fp.read(content_length)
        self.assertEqual(int(status), 200)
        self.assertEqual(content_length, len(response_body))
        self.assertEqual(response_body, tobytes('abcdefgh'))
        # remote does not close connection (keepalive header)
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        content_length = int(headers.get('content-length')) or None
        response_body = fp.read(content_length)
        self.assertEqual(int(status), 200)

class NoContentLengthTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import nocl
        self.start_subprocess(nocl.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_http10_generator(self):
        body = string.ascii_letters
        to_send = ("GET / HTTP/1.0\n"
                   "Connection: Keep-Alive\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), None)
        self.assertEqual(headers.get('connection'), 'close')
        self.assertEqual(response_body, tobytes(body))
        # remote closed connection (despite keepalive header), because
        # generators cannot have a content-length divined
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_http10_list(self):
        body = string.ascii_letters
        to_send = ("GET /list HTTP/1.0\n"
                   "Connection: Keep-Alive\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers['content-length'], str(len(body)))
        self.assertEqual(headers.get('connection'), 'Keep-Alive')
        self.assertEqual(response_body, tobytes(body))
        # remote keeps connection open because it divined the content length
        # from a length-1 list
        self.sock.send(to_send)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')

    def test_http10_listlentwo(self):
        body = string.ascii_letters
        to_send = ("GET /list_lentwo HTTP/1.0\n"
                   "Connection: Keep-Alive\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), None)
        self.assertEqual(headers.get('connection'), 'close')
        self.assertEqual(response_body, tobytes(body))
        # remote closed connection (despite keepalive header), because
        # lists of length > 1 cannot have their content length divined
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_http11_generator(self):
        body = string.ascii_letters
        to_send = ("GET / HTTP/1.1\n"
                   "Content-Length: %s\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        expected = b''
        for chunk in chunks(body, 10):
            expected += tobytes(
                '%s\r\n%s\r\n' % (str(hex(len(chunk))[2:].upper()), chunk)
            )
        expected += b'0\r\n\r\n'
        self.assertEqual(response_body, expected)
        # connection is always closed at the end of a chunked response
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_http11_list(self):
        body = string.ascii_letters
        to_send = ("GET /list HTTP/1.1\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(headers['content-length'], str(len(body)))
        self.assertEqual(response_body, tobytes(body))
        # remote keeps connection open because it divined the content length
        # from a length-1 list
        self.sock.send(to_send)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')

    def test_http11_listlentwo(self):
        body = string.ascii_letters
        to_send = ("GET /list_lentwo HTTP/1.1\n"
                   "Content-Length: %s\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        expected = b''
        for chunk in (body[0], body[1:]):
            expected += tobytes(
                '%s\r\n%s\r\n' % (str(hex(len(chunk))[2:].upper()), chunk)
            )
        expected += b'0\r\n\r\n'
        self.assertEqual(response_body, expected)
        # connection is always closed at the end of a chunked response
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class WriteCallbackTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import writecb
        self.start_subprocess(writecb.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_short_body(self):
        # check to see if server closes connection when body is too short
        # for cl header
        to_send = tobytes(
            "GET /short_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (5)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, 9)
        self.assertNotEqual(cl, len(response_body))
        self.assertEqual(len(response_body), cl - 1)
        self.assertEqual(response_body, tobytes('abcdefgh'))
        # remote closed connection (despite keepalive header)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_long_body(self):
        # check server doesnt close connection when body is too long
        # for cl header
        to_send = tobytes(
            "GET /long_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        content_length = int(headers.get('content-length')) or None
        self.assertEqual(content_length, 9)
        self.assertEqual(content_length, len(response_body))
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote does not close connection (keepalive header)
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')

    def test_equal_body(self):
        # check server doesnt close connection when body is equal to
        # cl header
        to_send = tobytes(
            "GET /equal_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        content_length = int(headers.get('content-length')) or None
        self.assertEqual(content_length, 9)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(content_length, len(response_body))
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote does not close connection (keepalive header)
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')

    def test_no_content_length(self):
        # wtf happens when there's no content-length
        to_send = tobytes(
            "GET /no_content_length HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        line, headers, response_body = read_http(fp)
        content_length = headers.get('content-length')
        self.assertEqual(content_length, None)
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote closed connection (despite keepalive header)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class TooLargeTests(object):

    toobig = 1050

    def setUp(self):
        from waitress.tests.fixtureapps import toolarge
        self.start_subprocess(toolarge.app,
                              max_request_header_size=1000,
                              max_request_body_size=1000)

    def tearDown(self):
        self.stop_subprocess()

    def test_request_body_too_large_with_wrong_cl_http10(self):
        body = 'a' * self.toobig
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 5\n\n")
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # first request succeeds (content-length 5)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # server trusts the content-length header; no pipelining,
        # so request fulfilled, extra bytes are thrown away
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_wrong_cl_http10_keepalive(self):
        body = 'a' * self.toobig
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 5\n"
                   "Connection: Keep-Alive\n\n")
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # first request succeeds (content-length 5)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        line, headers, response_body = read_http(fp)
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http10(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.0\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # extra bytes are thrown away (no pipelining), connection closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http10_keepalive(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.0\nConnection: Keep-Alive\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (assumed zero)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        line, headers, response_body = read_http(fp)
        # next response overruns because the extra data appears to be
        # header data
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_wrong_cl_http11(self):
        body = 'a' * self.toobig
        to_send = ("GET / HTTP/1.1\n"
                   "Content-Length: 5\n\n")
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # first request succeeds (content-length 5)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # second response is an error response
        line, headers, response_body = read_http(fp)
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_wrong_cl_http11_connclose(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.1\nContent-Length: 5\nConnection: close\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (5)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http11(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.1\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # server trusts the content-length header (assumed 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # server assumes pipelined requests due to http/1.1, and the first
        # request was assumed c-l 0 because it had no content-length header,
        # so entire body looks like the header of the subsequent request
        # second response is an error response
        line, headers, response_body = read_http(fp)
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http11_connclose(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.1\nConnection: close\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (assumed 0)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_chunked_encoding(self):
        control_line = "20;\r\n" # 20 hex = 32 dec
        s = 'This string has 32 characters.\r\n'
        to_send = "GET / HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        repeat = control_line + s
        to_send += repeat * ((self.toobig // len(repeat)) + 1)
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # body bytes counter caught a max_request_body_size overrun
        self.assertline(line, '413', 'Request Entity Too Large', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertEqual(headers['content-type'], 'text/plain')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class InternalServerErrorTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import error
        self.start_subprocess(error.app, expose_tracebacks=True)

    def tearDown(self):
        self.stop_subprocess()

    def test_before_start_response_http_10(self):
        to_send = "GET /before_start_response HTTP/1.0\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_before_start_response_http_11(self):
        to_send = "GET /before_start_response HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['content-length', 'content-type', 'date', 'server'])
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_before_start_response_http_11_close(self):
        to_send = tobytes(
            "GET /before_start_response HTTP/1.1\n"
            "Connection: close\n\n")
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['connection', 'content-length', 'content-type', 'date',
             'server'])
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_start_response_http10(self):
        to_send = "GET /after_start_response HTTP/1.0\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['connection', 'content-length', 'content-type', 'date',
             'server'])
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_start_response_http11(self):
        to_send = "GET /after_start_response HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['content-length', 'content-type', 'date', 'server'])
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_start_response_http11_close(self):
        to_send = tobytes(
            "GET /after_start_response HTTP/1.1\n"
            "Connection: close\n\n")
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['connection', 'content-length', 'content-type', 'date',
             'server'])
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_write_cb(self):
        to_send = "GET /after_write_cb HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, b'')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_in_generator(self):
        to_send = "GET /in_generator HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, b'')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class FileWrapperTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import filewrapper
        self.start_subprocess(filewrapper.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_filelike_http11(self):
        to_send = "GET /filelike HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_filelike_nocl_http11(self):
        to_send = "GET /filelike_nocl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_filelike_shortcl_http11(self):
        to_send = "GET /filelike_shortcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, 1)
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377' in response_body)
            # connection has not been closed

    def test_filelike_longcl_http11(self):
        to_send = "GET /filelike_longcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_notfilelike_http11(self):
        to_send = "GET /notfilelike HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_notfilelike_nocl_http11(self):
        to_send = "GET /notfilelike_nocl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed (no content-length)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_notfilelike_shortcl_http11(self):
        to_send = "GET /notfilelike_shortcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, 1)
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377' in response_body)
            # connection has not been closed

    def test_notfilelike_longcl_http11(self):
        to_send = "GET /notfilelike_longcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body) + 10)
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_filelike_http10(self):
        to_send = "GET /filelike HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_filelike_nocl_http10(self):
        to_send = "GET /filelike_nocl HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_notfilelike_http10(self):
        to_send = "GET /notfilelike HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_notfilelike_nocl_http10(self):
        to_send = "GET /notfilelike_nocl HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed (no content-length)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class TcpEchoTests(EchoTests, TcpTests, unittest.TestCase):
    pass

class TcpPipeliningTests(PipeliningTests, TcpTests, unittest.TestCase):
    pass

class TcpExpectContinueTests(ExpectContinueTests, TcpTests, unittest.TestCase):
    pass

class TcpBadContentLengthTests(
        BadContentLengthTests, TcpTests, unittest.TestCase):
    pass

class TcpNoContentLengthTests(
        NoContentLengthTests, TcpTests, unittest.TestCase):
    pass

class TcpWriteCallbackTests(WriteCallbackTests, TcpTests, unittest.TestCase):
    pass

class TcpTooLargeTests(TooLargeTests, TcpTests, unittest.TestCase):
    pass

class TcpInternalServerErrorTests(
        InternalServerErrorTests, TcpTests, unittest.TestCase):
    pass

class TcpFileWrapperTests(FileWrapperTests, TcpTests, unittest.TestCase):
    pass

if hasattr(socket, 'AF_UNIX'):

    class FixtureUnixWSGIServer(server.UnixWSGIServer):
        """A version of UnixWSGIServer that relays back what it's bound to.
        """

        family = socket.AF_UNIX # Testing

        def __init__(self, application, queue, **kw): # pragma: no cover
            # Coverage doesn't see this as it's ran in a separate process.
            # To permit parallel testing, use a PID-dependent socket.
            kw['unix_socket'] = '/tmp/waitress.test-%d.sock' % os.getpid()
            super(FixtureUnixWSGIServer, self).__init__(application, **kw)
            queue.put(self.socket.getsockname())

    class UnixTests(SubprocessTests):

        server = FixtureUnixWSGIServer

        def make_http_connection(self):
            return UnixHTTPConnection(self.bound_to)

        def stop_subprocess(self):
            super(UnixTests, self).stop_subprocess()
            cleanup_unix_socket(self.bound_to)

        def send_check_error(self, to_send):
            # Unlike inet domain sockets, Unix domain sockets can trigger a
            # 'Broken pipe' error when the socket it closed.
            try:
                self.sock.send(to_send)
            except socket.error as exc:
                self.assertEqual(get_errno(exc), errno.EPIPE)

    class UnixEchoTests(EchoTests, UnixTests, unittest.TestCase):
        pass

    class UnixPipeliningTests(PipeliningTests, UnixTests, unittest.TestCase):
        pass

    class UnixExpectContinueTests(
            ExpectContinueTests, UnixTests, unittest.TestCase):
        pass

    class UnixBadContentLengthTests(
            BadContentLengthTests, UnixTests, unittest.TestCase):
        pass

    class UnixNoContentLengthTests(
            NoContentLengthTests, UnixTests, unittest.TestCase):
        pass

    class UnixWriteCallbackTests(
            WriteCallbackTests, UnixTests, unittest.TestCase):
        pass

    class UnixTooLargeTests(TooLargeTests, UnixTests, unittest.TestCase):
        pass

    class UnixInternalServerErrorTests(
            InternalServerErrorTests, UnixTests, unittest.TestCase):
        pass

    class UnixFileWrapperTests(FileWrapperTests, UnixTests, unittest.TestCase):
        pass

def parse_headers(fp):
    """Parses only RFC2822 headers from a file pointer.
    """
    headers = {}
    while True:
        line = fp.readline()
        if line in (b'\r\n', b'\n', b''):
            break
        line = line.decode('iso-8859-1')
        name, value = line.strip().split(':', 1)
        headers[name.lower().strip()] = value.lower().strip()
    return headers

class UnixHTTPConnection(httplib.HTTPConnection):
    """Patched version of HTTPConnection that uses Unix domain sockets.
    """

    def __init__(self, path):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.path = path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.path)
        self.sock = sock

class ConnectionClosed(Exception):
    pass

# stolen from gevent
def read_http(fp): # pragma: no cover
    try:
        response_line = fp.readline()
    except socket.error as exc:
        fp.close()
        # errno 104 is ENOTRECOVERABLE, In WinSock 10054 is ECONNRESET
        if get_errno(exc) in (errno.ECONNABORTED, errno.ECONNRESET, 104, 10054):
            raise ConnectionClosed
        raise
    if not response_line:
        raise ConnectionClosed

    header_lines = []
    while True:
        line = fp.readline()
        if line in (b'\r\n', b'\n', b''):
            break
        else:
            header_lines.append(line)
    headers = dict()
    for x in header_lines:
        x = x.strip()
        if not x:
            continue
        key, value = x.split(b': ', 1)
        key = key.decode('iso-8859-1').lower()
        value = value.decode('iso-8859-1')
        assert key not in headers, "%s header duplicated" % key
        headers[key] = value

    if 'content-length' in headers:
        num = int(headers['content-length'])
        body = b''
        left = num
        while left > 0:
            data = fp.read(left)
            if not data:
                break
            body += data
            left -= len(data)
    else:
        # read until EOF
        body = fp.read()

    return response_line, headers, body

# stolen from gevent
def get_errno(exc): # pragma: no cover
    """ Get the error code out of socket.error objects.
    socket.error in <2.5 does not have errno attribute
    socket.error in 3.x does not allow indexing access
    e.args[0] works for all.
    There are cases when args[0] is not errno.
    i.e. http://bugs.python.org/issue6471
    Maybe there are cases when errno is set, but it is not the first argument?
    """
    try:
        if exc.errno is not None:
            return exc.errno
    except AttributeError:
        pass
    try:
        return exc.args[0]
    except IndexError:
        return None

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]
