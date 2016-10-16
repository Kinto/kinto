import unittest
from pyramid import testing

class Test_excview_tween_factory(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _makeOne(self, handler, registry=None):
        from pyramid.tweens import excview_tween_factory
        if registry is None:
            registry = self.config.registry
        return excview_tween_factory(handler, registry)

    def test_it_passthrough_no_exception(self):
        dummy_response = DummyResponse()
        def handler(request):
            return dummy_response
        tween = self._makeOne(handler)
        request = DummyRequest()
        result = tween(request)
        self.assertTrue(result is dummy_response)

    def test_it_catches_notfound(self):
        from pyramid.request import Request
        from pyramid.httpexceptions import HTTPNotFound
        self.config.add_notfound_view(lambda exc, request: exc)
        def handler(request):
            raise HTTPNotFound
        tween = self._makeOne(handler)
        request = Request.blank('/')
        result = tween(request)
        self.assertEqual(result.status, '404 Not Found')

    def test_it_catches_with_predicate(self):
        from pyramid.request import Request
        from pyramid.response import Response
        def excview(request):
            return Response('foo')
        self.config.add_view(excview, context=ValueError, request_method='GET')
        def handler(request):
            raise ValueError
        tween = self._makeOne(handler)
        request = Request.blank('/')
        result = tween(request)
        self.assertTrue(b'foo' in result.body)

    def test_it_reraises_on_mismatch(self):
        from pyramid.request import Request
        def excview(request): pass
        self.config.add_view(excview, context=ValueError, request_method='GET')
        def handler(request):
            raise ValueError
        tween = self._makeOne(handler)
        request = Request.blank('/')
        request.method = 'POST'
        self.assertRaises(ValueError, lambda: tween(request))

    def test_it_reraises_on_no_match(self):
        from pyramid.request import Request
        def handler(request):
            raise ValueError
        tween = self._makeOne(handler)
        request = Request.blank('/')
        self.assertRaises(ValueError, lambda: tween(request))

class DummyRequest:
    pass

class DummyResponse:
    pass
