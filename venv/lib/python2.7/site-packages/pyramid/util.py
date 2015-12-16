import functools
import inspect
import traceback
import weakref

from zope.interface import implementer

from pyramid.exceptions import (
    ConfigurationError,
    CyclicDependencyError,
    )

from pyramid.compat import (
    iteritems_,
    is_nonstr_iter,
    integer_types,
    string_types,
    text_,
    PY3,
    )

from pyramid.interfaces import IActionInfo
from pyramid.path import DottedNameResolver as _DottedNameResolver

class DottedNameResolver(_DottedNameResolver):
    def __init__(self, package=None): # default to package = None for bw compat
        return _DottedNameResolver.__init__(self, package)

_marker = object()

class InstancePropertyMixin(object):
    """ Mixin that will allow an instance to add properties at
    run-time as if they had been defined via @property or @reify
    on the class itself.
    """

    @classmethod
    def _make_property(cls, callable, name=None, reify=False):
        """ Convert a callable into one suitable for adding to the
        instance. This will return a 2-tuple containing the computed
        (name, property) pair.
        """

        is_property = isinstance(callable, property)
        if is_property:
            fn = callable
            if name is None:
                raise ValueError('must specify "name" for a property')
            if reify:
                raise ValueError('cannot reify a property')
        elif name is not None:
            fn = lambda this: callable(this)
            fn.__name__ = name
            fn.__doc__ = callable.__doc__
        else:
            name = callable.__name__
            fn = callable
        if reify:
            import pyramid.decorator # avoid circular import
            fn = pyramid.decorator.reify(fn)
        elif not is_property:
            fn = property(fn)

        return name, fn

    def _set_properties(self, properties):
        """ Create several properties on the instance at once.

        This is a more efficient version of
        :meth:`pyramid.util.InstancePropertyMixin.set_property` which
        can accept multiple ``(name, property)`` pairs generated via
        :meth:`pyramid.util.InstancePropertyMixin._make_property`.

        ``properties`` is a sequence of two-tuples *or* a data structure
        with an ``.items()`` method which returns a sequence of two-tuples
        (presumably a dictionary). It will be used to add several
        properties to the instance in a manner that is more efficient
        than simply calling ``set_property`` repeatedly.
        """
        attrs = dict(properties)

        if attrs:
            parent = self.__class__
            cls = type(parent.__name__, (parent, object), attrs)
            # We assign __provides__, __implemented__ and __providedBy__ below
            # to prevent a memory leak that results from from the usage of this
            # instance's eventual use in an adapter lookup.  Adapter lookup
            # results in ``zope.interface.implementedBy`` being called with the
            # newly-created class as an argument.  Because the newly-created
            # class has no interface specification data of its own, lookup
            # causes new ClassProvides and Implements instances related to our
            # just-generated class to be created and set into the newly-created
            # class' __dict__.  We don't want these instances to be created; we
            # want this new class to behave exactly like it is the parent class
            # instead.  See https://github.com/Pylons/pyramid/issues/1212 for
            # more information.
            for name in ('__implemented__', '__providedBy__', '__provides__'):
                # we assign these attributes conditionally to make it possible
                # to test this class in isolation without having any interfaces
                # attached to it
                val = getattr(parent, name, _marker)
                if val is not _marker:
                    setattr(cls, name, val)
            self.__class__ = cls

    def _set_extensions(self, extensions):
        for name, fn in iteritems_(extensions.methods):
            method = fn.__get__(self, self.__class__)
            setattr(self, name, method)
        self._set_properties(extensions.descriptors)

    def set_property(self, callable, name=None, reify=False):
        """ Add a callable or a property descriptor to the instance.

        Properties, unlike attributes, are lazily evaluated by executing
        an underlying callable when accessed. They can be useful for
        adding features to an object without any cost if those features
        go unused.

        A property may also be reified via the
        :class:`pyramid.decorator.reify` decorator by setting
        ``reify=True``, allowing the result of the evaluation to be
        cached. Using this method, the value of the property is only
        computed once for the lifetime of the object.

        ``callable`` can either be a callable that accepts the instance
        as its single positional parameter, or it can be a property
        descriptor.

        If the ``callable`` is a property descriptor, the ``name``
        parameter must be supplied or a ``ValueError`` will be raised.
        Also note that a property descriptor cannot be reified, so
        ``reify`` must be ``False``.

        If ``name`` is None, the name of the property will be computed
        from the name of the ``callable``.

        .. code-block:: python
           :linenos:

           class Foo(InstancePropertyMixin):
               _x = 1

           def _get_x(self):
               return _x

           def _set_x(self, value):
               self._x = value

           foo = Foo()
           foo.set_property(property(_get_x, _set_x), name='x')
           foo.set_property(_get_x, name='y', reify=True)

           >>> foo.x
           1
           >>> foo.y
           1
           >>> foo.x = 5
           >>> foo.x
           5
           >>> foo.y # notice y keeps the original value
           1
        """
        prop = self._make_property(callable, name=name, reify=reify)
        self._set_properties([prop])

class WeakOrderedSet(object):
    """ Maintain a set of items.

    Each item is stored as a weakref to avoid extending their lifetime.

    The values may be iterated over or the last item added may be
    accessed via the ``last`` property.

    If items are added more than once, the most recent addition will
    be remembered in the order:

        order = WeakOrderedSet()
        order.add('1')
        order.add('2')
        order.add('1')

        list(order) == ['2', '1']
        order.last == '1'
    """

    def __init__(self):
        self._items = {}
        self._order = []

    def add(self, item):
        """ Add an item to the set."""
        oid = id(item)
        if oid in self._items:
            self._order.remove(oid)
            self._order.append(oid)
            return
        ref = weakref.ref(item, lambda x: self.remove(item))
        self._items[oid] = ref
        self._order.append(oid)

    def remove(self, item):
        """ Remove an item from the set."""
        oid = id(item)
        if oid in self._items:
            del self._items[oid]
            self._order.remove(oid)

    def empty(self):
        """ Clear all objects from the set."""
        self._items = {}
        self._order = []

    def __len__(self):
        return len(self._order)

    def __contains__(self, item):
        oid = id(item)
        return oid in self._items

    def __iter__(self):
        return (self._items[oid]() for oid in self._order)

    @property
    def last(self):
        if self._order:
            oid = self._order[-1]
            return self._items[oid]()

def strings_differ(string1, string2):
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    """
    if len(string1) != len(string2):
        return True

    invalid_bits = 0
    for a, b in zip(string1, string2):
        invalid_bits += a != b

    return invalid_bits != 0

def object_description(object):
    """ Produce a human-consumable text description of ``object``,
    usually involving a Python dotted name. For example:

    >>> object_description(None)
    u'None'
    >>> from xml.dom import minidom
    >>> object_description(minidom)
    u'module xml.dom.minidom'
    >>> object_description(minidom.Attr)
    u'class xml.dom.minidom.Attr'
    >>> object_description(minidom.Attr.appendChild)
    u'method appendChild of class xml.dom.minidom.Attr'

    If this method cannot identify the type of the object, a generic
    description ala ``object <object.__name__>`` will be returned.

    If the object passed is already a string, it is simply returned.  If it
    is a boolean, an integer, a list, a tuple, a set, or ``None``, a
    (possibly shortened) string representation is returned.
    """
    if isinstance(object, string_types):
        return text_(object)
    if isinstance(object, integer_types):
        return text_(str(object))
    if isinstance(object, (bool, float, type(None))):
        return text_(str(object))
    if isinstance(object, set):
        if PY3: # pragma: no cover
            return shortrepr(object, '}')
        else:
            return shortrepr(object, ')')
    if isinstance(object, tuple):
        return shortrepr(object, ')')
    if isinstance(object, list):
        return shortrepr(object, ']')
    if isinstance(object, dict):
        return shortrepr(object, '}')
    module = inspect.getmodule(object)
    if module is None:
        return text_('object %s' % str(object))
    modulename = module.__name__
    if inspect.ismodule(object):
        return text_('module %s' % modulename)
    if inspect.ismethod(object):
        oself = getattr(object, '__self__', None)
        if oself is None: # pragma: no cover
            oself = getattr(object, 'im_self', None)
        return text_('method %s of class %s.%s' %
                     (object.__name__, modulename,
                      oself.__class__.__name__))

    if inspect.isclass(object):
        dottedname = '%s.%s' % (modulename, object.__name__)
        return text_('class %s' % dottedname)
    if inspect.isfunction(object):
        dottedname = '%s.%s' % (modulename, object.__name__)
        return text_('function %s' % dottedname)
    return text_('object %s' % str(object))

def shortrepr(object, closer):
    r = str(object)
    if len(r) > 100:
        r = r[:100] + ' ... %s' % closer
    return r

class Sentinel(object):
    def __init__(self, repr):
        self.repr = repr

    def __repr__(self):
        return self.repr

FIRST = Sentinel('FIRST')
LAST = Sentinel('LAST')

class TopologicalSorter(object):
    """ A utility class which can be used to perform topological sorts against
    tuple-like data."""
    def __init__(
        self,
        default_before=LAST,
        default_after=None,
        first=FIRST,
        last=LAST,
        ):
        self.names = []
        self.req_before = set()
        self.req_after = set()
        self.name2before = {}
        self.name2after = {}
        self.name2val = {}
        self.order = []
        self.default_before = default_before
        self.default_after = default_after
        self.first = first
        self.last = last

    def remove(self, name):
        """ Remove a node from the sort input """
        self.names.remove(name)
        del self.name2val[name]
        after = self.name2after.pop(name, [])
        if after:
            self.req_after.remove(name)
            for u in after:
                self.order.remove((u, name))
        before = self.name2before.pop(name, [])
        if before:
            self.req_before.remove(name)
            for u in before:
                self.order.remove((name, u))
                
    def add(self, name, val, after=None, before=None):
        """ Add a node to the sort input.  The ``name`` should be a string or
        any other hashable object, the ``val`` should be the sortable (doesn't
        need to be hashable).  ``after`` and ``before`` represents the name of
        one of the other sortables (or a sequence of such named) or one of the
        special sentinel values :attr:`pyramid.util.FIRST`` or
        :attr:`pyramid.util.LAST` representing the first or last positions
        respectively.  ``FIRST`` and ``LAST`` can also be part of a sequence
        passed as ``before`` or ``after``.  A sortable should not be added
        after LAST or before FIRST.  An example::

           sorter = TopologicalSorter()
           sorter.add('a', {'a':1}, before=LAST, after='b')
           sorter.add('b', {'b':2}, before=LAST, after='c')
           sorter.add('c', {'c':3})

           sorter.sorted() # will be {'c':3}, {'b':2}, {'a':1}

        """
        if name in self.names:
            self.remove(name)
        self.names.append(name)
        self.name2val[name] = val
        if after is None and before is None:
            before = self.default_before
            after = self.default_after
        if after is not None:
            if not is_nonstr_iter(after):
                after = (after,)
            self.name2after[name] = after
            self.order += [(u, name) for u in after]
            self.req_after.add(name)
        if before is not None:
            if not is_nonstr_iter(before):
                before = (before,)
            self.name2before[name] = before
            self.order += [(name, o) for o in before]
            self.req_before.add(name)


    def sorted(self):
        """ Returns the sort input values in topologically sorted order"""
        order = [(self.first, self.last)]
        roots = []
        graph = {}
        names = [self.first, self.last]
        names.extend(self.names)

        for a, b in self.order:
            order.append((a, b))

        def add_node(node):
            if not node in graph:
                roots.append(node)
                graph[node] = [0] # 0 = number of arcs coming into this node

        def add_arc(fromnode, tonode):
            graph[fromnode].append(tonode)
            graph[tonode][0] += 1
            if tonode in roots:
                roots.remove(tonode)

        for name in names:
            add_node(name)

        has_before, has_after = set(), set()
        for a, b in order:
            if a in names and b in names: # deal with missing dependencies
                add_arc(a, b)
                has_before.add(a)
                has_after.add(b)

        if not self.req_before.issubset(has_before):
            raise ConfigurationError(
                'Unsatisfied before dependencies: %s'
                % (', '.join(sorted(self.req_before - has_before)))
            )
        if not self.req_after.issubset(has_after):
            raise ConfigurationError(
                'Unsatisfied after dependencies: %s'
                % (', '.join(sorted(self.req_after - has_after)))
            )

        sorted_names = []

        while roots:
            root = roots.pop(0)
            sorted_names.append(root)
            children = graph[root][1:]
            for child in children:
                arcs = graph[child][0]
                arcs -= 1
                graph[child][0] = arcs 
                if arcs == 0:
                    roots.insert(0, child)
            del graph[root]

        if graph:
            # loop in input
            cycledeps = {}
            for k, v in graph.items():
                cycledeps[k] = v[1:]
            raise CyclicDependencyError(cycledeps)

        result = []

        for name in sorted_names:
            if name in self.names:
                result.append((name, self.name2val[name]))

        return result

def viewdefaults(wrapped):
    """ Decorator for add_view-like methods which takes into account
    __view_defaults__ attached to view it is passed.  Not a documented API but
    used by some external systems."""
    def wrapper(self, *arg, **kw):
        defaults = {}
        if arg:
            view = arg[0]
        else:
            view = kw.get('view')
        view = self.maybe_dotted(view)
        if inspect.isclass(view):
            defaults = getattr(view, '__view_defaults__', {}).copy()
        if not '_backframes' in kw:
            kw['_backframes'] = 1 # for action_method
        defaults.update(kw)
        return wrapped(self, *arg, **defaults)
    return functools.wraps(wrapped)(wrapper)

@implementer(IActionInfo)
class ActionInfo(object):
    def __init__(self, file, line, function, src):
        self.file = file
        self.line = line
        self.function = function
        self.src = src

    def __str__(self):
        srclines = self.src.split('\n')
        src = '\n'.join('    %s' % x for x in srclines)
        return 'Line %s of file %s:\n%s' % (self.line, self.file, src)

def action_method(wrapped):
    """ Wrapper to provide the right conflict info report data when a method
    that calls Configurator.action calls another that does the same.  Not a
    documented API but used by some external systems."""
    def wrapper(self, *arg, **kw):
        if self._ainfo is None:
            self._ainfo = []
        info = kw.pop('_info', None)
        # backframes for outer decorators to actionmethods
        backframes = kw.pop('_backframes', 0) + 2
        if is_nonstr_iter(info) and len(info) == 4:
            # _info permitted as extract_stack tuple
            info = ActionInfo(*info)
        if info is None:
            try:
                f = traceback.extract_stack(limit=3)
                info = ActionInfo(*f[-backframes])
            except: # pragma: no cover
                info = ActionInfo(None, 0, '', '')
        self._ainfo.append(info)
        try:
            result = wrapped(self, *arg, **kw)
        finally:
            self._ainfo.pop()
        return result

    if hasattr(wrapped, '__name__'):
        functools.update_wrapper(wrapper, wrapped)
    wrapper.__docobj__ = wrapped
    return wrapper

