import unittest
import warnings

from pyramid.testing import cleanUp

from pyramid.compat import (
    text_,
    native_,
    text_type,
    url_quote,
    PY2,
    )

with warnings.catch_warnings(record=True) as w:
    warnings.filterwarnings('always')
    from pyramid.interfaces import IContextURL
    assert(len(w) == 1)

class TraversalPathTests(unittest.TestCase):
    def _callFUT(self, path):
        from pyramid.traversal import traversal_path
        return traversal_path(path)

    def test_utf8(self):
        la = b'La Pe\xc3\xb1a'
        encoded = url_quote(la)
        decoded = text_(la, 'utf-8')
        path = '/'.join([encoded, encoded])
        result = self._callFUT(path)
        self.assertEqual(result, (decoded, decoded))

    def test_utf16(self):
        from pyramid.exceptions import URLDecodeError
        la = text_(b'La Pe\xc3\xb1a', 'utf-8').encode('utf-16')
        encoded = url_quote(la)
        path = '/'.join([encoded, encoded])
        self.assertRaises(URLDecodeError, self._callFUT, path)

    def test_unicode_highorder_chars(self):
        path = text_('/%E6%B5%81%E8%A1%8C%E8%B6%8B%E5%8A%BF')
        self.assertEqual(self._callFUT(path),
                         (text_('\u6d41\u884c\u8d8b\u52bf', 'unicode_escape'),))

    def test_element_urllquoted(self):
        self.assertEqual(self._callFUT('/foo/space%20thing/bar'),
                         (text_('foo'), text_('space thing'), text_('bar')))

    def test_unicode_undecodeable_to_ascii(self):
        path = text_(b'/La Pe\xc3\xb1a', 'utf-8')
        self.assertRaises(UnicodeEncodeError, self._callFUT, path)

class TraversalPathInfoTests(unittest.TestCase):
    def _callFUT(self, path):
        from pyramid.traversal import traversal_path_info
        return traversal_path_info(path)

    def test_path_startswith_endswith(self):
        self.assertEqual(self._callFUT('/foo/'), (text_('foo'),))

    def test_empty_elements(self):
        self.assertEqual(self._callFUT('foo///'), (text_('foo'),))

    def test_onedot(self):
        self.assertEqual(self._callFUT('foo/./bar'),
                         (text_('foo'), text_('bar')))

    def test_twodots(self):
        self.assertEqual(self._callFUT('foo/../bar'), (text_('bar'),))

    def test_twodots_at_start(self):
        self.assertEqual(self._callFUT('../../bar'), (text_('bar'),))

    def test_segments_are_unicode(self):
        result = self._callFUT('/foo/bar')
        self.assertEqual(type(result[0]), text_type)
        self.assertEqual(type(result[1]), text_type)

    def test_same_value_returned_if_cached(self):
        result1 = self._callFUT('/foo/bar')
        result2 = self._callFUT('/foo/bar')
        self.assertEqual(result1, (text_('foo'), text_('bar')))
        self.assertEqual(result2, (text_('foo'), text_('bar')))

    def test_unicode_simple(self):
        path = text_('/abc')
        self.assertEqual(self._callFUT(path), (text_('abc'),))

    def test_highorder(self):
        la = b'La Pe\xc3\xb1a'
        latin1 = native_(la)
        result = self._callFUT(latin1)
        self.assertEqual(result, (text_(la, 'utf-8'),))

    def test_highorder_undecodeable(self):
        from pyramid.exceptions import URLDecodeError
        la = text_(b'La Pe\xc3\xb1a', 'utf-8')
        notlatin1 = native_(la)
        self.assertRaises(URLDecodeError, self._callFUT, notlatin1)

class ResourceTreeTraverserTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _getTargetClass(self):
        from pyramid.traversal import ResourceTreeTraverser
        return ResourceTreeTraverser

    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def _getEnviron(self, **kw):
        environ = {}
        environ.update(kw)
        return environ

    def test_class_conforms_to_ITraverser(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import ITraverser
        verifyClass(ITraverser, self._getTargetClass())

    def test_instance_conforms_to_ITraverser(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import ITraverser
        context = DummyContext()
        verifyObject(ITraverser, self._makeOne(context))

    def test_call_with_empty_pathinfo(self):
        policy = self._makeOne(None)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info='')
        result = policy(request)
        self.assertEqual(result['context'], None)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], policy.root)
        self.assertEqual(result['virtual_root'], policy.root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_with_pathinfo_KeyError(self):
        policy = self._makeOne(None)
        environ = self._getEnviron()
        request = DummyRequest(environ, toraise=KeyError)
        result = policy(request)
        self.assertEqual(result['context'], None)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], policy.root)
        self.assertEqual(result['virtual_root'], policy.root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_with_pathinfo_highorder(self):
        path = text_(b'/Qu\xc3\xa9bec', 'utf-8')
        foo = DummyContext(None, path)
        root = DummyContext(foo, 'root')
        policy = self._makeOne(root)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info=path)
        result = policy(request)
        self.assertEqual(result['context'], foo)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], (path[1:],))
        self.assertEqual(result['root'], policy.root)
        self.assertEqual(result['virtual_root'], policy.root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_pathel_with_no_getitem(self):
        policy = self._makeOne(None)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info=text_('/foo/bar'))
        result = policy(request)
        self.assertEqual(result['context'], None)
        self.assertEqual(result['view_name'], 'foo')
        self.assertEqual(result['subpath'], ('bar',))
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], policy.root)
        self.assertEqual(result['virtual_root'], policy.root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_withconn_getitem_emptypath_nosubpath(self):
        root = DummyContext()
        policy = self._makeOne(root)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info=text_(''))
        result = policy(request)
        self.assertEqual(result['context'], root)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_withconn_getitem_withpath_nosubpath(self):
        foo = DummyContext()
        root = DummyContext(foo)
        policy = self._makeOne(root)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info=text_('/foo/bar'))
        result = policy(request)
        self.assertEqual(result['context'], foo)
        self.assertEqual(result['view_name'], 'bar')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], (text_('foo'),))
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_withconn_getitem_withpath_withsubpath(self):
        foo = DummyContext()
        root = DummyContext(foo)
        policy = self._makeOne(root)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info=text_('/foo/bar/baz/buz'))
        result = policy(request)
        self.assertEqual(result['context'], foo)
        self.assertEqual(result['view_name'], 'bar')
        self.assertEqual(result['subpath'], ('baz', 'buz'))
        self.assertEqual(result['traversed'], (text_('foo'),))
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_with_explicit_viewname(self):
        foo = DummyContext()
        root = DummyContext(foo)
        policy = self._makeOne(root)
        environ = self._getEnviron()
        request = DummyRequest(environ, path_info=text_('/@@foo'))
        result = policy(request)
        self.assertEqual(result['context'], root)
        self.assertEqual(result['view_name'], 'foo')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_with_vh_root(self):
        environ = self._getEnviron(HTTP_X_VHM_ROOT='/foo/bar')
        baz = DummyContext(None, 'baz')
        bar = DummyContext(baz, 'bar')
        foo = DummyContext(bar, 'foo')
        root = DummyContext(foo, 'root')
        policy = self._makeOne(root)
        request = DummyRequest(environ, path_info=text_('/baz'))
        result = policy(request)
        self.assertEqual(result['context'], baz)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'],
                         (text_('foo'), text_('bar'), text_('baz')))
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], bar)
        self.assertEqual(result['virtual_root_path'],
                         (text_('foo'), text_('bar')))

    def test_call_with_vh_root2(self):
        environ = self._getEnviron(HTTP_X_VHM_ROOT='/foo')
        baz = DummyContext(None, 'baz')
        bar = DummyContext(baz, 'bar')
        foo = DummyContext(bar, 'foo')
        root = DummyContext(foo, 'root')
        policy = self._makeOne(root)
        request = DummyRequest(environ, path_info=text_('/bar/baz'))
        result = policy(request)
        self.assertEqual(result['context'], baz)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'],
                         (text_('foo'), text_('bar'), text_('baz')))
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], foo)
        self.assertEqual(result['virtual_root_path'], (text_('foo'),))

    def test_call_with_vh_root3(self):
        environ = self._getEnviron(HTTP_X_VHM_ROOT='/')
        baz = DummyContext()
        bar = DummyContext(baz)
        foo = DummyContext(bar)
        root = DummyContext(foo)
        policy = self._makeOne(root)
        request = DummyRequest(environ, path_info=text_('/foo/bar/baz'))
        result = policy(request)
        self.assertEqual(result['context'], baz)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'],
                         (text_('foo'), text_('bar'), text_('baz')))
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_with_vh_root4(self):
        environ = self._getEnviron(HTTP_X_VHM_ROOT='/foo/bar/baz')
        baz = DummyContext(None, 'baz')
        bar = DummyContext(baz, 'bar')
        foo = DummyContext(bar, 'foo')
        root = DummyContext(foo, 'root')
        policy = self._makeOne(root)
        request = DummyRequest(environ, path_info=text_('/'))
        result = policy(request)
        self.assertEqual(result['context'], baz)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'],
                         (text_('foo'), text_('bar'), text_('baz')))
        self.assertEqual(result['root'], root)
        self.assertEqual(result['virtual_root'], baz)
        self.assertEqual(result['virtual_root_path'],
                         (text_('foo'), text_('bar'), text_('baz')))

    def test_call_with_vh_root_path_root(self):
        policy = self._makeOne(None)
        environ = self._getEnviron(HTTP_X_VHM_ROOT='/')
        request = DummyRequest(environ, path_info=text_('/'))
        result = policy(request)
        self.assertEqual(result['context'], None)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], policy.root)
        self.assertEqual(result['virtual_root'], policy.root)
        self.assertEqual(result['virtual_root_path'], ())

    def test_call_with_vh_root_highorder(self):
        path = text_(b'Qu\xc3\xa9bec', 'utf-8')
        bar = DummyContext(None, 'bar')
        foo = DummyContext(bar, path)
        root = DummyContext(foo, 'root')
        policy = self._makeOne(root)
        if PY2:
            vhm_root = b'/Qu\xc3\xa9bec'
        else:
            vhm_root = b'/Qu\xc3\xa9bec'.decode('latin-1')
        environ = self._getEnviron(HTTP_X_VHM_ROOT=vhm_root)
        request = DummyRequest(environ, path_info=text_('/bar'))
        result = policy(request)
        self.assertEqual(result['context'], bar)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(
            result['traversed'],
            (path, text_('bar'))
            )
        self.assertEqual(result['root'], policy.root)
        self.assertEqual(result['virtual_root'], foo)
        self.assertEqual(
            result['virtual_root_path'],
            (path,)
            )

    def test_path_info_raises_unicodedecodeerror(self):
        from pyramid.exceptions import URLDecodeError
        foo = DummyContext()
        root = DummyContext(foo)
        policy = self._makeOne(root)
        environ = self._getEnviron()
        toraise = UnicodeDecodeError('ascii', b'a', 2, 3, '5')
        request = DummyRequest(environ, toraise=toraise)
        request.matchdict = None
        self.assertRaises(URLDecodeError, policy, request)

    def test_withroute_nothingfancy(self):
        resource = DummyContext()
        traverser = self._makeOne(resource)
        request = DummyRequest({})
        request.matchdict = {}
        result = traverser(request)
        self.assertEqual(result['context'], resource)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], resource)
        self.assertEqual(result['virtual_root_path'], ())

    def test_withroute_with_subpath_string(self):
        resource = DummyContext()
        traverser = self._makeOne(resource)
        matchdict = {'subpath':'/a/b/c'}
        request = DummyRequest({})
        request.matchdict = matchdict
        result = traverser(request)
        self.assertEqual(result['context'], resource)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ('a', 'b','c'))
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], resource)
        self.assertEqual(result['virtual_root_path'], ())

    def test_withroute_with_subpath_tuple(self):
        resource = DummyContext()
        traverser = self._makeOne(resource)
        matchdict = {'subpath':('a', 'b', 'c')}
        request = DummyRequest({})
        request.matchdict = matchdict
        result = traverser(request)
        self.assertEqual(result['context'], resource)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ('a', 'b','c'))
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], resource)
        self.assertEqual(result['virtual_root_path'], ())

    def test_withroute_and_traverse_string(self):
        resource = DummyContext()
        traverser = self._makeOne(resource)
        matchdict =  {'traverse':text_('foo/bar')}
        request = DummyRequest({})
        request.matchdict = matchdict
        result = traverser(request)
        self.assertEqual(result['context'], resource)
        self.assertEqual(result['view_name'], 'foo')
        self.assertEqual(result['subpath'], ('bar',))
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], resource)
        self.assertEqual(result['virtual_root_path'], ())

    def test_withroute_and_traverse_tuple(self):
        resource = DummyContext()
        traverser = self._makeOne(resource)
        matchdict = {'traverse':('foo', 'bar')}
        request = DummyRequest({})
        request.matchdict = matchdict
        result = traverser(request)
        self.assertEqual(result['context'], resource)
        self.assertEqual(result['view_name'], 'foo')
        self.assertEqual(result['subpath'], ('bar',))
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], resource)
        self.assertEqual(result['virtual_root_path'], ())

    def test_withroute_and_traverse_empty(self):
        resource = DummyContext()
        traverser = self._makeOne(resource)
        matchdict = {'traverse':''}
        request = DummyRequest({})
        request.matchdict = matchdict
        result = traverser(request)
        self.assertEqual(result['context'], resource)
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['subpath'], ())
        self.assertEqual(result['traversed'], ())
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], resource)
        self.assertEqual(result['virtual_root_path'], ())

    def test_withroute_and_traverse_and_vroot(self):
        abc = DummyContext()
        resource = DummyContext(next=abc)
        environ = self._getEnviron(HTTP_X_VHM_ROOT='/abc')
        request = DummyRequest(environ)
        traverser = self._makeOne(resource)
        matchdict =  {'traverse':text_('/foo/bar')}
        request.matchdict = matchdict
        result = traverser(request)
        self.assertEqual(result['context'], abc)
        self.assertEqual(result['view_name'], 'foo')
        self.assertEqual(result['subpath'], ('bar',))
        self.assertEqual(result['traversed'], ('abc', 'foo'))
        self.assertEqual(result['root'], resource)
        self.assertEqual(result['virtual_root'], abc)
        self.assertEqual(result['virtual_root_path'], ('abc',))
        
class FindInterfaceTests(unittest.TestCase):
    def _callFUT(self, context, iface):
        from pyramid.traversal import find_interface
        return find_interface(context, iface)

    def test_it_interface(self):
        baz = DummyContext()
        bar = DummyContext(baz)
        foo = DummyContext(bar)
        root = DummyContext(foo)
        root.__parent__ = None
        root.__name__ = 'root'
        foo.__parent__ = root
        foo.__name__ = 'foo'
        bar.__parent__ = foo
        bar.__name__ = 'bar'
        baz.__parent__ = bar
        baz.__name__ = 'baz'
        from zope.interface import directlyProvides
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        directlyProvides(root, IFoo)
        result = self._callFUT(baz, IFoo)
        self.assertEqual(result.__name__, 'root')

    def test_it_class(self):
        class DummyRoot(object):
            def __init__(self, child):
                self.child = child
        baz = DummyContext()
        bar = DummyContext(baz)
        foo = DummyContext(bar)
        root = DummyRoot(foo)
        root.__parent__ = None
        root.__name__ = 'root'
        foo.__parent__ = root
        foo.__name__ = 'foo'
        bar.__parent__ = foo
        bar.__name__ = 'bar'
        baz.__parent__ = bar
        baz.__name__ = 'baz'
        result = self._callFUT(baz, DummyRoot)
        self.assertEqual(result.__name__, 'root')

class FindRootTests(unittest.TestCase):
    def _callFUT(self, context):
        from pyramid.traversal import find_root
        return find_root(context)

    def test_it(self):
        dummy = DummyContext()
        baz = DummyContext()
        baz.__parent__ = dummy
        baz.__name__ = 'baz'
        dummy.__parent__ = None
        dummy.__name__ = None
        result = self._callFUT(baz)
        self.assertEqual(result, dummy)

class FindResourceTests(unittest.TestCase):
    def _callFUT(self, context, name):
        from pyramid.traversal import find_resource
        return find_resource(context, name)

    def _registerTraverser(self, traverser):
        from pyramid.threadlocal import get_current_registry
        reg = get_current_registry()
        from pyramid.interfaces import ITraverser
        from zope.interface import Interface
        reg.registerAdapter(traverser, (Interface,), ITraverser)

    def test_list(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, [''])
        self.assertEqual(result, resource)
        self.assertEqual(resource.request.environ['PATH_INFO'], '/')

    def test_generator(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        def foo():
            yield ''
        result = self._callFUT(resource, foo())
        self.assertEqual(result, resource)
        self.assertEqual(resource.request.environ['PATH_INFO'], '/')

    def test_self_string_found(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, '')
        self.assertEqual(result, resource)
        self.assertEqual(resource.request.environ['PATH_INFO'], '')

    def test_self_tuple_found(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, ())
        self.assertEqual(result, resource)
        self.assertEqual(resource.request.environ['PATH_INFO'], '')

    def test_relative_string_found(self):
        resource = DummyContext()
        baz = DummyContext()
        traverser = make_traverser({'context':baz, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, 'baz')
        self.assertEqual(result, baz)
        self.assertEqual(resource.request.environ['PATH_INFO'], 'baz')

    def test_relative_tuple_found(self):
        resource = DummyContext()
        baz = DummyContext()
        traverser = make_traverser({'context':baz, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, ('baz',))
        self.assertEqual(result, baz)
        self.assertEqual(resource.request.environ['PATH_INFO'], 'baz')

    def test_relative_string_notfound(self):
        resource = DummyContext()
        baz = DummyContext()
        traverser = make_traverser({'context':baz, 'view_name':'bar'})
        self._registerTraverser(traverser)
        self.assertRaises(KeyError, self._callFUT, resource, 'baz')
        self.assertEqual(resource.request.environ['PATH_INFO'], 'baz')

    def test_relative_tuple_notfound(self):
        resource = DummyContext()
        baz = DummyContext()
        traverser = make_traverser({'context':baz, 'view_name':'bar'})
        self._registerTraverser(traverser)
        self.assertRaises(KeyError, self._callFUT, resource, ('baz',))
        self.assertEqual(resource.request.environ['PATH_INFO'], 'baz')

    def test_absolute_string_found(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, '/')
        self.assertEqual(result, root)
        self.assertEqual(root.wascontext, True)
        self.assertEqual(root.request.environ['PATH_INFO'], '/')

    def test_absolute_tuple_found(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':''})
        self._registerTraverser(traverser)
        result = self._callFUT(resource, ('',))
        self.assertEqual(result, root)
        self.assertEqual(root.wascontext, True)
        self.assertEqual(root.request.environ['PATH_INFO'], '/')

    def test_absolute_string_notfound(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':'fuz'})
        self._registerTraverser(traverser)
        self.assertRaises(KeyError, self._callFUT, resource, '/')
        self.assertEqual(root.wascontext, True)
        self.assertEqual(root.request.environ['PATH_INFO'], '/')

    def test_absolute_tuple_notfound(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':'fuz'})
        self._registerTraverser(traverser)
        self.assertRaises(KeyError, self._callFUT, resource, ('',))
        self.assertEqual(root.wascontext, True)
        self.assertEqual(root.request.environ['PATH_INFO'], '/')

    def test_absolute_unicode_found(self):
        # test for bug wiggy found in wild, traceback stack:
        # root = u'/%E6%B5%81%E8%A1%8C%E8%B6%8B%E5%8A%BF'
        # wiggy's code: section=find_resource(page, root)
        # find_resource L76: D = traverse(resource, path)
        # traverse L291: return traverser(request)
        # __call__ line 568: vpath_tuple = traversal_path(vpath)
        # lru_cached line 91: f(*arg)
        # traversal_path line 443: path.encode('ascii')
        # UnicodeEncodeError: 'ascii' codec can't encode characters in
        #     position 1-12: ordinal not in range(128)
        #
        # solution: encode string to ascii in pyramid.traversal.traverse
        # before passing it along to webob as path_info
        from pyramid.traversal import ResourceTreeTraverser
        unprintable = DummyContext()
        root = DummyContext(unprintable)
        unprintable.__parent__ = root
        unprintable.__name__ = text_(
            b'/\xe6\xb5\x81\xe8\xa1\x8c\xe8\xb6\x8b\xe5\x8a\xbf', 'utf-8')
        root.__parent__ = None
        root.__name__ = None
        traverser = ResourceTreeTraverser
        self._registerTraverser(traverser)
        result = self._callFUT(
            root,
            text_(b'/%E6%B5%81%E8%A1%8C%E8%B6%8B%E5%8A%BF')
            )
        self.assertEqual(result, unprintable)

class ResourcePathTests(unittest.TestCase):
    def _callFUT(self, resource, *elements):
        from pyramid.traversal import resource_path
        return resource_path(resource, *elements)

    def test_it(self):
        baz = DummyContext()
        bar = DummyContext(baz)
        foo = DummyContext(bar)
        root = DummyContext(foo)
        root.__parent__ = None
        root.__name__ = None
        foo.__parent__ = root
        foo.__name__ = 'foo '
        bar.__parent__ = foo
        bar.__name__ = 'bar'
        baz.__parent__ = bar
        baz.__name__ = 'baz'
        result = self._callFUT(baz, 'this/theotherthing', 'that')
        self.assertEqual(result, '/foo%20/bar/baz/this%2Ftheotherthing/that')

    def test_root_default(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        result = self._callFUT(root)
        self.assertEqual(result, '/')

    def test_root_default_emptystring(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = ''
        result = self._callFUT(root)
        self.assertEqual(result, '/')

    def test_root_object_nonnull_name_direct(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = 'flubadub'
        result = self._callFUT(root)
        self.assertEqual(result, 'flubadub') # insane case

    def test_root_object_nonnull_name_indirect(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = 'flubadub'
        other = DummyContext()
        other.__parent__ = root
        other.__name__ = 'barker'
        result = self._callFUT(other)
        self.assertEqual(result, 'flubadub/barker') # insane case

    def test_nonroot_default(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        other = DummyContext()
        other.__parent__ = root
        other.__name__ = 'other'
        result = self._callFUT(other)
        self.assertEqual(result, '/other')

    def test_path_with_None_itermediate_names(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        other = DummyContext()
        other.__parent__ = root
        other.__name__ = None
        other2 = DummyContext()
        other2.__parent__ = other
        other2.__name__ = 'other2'
        result = self._callFUT(other2)
        self.assertEqual(result, '//other2')

class ResourcePathTupleTests(unittest.TestCase):
    def _callFUT(self, resource, *elements):
        from pyramid.traversal import resource_path_tuple
        return resource_path_tuple(resource, *elements)

    def test_it(self):
        baz = DummyContext()
        bar = DummyContext(baz)
        foo = DummyContext(bar)
        root = DummyContext(foo)
        root.__parent__ = None
        root.__name__ = None
        foo.__parent__ = root
        foo.__name__ = 'foo '
        bar.__parent__ = foo
        bar.__name__ = 'bar'
        baz.__parent__ = bar
        baz.__name__ = 'baz'
        result = self._callFUT(baz, 'this/theotherthing', 'that')
        self.assertEqual(result, ('','foo ', 'bar', 'baz', 'this/theotherthing',
                                  'that'))

    def test_root_default(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        result = self._callFUT(root)
        self.assertEqual(result, ('',))

    def test_root_default_emptystring_name(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = ''
        other = DummyContext()
        other.__parent__ = root
        other.__name__ = 'other'
        result = self._callFUT(other)
        self.assertEqual(result, ('', 'other',))

    def test_nonroot_default(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        other = DummyContext()
        other.__parent__ = root
        other.__name__ = 'other'
        result = self._callFUT(other)
        self.assertEqual(result, ('', 'other'))

    def test_path_with_None_itermediate_names(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        other = DummyContext()
        other.__parent__ = root
        other.__name__ = None
        other2 = DummyContext()
        other2.__parent__ = other
        other2.__name__ = 'other2'
        result = self._callFUT(other2)
        self.assertEqual(result, ('', '', 'other2'))

class QuotePathSegmentTests(unittest.TestCase):
    def _callFUT(self, s):
        from pyramid.traversal import quote_path_segment
        return quote_path_segment(s)

    def test_unicode(self):
        la = text_(b'/La Pe\xc3\xb1a', 'utf-8')
        result = self._callFUT(la)
        self.assertEqual(result, '%2FLa%20Pe%C3%B1a')

    def test_string(self):
        s = '/ hello!'
        result = self._callFUT(s)
        self.assertEqual(result, '%2F%20hello%21')

    def test_int(self):
        s = 12345
        result = self._callFUT(s)
        self.assertEqual(result, '12345')
        
    def test_long(self):
        from pyramid.compat import long
        import sys
        s = long(sys.maxsize + 1)
        result = self._callFUT(s)
        expected = str(s)
        self.assertEqual(result, expected)

    def test_other(self):
        class Foo(object):
            def __str__(self):
                return 'abc'
        s = Foo()
        result = self._callFUT(s)
        self.assertEqual(result, 'abc')

class ResourceURLTests(unittest.TestCase):
    def _makeOne(self, context, url):
        return self._getTargetClass()(context, url)

    def _getTargetClass(self):
        from pyramid.traversal import ResourceURL
        return ResourceURL

    def _registerTraverser(self, traverser):
        from pyramid.threadlocal import get_current_registry
        reg = get_current_registry()
        from pyramid.interfaces import ITraverser
        from zope.interface import Interface
        reg.registerAdapter(traverser, (Interface,), ITraverser)

    def test_class_conforms_to_IContextURL(self):
        # bw compat
        from zope.interface.verify import verifyClass
        verifyClass(IContextURL, self._getTargetClass())

    def test_instance_conforms_to_IContextURL(self):
        from zope.interface.verify import verifyObject
        context = DummyContext()
        request = DummyRequest()
        verifyObject(IContextURL, self._makeOne(context, request))

    def test_instance_conforms_to_IResourceURL(self):
        from pyramid.interfaces import IResourceURL
        from zope.interface.verify import verifyObject
        context = DummyContext()
        request = DummyRequest()
        verifyObject(IResourceURL, self._makeOne(context, request))
        
    def test_call_withlineage(self):
        baz = DummyContext()
        bar = DummyContext(baz)
        foo = DummyContext(bar)
        root = DummyContext(foo)
        root.__parent__ = None
        root.__name__ = None
        foo.__parent__ = root
        foo.__name__ = 'foo '
        bar.__parent__ = foo
        bar.__name__ = 'bar'
        baz.__parent__ = bar
        baz.__name__ = 'baz'
        request = DummyRequest()
        context_url = self._makeOne(baz, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432/foo%20/bar/baz/')

    def test_call_nolineage(self):
        context = DummyContext()
        context.__name__ = ''
        context.__parent__ = None
        request = DummyRequest()
        context_url = self._makeOne(context, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432/')

    def test_call_unicode_mixed_with_bytes_in_resource_names(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        one = DummyContext()
        one.__parent__ = root
        one.__name__ = text_(b'La Pe\xc3\xb1a', 'utf-8')
        two = DummyContext()
        two.__parent__ = one
        two.__name__ = b'La Pe\xc3\xb1a'
        request = DummyRequest()
        context_url = self._makeOne(two, request)
        result = context_url()
        self.assertEqual(
            result,
            'http://example.com:5432/La%20Pe%C3%B1a/La%20Pe%C3%B1a/')

    def test_call_with_virtual_root_path(self):
        from pyramid.interfaces import VH_ROOT_KEY
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        one = DummyContext()
        one.__parent__ = root
        one.__name__ = 'one'
        two = DummyContext()
        two.__parent__ = one
        two.__name__ = 'two'
        request = DummyRequest({VH_ROOT_KEY:'/one'})
        context_url = self._makeOne(two, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432/two/')

        request = DummyRequest({VH_ROOT_KEY:'/one/two'})
        context_url = self._makeOne(two, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432/')

    def test_call_with_virtual_root_path_physical_not_startwith_vroot(self):
        from pyramid.interfaces import VH_ROOT_KEY
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        one = DummyContext()
        one.__parent__ = root
        one.__name__ = 'one'
        two = DummyContext()
        two.__parent__ = one
        two.__name__ = 'two'
        request = DummyRequest({VH_ROOT_KEY:'/wrong'})
        context_url = self._makeOne(two, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432/one/two/')

    def test_call_empty_names_not_ignored(self):
        bar = DummyContext()
        empty = DummyContext(bar)
        root = DummyContext(empty)
        root.__parent__ = None
        root.__name__ = None
        empty.__parent__ = root
        empty.__name__ = ''
        bar.__parent__ = empty
        bar.__name__ = 'bar'
        request = DummyRequest()
        context_url = self._makeOne(bar, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432//bar/')

    def test_call_local_url_returns_None(self):
        resource = DummyContext()
        def resource_url(request, info):
            self.assertEqual(info['virtual_path'], '/')
            self.assertEqual(info['physical_path'], '/')
            return None
        resource.__resource_url__ = resource_url
        request = DummyRequest()
        context_url = self._makeOne(resource, request)
        result = context_url()
        self.assertEqual(result, 'http://example.com:5432/')
        
    def test_call_local_url_returns_url(self):
        resource = DummyContext()
        def resource_url(request, info):
            self.assertEqual(info['virtual_path'], '/')
            self.assertEqual(info['physical_path'], '/')
            return 'abc'
        resource.__resource_url__ = resource_url
        request = DummyRequest()
        context_url = self._makeOne(resource, request)
        result = context_url()
        self.assertEqual(result, 'abc')

    def test_virtual_root_no_virtual_root_path(self):
        root = DummyContext()
        root.__name__ = None
        root.__parent__ = None
        one = DummyContext()
        one.__name__ = 'one'
        one.__parent__ = root
        request = DummyRequest()
        context_url = self._makeOne(one, request)
        self.assertEqual(context_url.virtual_root(), root)

    def test_virtual_root_no_virtual_root_path_with_root_on_request(self):
        context = DummyContext()
        context.__parent__ = None
        request = DummyRequest()
        request.root = DummyContext()
        context_url = self._makeOne(context, request)
        self.assertEqual(context_url.virtual_root(), request.root)

    def test_virtual_root_with_virtual_root_path(self):
        from pyramid.interfaces import VH_ROOT_KEY
        context = DummyContext()
        context.__parent__ = None
        traversed_to = DummyContext()
        environ = {VH_ROOT_KEY:'/one'}
        request = DummyRequest(environ)
        traverser = make_traverser({'context':traversed_to, 'view_name':''})
        self._registerTraverser(traverser)
        context_url = self._makeOne(context, request)
        self.assertEqual(context_url.virtual_root(), traversed_to)
        self.assertEqual(context.request.environ['PATH_INFO'], '/one')

    def test_IResourceURL_attributes_with_vroot(self):
        from pyramid.interfaces import VH_ROOT_KEY
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        one = DummyContext()
        one.__parent__ = root
        one.__name__ = 'one'
        two = DummyContext()
        two.__parent__ = one
        two.__name__ = 'two'
        environ = {VH_ROOT_KEY:'/one'}
        request = DummyRequest(environ)
        context_url = self._makeOne(two, request)
        self.assertEqual(context_url.physical_path, '/one/two/')
        self.assertEqual(context_url.virtual_path, '/two/')
        self.assertEqual(context_url.physical_path_tuple, ('', 'one', 'two',''))
        self.assertEqual(context_url.virtual_path_tuple, ('', 'two', ''))
        
    def test_IResourceURL_attributes_vroot_ends_with_slash(self):
        from pyramid.interfaces import VH_ROOT_KEY
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        one = DummyContext()
        one.__parent__ = root
        one.__name__ = 'one'
        two = DummyContext()
        two.__parent__ = one
        two.__name__ = 'two'
        environ = {VH_ROOT_KEY:'/one/'}
        request = DummyRequest(environ)
        context_url = self._makeOne(two, request)
        self.assertEqual(context_url.physical_path, '/one/two/')
        self.assertEqual(context_url.virtual_path, '/two/')
        self.assertEqual(context_url.physical_path_tuple, ('', 'one', 'two',''))
        self.assertEqual(context_url.virtual_path_tuple, ('', 'two', ''))
        
    def test_IResourceURL_attributes_no_vroot(self):
        root = DummyContext()
        root.__parent__ = None
        root.__name__ = None
        one = DummyContext()
        one.__parent__ = root
        one.__name__ = 'one'
        two = DummyContext()
        two.__parent__ = one
        two.__name__ = 'two'
        environ = {}
        request = DummyRequest(environ)
        context_url = self._makeOne(two, request)
        self.assertEqual(context_url.physical_path, '/one/two/')
        self.assertEqual(context_url.virtual_path, '/one/two/')
        self.assertEqual(context_url.physical_path_tuple, ('', 'one', 'two',''))
        self.assertEqual(context_url.virtual_path_tuple, ('', 'one', 'two', ''))

class TestVirtualRoot(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, resource, request):
        from pyramid.traversal import virtual_root
        return virtual_root(resource, request)

    def test_registered(self):
        from zope.interface import Interface
        request = _makeRequest()
        request.registry.registerAdapter(DummyContextURL, (Interface,Interface),
                                         IContextURL)
        context = DummyContext()
        result = self._callFUT(context, request)
        self.assertEqual(result, '123')

    def test_default(self):
        context = DummyContext()
        request = _makeRequest()
        request.environ['PATH_INFO'] = '/'
        result = self._callFUT(context, request)
        self.assertEqual(result, context)

    def test_default_no_registry_on_request(self):
        context = DummyContext()
        request = _makeRequest()
        del request.registry
        request.environ['PATH_INFO'] = '/'
        result = self._callFUT(context, request)
        self.assertEqual(result, context)

class TraverseTests(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _callFUT(self, context, name):
        from pyramid.traversal import traverse
        return traverse(context, name)

    def _registerTraverser(self, traverser):
        from pyramid.threadlocal import get_current_registry
        reg = get_current_registry()
        from pyramid.interfaces import ITraverser
        from zope.interface import Interface
        reg.registerAdapter(traverser, (Interface,), ITraverser)

    def test_request_has_registry(self):
        from pyramid.threadlocal import get_current_registry
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, [''])
        self.assertEqual(resource.request.registry, get_current_registry())

    def test_list(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, [''])
        self.assertEqual(resource.request.environ['PATH_INFO'], '/')

    def test_generator(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        def foo():
            yield ''
        self._callFUT(resource, foo())
        self.assertEqual(resource.request.environ['PATH_INFO'], '/')

    def test_self_string_found(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, '')
        self.assertEqual(resource.request.environ['PATH_INFO'], '')

    def test_self_unicode_found(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, text_(''))
        self.assertEqual(resource.request.environ['PATH_INFO'], '')

    def test_self_tuple_found(self):
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, ())
        self.assertEqual(resource.request.environ['PATH_INFO'], '')

    def test_relative_string_found(self):
        resource = DummyContext()
        baz = DummyContext()
        traverser = make_traverser({'context':baz, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, 'baz')
        self.assertEqual(resource.request.environ['PATH_INFO'], 'baz')

    def test_relative_tuple_found(self):
        resource = DummyContext()
        baz = DummyContext()
        traverser = make_traverser({'context':baz, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, ('baz',))
        self.assertEqual(resource.request.environ['PATH_INFO'], 'baz')

    def test_absolute_string_found(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, '/')
        self.assertEqual(root.wascontext, True)
        self.assertEqual(root.request.environ['PATH_INFO'], '/')

    def test_absolute_tuple_found(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, ('',))
        self.assertEqual(root.wascontext, True)
        self.assertEqual(root.request.environ['PATH_INFO'], '/')

    def test_empty_sequence(self):
        root = DummyContext()
        resource = DummyContext()
        resource.__parent__ = root
        resource.__name__ = 'baz'
        traverser = make_traverser({'context':root, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, [])
        self.assertEqual(resource.wascontext, True)
        self.assertEqual(resource.request.environ['PATH_INFO'], '')

    def test_default_traverser(self):
        resource = DummyContext()
        result = self._callFUT(resource, '')
        self.assertEqual(result['view_name'], '')
        self.assertEqual(result['context'], resource)

    def test_requestfactory_overridden(self):
        from pyramid.interfaces import IRequestFactory
        from pyramid.request import Request
        from pyramid.threadlocal import get_current_registry
        reg = get_current_registry()
        class MyRequest(Request):
            pass
        reg.registerUtility(MyRequest, IRequestFactory)
        resource = DummyContext()
        traverser = make_traverser({'context':resource, 'view_name':''})
        self._registerTraverser(traverser)
        self._callFUT(resource, [''])
        self.assertEqual(resource.request.__class__, MyRequest)

class TestDefaultRootFactory(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.traversal import DefaultRootFactory
        return DefaultRootFactory

    def _makeOne(self, environ):
        return self._getTargetClass()(environ)

    def test_it(self):
        class DummyRequest(object):
            pass
        root = self._makeOne(DummyRequest())
        self.assertEqual(root.__parent__, None)
        self.assertEqual(root.__name__, None)

class Test__join_path_tuple(unittest.TestCase):
    def _callFUT(self, tup):
        from pyramid.traversal import _join_path_tuple
        return _join_path_tuple(tup)

    def test_empty_tuple(self):
        # tests "or '/'" case
        result = self._callFUT(())
        self.assertEqual(result, '/')

    def test_nonempty_tuple(self):
        result = self._callFUT(('x',))
        self.assertEqual(result, 'x')

def make_traverser(result):
    class DummyTraverser(object):
        def __init__(self, context):
            self.context = context
            context.wascontext = True
        def __call__(self, request):
            self.context.request = request
            return result
    return DummyTraverser

class DummyContext(object):
    __parent__ = None
    def __init__(self, next=None, name=None):
        self.next = next
        self.__name__ = name

    def __getitem__(self, name):
        if self.next is None:
            raise KeyError(name)
        return self.next

    def __repr__(self):
        return '<DummyContext with name %s at id %s>'%(self.__name__, id(self))

class DummyRequest:

    application_url = 'http://example.com:5432' # app_url never ends with slash
    matchdict = None
    matched_route = None

    def __init__(self, environ=None, path_info=text_('/'), toraise=None):
        if environ is None:
            environ = {}
        self.environ = environ
        self._set_path_info(path_info)
        self.toraise = toraise

    def _get_path_info(self):
        if self.toraise:
            raise self.toraise
        return self._path_info

    def _set_path_info(self, v):
        self._path_info = v

    path_info = property(_get_path_info, _set_path_info)
        

class DummyContextURL:
    def __init__(self, context, request):
        pass

    def virtual_root(self):
        return '123'

def _makeRequest(environ=None):
    from pyramid.registry import Registry
    request = DummyRequest()
    request.registry = Registry()
    return request
