##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
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
"""HTTP Request Parser

This server uses asyncore to accept connections and do initial
processing but threads to do work.
"""
import re
from io import BytesIO

from waitress.compat import (
    tostr,
    urlparse,
    unquote_bytes_to_wsgi,
)

from waitress.buffers import OverflowableBuffer

from waitress.receiver import (
    FixedStreamReceiver,
    ChunkedReceiver,
)

from waitress.utilities import (
    find_double_newline,
    RequestEntityTooLarge,
    RequestHeaderFieldsTooLarge,
    BadRequest,
)

class ParsingError(Exception):
    pass

class HTTPRequestParser(object):
    """A structure that collects the HTTP request.

    Once the stream is completed, the instance is passed to
    a server task constructor.
    """
    completed = False        # Set once request is completed.
    empty = False            # Set if no request was made.
    expect_continue = False  # client sent "Expect: 100-continue" header
    headers_finished = False # True when headers have been read
    header_plus = b''
    chunked = False
    content_length = 0
    header_bytes_received = 0
    body_bytes_received = 0
    body_rcv = None
    version = '1.0'
    error = None
    connection_close = False

    # Other attributes: first_line, header, headers, command, uri, version,
    # path, query, fragment

    def __init__(self, adj):
        """
        adj is an Adjustments object.
        """
        # headers is a mapping containing keys translated to uppercase
        # with dashes turned into underscores.
        self.headers = {}
        self.adj = adj

    def received(self, data):
        """
        Receives the HTTP stream for one request.  Returns the number of
        bytes consumed.  Sets the completed flag once both the header and the
        body have been received.
        """
        if self.completed:
            return 0 # Can't consume any more.
        datalen = len(data)
        br = self.body_rcv
        if br is None:
            # In header.
            s = self.header_plus + data
            index = find_double_newline(s)
            if index >= 0:
                # Header finished.
                header_plus = s[:index]
                consumed = len(data) - (len(s) - index)
                # Remove preceeding blank lines.
                header_plus = header_plus.lstrip()
                if not header_plus:
                    self.empty = True
                    self.completed = True
                else:
                    try:
                        self.parse_header(header_plus)
                    except ParsingError as e:
                        self.error = BadRequest(e.args[0])
                        self.completed = True
                    else:
                        if self.body_rcv is None:
                            # no content-length header and not a t-e: chunked
                            # request
                            self.completed = True
                        if self.content_length > 0:
                            max_body = self.adj.max_request_body_size
                            # we won't accept this request if the content-length
                            # is too large
                            if self.content_length >= max_body:
                                self.error = RequestEntityTooLarge(
                                    'exceeds max_body of %s' % max_body)
                                self.completed = True
                self.headers_finished = True
                return consumed
            else:
                # Header not finished yet.
                self.header_bytes_received += datalen
                max_header = self.adj.max_request_header_size
                if self.header_bytes_received >= max_header:
                    # malformed header, we need to construct some request
                    # on our own. we disregard the incoming(?) requests HTTP
                    # version and just use 1.0. IOW someone just sent garbage
                    # over the wire
                    self.parse_header(b'GET / HTTP/1.0\n')
                    self.error = RequestHeaderFieldsTooLarge(
                        'exceeds max_header of %s' % max_header)
                    self.completed = True
                self.header_plus = s
                return datalen
        else:
            # In body.
            consumed = br.received(data)
            self.body_bytes_received += consumed
            max_body = self.adj.max_request_body_size
            if self.body_bytes_received >= max_body:
                # this will only be raised during t-e: chunked requests
                self.error = RequestEntityTooLarge(
                    'exceeds max_body of %s' % max_body)
                self.completed = True
            elif br.error:
                # garbage in chunked encoding input probably
                self.error = br.error
                self.completed = True
            elif br.completed:
                # The request (with the body) is ready to use.
                self.completed = True
                if self.chunked:
                    # We've converted the chunked transfer encoding request
                    # body into a normal request body, so we know its content
                    # length; set the header here.  We already popped the
                    # TRANSFER_ENCODING header in parse_header, so this will
                    # appear to the client to be an entirely non-chunked HTTP
                    # request with a valid content-length.
                    self.headers['CONTENT_LENGTH'] = str(br.__len__())
            return consumed

    def parse_header(self, header_plus):
        """
        Parses the header_plus block of text (the headers plus the
        first line of the request).
        """
        index = header_plus.find(b'\n')
        if index >= 0:
            first_line = header_plus[:index].rstrip()
            header = header_plus[index + 1:]
        else:
            first_line = header_plus.rstrip()
            header = b''

        self.first_line = first_line # for testing

        lines = get_header_lines(header)

        headers = self.headers
        for line in lines:
            index = line.find(b':')
            if index > 0:
                key = line[:index]
                if b'_' in key:
                    continue
                value = line[index + 1:].strip()
                key1 = tostr(key.upper().replace(b'-', b'_'))
                # If a header already exists, we append subsequent values
                # seperated by a comma. Applications already need to handle
                # the comma seperated values, as HTTP front ends might do
                # the concatenation for you (behavior specified in RFC2616).
                try:
                    headers[key1] += tostr(b', ' + value)
                except KeyError:
                    headers[key1] = tostr(value)
            # else there's garbage in the headers?

        # command, uri, version will be bytes
        command, uri, version = crack_first_line(first_line)
        version = tostr(version)
        command = tostr(command)
        self.command = command
        self.version = version
        (self.proxy_scheme,
         self.proxy_netloc,
         self.path,
         self.query, self.fragment) = split_uri(uri)
        self.url_scheme = self.adj.url_scheme
        connection = headers.get('CONNECTION', '')

        if version == '1.0':
            if connection.lower() != 'keep-alive':
                self.connection_close = True

        if version == '1.1':
            # since the server buffers data from chunked transfers and clients
            # never need to deal with chunked requests, downstream clients
            # should not see the HTTP_TRANSFER_ENCODING header; we pop it
            # here
            te = headers.pop('TRANSFER_ENCODING', '')
            if te.lower() == 'chunked':
                self.chunked = True
                buf = OverflowableBuffer(self.adj.inbuf_overflow)
                self.body_rcv = ChunkedReceiver(buf)
            expect = headers.get('EXPECT', '').lower()
            self.expect_continue = expect == '100-continue'
            if connection.lower() == 'close':
                self.connection_close = True

        if not self.chunked:
            try:
                cl = int(headers.get('CONTENT_LENGTH', 0))
            except ValueError:
                cl = 0
            self.content_length = cl
            if cl > 0:
                buf = OverflowableBuffer(self.adj.inbuf_overflow)
                self.body_rcv = FixedStreamReceiver(cl, buf)

    def get_body_stream(self):
        body_rcv = self.body_rcv
        if body_rcv is not None:
            return body_rcv.getfile()
        else:
            return BytesIO()

    def close(self):
        body_rcv = self.body_rcv
        if body_rcv is not None:
            body_rcv.getbuf().close()

def split_uri(uri):
    # urlsplit handles byte input by returning bytes on py3, so
    # scheme, netloc, path, query, and fragment are bytes
    scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)
    return (
        tostr(scheme),
        tostr(netloc),
        unquote_bytes_to_wsgi(path),
        tostr(query),
        tostr(fragment),
    )

def get_header_lines(header):
    """
    Splits the header into lines, putting multi-line headers together.
    """
    r = []
    lines = header.split(b'\n')
    for line in lines:
        if line.startswith((b' ', b'\t')):
            if not r:
                # http://corte.si/posts/code/pathod/pythonservers/index.html
                raise ParsingError('Malformed header line "%s"' % tostr(line))
            r[-1] += line
        else:
            r.append(line)
    return r

first_line_re = re.compile(
    b'([^ ]+) '
    b'((?:[^ :?#]+://[^ ?#/]*(?:[0-9]{1,5})?)?[^ ]+)'
    b'(( HTTP/([0-9.]+))$|$)'
)

def crack_first_line(line):
    m = first_line_re.match(line)
    if m is not None and m.end() == len(line):
        if m.group(3):
            version = m.group(5)
        else:
            version = None
        command = m.group(1).upper()
        uri = m.group(2)
        return command, uri, version
    else:
        return b'', b'', b''
