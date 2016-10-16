import contextlib
import functools
try:
    # py2.7.7+ and py3.3+ have native comparison support
    from hmac import compare_digest
except ImportError: # pragma: nocover
    compare_digest = None
import inspect
import traceback
import weakref

from zope.interface import implementer

from pyramid.exceptions import (
    ConfigurationError,
    CyclicDependencyError,
    )

from pyramid.compat import (
    is_nonstr_iter,
    integer_types,
    string_types,
    text_,
    PY2,
    native_
    )

from pyramid.interfaces import IActionInfo
from pyramid.path import DottedNameResolver as _DottedNameResolver


class DottedNameResolver(_DottedNameResolver):
    def __init__(self, package=None): # default to package = None for bw compat
        _DottedNameResolver.__init__(self, package)

_marker = object()


class InstancePropertyHelper(object):
    """A helper object for assigning properties and descriptors to instances.
    It is not normally possible to do this because descriptors must be
    defined on the class itself.

    This class is optimized for adding multiple properties at once to an
    instance. This is done by calling :meth:`.add_property` once
    per-property and then invoking :meth:`.apply` on target objects.

    """
    def __init__(self):
        self.properties = {}

    @classmethod
    def make_property(cls, callable, name=None, reify=False):
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
            fn.__name__ = get_callable_name(name)
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

    @classmethod
    def apply_properties(cls, target, properties):
        """Accept a list or dict of ``properties`` generated from
        :meth:`.make_property` and apply them to a ``target`` object.
        """
        attrs = dict(properties)
        if attrs:
            parent = target.__class__
            newcls = type(parent.__name__, (parent, object), attrs)
            # We assign __provides__ and __implemented__ below to prevent a
            # memory leak that results from from the usage of this instance's
            # eventual use in an adapter lookup.  Adapter lookup results in
            # ``zope.interface.implementedBy`` being called with the
            # newly-created class as an argument.  Because the newly-created
            # class has no interface specification data of its own, lookup
            # causes new ClassProvides and Implements instances related to our
            # just-generated class to be created and set into the newly-created
            # class' __dict__.  We don't want these instances to be created; we
            # want this new class to behave exactly like it is the parent class
            # instead.  See GitHub issues #1212, #1529 and #1568 for more
            # information.
            for name in ('__implemented__', '__provides__'):
                # we assign these attributes conditionally to make it possible
                # to test this class in isolation without having any interfaces
                # attached to it
                val = getattr(parent, name, _marker)
                if val is not _marker:
                    setattr(newcls, name, val)
            target.__class__ = newcls

    @classmethod
    def set_property(cls, target, callable, name=None, reify=False):
        """A helper method to apply a single property to an instance."""
        prop = cls.make_property(callable, name=name, reify=reify)
        cls.apply_properties(target, [prop])

    def add_property(self, callable, name=None, reify=False):
        """Add a new property configuration.

        This should be used in combination with :meth:`.apply` as a
        more efficient version of :meth:`.set_property`.
        """
        name, fn = self.make_property(callable, name=name, reify=reify)
        self.properties[name] = fn

    def apply(self, target):
        """ Apply all configured properties to the ``target`` instance."""
        if self.properties:
            self.apply_properties(target, self.properties)

class InstancePropertyMixin(object):
    """ Mixin that will allow an instance to add properties at
    run-time as if they had been defined via @property or @reify
    on the class itself.
    """

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
        InstancePropertyHelper.set_property(
            self, callable, name=name, reify=reify)

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

def strings_differ(string1, string2, compare_digest=compare_digest):
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    .. versionchanged:: 1.6
       Support :func:`hmac.compare_digest` if it is available (Python 2.7.7+
       and Python 3.3+).

    """
    len_eq = len(string1) == len(string2)
    if len_eq:
        invalid_bits = 0
        left = string1
    else:
        invalid_bits = 1
        left = string2
    right = string2

    if compare_digest is not None:
        invalid_bits += not compare_digest(left, right)
    else:
        for a, b in zip(left, right):
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
        if PY2:
            return shortrepr(object, ')')
        else:
            return shortrepr(object, '}')
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

    def values(self):
        return self.name2val.values()

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
            if node not in graph:
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
        if '_backframes' not in kw:
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
                f = traceback.extract_stack(limit=4)

                # Work around a Python 3.5 issue whereby it would insert an
                # extra stack frame. This should no longer be necessary in
                # Python 3.5.1
                last_frame = ActionInfo(*f[-1])
                if last_frame.function == 'extract_stack': # pragma: no cover
                    f.pop()
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


def get_callable_name(name):
    """
    Verifies that the ``name`` is ascii and will raise a ``ConfigurationError``
    if it is not.
    """
    try:
        return native_(name, 'ascii')
    except (UnicodeEncodeError, UnicodeDecodeError):
        msg = (
            '`name="%s"` is invalid. `name` must be ascii because it is '
            'used on __name__ of the method'
        )
        raise ConfigurationError(msg % name)

@contextlib.contextmanager
def hide_attrs(obj, *attrs):
    """
    Temporarily delete object attrs and restore afterward.
    """
    obj_vals = obj.__dict__ if obj is not None else {}
    saved_vals = {}
    for name in attrs:
        saved_vals[name] = obj_vals.pop(name, _marker)
    try:
        yield
    finally:
        for name in attrs:
            saved_val = saved_vals[name]
            if saved_val is not _marker:
                obj_vals[name] = saved_val
            elif name in obj_vals:
                del obj_vals[name]


def is_same_domain(host, pattern):
    """
    Return ``True`` if the host is either an exact match or a match
    to the wildcard pattern.
    Any pattern beginning with a period matches a domain and all of its
    subdomains. (e.g. ``.example.com`` matches ``example.com`` and
    ``foo.example.com``). Anything else is an exact string match.
    """
    if not pattern:
        return False

    pattern = pattern.lower()
    return (pattern[0] == "." and
            (host.endswith(pattern) or host == pattern[1:]) or
            pattern == host)
