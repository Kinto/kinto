import sys
import socket

if sys.version_info[:2] == (2, 6): # pragma: no cover
    import unittest2 as unittest
else: # pragma: no cover
    import unittest

class Test_asbool(unittest.TestCase):

    def _callFUT(self, s):
        from waitress.adjustments import asbool
        return asbool(s)

    def test_s_is_None(self):
        result = self._callFUT(None)
        self.assertEqual(result, False)

    def test_s_is_True(self):
        result = self._callFUT(True)
        self.assertEqual(result, True)

    def test_s_is_False(self):
        result = self._callFUT(False)
        self.assertEqual(result, False)

    def test_s_is_true(self):
        result = self._callFUT('True')
        self.assertEqual(result, True)

    def test_s_is_false(self):
        result = self._callFUT('False')
        self.assertEqual(result, False)

    def test_s_is_yes(self):
        result = self._callFUT('yes')
        self.assertEqual(result, True)

    def test_s_is_on(self):
        result = self._callFUT('on')
        self.assertEqual(result, True)

    def test_s_is_1(self):
        result = self._callFUT(1)
        self.assertEqual(result, True)

class TestAdjustments(unittest.TestCase):

    def _hasIPv6(self): # pragma: nocover
        if not socket.has_ipv6:
            return False

        try:
            socket.getaddrinfo(
                '::1',
                0,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                socket.AI_PASSIVE | socket.AI_ADDRCONFIG
            )

            return True
        except socket.gaierror as e:
            # Check to see what the error is
            if e.errno == socket.EAI_ADDRFAMILY:
                return False
            else:
                raise e

    def _makeOne(self, **kw):
        from waitress.adjustments import Adjustments
        return Adjustments(**kw)

    def test_goodvars(self):
        inst = self._makeOne(
            host='localhost',
            port='8080',
            threads='5',
            trusted_proxy='192.168.1.1',
            url_scheme='https',
            backlog='20',
            recv_bytes='200',
            send_bytes='300',
            outbuf_overflow='400',
            inbuf_overflow='500',
            connection_limit='1000',
            cleanup_interval='1100',
            channel_timeout='1200',
            log_socket_errors='true',
            max_request_header_size='1300',
            max_request_body_size='1400',
            expose_tracebacks='true',
            ident='abc',
            asyncore_loop_timeout='5',
            asyncore_use_poll=True,
            unix_socket='/tmp/waitress.sock',
            unix_socket_perms='777',
            url_prefix='///foo/',
            ipv4=True,
            ipv6=False,
        )

        self.assertEqual(inst.host, 'localhost')
        self.assertEqual(inst.port, 8080)
        self.assertEqual(inst.threads, 5)
        self.assertEqual(inst.trusted_proxy, '192.168.1.1')
        self.assertEqual(inst.url_scheme, 'https')
        self.assertEqual(inst.backlog, 20)
        self.assertEqual(inst.recv_bytes, 200)
        self.assertEqual(inst.send_bytes, 300)
        self.assertEqual(inst.outbuf_overflow, 400)
        self.assertEqual(inst.inbuf_overflow, 500)
        self.assertEqual(inst.connection_limit, 1000)
        self.assertEqual(inst.cleanup_interval, 1100)
        self.assertEqual(inst.channel_timeout, 1200)
        self.assertEqual(inst.log_socket_errors, True)
        self.assertEqual(inst.max_request_header_size, 1300)
        self.assertEqual(inst.max_request_body_size, 1400)
        self.assertEqual(inst.expose_tracebacks, True)
        self.assertEqual(inst.asyncore_loop_timeout, 5)
        self.assertEqual(inst.asyncore_use_poll, True)
        self.assertEqual(inst.ident, 'abc')
        self.assertEqual(inst.unix_socket, '/tmp/waitress.sock')
        self.assertEqual(inst.unix_socket_perms, 0o777)
        self.assertEqual(inst.url_prefix, '/foo')
        self.assertEqual(inst.ipv4, True)
        self.assertEqual(inst.ipv6, False)

        bind_pairs = [
            sockaddr[:2]
            for (family, _, _, sockaddr) in inst.listen
            if family == socket.AF_INET
        ]

        # On Travis, somehow we start listening to two sockets when resolving
        # localhost...
        self.assertEqual(('127.0.0.1', 8080), bind_pairs[0])

    def test_goodvar_listen(self):
        inst = self._makeOne(listen='127.0.0.1')

        bind_pairs = [(host, port) for (_, _, _, (host, port)) in inst.listen]

        self.assertEqual(bind_pairs, [('127.0.0.1', 8080)])

    def test_default_listen(self):
        inst = self._makeOne()

        bind_pairs = [(host, port) for (_, _, _, (host, port)) in inst.listen]

        self.assertEqual(bind_pairs, [('0.0.0.0', 8080)])

    def test_multiple_listen(self):
        inst = self._makeOne(listen='127.0.0.1:9090 127.0.0.1:8080')

        bind_pairs = [sockaddr[:2] for (_, _, _, sockaddr) in inst.listen]

        self.assertEqual(bind_pairs,
                         [('127.0.0.1', 9090),
                          ('127.0.0.1', 8080)])

    def test_wildcard_listen(self):
        inst = self._makeOne(listen='*:8080')

        bind_pairs = [sockaddr[:2] for (_, _, _, sockaddr) in inst.listen]

        self.assertTrue(len(bind_pairs) >= 1)

    def test_ipv6_no_port(self): # pragma: nocover
        if not self._hasIPv6():
            return

        inst = self._makeOne(listen='[::1]')

        bind_pairs = [sockaddr[:2] for (_, _, _, sockaddr) in inst.listen]

        self.assertEqual(bind_pairs, [('::1', 8080)])

    def test_bad_port(self):
        self.assertRaises(ValueError, self._makeOne, listen='127.0.0.1:test')

    def test_service_port(self):
        inst = self._makeOne(listen='127.0.0.1:http 0.0.0.0:https')

        bind_pairs = [sockaddr[:2] for (_, _, _, sockaddr) in inst.listen]

        self.assertEqual(bind_pairs, [('127.0.0.1', 80), ('0.0.0.0', 443)])

    def test_dont_mix_host_port_listen(self):
        self.assertRaises(
            ValueError,
            self._makeOne,
            host='localhost',
            port='8080',
            listen='127.0.0.1:8080',
        )

    def test_badvar(self):
        self.assertRaises(ValueError, self._makeOne, nope=True)

    def test_ipv4_disabled(self):
        self.assertRaises(ValueError, self._makeOne, ipv4=False, listen="127.0.0.1:8080")

    def test_ipv6_disabled(self):
        self.assertRaises(ValueError, self._makeOne, ipv6=False, listen="[::]:8080")

class TestCLI(unittest.TestCase):

    def parse(self, argv):
        from waitress.adjustments import Adjustments
        return Adjustments.parse_args(argv)

    def test_noargs(self):
        opts, args = self.parse([])
        self.assertDictEqual(opts, {'call': False, 'help': False})
        self.assertSequenceEqual(args, [])

    def test_help(self):
        opts, args = self.parse(['--help'])
        self.assertDictEqual(opts, {'call': False, 'help': True})
        self.assertSequenceEqual(args, [])

    def test_call(self):
        opts, args = self.parse(['--call'])
        self.assertDictEqual(opts, {'call': True, 'help': False})
        self.assertSequenceEqual(args, [])

    def test_both(self):
        opts, args = self.parse(['--call', '--help'])
        self.assertDictEqual(opts, {'call': True, 'help': True})
        self.assertSequenceEqual(args, [])

    def test_positive_boolean(self):
        opts, args = self.parse(['--expose-tracebacks'])
        self.assertDictContainsSubset({'expose_tracebacks': 'true'}, opts)
        self.assertSequenceEqual(args, [])

    def test_negative_boolean(self):
        opts, args = self.parse(['--no-expose-tracebacks'])
        self.assertDictContainsSubset({'expose_tracebacks': 'false'}, opts)
        self.assertSequenceEqual(args, [])

    def test_cast_params(self):
        opts, args = self.parse([
            '--host=localhost',
            '--port=80',
            '--unix-socket-perms=777'
        ])
        self.assertDictContainsSubset({
            'host': 'localhost',
            'port': '80',
            'unix_socket_perms': '777',
        }, opts)
        self.assertSequenceEqual(args, [])

    def test_listen_params(self):
        opts, args = self.parse([
            '--listen=test:80',
            ])

        self.assertDictContainsSubset({
            'listen': ' test:80'
            }, opts)
        self.assertSequenceEqual(args, [])

    def test_multiple_listen_params(self):
        opts, args = self.parse([
            '--listen=test:80',
            '--listen=test:8080',
            ])

        self.assertDictContainsSubset({
            'listen': ' test:80 test:8080'
            }, opts)
        self.assertSequenceEqual(args, [])

    def test_bad_param(self):
        import getopt
        self.assertRaises(getopt.GetoptError, self.parse, ['--no-host'])
