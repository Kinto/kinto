import json
import os
import re

from zope.interface import (
    implementer,
    providedBy,
    )
from zope.interface.registry import Components

from pyramid.interfaces import (
    IJSONAdapter,
    IRendererFactory,
    IRendererInfo,
    )

from pyramid.compat import (
    string_types,
    text_type,
    )

from pyramid.decorator import reify

from pyramid.events import BeforeRender

from pyramid.httpexceptions import HTTPBadRequest

from pyramid.path import caller_package

from pyramid.response import _get_response_factory
from pyramid.threadlocal import get_current_registry
from pyramid.util import hide_attrs

# API

def render(renderer_name, value, request=None, package=None):
    """ Using the renderer ``renderer_name`` (a template
    or a static renderer), render the value (or set of values) present
    in ``value``. Return the result of the renderer's ``__call__``
    method (usually a string or Unicode).

    If the ``renderer_name`` refers to a file on disk, such as when the
    renderer is a template, it's usually best to supply the name as an
    :term:`asset specification`
    (e.g. ``packagename:path/to/template.pt``).

    You may supply a relative asset spec as ``renderer_name``.  If
    the ``package`` argument is supplied, a relative renderer path
    will be converted to an absolute asset specification by
    combining the package ``package`` with the relative
    asset specification ``renderer_name``.  If ``package``
    is ``None`` (the default), the package name of the *caller* of
    this function will be used as the package.

    The ``value`` provided will be supplied as the input to the
    renderer.  Usually, for template renderings, this should be a
    dictionary.  For other renderers, this will need to be whatever
    sort of value the renderer expects.

    The 'system' values supplied to the renderer will include a basic set of
    top-level system names, such as ``request``, ``context``,
    ``renderer_name``, and ``view``.  See :ref:`renderer_system_values` for
    the full list.  If :term:`renderer globals` have been specified, these
    will also be used to augment the value.

    Supply a ``request`` parameter in order to provide the renderer
    with the most correct 'system' values (``request`` and ``context``
    in particular).

    """
    try:
        registry = request.registry
    except AttributeError:
        registry = None
    if package is None:
        package = caller_package()
    helper = RendererHelper(name=renderer_name, package=package,
                            registry=registry)

    with hide_attrs(request, 'response'):
        result = helper.render(value, None, request=request)

    return result

def render_to_response(renderer_name,
                       value,
                       request=None,
                       package=None,
                       response=None):
    """ Using the renderer ``renderer_name`` (a template
    or a static renderer), render the value (or set of values) using
    the result of the renderer's ``__call__`` method (usually a string
    or Unicode) as the response body.

    If the renderer name refers to a file on disk (such as when the
    renderer is a template), it's usually best to supply the name as a
    :term:`asset specification`.

    You may supply a relative asset spec as ``renderer_name``.  If
    the ``package`` argument is supplied, a relative renderer name
    will be converted to an absolute asset specification by
    combining the package ``package`` with the relative
    asset specification ``renderer_name``.  If you do
    not supply a ``package`` (or ``package`` is ``None``) the package
    name of the *caller* of this function will be used as the package.

    The ``value`` provided will be supplied as the input to the
    renderer.  Usually, for template renderings, this should be a
    dictionary.  For other renderers, this will need to be whatever
    sort of value the renderer expects.

    The 'system' values supplied to the renderer will include a basic set of
    top-level system names, such as ``request``, ``context``,
    ``renderer_name``, and ``view``.  See :ref:`renderer_system_values` for
    the full list.  If :term:`renderer globals` have been specified, these
    will also be used to argument the value.

    Supply a ``request`` parameter in order to provide the renderer
    with the most correct 'system' values (``request`` and ``context``
    in particular). Keep in mind that any changes made to ``request.response``
    prior to calling this function will not be reflected in the resulting
    response object. A new response object will be created for each call
    unless one is passed as the ``response`` argument.

    .. versionchanged:: 1.6
       In previous versions, any changes made to ``request.response`` outside
       of this function call would affect the returned response. This is no
       longer the case. If you wish to send in a pre-initialized response
       then you may pass one in the ``response`` argument.

    """
    try:
        registry = request.registry
    except AttributeError:
        registry = None
    if package is None:
        package = caller_package()
    helper = RendererHelper(name=renderer_name, package=package,
                            registry=registry)

    with hide_attrs(request, 'response'):
        if response is not None:
            request.response = response
        result = helper.render_to_response(value, None, request=request)

    return result

def get_renderer(renderer_name, package=None):
    """ Return the renderer object for the renderer ``renderer_name``.

    You may supply a relative asset spec as ``renderer_name``.  If
    the ``package`` argument is supplied, a relative renderer name
    will be converted to an absolute asset specification by
    combining the package ``package`` with the relative
    asset specification ``renderer_name``.  If ``package`` is ``None``
    (the default), the package name of the *caller* of this function
    will be used as the package.
    """
    if package is None:
        package = caller_package()
    helper = RendererHelper(name=renderer_name, package=package)
    return helper.renderer

# concrete renderer factory implementations (also API)

def string_renderer_factory(info):
    def _render(value, system):
        if not isinstance(value, string_types):
            value = str(value)
        request = system.get('request')
        if request is not None:
            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'text/plain'
        return value
    return _render

_marker = object()

class JSON(object):
    """ Renderer that returns a JSON-encoded string.

    Configure a custom JSON renderer using the
    :meth:`~pyramid.config.Configurator.add_renderer` API at application
    startup time:

    .. code-block:: python

       from pyramid.config import Configurator

       config = Configurator()
       config.add_renderer('myjson', JSON(indent=4))

    Once this renderer is registered as above, you can use
    ``myjson`` as the ``renderer=`` parameter to ``@view_config`` or
    :meth:`~pyramid.config.Configurator.add_view``:

    .. code-block:: python

       from pyramid.view import view_config

       @view_config(renderer='myjson')
       def myview(request):
           return {'greeting':'Hello world'}

    Custom objects can be serialized using the renderer by either
    implementing the ``__json__`` magic method, or by registering
    adapters with the renderer.  See
    :ref:`json_serializing_custom_objects` for more information.

    .. note::

        The default serializer uses ``json.JSONEncoder``. A different
        serializer can be specified via the ``serializer`` argument.  Custom
        serializers should accept the object, a callback ``default``, and any
        extra ``kw`` keyword arguments passed during renderer construction.
        This feature isn't widely used but it can be used to replace the
        stock JSON serializer with, say, simplejson.  If all you want to
        do, however, is serialize custom objects, you should use the method
        explained in :ref:`json_serializing_custom_objects` instead
        of replacing the serializer.

    .. versionadded:: 1.4
       Prior to this version, there was no public API for supplying options
       to the underlying serializer without defining a custom renderer.
    """

    def __init__(self, serializer=json.dumps, adapters=(), **kw):
        """ Any keyword arguments will be passed to the ``serializer``
        function."""
        self.serializer = serializer
        self.kw = kw
        self.components = Components()
        for type, adapter in adapters:
            self.add_adapter(type, adapter)

    def add_adapter(self, type_or_iface, adapter):
        """ When an object of the type (or interface) ``type_or_iface`` fails
        to automatically encode using the serializer, the renderer will use
        the adapter ``adapter`` to convert it into a JSON-serializable
        object.  The adapter must accept two arguments: the object and the
        currently active request.

        .. code-block:: python

           class Foo(object):
               x = 5

           def foo_adapter(obj, request):
               return obj.x

           renderer = JSON(indent=4)
           renderer.add_adapter(Foo, foo_adapter)

        When you've done this, the JSON renderer will be able to serialize
        instances of the ``Foo`` class when they're encountered in your view
        results."""

        self.components.registerAdapter(adapter, (type_or_iface,),
                                        IJSONAdapter)

    def __call__(self, info):
        """ Returns a plain JSON-encoded string with content-type
        ``application/json``. The content-type may be overridden by
        setting ``request.response.content_type``."""
        def _render(value, system):
            request = system.get('request')
            if request is not None:
                response = request.response
                ct = response.content_type
                if ct == response.default_content_type:
                    response.content_type = 'application/json'
            default = self._make_default(request)
            return self.serializer(value, default=default, **self.kw)

        return _render

    def _make_default(self, request):
        def default(obj):
            if hasattr(obj, '__json__'):
                return obj.__json__(request)
            obj_iface = providedBy(obj)
            adapters = self.components.adapters
            result = adapters.lookup((obj_iface,), IJSONAdapter,
                                     default=_marker)
            if result is _marker:
                raise TypeError('%r is not JSON serializable' % (obj,))
            return result(obj, request)
        return default

json_renderer_factory = JSON() # bw compat

JSONP_VALID_CALLBACK = re.compile(r"^[$a-z_][$0-9a-z_\.\[\]]+[^.]$", re.I)

class JSONP(JSON):
    """ `JSONP <https://en.wikipedia.org/wiki/JSONP>`_ renderer factory helper
    which implements a hybrid json/jsonp renderer.  JSONP is useful for
    making cross-domain AJAX requests.

    Configure a JSONP renderer using the
    :meth:`pyramid.config.Configurator.add_renderer` API at application
    startup time:

    .. code-block:: python

       from pyramid.config import Configurator

       config = Configurator()
       config.add_renderer('jsonp', JSONP(param_name='callback'))

    The class' constructor also accepts arbitrary keyword arguments.  All
    keyword arguments except ``param_name`` are passed to the ``json.dumps``
    function as its keyword arguments.

    .. code-block:: python

       from pyramid.config import Configurator

       config = Configurator()
       config.add_renderer('jsonp', JSONP(param_name='callback', indent=4))

    .. versionchanged:: 1.4
       The ability of this class to accept a ``**kw`` in its constructor.

    The arguments passed to this class' constructor mean the same thing as
    the arguments passed to :class:`pyramid.renderers.JSON` (including
    ``serializer`` and ``adapters``).

    Once this renderer is registered via
    :meth:`~pyramid.config.Configurator.add_renderer` as above, you can use
    ``jsonp`` as the ``renderer=`` parameter to ``@view_config`` or
    :meth:`pyramid.config.Configurator.add_view``:

    .. code-block:: python

       from pyramid.view import view_config

       @view_config(renderer='jsonp')
       def myview(request):
           return {'greeting':'Hello world'}

    When a view is called that uses the JSONP renderer:

    - If there is a parameter in the request's HTTP query string that matches
      the ``param_name`` of the registered JSONP renderer (by default,
      ``callback``), the renderer will return a JSONP response.

    - If there is no callback parameter in the request's query string, the
      renderer will return a 'plain' JSON response.

    .. versionadded:: 1.1

    .. seealso::

        See also :ref:`jsonp_renderer`.
    """

    def __init__(self, param_name='callback', **kw):
        self.param_name = param_name
        JSON.__init__(self, **kw)

    def __call__(self, info):
        """ Returns JSONP-encoded string with content-type
        ``application/javascript`` if query parameter matching
        ``self.param_name`` is present in request.GET; otherwise returns
        plain-JSON encoded string with content-type ``application/json``"""
        def _render(value, system):
            request = system.get('request')
            default = self._make_default(request)
            val = self.serializer(value, default=default, **self.kw)
            ct = 'application/json'
            body = val
            if request is not None:
                callback = request.GET.get(self.param_name)

                if callback is not None:
                    if not JSONP_VALID_CALLBACK.match(callback):
                        raise HTTPBadRequest('Invalid JSONP callback function name.')

                    ct = 'application/javascript'
                    body = '/**/{0}({1});'.format(callback, val)
                response = request.response
                if response.content_type == response.default_content_type:
                    response.content_type = ct
            return body
        return _render

@implementer(IRendererInfo)
class RendererHelper(object):
    def __init__(self, name=None, package=None, registry=None):
        if name and '.' in name:
            rtype = os.path.splitext(name)[1]
        else:
            # important.. must be a string; cannot be None; see issue 249
            rtype = name or ''

        if registry is None:
            registry = get_current_registry()

        self.name = name
        self.package = package
        self.type = rtype
        self.registry = registry

    @reify
    def settings(self):
        settings = self.registry.settings
        if settings is None:
            settings = {}
        return settings

    @reify
    def renderer(self):
        factory = self.registry.queryUtility(IRendererFactory, name=self.type)
        if factory is None:
            raise ValueError(
                'No such renderer factory %s' % str(self.type))
        return factory(self)

    def get_renderer(self):
        return self.renderer

    def render_view(self, request, response, view, context):
        system = {'view':view,
                  'renderer_name':self.name, # b/c
                  'renderer_info':self,
                  'context':context,
                  'request':request,
                  'req':request,
                  }
        return self.render_to_response(response, system, request=request)

    def render(self, value, system_values, request=None):
        renderer = self.renderer
        if system_values is None:
            system_values = {
                'view':None,
                'renderer_name':self.name, # b/c
                'renderer_info':self,
                'context':getattr(request, 'context', None),
                'request':request,
                'req':request,
                }

        system_values = BeforeRender(system_values, value)

        registry = self.registry
        registry.notify(system_values)

        result = renderer(value, system_values)
        return result

    def render_to_response(self, value, system_values, request=None):
        result = self.render(value, system_values, request=request)
        return self._make_response(result, request)

    def _make_response(self, result, request):
        # broken out of render_to_response as a separate method for testing
        # purposes
        response = getattr(request, 'response', None)
        if response is None:
            # request is None or request is not a pyramid.response.Response
            registry = self.registry
            response_factory = _get_response_factory(registry)
            response = response_factory(request)

        if result is not None:
            if isinstance(result, text_type):
                response.text = result
            elif isinstance(result, bytes):
                response.body = result
            elif hasattr(result, '__iter__'):
                response.app_iter = result
            else:
                response.body = result

        return response

    def clone(self, name=None, package=None, registry=None):
        if name is None:
            name = self.name
        if package is None:
            package = self.package
        if registry is None:
            registry = self.registry
        return self.__class__(name=name, package=package, registry=registry)

class NullRendererHelper(RendererHelper):
    """ Special renderer helper that has render_* methods which simply return
    the value they are fed rather than converting them to response objects;
    useful for testing purposes and special case view configuration
    registrations that want to use the view configuration machinery but do
    not want actual rendering to happen ."""
    def __init__(self, name=None, package=None, registry=None):
        # we override the initializer to avoid calling get_current_registry
        # (it will return a reference to the global registry when this
        # thing is called at module scope; we don't want that).
        self.name = None
        self.package = None
        self.type = ''
        self.registry = None

    @property
    def settings(self):
        return {}

    def render_view(self, request, value, view, context):
        return value

    def render(self, value, system_values, request=None):
        return value

    def render_to_response(self, value, system_values, request=None):
        return value

    def clone(self, name=None, package=None, registry=None):
        return self

null_renderer = NullRendererHelper()
