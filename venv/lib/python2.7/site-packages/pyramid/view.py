import venusian

from zope.interface import providedBy

from pyramid.interfaces import (
    IRoutesMapper,
    IView,
    IViewClassifier,
    )

from pyramid.compat import (
    map_,
    decode_path_info,
    )

from pyramid.httpexceptions import (
    HTTPFound,
    default_exceptionresponse_view,
    )

from pyramid.threadlocal import get_current_registry

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
    provides = [IViewClassifier] + map_(providedBy, (request, context))
    try:
        reg = request.registry
    except AttributeError:
        reg = get_current_registry()
    view = reg.adapters.lookup(provides, IView, name=name)
    if view is None:
        return None

    if not secure:
        # the view will have a __call_permissive__ attribute if it's
        # secured; otherwise it won't.
        view = getattr(view, '__call_permissive__', view)

    # if this view is secured, it will raise a Forbidden
    # appropriately if the executing user does not have the proper
    # permission
    return view(context, request)

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
    ``match_param``, ``csrf_token``, ``physical_path``, and ``predicates``.

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
    def __init__(self, notfound_view=None):
        if notfound_view is None:
            notfound_view = default_exceptionresponse_view
        self.notfound_view = notfound_view

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
                    return HTTPFound(location=request.path+'/'+qs)
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
            return Response('Not found, dude!', status='404 Not Found')

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
            return Response('You are not allowed', status='401 Unauthorized')

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

