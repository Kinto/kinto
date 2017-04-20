# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
import logging.handlers
import weakref

try:
    from unittest2 import TestCase
except ImportError:
    # Maybe we're running in python2.7?
    from unittest import TestCase  # NOQA

from webob.dec import wsgify
from webob import exc
from pyramid.httpexceptions import HTTPException
from pyramid import testing


logger = logging.getLogger('cornice')


class DummyContext(object):

    def __repr__(self):
        return 'context!'


class DummyRequest(testing.DummyRequest):
    errors = []

    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.context = DummyContext()


def dummy_factory(request):
    return DummyContext()


# stolen from the packaging stdlib testsuite tools


class _TestHandler(logging.handlers.BufferingHandler):
    # stolen and adapted from test.support

    def __init__(self):
        logging.handlers.BufferingHandler.__init__(self, 0)
        self.setLevel(logging.DEBUG)

    def shouldFlush(self):
        return False

    def emit(self, record):
        self.buffer.append(record)


class LoggingCatcher(object):
    """TestCase-compatible mixin to receive logging calls.

    Upon setUp, instances of this classes get a BufferingHandler that's
    configured to record all messages logged to the 'cornice' logger
    """

    def setUp(self):
        super(LoggingCatcher, self).setUp()
        self.loghandler = handler = _TestHandler()
        self._old_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)  # we want all messages

    def tearDown(self):
        handler = self.loghandler
        # All this is necessary to properly shut down the logging system and
        # avoid a regrtest complaint.  Thanks to Vinay Sajip for the help.
        handler.close()
        logger.removeHandler(handler)
        for ref in weakref.getweakrefs(handler):
            logging._removeHandlerRef(ref)
        del self.loghandler
        logger.setLevel(self._old_level)
        super(LoggingCatcher, self).tearDown()

    def get_logs(self, level=logging.WARNING, flush=True):
        """Return all log messages with given level.

        *level* defaults to logging.WARNING.

        For log calls with arguments (i.e.  logger.info('bla bla %r', arg)),
        the messages will be formatted before being returned (e.g. "bla bla
        'thing'").

        Returns a list.  Automatically flushes the loghandler after being
        called, unless *flush* is False (this is useful to get e.g. all
        warnings then all info messages).
        """
        messages = [log.getMessage() for log in self.loghandler.buffer
                    if log.levelno == level]
        if flush:
            self.loghandler.flush()
        return messages


class CatchErrors(object):
    def __init__(self, app):
        self.app = app
        if hasattr(app, 'registry'):
            self.registry = app.registry

    @wsgify
    def __call__(self, request):
        try:
            return request.get_response(self.app)
        except (exc.HTTPException, HTTPException) as e:
            return e
