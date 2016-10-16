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
import asyncore
import socket
import threading
import time
import traceback

from waitress.buffers import (
    OverflowableBuffer,
    ReadOnlyFileBasedBuffer,
)

from waitress.parser import HTTPRequestParser

from waitress.task import (
    ErrorTask,
    WSGITask,
)

from waitress.utilities import (
    logging_dispatcher,
    InternalServerError,
)

class HTTPChannel(logging_dispatcher, object):
    """
    Setting self.requests = [somerequest] prevents more requests from being
    received until the out buffers have been flushed.

    Setting self.requests = [] allows more requests to be received.
    """

    task_class = WSGITask
    error_task_class = ErrorTask
    parser_class = HTTPRequestParser

    request = None               # A request parser instance
    last_activity = 0            # Time of last activity
    will_close = False           # set to True to close the socket.
    close_when_flushed = False   # set to True to close the socket when flushed
    requests = ()                # currently pending requests
    sent_continue = False        # used as a latch after sending 100 continue
    force_flush = False          # indicates a need to flush the outbuf

    #
    # ASYNCHRONOUS METHODS (including __init__)
    #

    def __init__(
            self,
            server,
            sock,
            addr,
            adj,
            map=None,
            ):
        self.server = server
        self.adj = adj
        self.outbufs = [OverflowableBuffer(adj.outbuf_overflow)]
        self.creation_time = self.last_activity = time.time()

        # task_lock used to push/pop requests
        self.task_lock = threading.Lock()
        # outbuf_lock used to access any outbuf
        self.outbuf_lock = threading.Lock()

        asyncore.dispatcher.__init__(self, sock, map=map)

        # Don't let asyncore.dispatcher throttle self.addr on us.
        self.addr = addr

    def any_outbuf_has_data(self):
        for outbuf in self.outbufs:
            if bool(outbuf):
                return True
        return False

    def total_outbufs_len(self):
        # genexpr == more funccalls
        # use b.__len__ rather than len(b) FBO of not getting OverflowError
        # on Python 2
        return sum([b.__len__() for b in self.outbufs]) 

    def writable(self):
        # if there's data in the out buffer or we've been instructed to close
        # the channel (possibly by our server maintenance logic), run
        # handle_write
        return self.any_outbuf_has_data() or self.will_close

    def handle_write(self):
        # Precondition: there's data in the out buffer to be sent, or
        # there's a pending will_close request
        if not self.connected:
            # we dont want to close the channel twice
            return

        # try to flush any pending output
        if not self.requests:
            # 1. There are no running tasks, so we don't need to try to lock
            #    the outbuf before sending
            # 2. The data in the out buffer should be sent as soon as possible
            #    because it's either data left over from task output
            #    or a 100 Continue line sent within "received".
            flush = self._flush_some
        elif self.force_flush:
            # 1. There's a running task, so we need to try to lock
            #    the outbuf before sending
            # 2. This is the last chunk sent by the Nth of M tasks in a
            #    sequence on this channel, so flush it regardless of whether
            #    it's >= self.adj.send_bytes.  We need to do this now, or it
            #    won't get done.
            flush = self._flush_some_if_lockable
            self.force_flush = False
        elif (self.total_outbufs_len() >= self.adj.send_bytes):
            # 1. There's a running task, so we need to try to lock
            #    the outbuf before sending
            # 2. Only try to send if the data in the out buffer is larger
            #    than self.adj_bytes to avoid TCP fragmentation
            flush = self._flush_some_if_lockable
        else:
            # 1. There's not enough data in the out buffer to bother to send
            #    right now.
            flush = None

        if flush:
            try:
                flush()
            except socket.error:
                if self.adj.log_socket_errors:
                    self.logger.exception('Socket error')
                self.will_close = True
            except:
                self.logger.exception('Unexpected exception when flushing')
                self.will_close = True

        if self.close_when_flushed and not self.any_outbuf_has_data():
            self.close_when_flushed = False
            self.will_close = True

        if self.will_close:
            self.handle_close()

    def readable(self):
        # We might want to create a new task.  We can only do this if:
        # 1. We're not already about to close the connection.
        # 2. There's no already currently running task(s).
        # 3. There's no data in the output buffer that needs to be sent
        #    before we potentially create a new task.
        return not (self.will_close or self.requests or
                    self.any_outbuf_has_data())

    def handle_read(self):
        try:
            data = self.recv(self.adj.recv_bytes)
        except socket.error:
            if self.adj.log_socket_errors:
                self.logger.exception('Socket error')
            self.handle_close()
            return
        if data:
            self.last_activity = time.time()
            self.received(data)

    def received(self, data):
        """
        Receives input asynchronously and assigns one or more requests to the
        channel.
        """
        # Preconditions: there's no task(s) already running
        request = self.request
        requests = []

        if not data:
            return False

        while data:
            if request is None:
                request = self.parser_class(self.adj)
            n = request.received(data)
            if request.expect_continue and request.headers_finished:
                # guaranteed by parser to be a 1.1 request
                request.expect_continue = False
                if not self.sent_continue:
                    # there's no current task, so we don't need to try to
                    # lock the outbuf to append to it.
                    self.outbufs[-1].append(b'HTTP/1.1 100 Continue\r\n\r\n')
                    self.sent_continue = True
                    self._flush_some()
                    request.completed = False
            if request.completed:
                # The request (with the body) is ready to use.
                self.request = None
                if not request.empty:
                    requests.append(request)
                request = None
            else:
                self.request = request
            if n >= len(data):
                break
            data = data[n:]

        if requests:
            self.requests = requests
            self.server.add_task(self)

        return True

    def _flush_some_if_lockable(self):
        # Since our task may be appending to the outbuf, we try to acquire
        # the lock, but we don't block if we can't.
        locked = self.outbuf_lock.acquire(False)
        if locked:
            try:
                self._flush_some()
            finally:
                self.outbuf_lock.release()

    def _flush_some(self):
        # Send as much data as possible to our client

        sent = 0
        dobreak = False

        while True:
            outbuf = self.outbufs[0]
            # use outbuf.__len__ rather than len(outbuf) FBO of not getting
            # OverflowError on Python 2
            outbuflen = outbuf.__len__()
            if outbuflen <= 0:
                # self.outbufs[-1] must always be a writable outbuf
                if len(self.outbufs) > 1:
                    toclose = self.outbufs.pop(0)
                    try:
                        toclose.close()
                    except:
                        self.logger.exception(
                            'Unexpected error when closing an outbuf')
                    continue # pragma: no cover (coverage bug, it is hit)
                else:
                    if hasattr(outbuf, 'prune'):
                        outbuf.prune()
                    dobreak = True

            while outbuflen > 0:
                chunk = outbuf.get(self.adj.send_bytes)
                num_sent = self.send(chunk)
                if num_sent:
                    outbuf.skip(num_sent, True)
                    outbuflen -= num_sent
                    sent += num_sent
                else:
                    dobreak = True
                    break

            if dobreak:
                break

        if sent:
            self.last_activity = time.time()
            return True

        return False

    def handle_close(self):
        for outbuf in self.outbufs:
            try:
                outbuf.close()
            except:
                self.logger.exception(
                    'Unknown exception while trying to close outbuf')
        self.connected = False
        asyncore.dispatcher.close(self)

    def add_channel(self, map=None):
        """See asyncore.dispatcher

        This hook keeps track of opened channels.
        """
        asyncore.dispatcher.add_channel(self, map)
        self.server.active_channels[self._fileno] = self

    def del_channel(self, map=None):
        """See asyncore.dispatcher

        This hook keeps track of closed channels.
        """
        fd = self._fileno # next line sets this to None
        asyncore.dispatcher.del_channel(self, map)
        ac = self.server.active_channels
        if fd in ac:
            del ac[fd]

    #
    # SYNCHRONOUS METHODS
    #

    def write_soon(self, data):
        if data:
            # the async mainloop might be popping data off outbuf; we can
            # block here waiting for it because we're in a task thread
            with self.outbuf_lock:
                if data.__class__ is ReadOnlyFileBasedBuffer:
                    # they used wsgi.file_wrapper
                    self.outbufs.append(data)
                    nextbuf = OverflowableBuffer(self.adj.outbuf_overflow)
                    self.outbufs.append(nextbuf)
                else:
                    self.outbufs[-1].append(data)
            # XXX We might eventually need to pull the trigger here (to
            # instruct select to stop blocking), but it slows things down so
            # much that I'll hold off for now; "server push" on otherwise
            # unbusy systems may suffer.
            return len(data)
        return 0

    def service(self):
        """Execute all pending requests """
        with self.task_lock:
            while self.requests:
                request = self.requests[0]
                if request.error:
                    task = self.error_task_class(self, request)
                else:
                    task = self.task_class(self, request)
                try:
                    task.service()
                except:
                    self.logger.exception('Exception when serving %s' %
                                          task.request.path)
                    if not task.wrote_header:
                        if self.adj.expose_tracebacks:
                            body = traceback.format_exc()
                        else:
                            body = ('The server encountered an unexpected '
                                    'internal server error')
                        req_version = request.version
                        req_headers = request.headers
                        request = self.parser_class(self.adj)
                        request.error = InternalServerError(body)
                        # copy some original request attributes to fulfill
                        # HTTP 1.1 requirements
                        request.version = req_version
                        try:
                            request.headers['CONNECTION'] = req_headers[
                                'CONNECTION']
                        except KeyError:
                            pass
                        task = self.error_task_class(self, request)
                        task.service() # must not fail
                    else:
                        task.close_on_finish = True
                # we cannot allow self.requests to drop to empty til
                # here; otherwise the mainloop gets confused
                if task.close_on_finish:
                    self.close_when_flushed = True
                    for request in self.requests:
                        request.close()
                    self.requests = []
                else:
                    request = self.requests.pop(0)
                    request.close()

        self.force_flush = True
        self.server.pull_trigger()
        self.last_activity = time.time()

    def cancel(self):
        """ Cancels all pending requests """
        self.force_flush = True
        self.last_activity = time.time()
        self.requests = []

    def defer(self):
        pass
