# -*- coding: utf-8 -*-

import unittest
import transaction
from transaction import TransactionManager
from pyramid import testing
from webtest import TestApp

class TestDefaultCommitVeto(unittest.TestCase):
    def _callFUT(self, response, request=None):
        from pyramid_tm import default_commit_veto
        return default_commit_veto(request, response)

    def test_it_true_500(self):
        response = DummyResponse('500 Server Error')
        self.assertTrue(self._callFUT(response))

    def test_it_true_503(self):
        response = DummyResponse('503 Service Unavailable')
        self.assertTrue(self._callFUT(response))

    def test_it_true_400(self):
        response = DummyResponse('400 Bad Request')
        self.assertTrue(self._callFUT(response))

    def test_it_true_411(self):
        response = DummyResponse('411 Length Required')
        self.assertTrue(self._callFUT(response))

    def test_it_false_200(self):
        response = DummyResponse('200 OK')
        self.assertFalse(self._callFUT(response))

    def test_it_false_201(self):
        response = DummyResponse('201 Created')
        self.assertFalse(self._callFUT(response))

    def test_it_false_301(self):
        response = DummyResponse('301 Moved Permanently')
        self.assertFalse(self._callFUT(response))

    def test_it_false_302(self):
        response = DummyResponse('302 Found')
        self.assertFalse(self._callFUT(response))

    def test_it_false_x_tm_commit(self):
        response = DummyResponse('200 OK', {'x-tm':'commit'})
        self.assertFalse(self._callFUT(response))

    def test_it_true_x_tm_abort(self):
        response = DummyResponse('200 OK', {'x-tm':'abort'})
        self.assertTrue(self._callFUT(response))

    def test_it_true_x_tm_anythingelse(self):
        response = DummyResponse('200 OK', {'x-tm':''})
        self.assertTrue(self._callFUT(response))

class Test_tm_tween_factory(unittest.TestCase):
    def setUp(self):
        self.txn = DummyTransaction()
        self.request = DummyRequest()
        self.response = DummyResponse()
        self.registry = DummyRegistry()
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, handler=None, registry=None, request=None, txn=None):
        if handler is None:
            def handler(request):
                return self.response
        if registry is None:
            registry = self.registry
        if request is None:
            request = self.request
        if txn is None:
            txn = self.txn
        request.tm = txn
        from pyramid_tm import tm_tween_factory
        factory = tm_tween_factory(handler, registry)
        return factory(request)

    def test_repoze_tm_active(self):
        request = DummyRequest()
        request.environ['repoze.tm.active'] = True
        result = self._callFUT(request=request)
        self.assertEqual(result, self.response)
        self.assertFalse(self.txn.began)

    def test_should_activate_true(self):
        registry = DummyRegistry(
            {'tm.activate_hook':'pyramid_tm.tests.activate_true'})
        result = self._callFUT(registry=registry)
        self.assertEqual(result, self.response)
        self.assertTrue(self.txn.began)

    def test_should_activate_false(self):
        registry = DummyRegistry(
            {'tm.activate_hook':'pyramid_tm.tests.activate_false'})
        result = self._callFUT(registry=registry)
        self.assertEqual(result, self.response)
        self.assertFalse(self.txn.began)

    def test_handler_exception(self):
        def handler(request):
            raise NotImplementedError
        self.assertRaises(NotImplementedError, self._callFUT, handler=handler)
        self.assertTrue(self.txn.began)
        self.assertTrue(self.txn.aborted)
        self.assertFalse(self.txn.committed)

    def test_handler_retryable_exception(self):
        from transaction.interfaces import TransientError
        class Conflict(TransientError):
            pass
        count = []
        response = DummyResponse()
        self.registry.settings['tm.attempts'] = '3'
        def handler(request, count=count):
            count.append(True)
            if len(count) == 3:
                return response
            raise Conflict
        txn = DummyTransaction(retryable=True)
        result = self._callFUT(handler=handler, txn=txn)
        self.assertTrue(txn.began)
        self.assertEqual(txn.committed, 1)
        self.assertEqual(txn.aborted, 2)
        self.assertEqual(self.request.made_seekable, 3)
        self.assertEqual(result, response)

    def test_handler_retryable_exception_defaults_to_1(self):
        from transaction.interfaces import TransientError
        class Conflict(TransientError):
            pass
        count = []
        def handler(request, count=count):
            raise Conflict
        self.assertRaises(Conflict, self._callFUT, handler=handler)

    def test_handler_isdoomed(self):
        txn = DummyTransaction(True)
        self._callFUT(txn=txn)
        self.assertTrue(txn.began)
        self.assertTrue(txn.aborted)
        self.assertFalse(txn.committed)

    def test_handler_w_native_unauthenticated_userid(self):
        self.config.testing_securitypolicy(userid='phred')
        self._callFUT()
        self.assertEqual(self.txn.username, ' phred')

    def test_handler_w_unicode_unauthenticated_userid(self):
        from pyramid_tm.compat import native_
        from pyramid_tm.compat import PY3
        USERID = b'phred/\xd1\x80\xd0\xb5\xd1\x81'.decode('utf-8')
        self.config.testing_securitypolicy(userid=USERID)
        self._callFUT()
        if PY3:
            self.assertEqual(self.txn.username, ' phred/рес')
        else:
            self.assertEqual(self.txn.username,
                             ' ' + native_(USERID, 'utf-8'))

    def test_handler_w_integer_unauthenticated_userid(self):
        # See https://github.com/Pylons/pyramid_tm/issues/28
        USERID = 1234
        self.config.testing_securitypolicy(userid=USERID)
        self._callFUT()
        self.assertEqual(self.txn.username, ' 1234')

    def test_disables_user_annotation(self):
        self.config.testing_securitypolicy(userid="nope")
        registry = DummyRegistry({"tm.annotate_user": 'false'})
        result = self._callFUT(registry=registry)
        self.assertEqual(self.txn.username, None)

    def test_handler_notes(self):
        self._callFUT()
        self.assertEqual(self.txn._note, '/')
        self.assertEqual(self.txn.username, None)

    def test_handler_notes_unicode_decode_error(self):
        class DummierRequest(DummyRequest):
            def _get_path_info(self):
                b"\xc0".decode("utf-8")
            def _set_path_info(self, val):
                pass
            path_info = property(_get_path_info, _set_path_info)

        request = DummierRequest()

        self._callFUT(request=request)
        self.assertEqual(self.txn._note, 'Unable to decode path as unicode')
        self.assertEqual(self.txn.username, None)

    def test_handler_notes_unicode_path(self):
        from pyramid_tm.compat import PY3
        class DummierRequest(DummyRequest):

            def _get_path_info(self):
                return b'collection/\xd1\x80\xd0\xb5\xd1\x81'.decode('utf-8')

            def _set_path_info(self, val):
                pass

            path_info = property(_get_path_info, _set_path_info)

        request = DummierRequest()
        self._callFUT(request=request)
        if PY3:
            self.assertEqual(self.txn._note, 'collection/рес')
        else:
            self.assertEqual(self.txn._note,
                             'collection/\xd1\x80\xd0\xb5\xd1\x81')
        self.assertEqual(self.txn.username, None)

    def test_handler_notes_native_str_path(self):
        class DummierRequest(DummyRequest):

            def _get_path_info(self):
                return 'some/resource'

            def _set_path_info(self, val):
                pass

            path_info = property(_get_path_info, _set_path_info)

        request = DummierRequest()
        self._callFUT(request=request)
        self.assertEqual(self.txn._note, 'some/resource')
        self.assertEqual(self.txn.username, None)

    def test_500_without_commit_veto(self):
        response = DummyResponse()
        response.status = '500 Bad Request'
        def handler(request):
            return response
        result = self._callFUT(handler=handler)
        self.assertEqual(result, response)
        self.assertTrue(self.txn.began)
        self.assertFalse(self.txn.aborted)
        self.assertTrue(self.txn.committed)

    def test_500_with_default_commit_veto(self):
        settings = self.registry.settings
        settings['tm.commit_veto'] = 'pyramid_tm.default_commit_veto'
        response = DummyResponse()
        response.status = '500 Bad Request'
        def handler(request):
            return response
        result = self._callFUT(handler=handler)
        self.assertEqual(result, response)
        self.assertTrue(self.txn.began)
        self.assertTrue(self.txn.aborted)
        self.assertFalse(self.txn.committed)

    def test_null_commit_veto(self):
        response = DummyResponse()
        response.status = '500 Bad Request'
        def handler(request):
            return response
        registry = DummyRegistry({'tm.commit_veto':None})
        result = self._callFUT(handler=handler, registry=registry)
        self.assertEqual(result, response)
        self.assertTrue(self.txn.began)
        self.assertFalse(self.txn.aborted)
        self.assertTrue(self.txn.committed)

    def test_commit_veto_true(self):
        registry = DummyRegistry(
            {'tm.commit_veto':'pyramid_tm.tests.veto_true'})
        result = self._callFUT(registry=registry)
        self.assertEqual(result, self.response)
        self.assertTrue(self.txn.began)
        self.assertTrue(self.txn.aborted)
        self.assertFalse(self.txn.committed)

    def test_commit_veto_false(self):
        registry = DummyRegistry(
            {'tm.commit_veto':'pyramid_tm.tests.veto_false'})
        result = self._callFUT(registry=registry)
        self.assertEqual(result, self.response)
        self.assertTrue(self.txn.began)
        self.assertFalse(self.txn.aborted)
        self.assertTrue(self.txn.committed)

    def test_commitonly(self):
        result = self._callFUT()
        self.assertEqual(result, self.response)
        self.assertTrue(self.txn.began)
        self.assertFalse(self.txn.aborted)
        self.assertTrue(self.txn.committed)

    def test_commit_veto_alias(self):
        registry = DummyRegistry(
            {'pyramid_tm.commit_veto':'pyramid_tm.tests.veto_true'})
        result = self._callFUT(registry=registry)
        self.assertEqual(result, self.response)
        self.assertTrue(self.txn.began)
        self.assertTrue(self.txn.aborted)
        self.assertFalse(self.txn.committed)

class Test_create_tm(unittest.TestCase):

    def setUp(self):
        self.request = DummyRequest()
        self.request.registry = Dummy(settings={})
        # Get rid of the request.transaction attribute since it shouldn't be
        # here yet.
        del self.request.tm


    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, request=None):
        if request is None:
            request = self.request
        from pyramid_tm import create_tm
        return create_tm(request)

    def test_default_threadlocal(self):
        self.assertTrue(self._callFUT() is transaction.manager)

    def test_overridden_manager(self):
        txn = DummyTransaction()
        request = DummyRequest()
        request.registry = Dummy(settings={})
        request.registry.settings["tm.manager_hook"] = lambda request: txn
        self.assertTrue(self._callFUT(request=request) is txn)


def veto_true(request, response):
    return True

def veto_false(request, response):
    return False

def activate_true(request):
    return True

def activate_false(request):
    return False

create_manager = None

class Test_includeme(unittest.TestCase):
    def test_it(self):
        from pyramid.tweens import EXCVIEW
        from pyramid_tm import includeme
        config = DummyConfig()
        includeme(config)
        self.assertEqual(config.tweens,
                         [('pyramid_tm.tm_tween_factory', EXCVIEW, None)])
        self.assertEqual(config.request_methods,
                         [('pyramid_tm.create_tm', 'tm', True)])
        self.assertEqual(len(config.actions), 1)
        self.assertEqual(config.actions[0][0], None)
        self.assertEqual(config.actions[0][2], 10)

    def test_invalid_dotted(self):
        from pyramid_tm import includeme
        config = DummyConfig()
        config.registry.settings["tm.manager_hook"] = "an.invalid.import"
        includeme(config)
        self.assertRaises(ImportError, config.actions[0][1])

    def test_valid_dotted(self):
        from pyramid_tm import includeme
        config = DummyConfig()
        config.registry.settings["tm.manager_hook"] = \
            "pyramid_tm.tests.create_manager"
        includeme(config)
        config.actions[0][1]()
        self.assertTrue(
            config.registry.settings["tm.manager_hook"] is create_manager
        )

    def test_it_config(self):
        config = testing.setUp()
        try:
            config.include('pyramid_tm')
        finally:
            testing.tearDown()

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.config = config = testing.setUp()
        config.include('pyramid_tm')

    def tearDown(self):
        testing.tearDown()

    def _makeApp(self):
        app = self.config.make_wsgi_app()
        return TestApp(app)

    def test_it(self):
        config = self.config
        dm = DummyDataManager()
        def view(request):
            dm.bind(request.tm)
            return 'ok'
        config.add_view(view, name='', renderer='string')
        app = self._makeApp()
        resp = app.get('/')
        self.assertEqual(resp.body, b'ok')
        self.assertEqual(dm.action, 'commit')

    def test_unhandled_error_aborts(self):
        config = self.config
        dm = DummyDataManager()
        def view(request):
            dm.bind(request.tm)
            raise ValueError
        config.add_view(view)
        app = self._makeApp()
        self.assertRaises(ValueError, app.get, '/')
        self.assertEqual(dm.action, 'abort')

    def test_handled_error_aborts(self):
        config = self.config
        dm = DummyDataManager()
        def view(request):
            dm.bind(request.tm)
            raise ValueError
        config.add_view(view)
        def exc_view(request):
            return 'failure'
        config.add_view(exc_view, context=ValueError, renderer='string')
        app = self._makeApp()
        resp = app.get('/')
        self.assertEqual(resp.body, b'failure')
        self.assertEqual(dm.action, 'abort')

class Dummy(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class DummyRegistry(object):
    def __init__(self, settings=None):
        if settings is None:
            settings = {}
        self.settings = settings


class DummyTransaction(TransactionManager):
    began = False
    committed = False
    aborted = False
    _resources = []
    username = None

    def __init__(self, doomed=False, retryable=False):
        self.doomed = doomed
        self.began = 0
        self.committed = 0
        self.aborted = 0
        self.retryable = retryable
        self.active = False

    def _retryable(self, t, v):
        if self.active:
            return self.retryable

    def get(self):
        return self

    def setUser(self, name, path='/'):
        self.username = "%s %s" % (path, name)

    def isDoomed(self):
        return self.doomed

    def begin(self):
        self.began+=1
        self.active = True
        return self

    def commit(self):
        self.committed+=1

    def abort(self):
        self.active = False
        self.aborted+=1

    def note(self, value):
        self._note = value

class DummyDataManager(object):
    action = None

    def bind(self, tm):
        self.transaction_manager = tm
        tm.get().join(self)

    def abort(self, transaction):
        self.action = 'abort'

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        self.action = 'commit'

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        pass

    def tpc_abort(self, transaction): # pragma: no cover
        pass

    def sortKey(self):
        return 'dummy:%s' % id(self)

class DummyRequest(testing.DummyRequest):
    def __init__(self, *args, **kwargs):
        self.made_seekable = 0
        self.tm = TransactionManager()
        super(DummyRequest, self).__init__(self, *args, **kwargs)

    def make_body_seekable(self):
        self.made_seekable += 1

class DummyResponse(object):
    def __init__(self, status='200 OK', headers=None):
        self.status = status
        if headers is None:
            headers = {}
        self.headers = headers

class DummyConfig(object):
    def __init__(self):
        self.registry = Dummy(settings={})
        self.tweens = []
        self.request_methods = []
        self.actions = []

    def add_tween(self, x, under=None, over=None):
        self.tweens.append((x, under, over))

    def add_request_method(self, x, name=None, reify=None):
        self.request_methods.append((x, name, reify))

    def action(self, x, fun, order=None):
        self.actions.append((x, fun, order))
