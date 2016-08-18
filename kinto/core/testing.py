import os
from collections import defaultdict

try:
    import unittest2 as unittest
except ImportError:  # pragma: no cover
    import unittest  # NOQA

import mock
import webtest
from cornice import errors as cornice_errors
from enum import Enum
from pyramid.url import parse_url_overrides

from kinto.core import DEFAULT_SETTINGS
from kinto.core.storage import generators
from kinto.core.utils import sqlalchemy, follow_subrequest, encode64

skip_if_travis = unittest.skipIf('TRAVIS' in os.environ, "travis")
skip_if_no_postgresql = unittest.skipIf(sqlalchemy is None,
                                        "postgresql is not installed.")


class DummyRequest(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.upath_info = '/v0/'
        self.registry = mock.MagicMock(settings=DEFAULT_SETTINGS.copy())
        self.registry.id_generators = defaultdict(generators.UUID4)
        self.GET = {}
        self.headers = {}
        self.errors = cornice_errors.Errors(request=self)
        self.authenticated_userid = 'bob'
        self.authn_type = 'basicauth'
        self.prefixed_userid = 'basicauth:bob'
        self.json = {}
        self.validated = {}
        self.matchdict = {}
        self.response = mock.MagicMock(headers={})

        def route_url(*a, **kw):
            # XXX: refactor DummyRequest to take advantage of `pyramid.testing`
            parts = parse_url_overrides(kw)
            return ''.join([p for p in parts if p])

        self.route_url = route_url

    follow_subrequest = follow_subrequest


def get_request_class(prefix):

    class PrefixedRequestClass(webtest.app.TestRequest):

        @classmethod
        def blank(cls, path, *args, **kwargs):
            if prefix:
                path = '/%s%s' % (prefix, path)
            return webtest.app.TestRequest.blank(path, *args, **kwargs)

    return PrefixedRequestClass


class FormattedErrorMixin(object):

    def assertFormattedError(self, response, code, errno, error,
                             message=None, info=None):
        if isinstance(errno, Enum):
            errno = errno.value

        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=UTF-8')
        self.assertEqual(response.json['code'], code)
        self.assertEqual(response.json['errno'], errno)
        self.assertEqual(response.json['error'], error)

        if message is not None:
            self.assertIn(message, response.json['message'])
        else:  # pragma: no cover
            self.assertNotIn('message', response.json)

        if info is not None:
            self.assertIn(info, response.json['info'])
        else:  # pragma: no cover
            self.assertNotIn('info', response.json)


def get_user_headers(user):
    credentials = "%s:secret" % user
    authorization = 'Basic {0}'.format(encode64(credentials))
    return {
        'Authorization': authorization
    }
