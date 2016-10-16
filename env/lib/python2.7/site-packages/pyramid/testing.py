import copy
import os
from contextlib import contextmanager

from zope.interface import (
    implementer,
    alsoProvides,
    )

from pyramid.interfaces import (
    IRequest,
    ISession,
    )

from pyramid.compat import (
    PY3,
    PYPY,
    class_types,
    text_,
    )

from pyramid.config import Configurator
from pyramid.decorator import reify
from pyramid.path import caller_package
from pyramid.response import _get_response_factory
from pyramid.registry import Registry

from pyramid.security import (
    Authenticated,
    Everyone,
    AuthenticationAPIMixin,
    AuthorizationAPIMixin,
    )

from pyramid.threadlocal import (
    get_current_registry,
    manager,
    )

from pyramid.i18n import LocalizerRequestMixin
from pyramid.request import CallbackMethodsMixin
from pyramid.url import URLMethodsMixin
from pyramid.util import InstancePropertyMixin
from pyramid.view import ViewMethodsMixin


_marker = object()

class DummyRootFactory(object):
    __parent__ = None
    __name__ = None
    def __init__(self, request):
        if 'bfg.routes.matchdict' in request:
            self.__dict__.update(request['bfg.routes.matchdict'])

class DummySecurityPolicy(object):
    """ A standin for both an IAuthentication and IAuthorization policy """
    def __init__(self, userid=None, groupids=(), permissive=True,
                 remember_result=None, forget_result=None):
        self.userid = userid
        self.groupids = groupids
        self.permissive = permissive
        if remember_result is None:
            remember_result = []
        if forget_result is None:
            forget_result = []
        self.remember_result = remember_result
        self.forget_result = forget_result

    def authenticated_userid(self, request):
        return self.userid

    def unauthenticated_userid(self, request):
        return self.userid

    def effective_principals(self, request):
        effective_principals = [Everyone]
        if self.userid:
            effective_principals.append(Authenticated)
            effective_principals.append(self.userid)
            effective_principals.extend(self.groupids)
        return effective_principals

    def remember(self, request, userid, **kw):
        self.remembered = userid
        return self.remember_result

    def forget(self, request):
        self.forgotten = True
        return self.forget_result

    def permits(self, context, principals, permission):
        return self.permissive

    def principals_allowed_by_permission(self, context, permission):
        return self.effective_principals(None)

class DummyTemplateRenderer(object):
    """
    An instance of this class is returned from
    :meth:`pyramid.config.Configurator.testing_add_renderer`.  It has a
    helper function (``assert_``) that makes it possible to make an
    assertion which compares data passed to the renderer by the view
    function against expected key/value pairs.
    """
    def __init__(self, string_response=''):
        self._received = {}
        self._string_response = string_response
        self._implementation = MockTemplate(string_response)

    # For in-the-wild test code that doesn't create its own renderer,
    # but mutates our internals instead.  When all you read is the
    # source code, *everything* is an API!
    def _get_string_response(self):
        return self._string_response
    def _set_string_response(self, response):
        self._string_response = response
        self._implementation.response = response
    string_response = property(_get_string_response, _set_string_response)

    def implementation(self):
        return self._implementation

    def __call__(self, kw, system=None):
        if system:
            self._received.update(system)
        self._received.update(kw)
        return self.string_response

    def __getattr__(self, k):
        """ Backwards compatibility """
        val = self._received.get(k, _marker)
        if val is _marker:
            val = self._implementation._received.get(k, _marker)
            if val is _marker:
                raise AttributeError(k)
        return val

    def assert_(self, **kw):
        """ Accept an arbitrary set of assertion key/value pairs.  For
        each assertion key/value pair assert that the renderer
        (eg. :func:`pyramid.renderers.render_to_response`)
        received the key with a value that equals the asserted
        value. If the renderer did not receive the key at all, or the
        value received by the renderer doesn't match the assertion
        value, raise an :exc:`AssertionError`."""
        for k, v in kw.items():
            myval = self._received.get(k, _marker)
            if myval is _marker:
                myval = self._implementation._received.get(k, _marker)
                if myval is _marker:
                    raise AssertionError(
                        'A value for key "%s" was not passed to the renderer'
                        % k)

            if myval != v:
                raise AssertionError(
                    '\nasserted value for %s: %r\nactual value: %r' % (
                        k, v, myval))
        return True


class DummyResource:
    """ A dummy :app:`Pyramid` :term:`resource` object."""
    def __init__(self, __name__=None, __parent__=None, __provides__=None,
                 **kw):
        """ The resource's ``__name__`` attribute will be set to the
        value of the ``__name__`` argument, and the resource's
        ``__parent__`` attribute will be set to the value of the
        ``__parent__`` argument.  If ``__provides__`` is specified, it
        should be an interface object or tuple of interface objects
        that will be attached to the resulting resource via
        :func:`zope.interface.alsoProvides`. Any extra keywords passed
        in the ``kw`` argumnent will be set as direct attributes of
        the resource object.

        .. note:: For backwards compatibility purposes, this class can also
                  be imported as :class:`pyramid.testing.DummyModel`.

        """
        self.__name__ = __name__
        self.__parent__ = __parent__
        if __provides__ is not None:
            alsoProvides(self, __provides__)
        self.kw = kw
        self.__dict__.update(**kw)
        self.subs = {}

    def __setitem__(self, name, val):
        """ When the ``__setitem__`` method is called, the object
        passed in as ``val`` will be decorated with a ``__parent__``
        attribute pointing at the dummy resource and a ``__name__``
        attribute that is the value of ``name``.  The value will then
        be returned when dummy resource's ``__getitem__`` is called with
        the name ``name```."""
        val.__name__ = name
        val.__parent__ = self
        self.subs[name] = val

    def __getitem__(self, name):
        """ Return a named subobject (see ``__setitem__``)"""
        ob = self.subs[name]
        return ob

    def __delitem__(self, name):
        del self.subs[name]

    def get(self, name, default=None):
        return self.subs.get(name, default)

    def values(self):
        """ Return the values set by __setitem__ """
        return self.subs.values()

    def items(self):
        """ Return the items set by __setitem__ """
        return self.subs.items()

    def keys(self):
        """ Return the keys set by __setitem__ """
        return self.subs.keys()

    __iter__ = keys

    def __nonzero__(self):
        return True

    __bool__ = __nonzero__

    def __len__(self):
        return len(self.subs)

    def __contains__(self, name):
        return name in self.subs

    def clone(self, __name__=_marker, __parent__=_marker, **kw):
        """ Create a clone of the resource object.  If ``__name__`` or
        ``__parent__`` arguments are passed, use these values to
        override the existing ``__name__`` or ``__parent__`` of the
        resource.  If any extra keyword args are passed in via the ``kw``
        argument, use these keywords to add to or override existing
        resource keywords (attributes)."""
        oldkw = self.kw.copy()
        oldkw.update(kw)
        inst = self.__class__(self.__name__, self.__parent__, **oldkw)
        inst.subs = copy.deepcopy(self.subs)
        if __name__ is not _marker:
            inst.__name__ = __name__
        if __parent__ is not _marker:
            inst.__parent__ = __parent__
        return inst

DummyModel = DummyResource # b/w compat (forever)

@implementer(ISession)
class DummySession(dict):
    created = None
    new = True
    def changed(self):
        pass

    def invalidate(self):
        self.clear()

    def flash(self, msg, queue='', allow_duplicate=True):
        storage = self.setdefault('_f_' + queue, [])
        if allow_duplicate or (msg not in storage):
            storage.append(msg)

    def pop_flash(self, queue=''):
        storage = self.pop('_f_' + queue, [])
        return storage

    def peek_flash(self, queue=''):
        storage = self.get('_f_' + queue, [])
        return storage

    def new_csrf_token(self):
        token = text_('0123456789012345678901234567890123456789')
        self['_csrft_'] = token
        return token

    def get_csrf_token(self):
        token = self.get('_csrft_', None)
        if token is None:
            token = self.new_csrf_token()
        return token

@implementer(IRequest)
class DummyRequest(
    URLMethodsMixin,
    CallbackMethodsMixin,
    InstancePropertyMixin,
    LocalizerRequestMixin,
    AuthenticationAPIMixin,
    AuthorizationAPIMixin,
    ViewMethodsMixin,
    ):
    """ A DummyRequest object (incompletely) imitates a :term:`request` object.

    The ``params``, ``environ``, ``headers``, ``path``, and
    ``cookies`` arguments correspond to their :term:`WebOb`
    equivalents.

    The ``post`` argument,  if passed, populates the request's
    ``POST`` attribute, but *not* ``params``, in order to allow testing
    that the app accepts data for a given view only from POST requests.
    This argument also sets ``self.method`` to "POST".

    Extra keyword arguments are assigned as attributes of the request
    itself.

    Note that DummyRequest does not have complete fidelity with a "real"
    request.  For example, by default, the DummyRequest ``GET`` and ``POST``
    attributes are of type ``dict``, unlike a normal Request's GET and POST,
    which are of type ``MultiDict``. If your code uses the features of
    MultiDict, you should either use a real :class:`pyramid.request.Request`
    or adapt your DummyRequest by replacing the attributes with ``MultiDict``
    instances.

    Other similar incompatibilities exist.  If you need all the features of
    a Request, use the :class:`pyramid.request.Request` class itself rather
    than this class while writing tests.
    """
    method = 'GET'
    application_url = 'http://example.com'
    host = 'example.com:80'
    domain = 'example.com'
    content_length = 0
    query_string = ''
    charset = 'UTF-8'
    script_name = ''
    _registry = None
    request_iface = IRequest

    def __init__(self, params=None, environ=None, headers=None, path='/',
                 cookies=None, post=None, **kw):
        if environ is None:
            environ = {}
        if params is None:
            params = {}
        if headers is None:
            headers = {}
        if cookies is None:
            cookies = {}
        self.environ = environ
        self.headers = headers
        self.params = params
        self.cookies = cookies
        self.matchdict = {}
        self.GET = params
        if post is not None:
            self.method = 'POST'
            self.POST = post
        else:
            self.POST = params
        self.host_url = self.application_url
        self.path_url = self.application_url
        self.url = self.application_url
        self.path = path
        self.path_info = path
        self.script_name = ''
        self.path_qs = ''
        self.body = ''
        self.view_name = ''
        self.subpath = ()
        self.traversed = ()
        self.virtual_root_path = ()
        self.context = None
        self.root = None
        self.virtual_root = None
        self.marshalled = params # repoze.monty
        self.session = DummySession()
        self.__dict__.update(kw)

    def _get_registry(self):
        if self._registry is None:
            return get_current_registry()
        return self._registry

    def _set_registry(self, registry):
        self._registry = registry

    def _del_registry(self):
        self._registry = None

    registry = property(_get_registry, _set_registry, _del_registry)

    @reify
    def response(self):
        f = _get_response_factory(self.registry)
        return f(self)

have_zca = True


def setUp(registry=None, request=None, hook_zca=True, autocommit=True,
          settings=None, package=None):
    """
    Set :app:`Pyramid` registry and request thread locals for the
    duration of a single unit test.

    Use this function in the ``setUp`` method of a unittest test case
    which directly or indirectly uses:

    - any method of the :class:`pyramid.config.Configurator`
      object returned by this function.

    - the :func:`pyramid.threadlocal.get_current_registry` or
      :func:`pyramid.threadlocal.get_current_request` functions.

    If you use the ``get_current_*`` functions (or call :app:`Pyramid` code
    that uses these functions) without calling ``setUp``,
    :func:`pyramid.threadlocal.get_current_registry` will return a *global*
    :term:`application registry`, which may cause unit tests to not be
    isolated with respect to registrations they perform.

    If the ``registry`` argument is ``None``, a new empty
    :term:`application registry` will be created (an instance of the
    :class:`pyramid.registry.Registry` class).  If the ``registry``
    argument is not ``None``, the value passed in should be an
    instance of the :class:`pyramid.registry.Registry` class or a
    suitable testing analogue.

    After ``setUp`` is finished, the registry returned by the
    :func:`pyramid.threadlocal.get_current_registry` function will
    be the passed (or constructed) registry until
    :func:`pyramid.testing.tearDown` is called (or
    :func:`pyramid.testing.setUp` is called again) .

    If the ``hook_zca`` argument is ``True``, ``setUp`` will attempt
    to perform the operation ``zope.component.getSiteManager.sethook(
    pyramid.threadlocal.get_current_registry)``, which will cause
    the :term:`Zope Component Architecture` global API
    (e.g. :func:`zope.component.getSiteManager`,
    :func:`zope.component.getAdapter`, and so on) to use the registry
    constructed by ``setUp`` as the value it returns from
    :func:`zope.component.getSiteManager`.  If the
    :mod:`zope.component` package cannot be imported, or if
    ``hook_zca`` is ``False``, the hook will not be set.

    If ``settings`` is not ``None``, it must be a dictionary representing the
    values passed to a Configurator as its ``settings=`` argument.

    If ``package`` is ``None`` it will be set to the caller's package. The
    ``package`` setting in the :class:`pyramid.config.Configurator` will
    affect any relative imports made via
    :meth:`pyramid.config.Configurator.include` or
    :meth:`pyramid.config.Configurator.maybe_dotted`.

    This function returns an instance of the
    :class:`pyramid.config.Configurator` class, which can be
    used for further configuration to set up an environment suitable
    for a unit or integration test.  The ``registry`` attribute
    attached to the Configurator instance represents the 'current'
    :term:`application registry`; the same registry will be returned
    by :func:`pyramid.threadlocal.get_current_registry` during the
    execution of the test.
    """
    manager.clear()
    if registry is None:
        registry = Registry('testing')
    if package is None:
        package = caller_package()
    config = Configurator(registry=registry, autocommit=autocommit,
                          package=package)
    if settings is None:
        settings = {}
    if getattr(registry, 'settings', None) is None:
        config._set_settings(settings)
    if hasattr(registry, 'registerUtility'):
        # Sometimes nose calls us with a non-registry object because
        # it thinks this function is module test setup.  Likewise,
        # someone may be passing us an esoteric "dummy" registry, and
        # the below won't succeed if it doesn't have a registerUtility
        # method.
        config.add_default_renderers()
        config.add_default_view_predicates()
        config.add_default_view_derivers()
        config.add_default_route_predicates()
    config.commit()
    global have_zca
    try:
        have_zca and hook_zca and config.hook_zca()
    except ImportError: # pragma: no cover
        # (dont choke on not being able to import z.component)
        have_zca = False
    config.begin(request=request)
    return config

def tearDown(unhook_zca=True):
    """Undo the effects of :func:`pyramid.testing.setUp`.  Use this
    function in the ``tearDown`` method of a unit test that uses
    :func:`pyramid.testing.setUp` in its ``setUp`` method.

    If the ``unhook_zca`` argument is ``True`` (the default), call
    :func:`zope.component.getSiteManager.reset`.  This undoes the
    action of :func:`pyramid.testing.setUp` when called with the
    argument ``hook_zca=True``.  If :mod:`zope.component` cannot be
    imported, ``unhook_zca`` is set to ``False``.
    """
    global have_zca
    if unhook_zca and have_zca:
        try:
            from zope.component import getSiteManager
            getSiteManager.reset()
        except ImportError: # pragma: no cover
            have_zca = False
    info = manager.pop()
    manager.clear()
    if info is not None:
        registry = info['registry']
        if hasattr(registry, '__init__') and hasattr(registry, '__name__'):
            try:
                registry.__init__(registry.__name__)
            except TypeError:
                # calling __init__ is largely for the benefit of
                # people who want to use the global ZCA registry;
                # however maybe somebody's using a registry we don't
                # understand, let's not blow up
                pass

def cleanUp(*arg, **kw):
    """ An alias for :func:`pyramid.testing.setUp`. """
    package = kw.get('package', None)
    if package is None:
        package = caller_package()
        kw['package'] = package
    return setUp(*arg, **kw)

class DummyRendererFactory(object):
    """ Registered by
    :meth:`pyramid.config.Configurator.testing_add_renderer` as
    a dummy renderer factory.  The indecision about what to use as a
    key (a spec vs. a relative name) is caused by test suites in the
    wild believing they can register either.  The ``factory`` argument
    passed to this constructor is usually the *real* template renderer
    factory, found when ``testing_add_renderer`` is called."""
    def __init__(self, name, factory):
        self.name = name
        self.factory = factory # the "real" renderer factory reg'd previously
        self.renderers = {}

    def add(self, spec, renderer):
        self.renderers[spec] = renderer
        if ':' in spec:
            package, relative = spec.split(':', 1)
            self.renderers[relative] = renderer

    def __call__(self, info):
        spec = info.name
        renderer = self.renderers.get(spec)
        if renderer is None:
            if ':' in spec:
                package, relative = spec.split(':', 1)
                renderer = self.renderers.get(relative)
            if renderer is None:
                if self.factory:
                    renderer = self.factory(info)
                else:
                    raise KeyError('No testing renderer registered for %r' %
                                   spec)
        return renderer


class MockTemplate(object):
    def __init__(self, response):
        self._received = {}
        self.response = response
    def __getattr__(self, attrname):
        return self
    def __getitem__(self, attrname):
        return self
    def __call__(self, *arg, **kw):
        self._received.update(kw)
        return self.response

def skip_on(*platforms): # pragma: no  cover
    skip = False
    for platform in platforms:
        if skip_on.os_name.startswith(platform):
            skip = True
        if platform == 'pypy' and PYPY:
            skip = True
        if platform == 'py3' and PY3:
            skip = True

    def decorator(func):
        if isinstance(func, class_types):
            if skip:
                return None
            else:
                return func
        else:
            def wrapper(*args, **kw):
                if skip:
                    return
                return func(*args, **kw)
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper
    return decorator
skip_on.os_name = os.name # for testing

@contextmanager
def testConfig(registry=None,
        request=None,
        hook_zca=True,
        autocommit=True,
        settings=None):
    """Returns a context manager for test set up.

    This context manager calls :func:`pyramid.testing.setUp` when
    entering and :func:`pyramid.testing.tearDown` when exiting.

    All arguments are passed directly to :func:`pyramid.testing.setUp`.
    If the ZCA is hooked, it will always be un-hooked in tearDown.

    This context manager allows you to write test code like this:

    .. code-block:: python
        :linenos:

        with testConfig() as config:
            config.add_route('bar', '/bar/{id}')
            req = DummyRequest()
            resp = myview(req),
    """
    config = setUp(registry=registry,
            request=request,
            hook_zca=hook_zca,
            autocommit=autocommit,
            settings=settings)
    try:
        yield config
    finally:
        tearDown(unhook_zca=hook_zca)
