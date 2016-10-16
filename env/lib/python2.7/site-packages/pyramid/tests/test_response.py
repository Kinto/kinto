import io
import mimetypes
import os
import unittest
from pyramid import testing

class TestResponse(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.response import Response
        return Response

    def test_implements_IResponse(self):
        from pyramid.interfaces import IResponse
        cls = self._getTargetClass()
        self.assertTrue(IResponse.implementedBy(cls))

    def test_provides_IResponse(self):
        from pyramid.interfaces import IResponse
        inst = self._getTargetClass()()
        self.assertTrue(IResponse.providedBy(inst))

class TestFileResponse(unittest.TestCase):
    def _makeOne(self, file, **kw):
        from pyramid.response import FileResponse
        return FileResponse(file, **kw)

    def _getPath(self, suffix='txt'):
        here = os.path.dirname(__file__)
        return os.path.join(here, 'fixtures', 'minimal.%s' % (suffix,))

    def test_with_image_content_type(self):
        path = self._getPath('jpg')
        r = self._makeOne(path, content_type='image/jpeg')
        self.assertEqual(r.content_type, 'image/jpeg')
        self.assertEqual(r.headers['content-type'], 'image/jpeg')
        path = self._getPath()
        r.app_iter.close()

    def test_with_xml_content_type(self):
        path = self._getPath('xml')
        r = self._makeOne(path, content_type='application/xml')
        self.assertEqual(r.content_type, 'application/xml')
        self.assertEqual(r.headers['content-type'],
                         'application/xml; charset=UTF-8')
        r.app_iter.close()

    def test_with_pdf_content_type(self):
        path = self._getPath('xml')
        r = self._makeOne(path, content_type='application/pdf')
        self.assertEqual(r.content_type, 'application/pdf')
        self.assertEqual(r.headers['content-type'], 'application/pdf')
        r.app_iter.close()

    def test_without_content_type(self):
        for suffix in ('txt', 'xml', 'pdf'):
            path = self._getPath(suffix)
            r = self._makeOne(path)
            self.assertEqual(r.headers['content-type'].split(';')[0],
                             mimetypes.guess_type(path, strict=False)[0])
            r.app_iter.close()

    def test_python_277_bug_15207(self):
        # python 2.7.7 on windows has a bug where its mimetypes.guess_type
        # function returns Unicode for the content_type, unlike any previous
        # version of Python.  See https://github.com/Pylons/pyramid/issues/1360
        # for more information.
        from pyramid.compat import text_
        import mimetypes as old_mimetypes
        from pyramid import response
        class FakeMimetypesModule(object):
            def guess_type(self,  *arg, **kw):
                return text_('foo/bar'), None
        fake_mimetypes = FakeMimetypesModule()
        try:
            response.mimetypes = fake_mimetypes
            path = self._getPath('xml')
            r = self._makeOne(path)
            self.assertEqual(r.content_type, 'foo/bar')
            self.assertEqual(type(r.content_type), str)
        finally:
            response.mimetypes = old_mimetypes

class TestFileIter(unittest.TestCase):
    def _makeOne(self, file, block_size):
        from pyramid.response import FileIter
        return FileIter(file, block_size)

    def test___iter__(self):
        f = io.BytesIO(b'abc')
        inst = self._makeOne(f, 1)
        self.assertEqual(inst.__iter__(), inst)

    def test_iteration(self):
        data = b'abcdef'
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f, 1)
        r = b''
        for x in inst:
            self.assertEqual(len(x), 1)
            r+=x
        self.assertEqual(r, data)

    def test_close(self):
        f = io.BytesIO(b'abc')
        inst = self._makeOne(f, 1)
        inst.close()
        self.assertTrue(f.closed)

class Test_patch_mimetypes(unittest.TestCase):
    def _callFUT(self, module):
        from pyramid.response import init_mimetypes
        return init_mimetypes(module)

    def test_has_init(self):
        class DummyMimetypes(object):
            def init(self):
                self.initted = True
        module = DummyMimetypes()
        result = self._callFUT(module)
        self.assertEqual(result, True)
        self.assertEqual(module.initted, True)

    def test_missing_init(self):
        class DummyMimetypes(object):
            pass
        module = DummyMimetypes()
        result = self._callFUT(module)
        self.assertEqual(result, False)


class TestResponseAdapter(unittest.TestCase):
    def setUp(self):
        registry = Dummy()
        self.config = testing.setUp(registry=registry)

    def tearDown(self):
        self.config.end()

    def _makeOne(self, *types_or_ifaces):
        from pyramid.response import response_adapter
        return response_adapter(*types_or_ifaces)

    def test_register_single(self):
        from zope.interface import Interface
        class IFoo(Interface): pass
        dec = self._makeOne(IFoo)
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.adapters, [(foo, IFoo)])

    def test_register_multi(self):
        from zope.interface import Interface
        class IFoo(Interface): pass
        class IBar(Interface): pass
        dec = self._makeOne(IFoo, IBar)
        def foo(): pass
        config = DummyConfigurator()
        scanner = Dummy()
        scanner.config = config
        dec.register(scanner, None, foo)
        self.assertEqual(config.adapters, [(foo, IFoo), (foo, IBar)])

    def test___call__(self):
        from zope.interface import Interface
        class IFoo(Interface): pass
        dec = self._makeOne(IFoo)
        dummy_venusian = DummyVenusian()
        dec.venusian = dummy_venusian
        def foo(): pass
        dec(foo)
        self.assertEqual(dummy_venusian.attached,
                         [(foo, dec.register, 'pyramid')])


class TestGetResponseFactory(unittest.TestCase):
    def test_get_factory(self):
        from pyramid.registry import Registry
        from pyramid.response import Response, _get_response_factory

        registry = Registry()
        response = _get_response_factory(registry)(None)
        self.assertTrue(isinstance(response, Response))


class Dummy(object):
    pass

class DummyConfigurator(object):
    def __init__(self):
        self.adapters = []

    def add_response_adapter(self, wrapped, type_or_iface):
        self.adapters.append((wrapped, type_or_iface))

class DummyVenusian(object):
    def __init__(self):
        self.attached = []

    def attach(self, wrapped, fn, category=None):
        self.attached.append((wrapped, fn, category))
