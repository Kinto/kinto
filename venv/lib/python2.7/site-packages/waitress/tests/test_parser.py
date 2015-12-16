##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""HTTP Request Parser tests
"""
import unittest

from waitress.compat import (
    text_,
    tobytes,
)

class TestHTTPRequestParser(unittest.TestCase):

    def setUp(self):
        from waitress.parser import HTTPRequestParser
        from waitress.adjustments import Adjustments
        my_adj = Adjustments()
        self.parser = HTTPRequestParser(my_adj)

    def test_get_body_stream_None(self):
        self.parser.body_recv = None
        result = self.parser.get_body_stream()
        self.assertEqual(result.getvalue(), b'')

    def test_get_body_stream_nonNone(self):
        body_rcv = DummyBodyStream()
        self.parser.body_rcv = body_rcv
        result = self.parser.get_body_stream()
        self.assertEqual(result, body_rcv)

    def test_received_nonsense_with_double_cr(self):
        data = b"""\
HTTP/1.0 GET /foobar


"""
        result = self.parser.received(data)
        self.assertEqual(result, 22)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.headers, {})

    def test_received_bad_host_header(self):
        from waitress.utilities import BadRequest
        data = b"""\
HTTP/1.0 GET /foobar
 Host: foo


"""
        result = self.parser.received(data)
        self.assertEqual(result, 33)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.error.__class__, BadRequest)

    def test_received_nonsense_nothing(self):
        data = b"""\


"""
        result = self.parser.received(data)
        self.assertEqual(result, 2)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.headers, {})

    def test_received_no_doublecr(self):
        data = b"""\
GET /foobar HTTP/8.4
"""
        result = self.parser.received(data)
        self.assertEqual(result, 21)
        self.assertFalse(self.parser.completed)
        self.assertEqual(self.parser.headers, {})

    def test_received_already_completed(self):
        self.parser.completed = True
        result = self.parser.received(b'a')
        self.assertEqual(result, 0)

    def test_received_cl_too_large(self):
        from waitress.utilities import RequestEntityTooLarge
        self.parser.adj.max_request_body_size = 2
        data = b"""\
GET /foobar HTTP/8.4
Content-Length: 10

"""
        result = self.parser.received(data)
        self.assertEqual(result, 41)
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error, RequestEntityTooLarge))

    def test_received_headers_too_large(self):
        from waitress.utilities import RequestHeaderFieldsTooLarge
        self.parser.adj.max_request_header_size = 2
        data = b"""\
GET /foobar HTTP/8.4
X-Foo: 1
"""
        result = self.parser.received(data)
        self.assertEqual(result, 30)
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error,
                                   RequestHeaderFieldsTooLarge))

    def test_received_body_too_large(self):
        from waitress.utilities import RequestEntityTooLarge
        self.parser.adj.max_request_body_size = 2
        data = b"""\
GET /foobar HTTP/1.1
Transfer-Encoding: chunked
X-Foo: 1

20;\r\n
This string has 32 characters\r\n
0\r\n\r\n"""
        result = self.parser.received(data)
        self.assertEqual(result, 58)
        self.parser.received(data[result:])
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error,
                                   RequestEntityTooLarge))

    def test_received_error_from_parser(self):
        from waitress.utilities import BadRequest
        data = b"""\
GET /foobar HTTP/1.1
Transfer-Encoding: chunked
X-Foo: 1

garbage
"""
        # header
        result = self.parser.received(data)
        # body
        result = self.parser.received(data[result:])
        self.assertEqual(result, 8)
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error,
                                   BadRequest))

    def test_received_chunked_completed_sets_content_length(self):
        data = b"""\
GET /foobar HTTP/1.1
Transfer-Encoding: chunked
X-Foo: 1

20;\r\n
This string has 32 characters\r\n
0\r\n\r\n"""
        result = self.parser.received(data)
        self.assertEqual(result, 58)
        data = data[result:]
        result = self.parser.received(data)
        self.assertTrue(self.parser.completed)
        self.assertTrue(self.parser.error is None)
        self.assertEqual(self.parser.headers['CONTENT_LENGTH'], '32')
        
    def test_parse_header_gardenpath(self):
        data = b"""\
GET /foobar HTTP/8.4
foo: bar"""
        self.parser.parse_header(data)
        self.assertEqual(self.parser.first_line, b'GET /foobar HTTP/8.4')
        self.assertEqual(self.parser.headers['FOO'], 'bar')

    def test_parse_header_no_cr_in_headerplus(self):
        data = b"GET /foobar HTTP/8.4"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.first_line, data)

    def test_parse_header_bad_content_length(self):
        data = b"GET /foobar HTTP/8.4\ncontent-length: abc"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.body_rcv, None)

    def test_parse_header_11_te_chunked(self):
        # NB: test that capitalization of header value is unimportant
        data = b"GET /foobar HTTP/1.1\ntransfer-encoding: ChUnKed"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.body_rcv.__class__.__name__,
                         'ChunkedReceiver')

    def test_parse_header_11_expect_continue(self):
        data = b"GET /foobar HTTP/1.1\nexpect: 100-continue"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.expect_continue, True)

    def test_parse_header_connection_close(self):
        data = b"GET /foobar HTTP/1.1\nConnection: close\n\n"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.connection_close, True)

    def test_close_with_body_rcv(self):
        body_rcv = DummyBodyStream()
        self.parser.body_rcv = body_rcv
        self.parser.close()
        self.assertTrue(body_rcv.closed)

    def test_close_with_no_body_rcv(self):
        self.parser.body_rcv = None
        self.parser.close() # doesn't raise

class Test_split_uri(unittest.TestCase):

    def _callFUT(self, uri):
        from waitress.parser import split_uri
        (self.proxy_scheme,
         self.proxy_netloc,
         self.path,
         self.query, self.fragment) = split_uri(uri)

    def test_split_uri_unquoting_unneeded(self):
        self._callFUT(b'http://localhost:8080/abc def')
        self.assertEqual(self.path, '/abc def')

    def test_split_uri_unquoting_needed(self):
        self._callFUT(b'http://localhost:8080/abc%20def')
        self.assertEqual(self.path, '/abc def')

    def test_split_url_with_query(self):
        self._callFUT(b'http://localhost:8080/abc?a=1&b=2')
        self.assertEqual(self.path, '/abc')
        self.assertEqual(self.query, 'a=1&b=2')

    def test_split_url_with_query_empty(self):
        self._callFUT(b'http://localhost:8080/abc?')
        self.assertEqual(self.path, '/abc')
        self.assertEqual(self.query, '')

    def test_split_url_with_fragment(self):
        self._callFUT(b'http://localhost:8080/#foo')
        self.assertEqual(self.path, '/')
        self.assertEqual(self.fragment, 'foo')

    def test_split_url_https(self):
        self._callFUT(b'https://localhost:8080/')
        self.assertEqual(self.path, '/')
        self.assertEqual(self.proxy_scheme, 'https')
        self.assertEqual(self.proxy_netloc, 'localhost:8080')

class Test_get_header_lines(unittest.TestCase):

    def _callFUT(self, data):
        from waitress.parser import get_header_lines
        return get_header_lines(data)

    def test_get_header_lines(self):
        result = self._callFUT(b'slam\nslim')
        self.assertEqual(result, [b'slam', b'slim'])

    def test_get_header_lines_folded(self):
        # From RFC2616:
        # HTTP/1.1 header field values can be folded onto multiple lines if the
        # continuation line begins with a space or horizontal tab. All linear
        # white space, including folding, has the same semantics as SP. A
        # recipient MAY replace any linear white space with a single SP before
        # interpreting the field value or forwarding the message downstream.

        # We are just preserving the whitespace that indicates folding.
        result = self._callFUT(b'slim\n slam')
        self.assertEqual(result, [b'slim slam'])

    def test_get_header_lines_tabbed(self):
        result = self._callFUT(b'slam\n\tslim')
        self.assertEqual(result, [b'slam\tslim'])

    def test_get_header_lines_malformed(self):
        # http://corte.si/posts/code/pathod/pythonservers/index.html
        from waitress.parser import ParsingError
        self.assertRaises(ParsingError,
                          self._callFUT, b' Host: localhost\r\n\r\n')

class Test_crack_first_line(unittest.TestCase):

    def _callFUT(self, line):
        from waitress.parser import crack_first_line
        return crack_first_line(line)

    def test_crack_first_line_matchok(self):
        result = self._callFUT(b'get / HTTP/1.0')
        self.assertEqual(result, (b'GET', b'/', b'1.0'))

    def test_crack_first_line_nomatch(self):
        result = self._callFUT(b'get / bleh')
        self.assertEqual(result, (b'', b'', b''))

    def test_crack_first_line_missing_version(self):
        result = self._callFUT(b'get /')
        self.assertEqual(result, (b'GET', b'/', None))

class TestHTTPRequestParserIntegration(unittest.TestCase):

    def setUp(self):
        from waitress.parser import HTTPRequestParser
        from waitress.adjustments import Adjustments
        my_adj = Adjustments()
        self.parser = HTTPRequestParser(my_adj)

    def feed(self, data):
        parser = self.parser
        for n in range(100): # make sure we never loop forever
            consumed = parser.received(data)
            data = data[consumed:]
            if parser.completed:
                return
        raise ValueError('Looping') # pragma: no cover

    def testSimpleGET(self):
        data = b"""\
GET /foobar HTTP/8.4
FirstName: mickey
lastname: Mouse
content-length: 7

Hello.
"""
        parser = self.parser
        self.feed(data)
        self.assertTrue(parser.completed)
        self.assertEqual(parser.version, '8.4')
        self.assertFalse(parser.empty)
        self.assertEqual(parser.headers,
                         {'FIRSTNAME': 'mickey',
                          'LASTNAME': 'Mouse',
                          'CONTENT_LENGTH': '7',
                          })
        self.assertEqual(parser.path, '/foobar')
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.query, '')
        self.assertEqual(parser.proxy_scheme, '')
        self.assertEqual(parser.proxy_netloc, '')
        self.assertEqual(parser.get_body_stream().getvalue(), b'Hello.\n')

    def testComplexGET(self):
        data = b"""\
GET /foo/a+%2B%2F%C3%A4%3D%26a%3Aint?d=b+%2B%2F%3D%26b%3Aint&c+%2B%2F%3D%26c%3Aint=6 HTTP/8.4
FirstName: mickey
lastname: Mouse
content-length: 10

Hello mickey.
"""
        parser = self.parser
        self.feed(data)
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.version, '8.4')
        self.assertFalse(parser.empty)
        self.assertEqual(parser.headers,
                         {'FIRSTNAME': 'mickey',
                          'LASTNAME': 'Mouse',
                          'CONTENT_LENGTH': '10',
                          })
        # path should be utf-8 encoded
        self.assertEqual(tobytes(parser.path).decode('utf-8'),
                         text_(b'/foo/a++/\xc3\xa4=&a:int', 'utf-8'))
        self.assertEqual(parser.query,
                         'd=b+%2B%2F%3D%26b%3Aint&c+%2B%2F%3D%26c%3Aint=6')
        self.assertEqual(parser.get_body_stream().getvalue(), b'Hello mick')

    def testProxyGET(self):
        data = b"""\
GET https://example.com:8080/foobar HTTP/8.4
content-length: 7

Hello.
"""
        parser = self.parser
        self.feed(data)
        self.assertTrue(parser.completed)
        self.assertEqual(parser.version, '8.4')
        self.assertFalse(parser.empty)
        self.assertEqual(parser.headers,
                         {'CONTENT_LENGTH': '7',
                          })
        self.assertEqual(parser.path, '/foobar')
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.proxy_scheme, 'https')
        self.assertEqual(parser.proxy_netloc, 'example.com:8080')
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.query, '')
        self.assertEqual(parser.get_body_stream().getvalue(), b'Hello.\n')

    def testDuplicateHeaders(self):
        # Ensure that headers with the same key get concatenated as per
        # RFC2616.
        data = b"""\
GET /foobar HTTP/8.4
x-forwarded-for: 10.11.12.13
x-forwarded-for: unknown,127.0.0.1
X-Forwarded_for: 255.255.255.255
content-length: 7

Hello.
"""
        self.feed(data)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.headers, {
            'CONTENT_LENGTH': '7',
            'X_FORWARDED_FOR':
                '10.11.12.13, unknown,127.0.0.1, 255.255.255.255',
        })

class DummyBodyStream(object):

    def getfile(self):
        return self

    def getbuf(self):
        return self

    def close(self):
        self.closed = True
