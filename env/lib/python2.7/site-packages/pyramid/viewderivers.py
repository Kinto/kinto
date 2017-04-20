import inspect

from zope.interface import (
    implementer,
    provider,
    )

from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.session import (
    check_csrf_origin,
    check_csrf_token,
)
from pyramid.response import Response

from pyramid.interfaces import (
    IAuthenticationPolicy,
    IAuthorizationPolicy,
    IDefaultCSRFOptions,
    IDefaultPermission,
    IDebugLogger,
    IResponse,
    IViewMapper,
    IViewMapperFactory,
    )

from pyramid.compat import (
    is_bound_method,
    is_unbound_method,
    )

from pyramid.config.util import (
    DEFAULT_PHASH,
    MAX_ORDER,
    takes_one_arg,
    )

from pyramid.exceptions import (
    ConfigurationError,
    PredicateMismatch,
    )
from pyramid.httpexceptions import HTTPForbidden
from pyramid.util import object_description
from pyramid.view import render_view_to_response
from pyramid import renderers


def view_description(view):
    try:
        return view.__text__
    except AttributeError:
        # custom view mappers might not add __text__
        return object_description(view)

def requestonly(view, attr=None):
    return takes_one_arg(view, attr=attr, argname='request')

@implementer(IViewMapper)
@provider(IViewMapperFactory)
class DefaultViewMapper(object):
    def __init__(self, **kw):
        self.attr = kw.get('attr')

    def __call__(self, view):
        if is_unbound_method(view) and self.attr is None:
            raise ConfigurationError((
                'Unbound method calls are not supported, please set the class '
                'as your `view` and the method as your `attr`'
            ))

        if inspect.isclass(view):
            view = self.map_class(view)
        else:
            view = self.map_nonclass(view)
        return view

    def map_class(self, view):
        ronly = requestonly(view, self.attr)
        if ronly:
            mapped_view = self.map_class_requestonly(view)
        else:
            mapped_view = self.map_class_native(view)
        mapped_view.__text__ = 'method %s of %s' % (
            self.attr or '__call__', object_description(view))
        return mapped_view

    def map_nonclass(self, view):
        # We do more work here than appears necessary to avoid wrapping the
        # view unless it actually requires wrapping (to avoid function call
        # overhead).
        mapped_view = view
        ronly = requestonly(view, self.attr)
        if ronly:
            mapped_view = self.map_nonclass_requestonly(view)
        elif self.attr:
            mapped_view = self.map_nonclass_attr(view)
        if inspect.isroutine(mapped_view):
            # This branch will be true if the view is a function or a method.
            # We potentially mutate an unwrapped object here if it's a
            # function.  We do this to avoid function call overhead of
            # injecting another wrapper.  However, we must wrap if the
            # function is a bound method because we can't set attributes on a
            # bound method.
            if is_bound_method(view):
                _mapped_view = mapped_view
                def mapped_view(context, request):
                    return _mapped_view(context, request)
            if self.attr is not None:
                mapped_view.__text__ = 'attr %s of %s' % (
                    self.attr, object_description(view))
            else:
                mapped_view.__text__ = object_description(view)
        return mapped_view

    def map_class_requestonly(self, view):
        # its a class that has an __init__ which only accepts request
        attr = self.attr
        def _class_requestonly_view(context, request):
            inst = view(request)
            request.__view__ = inst
            if attr is None:
                response = inst()
            else:
                response = getattr(inst, attr)()
            return response
        return _class_requestonly_view

    def map_class_native(self, view):
        # its a class that has an __init__ which accepts both context and
        # request
        attr = self.attr
        def _class_view(context, request):
            inst = view(context, request)
            request.__view__ = inst
            if attr is None:
                response = inst()
            else:
                response = getattr(inst, attr)()
            return response
        return _class_view

    def map_nonclass_requestonly(self, view):
        # its a function that has a __call__ which accepts only a single
        # request argument
        attr = self.attr
        def _requestonly_view(context, request):
            if attr is None:
                response = view(request)
            else:
                response = getattr(view, attr)(request)
            return response
        return _requestonly_view

    def map_nonclass_attr(self, view):
        # its a function that has a __call__ which accepts both context and
        # request, but still has an attr
        def _attr_view(context, request):
            response = getattr(view, self.attr)(context, request)
            return response
        return _attr_view


def wraps_view(wrapper):
    def inner(view, info):
        wrapper_view = wrapper(view, info)
        return preserve_view_attrs(view, wrapper_view)
    return inner

def preserve_view_attrs(view, wrapper):
    if view is None:
        return wrapper

    if wrapper is view:
        return view

    original_view = getattr(view, '__original_view__', None)

    if original_view is None:
        original_view = view

    wrapper.__wraps__ = view
    wrapper.__original_view__ = original_view
    wrapper.__module__ = view.__module__
    wrapper.__doc__ = view.__doc__

    try:
        wrapper.__name__ = view.__name__
    except AttributeError:
        wrapper.__name__ = repr(view)

    # attrs that may not exist on "view", but, if so, must be attached to
    # "wrapped view"
    for attr in ('__permitted__', '__call_permissive__', '__permission__',
                 '__predicated__', '__predicates__', '__accept__',
                 '__order__', '__text__'):
        try:
            setattr(wrapper, attr, getattr(view, attr))
        except AttributeError:
            pass

    return wrapper

def mapped_view(view, info):
    mapper = info.options.get('mapper')
    if mapper is None:
        mapper = getattr(view, '__view_mapper__', None)
        if mapper is None:
            mapper = info.registry.queryUtility(IViewMapperFactory)
            if mapper is None:
                mapper = DefaultViewMapper

    mapped_view = mapper(**info.options)(view)
    return mapped_view

mapped_view.options = ('mapper', 'attr')

def owrapped_view(view, info):
    wrapper_viewname = info.options.get('wrapper')
    viewname = info.options.get('name')
    if not wrapper_viewname:
        return view
    def _owrapped_view(context, request):
        response = view(context, request)
        request.wrapped_response = response
        request.wrapped_body = response.body
        request.wrapped_view = view
        wrapped_response = render_view_to_response(context, request,
                                                   wrapper_viewname)
        if wrapped_response is None:
            raise ValueError(
                'No wrapper view named %r found when executing view '
                'named %r' % (wrapper_viewname, viewname))
        return wrapped_response
    return _owrapped_view

owrapped_view.options = ('name', 'wrapper')

def http_cached_view(view, info):
    if info.settings.get('prevent_http_cache', False):
        return view

    seconds = info.options.get('http_cache')

    if seconds is None:
        return view

    options = {}

    if isinstance(seconds, (tuple, list)):
        try:
            seconds, options = seconds
        except ValueError:
            raise ConfigurationError(
                'If http_cache parameter is a tuple or list, it must be '
                'in the form (seconds, options); not %s' % (seconds,))

    def wrapper(context, request):
        response = view(context, request)
        prevent_caching = getattr(response.cache_control, 'prevent_auto',
                                  False)
        if not prevent_caching:
            response.cache_expires(seconds, **options)
        return response

    return wrapper

http_cached_view.options = ('http_cache',)

def secured_view(view, info):
    for wrapper in (_secured_view, _authdebug_view):
        view = wraps_view(wrapper)(view, info)
    return view

secured_view.options = ('permission',)

def _secured_view(view, info):
    permission = explicit_val = info.options.get('permission')
    if permission is None:
        permission = info.registry.queryUtility(IDefaultPermission)
    if permission == NO_PERMISSION_REQUIRED:
        # allow views registered within configurations that have a
        # default permission to explicitly override the default
        # permission, replacing it with no permission at all
        permission = None

    wrapped_view = view
    authn_policy = info.registry.queryUtility(IAuthenticationPolicy)
    authz_policy = info.registry.queryUtility(IAuthorizationPolicy)

    if authn_policy and authz_policy and (permission is not None):
        def _permitted(context, request):
            principals = authn_policy.effective_principals(request)
            return authz_policy.permits(context, principals, permission)
        def _secured_view(context, request):
            if (
                getattr(request, 'exception', None) is not None and
                explicit_val is None
            ):
                return view(context, request)

            result = _permitted(context, request)
            if result:
                return view(context, request)
            view_name = getattr(view, '__name__', view)
            msg = getattr(
                request, 'authdebug_message',
                'Unauthorized: %s failed permission check' % view_name)
            raise HTTPForbidden(msg, result=result)
        _secured_view.__call_permissive__ = view
        _secured_view.__permitted__ = _permitted
        _secured_view.__permission__ = permission
        wrapped_view = _secured_view

    return wrapped_view

def _authdebug_view(view, info):
    wrapped_view = view
    settings = info.settings
    permission = explicit_val = info.options.get('permission')
    if permission is None:
        permission = info.registry.queryUtility(IDefaultPermission)
    authn_policy = info.registry.queryUtility(IAuthenticationPolicy)
    authz_policy = info.registry.queryUtility(IAuthorizationPolicy)
    logger = info.registry.queryUtility(IDebugLogger)
    if settings and settings.get('debug_authorization', False):
        def _authdebug_view(context, request):
            if (
                getattr(request, 'exception', None) is not None and
                explicit_val is None
            ):
                return view(context, request)

            view_name = getattr(request, 'view_name', None)

            if authn_policy and authz_policy:
                if permission is NO_PERMISSION_REQUIRED:
                    msg = 'Allowed (NO_PERMISSION_REQUIRED)'
                elif permission is None:
                    msg = 'Allowed (no permission registered)'
                else:
                    principals = authn_policy.effective_principals(request)
                    msg = str(authz_policy.permits(
                        context, principals, permission))
            else:
                msg = 'Allowed (no authorization policy in use)'

            view_name = getattr(request, 'view_name', None)
            url = getattr(request, 'url', None)
            msg = ('debug_authorization of url %s (view name %r against '
                   'context %r): %s' % (url, view_name, context, msg))
            if logger:
                logger.debug(msg)
            if request is not None:
                request.authdebug_message = msg
            return view(context, request)

        wrapped_view = _authdebug_view

    return wrapped_view

def predicated_view(view, info):
    preds = info.predicates
    if not preds:
        return view
    def predicate_wrapper(context, request):
        for predicate in preds:
            if not predicate(context, request):
                view_name = getattr(view, '__name__', view)
                raise PredicateMismatch(
                    'predicate mismatch for view %s (%s)' % (
                        view_name, predicate.text()))
        return view(context, request)
    def checker(context, request):
        return all((predicate(context, request) for predicate in
                    preds))
    predicate_wrapper.__predicated__ = checker
    predicate_wrapper.__predicates__ = preds
    return predicate_wrapper

def attr_wrapped_view(view, info):
    accept, order, phash = (info.options.get('accept', None),
                            getattr(info, 'order', MAX_ORDER),
                            getattr(info, 'phash', DEFAULT_PHASH))
    # this is a little silly but we don't want to decorate the original
    # function with attributes that indicate accept, order, and phash,
    # so we use a wrapper
    if (
        (accept is None) and
        (order == MAX_ORDER) and
        (phash == DEFAULT_PHASH)
    ):
        return view # defaults
    def attr_view(context, request):
        return view(context, request)
    attr_view.__accept__ = accept
    attr_view.__order__ = order
    attr_view.__phash__ = phash
    attr_view.__view_attr__ = info.options.get('attr')
    attr_view.__permission__ = info.options.get('permission')
    return attr_view

attr_wrapped_view.options = ('accept', 'attr', 'permission')

def rendered_view(view, info):
    # one way or another this wrapper must produce a Response (unless
    # the renderer is a NullRendererHelper)
    renderer = info.options.get('renderer')
    if renderer is None:
        # register a default renderer if you want super-dynamic
        # rendering.  registering a default renderer will also allow
        # override_renderer to work if a renderer is left unspecified for
        # a view registration.
        def viewresult_to_response(context, request):
            result = view(context, request)
            if result.__class__ is Response: # common case
                response = result
            else:
                response = info.registry.queryAdapterOrSelf(result, IResponse)
                if response is None:
                    if result is None:
                        append = (' You may have forgotten to return a value '
                                  'from the view callable.')
                    elif isinstance(result, dict):
                        append = (' You may have forgotten to define a '
                                  'renderer in the view configuration.')
                    else:
                        append = ''

                    msg = ('Could not convert return value of the view '
                           'callable %s into a response object. '
                           'The value returned was %r.' + append)

                    raise ValueError(msg % (view_description(view), result))

            return response

        return viewresult_to_response

    if renderer is renderers.null_renderer:
        return view

    def rendered_view(context, request):
        result = view(context, request)
        if result.__class__ is Response: # potential common case
            response = result
        else:
            # this must adapt, it can't do a simple interface check
            # (avoid trying to render webob responses)
            response = info.registry.queryAdapterOrSelf(result, IResponse)
            if response is None:
                attrs = getattr(request, '__dict__', {})
                if 'override_renderer' in attrs:
                    # renderer overridden by newrequest event or other
                    renderer_name = attrs.pop('override_renderer')
                    view_renderer = renderers.RendererHelper(
                        name=renderer_name,
                        package=info.package,
                        registry=info.registry)
                else:
                    view_renderer = renderer.clone()
                if '__view__' in attrs:
                    view_inst = attrs.pop('__view__')
                else:
                    view_inst = getattr(view, '__original_view__', view)
                response = view_renderer.render_view(
                    request, result, view_inst, context)
        return response

    return rendered_view

rendered_view.options = ('renderer',)

def decorated_view(view, info):
    decorator = info.options.get('decorator')
    if decorator is None:
        return view
    return decorator(view)

decorated_view.options = ('decorator',)

def csrf_view(view, info):
    explicit_val = info.options.get('require_csrf')
    defaults = info.registry.queryUtility(IDefaultCSRFOptions)
    if defaults is None:
        default_val = False
        token = 'csrf_token'
        header = 'X-CSRF-Token'
        safe_methods = frozenset(["GET", "HEAD", "OPTIONS", "TRACE"])
    else:
        default_val = defaults.require_csrf
        token = defaults.token
        header = defaults.header
        safe_methods = defaults.safe_methods
    enabled = (
        explicit_val is True or
        (explicit_val is not False and default_val)
    )
    # disable if both header and token are disabled
    enabled = enabled and (token or header)
    wrapped_view = view
    if enabled:
        def csrf_view(context, request):
            if (
                request.method not in safe_methods and
                (
                    # skip exception views unless value is explicitly defined
                    getattr(request, 'exception', None) is None or
                    explicit_val is not None
                )
            ):
                check_csrf_origin(request, raises=True)
                check_csrf_token(request, token, header, raises=True)
            return view(context, request)
        wrapped_view = csrf_view
    return wrapped_view

csrf_view.options = ('require_csrf',)

VIEW = 'VIEW'
INGRESS = 'INGRESS'
