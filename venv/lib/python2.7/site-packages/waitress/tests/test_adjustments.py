import sys

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

    def _makeOne(self, **kw):
        from waitress.adjustments import Adjustments
        return Adjustments(**kw)

    def test_goodvars(self):
        inst = self._makeOne(
            host='host',
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
        )
        self.assertEqual(inst.host, 'host')
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

    def test_badvar(self):
        self.assertRaises(ValueError, self._makeOne, nope=True)

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
            'unix_socket_perms':'777',
        }, opts)
        self.assertSequenceEqual(args, [])

    def test_bad_param(self):
        import getopt
        self.assertRaises(getopt.GetoptError, self.parse, ['--no-host'])
