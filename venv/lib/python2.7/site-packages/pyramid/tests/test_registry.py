import unittest

class TestRegistry(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.registry import Registry
        return Registry
    
    def _makeOne(self):
        return self._getTargetClass()()

    def test___nonzero__(self):
        registry = self._makeOne()
        self.assertEqual(registry.__nonzero__(), True)

    def test_registerHandler_and_notify(self):
        registry = self._makeOne()
        self.assertEqual(registry.has_listeners, False)
        L = []
        def f(event):
            L.append(event)
        registry.registerHandler(f, [IDummyEvent])
        self.assertEqual(registry.has_listeners, True)
        event = DummyEvent()
        registry.notify(event)
        self.assertEqual(L, [event])

    def test_registerSubscriptionAdapter(self):
        registry = self._makeOne()
        self.assertEqual(registry.has_listeners, False)
        from zope.interface import Interface
        registry.registerSubscriptionAdapter(DummyEvent,
                                             [IDummyEvent], Interface)
        self.assertEqual(registry.has_listeners, True)

    def test__get_settings(self):
        registry = self._makeOne()
        registry._settings = 'foo'
        self.assertEqual(registry.settings, 'foo')

    def test__set_settings(self):
        registry = self._makeOne()
        registry.settings = 'foo'
        self.assertEqual(registry._settings, 'foo')

class TestIntrospector(unittest.TestCase):
    def _getTargetClass(slf):
        from pyramid.registry import Introspector
        return Introspector
        
    def _makeOne(self):
        return self._getTargetClass()()

    def test_conformance(self):
        from zope.interface.verify import verifyClass
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IIntrospector
        verifyClass(IIntrospector, self._getTargetClass())
        verifyObject(IIntrospector, self._makeOne())

    def test_add(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        inst.add(intr)
        self.assertEqual(intr.order, 0)
        category = {'discriminator':intr, 'discriminator_hash':intr}
        self.assertEqual(inst._categories, {'category':category})

    def test_get_success(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        inst.add(intr)
        self.assertEqual(inst.get('category', 'discriminator'), intr)

    def test_get_success_byhash(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        inst.add(intr)
        self.assertEqual(inst.get('category', 'discriminator_hash'), intr)

    def test_get_fail(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        inst.add(intr)
        self.assertEqual(inst.get('category', 'wontexist', 'foo'), 'foo')

    def test_get_category(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr2 = DummyIntrospectable()
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        inst.add(intr2)
        inst.add(intr)
        expected = [
            {'introspectable':intr2, 'related':[]},
            {'introspectable':intr,  'related':[]},
            ]
        self.assertEqual(inst.get_category('category'), expected)

    def test_get_category_returns_default_on_miss(self):
        inst = self._makeOne()
        self.assertEqual(inst.get_category('category', '123'), '123')

    def test_get_category_with_sortkey(self):
        import operator
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr.foo = 2
        intr2 = DummyIntrospectable()
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        intr2.foo = 1
        inst.add(intr)
        inst.add(intr2)
        expected = [
            {'introspectable':intr2, 'related':[]},
            {'introspectable':intr,  'related':[]},
            ]
        self.assertEqual(
            inst.get_category('category', sort_key=operator.attrgetter('foo')),
                              expected)

    def test_categorized(self):
        import operator
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr.foo = 2
        intr2 = DummyIntrospectable()
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        intr2.foo = 1
        inst.add(intr)
        inst.add(intr2)
        expected = [('category', [
            {'introspectable':intr2, 'related':[]},
            {'introspectable':intr,  'related':[]},
            ])]
        self.assertEqual(
            inst.categorized(sort_key=operator.attrgetter('foo')), expected)

    def test_categories(self):
        inst = self._makeOne()
        inst._categories['a'] = 1
        inst._categories['b'] = 2
        self.assertEqual(list(inst.categories()), ['a', 'b'])

    def test_remove(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr2 = DummyIntrospectable()
        intr2.category_name = 'category2'
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        inst.add(intr)
        inst.add(intr2)
        inst.relate(('category', 'discriminator'),
                    ('category2', 'discriminator2'))
        inst.remove('category', 'discriminator')
        self.assertEqual(inst._categories,
                         {'category':
                              {},
                          'category2':
                              {'discriminator2': intr2,
                               'discriminator2_hash': intr2}
                         })
        self.assertEqual(inst._refs.get(intr), None)
        self.assertEqual(inst._refs[intr2], [])

    def test_remove_fail(self):
        inst = self._makeOne()
        self.assertEqual(inst.remove('a', 'b'), None)

    def test_relate(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr2 = DummyIntrospectable()
        intr2.category_name = 'category2'
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        inst.add(intr)
        inst.add(intr2)
        inst.relate(('category', 'discriminator'),
                    ('category2', 'discriminator2'))
        self.assertEqual(inst._categories,
                         {'category':
                              {'discriminator':intr,
                               'discriminator_hash':intr},
                          'category2':
                              {'discriminator2': intr2,
                               'discriminator2_hash': intr2}
                         })
        self.assertEqual(inst._refs[intr], [intr2])
        self.assertEqual(inst._refs[intr2], [intr])

    def test_relate_fail(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        inst.add(intr)
        self.assertRaises(
            KeyError,
            inst.relate,
            ('category', 'discriminator'),
            ('category2', 'discriminator2')
            )

    def test_unrelate(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr2 = DummyIntrospectable()
        intr2.category_name = 'category2'
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        inst.add(intr)
        inst.add(intr2)
        inst.relate(('category', 'discriminator'),
                    ('category2', 'discriminator2'))
        inst.unrelate(('category', 'discriminator'),
                    ('category2', 'discriminator2'))
        self.assertEqual(inst._categories,
                         {'category':
                              {'discriminator':intr,
                               'discriminator_hash':intr},
                          'category2':
                              {'discriminator2': intr2,
                               'discriminator2_hash': intr2}
                         })
        self.assertEqual(inst._refs[intr], [])
        self.assertEqual(inst._refs[intr2], [])

    def test_related(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr2 = DummyIntrospectable()
        intr2.category_name = 'category2'
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        inst.add(intr)
        inst.add(intr2)
        inst.relate(('category', 'discriminator'),
                    ('category2', 'discriminator2'))
        self.assertEqual(inst.related(intr), [intr2])

    def test_related_fail(self):
        inst = self._makeOne()
        intr = DummyIntrospectable()
        intr2 = DummyIntrospectable()
        intr2.category_name = 'category2'
        intr2.discriminator = 'discriminator2'
        intr2.discriminator_hash = 'discriminator2_hash'
        inst.add(intr)
        inst.add(intr2)
        inst.relate(('category', 'discriminator'),
                    ('category2', 'discriminator2'))
        del inst._categories['category']
        self.assertRaises(KeyError, inst.related, intr)

class TestIntrospectable(unittest.TestCase):
    def _getTargetClass(slf):
        from pyramid.registry import Introspectable
        return Introspectable
        
    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def _makeOnePopulated(self):
        return self._makeOne('category', 'discrim', 'title', 'type')

    def test_conformance(self):
        from zope.interface.verify import verifyClass
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IIntrospectable
        verifyClass(IIntrospectable, self._getTargetClass())
        verifyObject(IIntrospectable, self._makeOnePopulated())

    def test_relate(self):
        inst = self._makeOnePopulated()
        inst.relate('a', 'b')
        self.assertEqual(inst._relations, [(True, 'a', 'b')])

    def test_unrelate(self):
        inst = self._makeOnePopulated()
        inst.unrelate('a', 'b')
        self.assertEqual(inst._relations, [(False, 'a', 'b')])

    def test_discriminator_hash(self):
        inst = self._makeOnePopulated()
        self.assertEqual(inst.discriminator_hash, hash(inst.discriminator))

    def test___hash__(self):
        inst = self._makeOnePopulated()
        self.assertEqual(hash(inst),
                         hash((inst.category_name,) + (inst.discriminator,)))

    def test___repr__(self):
        inst = self._makeOnePopulated()
        self.assertEqual(
            repr(inst),
            "<Introspectable category 'category', discriminator 'discrim'>")

    def test___nonzero__(self):
        inst = self._makeOnePopulated()
        self.assertEqual(inst.__nonzero__(), True)

    def test___bool__(self):
        inst = self._makeOnePopulated()
        self.assertEqual(inst.__bool__(), True)

    def test_register(self):
        introspector = DummyIntrospector()
        action_info = object()
        inst = self._makeOnePopulated()
        inst._relations.append((True, 'category1', 'discrim1'))
        inst._relations.append((False, 'category2', 'discrim2'))
        inst.register(introspector, action_info)
        self.assertEqual(inst.action_info, action_info)
        self.assertEqual(introspector.intrs, [inst])
        self.assertEqual(introspector.relations,
                         [(('category', 'discrim'), ('category1', 'discrim1'))])
        self.assertEqual(introspector.unrelations,
                         [(('category', 'discrim'), ('category2', 'discrim2'))])

class DummyIntrospector(object):
    def __init__(self):
        self.intrs = []
        self.relations = []
        self.unrelations = []
            
    def add(self, intr):
        self.intrs.append(intr)

    def relate(self, *pairs):
        self.relations.append(pairs)

    def unrelate(self, *pairs):
        self.unrelations.append(pairs)

class DummyModule:
    __path__ = "foo"
    __name__ = "dummy"
    __file__ = ''

class DummyIntrospectable(object):
    category_name = 'category'
    discriminator = 'discriminator'
    title = 'title'
    type_name = 'type'
    order = None
    action_info = None
    discriminator_hash = 'discriminator_hash'

    def __hash__(self):
        return hash((self.category_name,) + (self.discriminator,))


from zope.interface import Interface
from zope.interface import implementer
class IDummyEvent(Interface):
    pass

@implementer(IDummyEvent)
class DummyEvent(object):
    pass
    
