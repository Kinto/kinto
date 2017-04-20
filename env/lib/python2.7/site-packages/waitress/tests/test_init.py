import unittest

class Test_serve(unittest.TestCase):

    def _callFUT(self, app, **kw):
        from waitress import serve
        return serve(app, **kw)

    def test_it(self):
        server = DummyServerFactory()
        app = object()
        result = self._callFUT(app, _server=server, _quiet=True)
        self.assertEqual(server.app, app)
        self.assertEqual(result, None)
        self.assertEqual(server.ran, True)

class Test_serve_paste(unittest.TestCase):

    def _callFUT(self, app, **kw):
        from waitress import serve_paste
        return serve_paste(app, None, **kw)

    def test_it(self):
        server = DummyServerFactory()
        app = object()
        result = self._callFUT(app, _server=server, _quiet=True)
        self.assertEqual(server.app, app)
        self.assertEqual(result, 0)
        self.assertEqual(server.ran, True)

class DummyServerFactory(object):
    ran = False

    def __call__(self, app, **kw):
        self.adj = DummyAdj(kw)
        self.app = app
        self.kw = kw
        return self

    def run(self):
        self.ran = True

class DummyAdj(object):
    verbose = False

    def __init__(self, kw):
        self.__dict__.update(kw)
