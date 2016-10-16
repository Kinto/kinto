import itertools
import sys

import venusian

from zope.interface import providedBy

from pyramid.interfaces import (
    IRoutesMapper,
    IMultiView,
    ISecuredView,
    IView,
    IViewClassifier,
    IRequest,
    IExceptionViewClassifier,
    )

from pyramid.compat import decode_path_info

from pyramid.exceptions import PredicateMismatch

from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    default_exceptionresponse_view,
    )

from pyramid.threadlocal import get_current_registry
from pyramid.util import hide_attrs

_marker = object()

def render_view_to_response(context, request, name='', secure=True):
    """ Call the :term:`view callable` configured with a :term:`view
    configuration` that matches the :term:`view name` ``name``
    registered against the specified ``context`` and ``request`` and
    return a :term:`response` object.  This function will return
    ``None`` if a corresponding :term:`view callable` cannot be found
    (when no :term:`view configuration` matches the combination of
    ``name`` / ``context`` / and ``request``).

    If `secure`` is ``True``, and the :term:`view callable` found is
    protected by a permission, the permission will be checked before calling
    the view function.  If the permission check disallows view execution
    (based on the current :term:`authorization policy`), a
    :exc:`pyramid.httpexceptions.HTTPForbidden` exception will be raised.
    The exception's ``args`` attribute explains why the view access was
    disallowed.

    If ``secure`` is ``False``, no permission checking is done."""

    registry = getattr(request, 'registry', None)
    if registry is None:
        registry = get_current_registry()

    context_iface = providedBy(context)
    # We explicitly pass in the interfaces provided by the request as
    # request_iface to _call_view; we don't want _call_view to use
    # request.request_iface, because render_view_to_response and friends are
    # pretty much limited to finding views that are not views associated with
    # routes, and the only thing request.request_iface is used for is to find
    # route-based views.  The render_view_to_response API is (and always has
    # been) a stepchild API reserved for use of those who actually use
    # traversal.  Doing this fixes an infinite recursion bug introduced in
    # Pyramid 1.6a1, and causes the render_view* APIs to behave as they did in
    # 1.5 and previous. We should probably provide some sort of different API
    # that would allow people to find views for routes.  See
    # https://github.com/Pylons/pyramid/issues/1643 for more info.
    request_iface = providedBy(request)

    response = _call_view(
        registry,
        request,
        context,
        context_iface,
        name,
        secure=secure,
        request_iface=request_iface,
        )

    return response # NB: might be None


def render_view_to_iterable(context, request, name='', secure=True):
    """ Call the :term:`view callable` configured with a :term:`view
    configuration` that matches the :term:`view name` ``name``
    registered against the specified ``context`` and ``request`` and
    return an iterable object which represents the body of a response.
    This function will return ``None`` if a corresponding :term:`view
    callable` cannot be found (when no :term:`view configuration`
    matches the combination of ``name`` / ``context`` / and
    ``request``).  Additionally, this function will raise a
    :exc:`ValueError` if a view function is found and called but the
    view function's result does not have an ``app_iter`` attribute.

    You can usually get the bytestring representation of the return value of
    this function by calling ``b''.join(iterable)``, or just use
    :func:`pyramid.view.render_view` instead.

    If ``secure`` is ``True``, and the view is protected by a permission, the
    permission will be checked before the view function is invoked.  If the
    permission check disallows view execution (based on the current
    :term:`authentication policy`), a
    :exc:`pyramid.httpexceptions.HTTPForbidden` exception will be raised; its
    ``args`` attribute explains why the view access was disallowed.

    If ``secure`` is ``False``, no permission checking is
    done."""
    response = render_view_to_response(context, request, name, secure)
    if response is None:
        return None
    return response.app_iter

def render_view(context, request, name='', secure=True):
    """ Call the :term:`view callable` configured with a :term:`view
    configuration` that matches the :term:`view name` ``name``
    registered against the specified ``context`` and ``request``
    and unwind the view response's ``app_iter`` (see
    :ref:`the_response`) into a single bytestring.  This function will
    return ``None`` if a corresponding :term:`view callable` cannot be
    found (when no :term:`view configuration` matches the combination
    of ``name`` / ``context`` / and ``request``).  Additionally, this
    function will raise a :exc:`ValueError` if a view function is
    found and called but the view function's result does not have an
    ``app_iter`` attribute. This function will return ``None`` if a
    corresponding view cannot be found.

    If ``secure`` is ``True``, and the view is protected by a permission, the
    permission will be checked before the view is invoked.  If the permission
    check disallows view execution (based on the current :term:`authorization
    policy`), a :exc:`pyramid.httpexceptions.HTTPForbidden` exception will be
    raised; its ``args`` attribute explains why the view access was
    disallowed.

    If ``secure`` is ``False``, no permission checking is done."""
    iterable = render_view_to_iterable(context, request, name, secure)
    if iterable is None:
        return None
    return b''.join(iterable)

class view_config(object):
    """ A function, class or method :term:`decorator` which allows a
    developer to create view registrations nearer to a :term:`view
    callable` definition than use :term:`imperative
    configuration` to do the same.

    For example, this code in a module ``views.py``::

      from resources import MyResource

      @view_config(name='my_view', context=MyResource, permission='read',
                   route_name='site1')
      def my_view(context, request):
          return 'OK'

    Might replace the following call to the
    :meth:`pyramid.config.Configurator.add_view` method::

       import views
       from resources import MyResource
       config.add_view(views.my_view, context=MyResource, name='my_view',
                       permission='read', route_name='site1')

    .. note: :class:`pyramid.view.view_config` is also importable, for
             backwards compatibility purposes, as the name
             :class:`pyramid.view.bfg_view`.

    :class:`pyramid.view.view_config` supports the following keyword
    arguments: ``context``, ``permission``, ``name``,
    ``request_type``, ``route_name``, ``request_method``, ``request_param``,
    ``containment``, ``xhr``, ``accept``, ``header``, ``path_info``,
    ``custom_predicates``, ``decorator``, ``mapper``, ``http_cache``,
    ``require_csrf``, ``match_param``, ``check_csrf``, ``physical_path``, and
    ``view_options``.

    The meanings of these arguments are the same as the arguments passed to
    :meth:`pyramid.config.Configurator.add_view`.  If any argument is left
    out, its default will be the equivalent ``add_view`` default.

    An additional keyword argument named ``_depth`` is provided for people who
    wish to reuse this class from another decorator.  The default value is
    ``0`` and should be specified relative to the ``view_config`` invocation.
    It will be passed in to the :term:`venusian` ``attach`` function as the
    depth of the callstack when Venusian checks if the decorator is being used
    in a class or module context.  It's not often used, but it can be useful
    in this circumstance.  See the ``attach`` function in Venusian for more
    information.
    
    .. seealso::
    
        See also :ref:`mapping_views_using_a_decorator_section` for
        details about using :class:`pyramid.view.view_config`.

    .. warning::
    
        ``view_config`` will work ONLY on module top level members
        because of the limitation of ``venusian.Scanner.scan``.

    """
    venusian = venusian # for testing injection
    def __init__(self, **settings):
        if 'for_' in settings:
            if settings.get('context') is None:
                settings['context'] = settings['for_']
        self.__dict__.update(settings)

    def __call__(self, wrapped):
        settings = self.__dict__.copy()
        depth = settings.pop('_depth', 0)

        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            config.add_view(view=ob, **settings)

        info = self.venusian.attach(wrapped, callback, category='pyramid',
                                    depth=depth + 1)

        if info.scope == 'class':
            # if the decorator was attached to a method in a class, or
            # otherwise executed at class scope, we need to set an
            # 'attr' into the settings if one isn't already in there
            if settings.get('attr') is None:
                settings['attr'] = wrapped.__name__

        settings['_info'] = info.codeinfo # fbo "action_method"
        return wrapped

bfg_view = view_config # bw compat (forever)

class view_defaults(view_config):
    """ A class :term:`decorator` which, when applied to a class, will
    provide defaults for all view configurations that use the class.  This
    decorator accepts all the arguments accepted by
    :meth:`pyramid.view.view_config`, and each has the same meaning.

    See :ref:`view_defaults` for more information.
    """

    def __call__(self, wrapped):
        wrapped.__view_defaults__ = self.__dict__.copy()
        return wrapped

class AppendSlashNotFoundViewFactory(object):
    """ There can only be one :term:`Not Found view` in any
    :app:`Pyramid` application.  Even if you use
    :func:`pyramid.view.append_slash_notfound_view` as the Not
    Found view, :app:`Pyramid` still must generate a ``404 Not
    Found`` response when it cannot redirect to a slash-appended URL;
    this not found response will be visible to site users.

    If you don't care what this 404 response looks like, and you only
    need redirections to slash-appended route URLs, you may use the
    :func:`pyramid.view.append_slash_notfound_view` object as the
    Not Found view.  However, if you wish to use a *custom* notfound
    view callable when a URL cannot be redirected to a slash-appended
    URL, you may wish to use an instance of this class as the Not
    Found view, supplying a :term:`view callable` to be used as the
    custom notfound view as the first argument to its constructor.
    For instance:

    .. code-block:: python

       from pyramid.httpexceptions import HTTPNotFound
       from pyramid.view import AppendSlashNotFoundViewFactory

       def notfound_view(context, request): return HTTPNotFound('nope')

       custom_append_slash = AppendSlashNotFoundViewFactory(notfound_view)
       config.add_view(custom_append_slash, context=HTTPNotFound)

    The ``notfound_view`` supplied must adhere to the two-argument
    view callable calling convention of ``(context, request)``
    (``context`` will be the exception object).

    .. deprecated:: 1.3

    """
    def __init__(self, notfound_view=None, redirect_class=HTTPFound):
        if notfound_view is None:
            notfound_view = default_exceptionresponse_view
        self.notfound_view = notfound_view
        self.redirect_class = redirect_class

    def __call__(self, context, request):
        path = decode_path_info(request.environ['PATH_INFO'] or '/')
        registry = request.registry
        mapper = registry.queryUtility(IRoutesMapper)
        if mapper is not None and not path.endswith('/'):
            slashpath = path + '/'
            for route in mapper.get_routes():
                if route.match(slashpath) is not None:
                    qs = request.query_string
                    if qs:
                        qs = '?' + qs
                    return self.redirect_class(location=request.path + '/' + qs)
        return self.notfound_view(context, request)

append_slash_notfound_view = AppendSlashNotFoundViewFactory()
append_slash_notfound_view.__doc__ = """\
For behavior like Django's ``APPEND_SLASH=True``, use this view as the
:term:`Not Found view` in your application.

When this view is the Not Found view (indicating that no view was found), and
any routes have been defined in the configuration of your application, if the
value of the ``PATH_INFO`` WSGI environment variable does not already end in
a slash, and if the value of ``PATH_INFO`` *plus* a slash matches any route's
path, do an HTTP redirect to the slash-appended PATH_INFO.  Note that this
will *lose* ``POST`` data information (turning it into a GET), so you
shouldn't rely on this to redirect POST requests.  Note also that static
routes are not considered when attempting to find a matching route.

Use the :meth:`pyramid.config.Configurator.add_view` method to configure this
view as the Not Found view::

  from pyramid.httpexceptions import HTTPNotFound
  from pyramid.view import append_slash_notfound_view
  config.add_view(append_slash_notfound_view, context=HTTPNotFound)

.. deprecated:: 1.3

"""

class notfound_view_config(object):
    """
    .. versionadded:: 1.3

    An analogue of :class:`pyramid.view.view_config` which registers a
    :term:`Not Found View`.

    The ``notfound_view_config`` constructor accepts most of the same arguments
    as the constructor of :class:`pyramid.view.view_config`.  It can be used
    in the same places, and behaves in largely the same way, except it always
    registers a not found exception view instead of a 'normal' view.

    Example:

    .. code-block:: python

        from pyramid.view import notfound_view_config
        from pyramid.response import Response

        @notfound_view_config()
        def notfound(request):
            return Response('Not found!', status='404 Not Found')

    All arguments except ``append_slash`` have the same meaning as
    :meth:`pyramid.view.view_config` and each predicate
    argument restricts the set of circumstances under which this notfound
    view will be invoked.

    If ``append_slash`` is ``True``, when the Not Found View is invoked, and
    the current path info does not end in a slash, the notfound logic will
    attempt to find a :term:`route` that matches the request's path info
    suffixed with a slash.  If such a route exists, Pyramid will issue a
    redirect to the URL implied by the route; if it does not, Pyramid will
    return the result of the view callable provided as ``view``, as normal.

    If the argument provided as ``append_slash`` is not a boolean but
    instead implements :class:`~pyramid.interfaces.IResponse`, the
    append_slash logic will behave as if ``append_slash=True`` was passed,
    but the provided class will be used as the response class instead of
    the default :class:`~pyramid.httpexceptions.HTTPFound` response class
    when a redirect is performed.  For example:

      .. code-block:: python

        from pyramid.httpexceptions import (
            HTTPMovedPermanently,
            HTTPNotFound
            )

        @notfound_view_config(append_slash=HTTPMovedPermanently)
        def aview(request):
            return HTTPNotFound('not found')

    The above means that a redirect to a slash-appended route will be
    attempted, but instead of :class:`~pyramid.httpexceptions.HTTPFound`
    being used, :class:`~pyramid.httpexceptions.HTTPMovedPermanently will
    be used` for the redirect response if a slash-appended route is found.

    .. versionchanged:: 1.6

    See :ref:`changing_the_notfound_view` for detailed usage information.

    """

    venusian = venusian

    def __init__(self, **settings):
        self.__dict__.update(settings)

    def __call__(self, wrapped):
        settings = self.__dict__.copy()

        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            config.add_notfound_view(view=ob, **settings)

        info = self.venusian.attach(wrapped, callback, category='pyramid')

        if info.scope == 'class':
            # if the decorator was attached to a method in a class, or
            # otherwise executed at class scope, we need to set an
            # 'attr' into the settings if one isn't already in there
            if settings.get('attr') is None:
                settings['attr'] = wrapped.__name__

        settings['_info'] = info.codeinfo # fbo "action_method"
        return wrapped

class forbidden_view_config(object):
    """
    .. versionadded:: 1.3

    An analogue of :class:`pyramid.view.view_config` which registers a
    :term:`forbidden view`.

    The forbidden_view_config constructor accepts most of the same arguments
    as the constructor of :class:`pyramid.view.view_config`.  It can be used
    in the same places, and behaves in largely the same way, except it always
    registers a forbidden exception view instead of a 'normal' view.

    Example:

    .. code-block:: python

        from pyramid.view import forbidden_view_config
        from pyramid.response import Response

        @forbidden_view_config()
        def forbidden(request):
            return Response('You are not allowed', status='403 Forbidden')

    All arguments passed to this function have the same meaning as
    :meth:`pyramid.view.view_config` and each predicate argument restricts
    the set of circumstances under which this notfound view will be invoked.

    See :ref:`changing_the_forbidden_view` for detailed usage information.

    """

    venusian = venusian

    def __init__(self, **settings):
        self.__dict__.update(settings)

    def __call__(self, wrapped):
        settings = self.__dict__.copy()

        def callback(context, name, ob):
            config = context.config.with_package(info.module)
            config.add_forbidden_view(view=ob, **settings)

        info = self.venusian.attach(wrapped, callback, category='pyramid')

        if info.scope == 'class':
            # if the decorator was attached to a method in a class, or
            # otherwise executed at class scope, we need to set an
            # 'attr' into the settings if one isn't already in there
            if settings.get('attr') is None:
                settings['attr'] = wrapped.__name__

        settings['_info'] = info.codeinfo # fbo "action_method"
        return wrapped

def _find_views(
    registry,
    request_iface,
    context_iface,
    view_name,
    view_types=None,
    view_classifier=None,
    ):
    if view_types is None:
        view_types = (IView, ISecuredView, IMultiView)
    if view_classifier is None:
        view_classifier = IViewClassifier
    registered = registry.adapters.registered
    cache = registry._view_lookup_cache
    views = cache.get((request_iface, context_iface, view_name))
    if views is None:
        views = []
        for req_type, ctx_type in itertools.product(
            request_iface.__sro__, context_iface.__sro__
        ):
            source_ifaces = (view_classifier, req_type, ctx_type)
            for view_type in view_types:
                view_callable = registered(
                    source_ifaces,
                    view_type,
                    name=view_name,
                )
                if view_callable is not None:
                    views.append(view_callable)
        if views:
            # do not cache view lookup misses.  rationale: dont allow cache to
            # grow without bound if somebody tries to hit the site with many
            # missing URLs.  we could use an LRU cache instead, but then
            # purposeful misses by an attacker would just blow out the cache
            # anyway. downside: misses will almost always consume more CPU than
            # hits in steady state.
            with registry._lock:
                cache[(request_iface, context_iface, view_name)] = views

    return views

def _call_view(
    registry,
    request,
    context,
    context_iface,
    view_name,
    view_types=None,
    view_classifier=None,
    secure=True,
    request_iface=None,
    ):
    if request_iface is None:
        request_iface = getattr(request, 'request_iface', IRequest)
    view_callables = _find_views(
        registry,
        request_iface,
        context_iface,
        view_name,
        view_types=view_types,
        view_classifier=view_classifier,
        )

    pme = None
    response = None

    for view_callable in view_callables:
        # look for views that meet the predicate criteria
        try:
            if not secure:
                # the view will have a __call_permissive__ attribute if it's
                # secured; otherwise it won't.
                view_callable = getattr(
                    view_callable,
                    '__call_permissive__',
                    view_callable
                    )

            # if this view is secured, it will raise a Forbidden
            # appropriately if the executing user does not have the proper
            # permission
            response = view_callable(context, request)
            return response
        except PredicateMismatch as _pme:
            pme = _pme

    if pme is not None:
        raise pme

    return response

class ViewMethodsMixin(object):
    """ Request methods mixin for BaseRequest having to do with executing
    views """
    def invoke_exception_view(
        self,
        exc_info=None,
        request=None,
        secure=True
        ):
        """ Executes an exception view related to the request it's called upon.
        The arguments it takes are these:

        ``exc_info``

            If provided, should be a 3-tuple in the form provided by
            ``sys.exc_info()``.  If not provided,
            ``sys.exc_info()`` will be called to obtain the current
            interpreter exception information.  Default: ``None``.

        ``request``

            If the request to be used is not the same one as the instance that
            this method is called upon, it may be passed here.  Default:
            ``None``.

        ``secure``

            If the exception view should not be rendered if the current user
            does not have the appropriate permission, this should be ``True``.
            Default: ``True``.

        If called with no arguments, it uses the global exception information
        returned by ``sys.exc_info()`` as ``exc_info``, the request
        object that this method is attached to as the ``request``, and
        ``True`` for ``secure``.

        This method returns a :term:`response` object or raises
        :class:`pyramid.httpexceptions.HTTPNotFound` if a matching view cannot
        be found."""

        if request is None:
            request = self
        registry = getattr(request, 'registry', None)
        if registry is None:
            registry = get_current_registry()
        if exc_info is None:
            exc_info = sys.exc_info()
        exc = exc_info[1]
        attrs = request.__dict__
        context_iface = providedBy(exc)

        # clear old generated request.response, if any; it may
        # have been mutated by the view, and its state is not
        # sane (e.g. caching headers)
        with hide_attrs(request, 'exception', 'exc_info', 'response'):
            attrs['exception'] = exc
            attrs['exc_info'] = exc_info
            # we use .get instead of .__getitem__ below due to
            # https://github.com/Pylons/pyramid/issues/700
            request_iface = attrs.get('request_iface', IRequest)
            response = _call_view(
                registry,
                request,
                exc,
                context_iface,
                '',
                view_types=None,
                view_classifier=IExceptionViewClassifier,
                secure=secure,
                request_iface=request_iface.combined,
                )
            if response is None:
                raise HTTPNotFound
            return response
