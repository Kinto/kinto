import operator

from zope.interface import implementer

from zope.interface.registry import Components

from pyramid.compat import text_

from pyramid.interfaces import (
    ISettings,
    IIntrospector,
    IIntrospectable,
    )

empty = text_('')

class Registry(Components, dict):
    """ A registry object is an :term:`application registry`.  It is used by
    the framework itself to perform mappings of URLs to view callables, as
    well as servicing other various framework duties. A registry has its own
    internal API, but this API is rarely used by Pyramid application
    developers (it's usually only used by developers of the Pyramid
    framework).  But it has a number of attributes that may be useful to
    application developers within application code, such as ``settings``,
    which is a dictionary containing application deployment settings.

    For information about the purpose and usage of the application registry,
    see :ref:`zca_chapter`.

    The application registry is usually accessed as ``request.registry`` in
    application code.

    """

    # for optimization purposes, if no listeners are listening, don't try
    # to notify them
    has_listeners = False

    _settings = None

    def __nonzero__(self):
        # defeat bool determination via dict.__len__
        return True

    def registerSubscriptionAdapter(self, *arg, **kw):
        result = Components.registerSubscriptionAdapter(self, *arg, **kw)
        self.has_listeners = True
        return result

    def registerSelfAdapter(self, required=None, provided=None, name=empty,
                            info=empty, event=True):
        # registerAdapter analogue which always returns the object itself
        # when required is matched
        return self.registerAdapter(lambda x: x, required=required,
                                    provided=provided, name=name,
                                    info=info, event=event)

    def queryAdapterOrSelf(self, object, interface, default=None):
        # queryAdapter analogue which returns the object if it implements
        # the interface, otherwise it will return an adaptation to the
        # interface
        if not interface.providedBy(object):
            return self.queryAdapter(object, interface, default=default)
        return object

    def registerHandler(self, *arg, **kw):
        result = Components.registerHandler(self, *arg, **kw)
        self.has_listeners = True
        return result

    def notify(self, *events):
        if self.has_listeners:
            # iterating over subscribers assures they get executed
            [ _ for _ in self.subscribers(events, None) ]

    # backwards compatibility for code that wants to look up a settings
    # object via ``registry.getUtility(ISettings)``
    def _get_settings(self):
        return self._settings

    def _set_settings(self, settings):
        self.registerUtility(settings, ISettings)
        self._settings = settings

    settings = property(_get_settings, _set_settings)

@implementer(IIntrospector)
class Introspector(object):
    def __init__(self):
        self._refs = {}
        self._categories = {}
        self._counter = 0

    def add(self, intr):
        category = self._categories.setdefault(intr.category_name, {})
        category[intr.discriminator] = intr
        category[intr.discriminator_hash] = intr
        intr.order = self._counter
        self._counter += 1

    def get(self, category_name, discriminator, default=None):
        category = self._categories.setdefault(category_name, {})
        intr = category.get(discriminator, default)
        return intr

    def get_category(self, category_name, default=None, sort_key=None):
        if sort_key is None:
            sort_key = operator.attrgetter('order')
        category = self._categories.get(category_name)
        if category is None:
            return default
        values = category.values()
        values = sorted(set(values), key=sort_key)
        return [
            {'introspectable':intr,
             'related':self.related(intr)}
             for intr in values
             ]

    def categorized(self, sort_key=None):
        L = []
        for category_name in self.categories():
            L.append((category_name, self.get_category(category_name,
                                                       sort_key=sort_key)))
        return L

    def categories(self):
        return sorted(self._categories.keys())

    def remove(self, category_name, discriminator):
        intr = self.get(category_name, discriminator)
        if intr is None:
            return
        L = self._refs.pop(intr, [])
        for d in L:
            L2 = self._refs[d]
            L2.remove(intr)
        category = self._categories[intr.category_name]
        del category[intr.discriminator]
        del category[intr.discriminator_hash]

    def _get_intrs_by_pairs(self, pairs):
        introspectables = []
        for pair in pairs:
            category_name, discriminator = pair
            intr = self._categories.get(category_name, {}).get(discriminator)
            if intr is None:
                raise KeyError((category_name, discriminator))
            introspectables.append(intr)
        return introspectables

    def relate(self, *pairs):
        introspectables = self._get_intrs_by_pairs(pairs)
        relatable = ((x,y) for x in introspectables for y in introspectables)
        for x, y in relatable:
            L = self._refs.setdefault(x, [])
            if x is not y and y not in L:
                L.append(y)

    def unrelate(self, *pairs):
        introspectables = self._get_intrs_by_pairs(pairs)
        relatable = ((x,y) for x in introspectables for y in introspectables)
        for x, y in relatable:
            L = self._refs.get(x, [])
            if y in L:
                L.remove(y)

    def related(self, intr):
        category_name, discriminator = intr.category_name, intr.discriminator
        intr = self._categories.get(category_name, {}).get(discriminator)
        if intr is None:
            raise KeyError((category_name, discriminator))
        return self._refs.get(intr, [])

@implementer(IIntrospectable)
class Introspectable(dict):

    order = 0 # mutated by introspector.add
    action_info = None # mutated by self.register

    def __init__(self, category_name, discriminator, title, type_name):
        self.category_name = category_name
        self.discriminator = discriminator
        self.title = title
        self.type_name = type_name
        self._relations = []

    def relate(self, category_name, discriminator):
        self._relations.append((True, category_name, discriminator))

    def unrelate(self, category_name, discriminator):
        self._relations.append((False, category_name, discriminator))

    def _assert_resolved(self):
        assert undefer(self.discriminator) is self.discriminator

    @property
    def discriminator_hash(self):
        self._assert_resolved()
        return hash(self.discriminator)

    def __hash__(self):
        self._assert_resolved()
        return hash((self.category_name,) + (self.discriminator,))

    def __repr__(self):
        self._assert_resolved()
        return '<%s category %r, discriminator %r>' % (self.__class__.__name__,
                                                       self.category_name,
                                                       self.discriminator)

    def __nonzero__(self):
        return True

    __bool__ = __nonzero__ # py3

    def register(self, introspector, action_info):
        self.discriminator = undefer(self.discriminator)
        self.action_info = action_info
        introspector.add(self)
        for relate, category_name, discriminator in self._relations:
            discriminator = undefer(discriminator)
            if relate:
                method = introspector.relate
            else:
                method = introspector.unrelate
            method(
                (self.category_name, self.discriminator),
                (category_name, discriminator)
                )

class Deferred(object):
    """ Can be used by a third-party configuration extender to wrap a
    :term:`discriminator` during configuration if an immediately hashable
    discriminator cannot be computed because it relies on unresolved values.
    The function should accept no arguments and should return a hashable
    discriminator."""
    def __init__(self, func):
        self.func = func

    def resolve(self):
        return self.func()

def undefer(v):
    """ Function which accepts an object and returns it unless it is a
    :class:`pyramid.registry.Deferred` instance.  If it is an instance of
    that class, its ``resolve`` method is called, and the result of the
    method is returned."""
    if isinstance(v, Deferred):
        v = v.resolve()
    return v

class predvalseq(tuple):
    """ A subtype of tuple used to represent a sequence of predicate values """
    pass

global_registry = Registry('global')
