import inspect
import operator
import os
import warnings

from zope.interface import (
    Interface,
    implementedBy,
    implementer,
    provider,
    )

from zope.interface.interfaces import IInterface

from pyramid.interfaces import (
    IAuthenticationPolicy,
    IAuthorizationPolicy,
    IDebugLogger,
    IDefaultPermission,
    IException,
    IExceptionViewClassifier,
    IMultiView,
    IRendererFactory,
    IRequest,
    IResponse,
    IRouteRequest,
    ISecuredView,
    IStaticURLInfo,
    IView,
    IViewClassifier,
    IViewMapper,
    IViewMapperFactory,
    PHASE1_CONFIG,
    )

from pyramid import renderers

from pyramid.compat import (
    string_types,
    urlparse,
    url_quote,
    WIN,
    is_bound_method,
    is_nonstr_iter
    )

from pyramid.encode import (
    quote_plus,
    urlencode,
)

from pyramid.exceptions import (
    ConfigurationError,
    PredicateMismatch,
    )

from pyramid.httpexceptions import (
    HTTPForbidden,
    HTTPNotFound,
    )

from pyramid.registry import (
    predvalseq,
    Deferred,
    )

from pyramid.response import Response

from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.static import static_view
from pyramid.threadlocal import get_current_registry

from pyramid.url import parse_url_overrides

from pyramid.view import (
    render_view_to_response,
    AppendSlashNotFoundViewFactory,
    )

from pyramid.util import (
    object_description,
    viewdefaults,
    action_method,
    )

import pyramid.config.predicates

from pyramid.config.util import (
    DEFAULT_PHASH,
    MAX_ORDER,
    takes_one_arg,
    )

urljoin = urlparse.urljoin
url_parse = urlparse.urlparse

def view_description(view):
    try:
        return view.__text__
    except AttributeError:
        # custom view mappers might not add __text__
        return object_description(view)

def wraps_view(wrapper):
    def inner(self, view):
        wrapper_view = wrapper(self, view)
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

class ViewDeriver(object):
    def __init__(self, **kw):
        self.kw = kw
        self.registry = kw['registry']
        self.authn_policy = self.registry.queryUtility(IAuthenticationPolicy)
        self.authz_policy = self.registry.queryUtility(IAuthorizationPolicy)
        self.logger = self.registry.queryUtility(IDebugLogger)

    def __call__(self, view):
        return self.attr_wrapped_view(
            self.predicated_view(
                self.authdebug_view(
                    self.secured_view(
                        self.owrapped_view(
                            self.http_cached_view(
                                self.decorated_view(
                                    self.rendered_view(
                                        self.mapped_view(
                                                view)))))))))

    @wraps_view
    def mapped_view(self, view):
        mapper = self.kw.get('mapper')
        if mapper is None:
            mapper = getattr(view, '__view_mapper__', None)
            if mapper is None:
                mapper = self.registry.queryUtility(IViewMapperFactory)
                if mapper is None:
                    mapper = DefaultViewMapper

        mapped_view = mapper(**self.kw)(view)
        return mapped_view

    @wraps_view
    def owrapped_view(self, view):
        wrapper_viewname = self.kw.get('wrapper_viewname')
        viewname = self.kw.get('viewname')
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

    @wraps_view
    def http_cached_view(self, view):
        if self.registry.settings.get('prevent_http_cache', False):
            return view

        seconds = self.kw.get('http_cache')

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

    @wraps_view
    def secured_view(self, view):
        permission = self.kw.get('permission')
        if permission == NO_PERMISSION_REQUIRED:
            # allow views registered within configurations that have a
            # default permission to explicitly override the default
            # permission, replacing it with no permission at all
            permission = None

        wrapped_view = view
        if self.authn_policy and self.authz_policy and (permission is not None):
            def _permitted(context, request):
                principals = self.authn_policy.effective_principals(request)
                return self.authz_policy.permits(context, principals,
                                                 permission)
            def _secured_view(context, request):
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

    @wraps_view
    def authdebug_view(self, view):
        wrapped_view = view
        settings = self.registry.settings
        permission = self.kw.get('permission')
        if settings and settings.get('debug_authorization', False):
            def _authdebug_view(context, request):
                view_name = getattr(request, 'view_name', None)

                if self.authn_policy and self.authz_policy:
                    if permission is NO_PERMISSION_REQUIRED:
                        msg = 'Allowed (NO_PERMISSION_REQUIRED)'
                    elif permission is None:
                        msg = 'Allowed (no permission registered)'
                    else:
                        principals = self.authn_policy.effective_principals(
                            request)
                        msg = str(self.authz_policy.permits(context, principals,
                                                            permission))
                else:
                    msg = 'Allowed (no authorization policy in use)'

                view_name = getattr(request, 'view_name', None)
                url = getattr(request, 'url', None)
                msg = ('debug_authorization of url %s (view name %r against '
                       'context %r): %s' % (url, view_name, context, msg))
                self.logger and self.logger.debug(msg)
                if request is not None:
                    request.authdebug_message = msg
                return view(context, request)

            wrapped_view = _authdebug_view

        return wrapped_view

    @wraps_view
    def predicated_view(self, view):
        preds = self.kw.get('predicates', ())
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

    @wraps_view
    def attr_wrapped_view(self, view):
        kw = self.kw
        accept, order, phash = (kw.get('accept', None),
                                kw.get('order', MAX_ORDER),
                                kw.get('phash', DEFAULT_PHASH))
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
        attr_view.__view_attr__ = self.kw.get('attr')
        attr_view.__permission__ = self.kw.get('permission')
        return attr_view

    @wraps_view
    def rendered_view(self, view):
        # one way or another this wrapper must produce a Response (unless
        # the renderer is a NullRendererHelper)
        renderer = self.kw.get('renderer')
        if renderer is None:
            # register a default renderer if you want super-dynamic
            # rendering.  registering a default renderer will also allow
            # override_renderer to work if a renderer is left unspecified for
            # a view registration.
            return self._response_resolved_view(view)
        if renderer is renderers.null_renderer:
            return view
        return self._rendered_view(view, renderer)

    def _rendered_view(self, view, view_renderer):
        def rendered_view(context, request):
            renderer = view_renderer
            result = view(context, request)
            if result.__class__ is Response: # potential common case
                response = result
            else:
                registry = self.registry
                # this must adapt, it can't do a simple interface check
                # (avoid trying to render webob responses)
                response = registry.queryAdapterOrSelf(result, IResponse)
                if response is None:
                    attrs = getattr(request, '__dict__', {})
                    if 'override_renderer' in attrs:
                        # renderer overridden by newrequest event or other
                        renderer_name = attrs.pop('override_renderer')
                        renderer = renderers.RendererHelper(
                            name=renderer_name,
                            package=self.kw.get('package'),
                            registry = registry)
                    if '__view__' in attrs:
                        view_inst = attrs.pop('__view__')
                    else:
                        view_inst = getattr(view, '__original_view__', view)
                    response = renderer.render_view(request, result, view_inst,
                                                    context)
            return response

        return rendered_view

    def _response_resolved_view(self, view):
        registry = self.registry
        def viewresult_to_response(context, request):
            result = view(context, request)
            if result.__class__ is Response: # common case
                response = result
            else:
                response = registry.queryAdapterOrSelf(result, IResponse)
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

    @wraps_view
    def decorated_view(self, view):
        decorator = self.kw.get('decorator')
        if decorator is None:
            return view
        return decorator(view)

@implementer(IViewMapper)
@provider(IViewMapperFactory)
class DefaultViewMapper(object):
    def __init__(self, **kw):
        self.attr = kw.get('attr')

    def __call__(self, view):
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

def requestonly(view, attr=None):
    return takes_one_arg(view, attr=attr, argname='request')

@implementer(IMultiView)
class MultiView(object):

    def __init__(self, name):
        self.name = name
        self.media_views = {}
        self.views = []
        self.accepts = []

    def __discriminator__(self, context, request):
        # used by introspection systems like so:
        # view = adapters.lookup(....)
        # view.__discriminator__(context, request) -> view's discriminator
        # so that superdynamic systems can feed the discriminator to
        # the introspection system to get info about it
        view = self.match(context, request)
        return view.__discriminator__(context, request)

    def add(self, view, order, accept=None, phash=None):
        if phash is not None:
            for i, (s, v, h) in enumerate(list(self.views)):
                if phash == h:
                    self.views[i] = (order, view, phash)
                    return

        if accept is None or '*' in accept:
            self.views.append((order, view, phash))
            self.views.sort(key=operator.itemgetter(0))
        else:
            subset = self.media_views.setdefault(accept, [])
            for i, (s, v, h) in enumerate(list(subset)):
                if phash == h:
                    subset[i] = (order, view, phash)
                    return
            else:
                subset.append((order, view, phash))
                subset.sort(key=operator.itemgetter(0))
            accepts = set(self.accepts)
            accepts.add(accept)
            self.accepts = list(accepts) # dedupe

    def get_views(self, request):
        if self.accepts and hasattr(request, 'accept'):
            accepts = self.accepts[:]
            views = []
            while accepts:
                match = request.accept.best_match(accepts)
                if match is None:
                    break
                subset = self.media_views[match]
                views.extend(subset)
                accepts.remove(match)
            views.extend(self.views)
            return views
        return self.views

    def match(self, context, request):
        for order, view, phash in self.get_views(request):
            if not hasattr(view, '__predicated__'):
                return view
            if view.__predicated__(context, request):
                return view
        raise PredicateMismatch(self.name)

    def __permitted__(self, context, request):
        view = self.match(context, request)
        if hasattr(view, '__permitted__'):
            return view.__permitted__(context, request)
        return True

    def __call_permissive__(self, context, request):
        view = self.match(context, request)
        view = getattr(view, '__call_permissive__', view)
        return view(context, request)

    def __call__(self, context, request):
        for order, view, phash in self.get_views(request):
            try:
                return view(context, request)
            except PredicateMismatch:
                continue
        raise PredicateMismatch(self.name)

class ViewsConfiguratorMixin(object):
    @viewdefaults
    @action_method
    def add_view(
        self,
        view=None,
        name="",
        for_=None,
        permission=None,
        request_type=None,
        route_name=None,
        request_method=None,
        request_param=None,
        containment=None,
        attr=None,
        renderer=None,
        wrapper=None,
        xhr=None,
        accept=None,
        header=None,
        path_info=None,
        custom_predicates=(),
        context=None,
        decorator=None,
        mapper=None,
        http_cache=None,
        match_param=None,
        check_csrf=None,
        **predicates):
        """ Add a :term:`view configuration` to the current
        configuration state.  Arguments to ``add_view`` are broken
        down below into *predicate* arguments and *non-predicate*
        arguments.  Predicate arguments narrow the circumstances in
        which the view callable will be invoked when a request is
        presented to :app:`Pyramid`; non-predicate arguments are
        informational.

        Non-Predicate Arguments

        view

          A :term:`view callable` or a :term:`dotted Python name`
          which refers to a view callable.  This argument is required
          unless a ``renderer`` argument also exists.  If a
          ``renderer`` argument is passed, and a ``view`` argument is
          not provided, the view callable defaults to a callable that
          returns an empty dictionary (see
          :ref:`views_which_use_a_renderer`).

        permission

          A :term:`permission` that the user must possess in order to invoke
          the :term:`view callable`.  See :ref:`view_security_section` for
          more information about view security and permissions.  This is
          often a string like ``view`` or ``edit``.

          If ``permission`` is omitted, a *default* permission may be used
          for this view registration if one was named as the
          :class:`pyramid.config.Configurator` constructor's
          ``default_permission`` argument, or if
          :meth:`pyramid.config.Configurator.set_default_permission` was used
          prior to this view registration.  Pass the value
          :data:`pyramid.security.NO_PERMISSION_REQUIRED` as the permission
          argument to explicitly indicate that the view should always be
          executable by entirely anonymous users, regardless of the default
          permission, bypassing any :term:`authorization policy` that may be
          in effect.

        attr

          This knob is most useful when the view definition is a class.

          The view machinery defaults to using the ``__call__`` method
          of the :term:`view callable` (or the function itself, if the
          view callable is a function) to obtain a response.  The
          ``attr`` value allows you to vary the method attribute used
          to obtain the response.  For example, if your view was a
          class, and the class has a method named ``index`` and you
          wanted to use this method instead of the class' ``__call__``
          method to return the response, you'd say ``attr="index"`` in the
          view configuration for the view.

        renderer

          This is either a single string term (e.g. ``json``) or a
          string implying a path or :term:`asset specification`
          (e.g. ``templates/views.pt``) naming a :term:`renderer`
          implementation.  If the ``renderer`` value does not contain
          a dot ``.``, the specified string will be used to look up a
          renderer implementation, and that renderer implementation
          will be used to construct a response from the view return
          value.  If the ``renderer`` value contains a dot (``.``),
          the specified term will be treated as a path, and the
          filename extension of the last element in the path will be
          used to look up the renderer implementation, which will be
          passed the full path.  The renderer implementation will be
          used to construct a :term:`response` from the view return
          value.

          Note that if the view itself returns a :term:`response` (see
          :ref:`the_response`), the specified renderer implementation
          is never called.

          When the renderer is a path, although a path is usually just
          a simple relative pathname (e.g. ``templates/foo.pt``,
          implying that a template named "foo.pt" is in the
          "templates" directory relative to the directory of the
          current :term:`package` of the Configurator), a path can be
          absolute, starting with a slash on UNIX or a drive letter
          prefix on Windows.  The path can alternately be a
          :term:`asset specification` in the form
          ``some.dotted.package_name:relative/path``, making it
          possible to address template assets which live in a
          separate package.

          The ``renderer`` attribute is optional.  If it is not
          defined, the "null" renderer is assumed (no rendering is
          performed and the value is passed back to the upstream
          :app:`Pyramid` machinery unmodified).

        http_cache

          .. versionadded:: 1.1

          When you supply an ``http_cache`` value to a view configuration,
          the ``Expires`` and ``Cache-Control`` headers of a response
          generated by the associated view callable are modified.  The value
          for ``http_cache`` may be one of the following:

          - A nonzero integer.  If it's a nonzero integer, it's treated as a
            number of seconds.  This number of seconds will be used to
            compute the ``Expires`` header and the ``Cache-Control:
            max-age`` parameter of responses to requests which call this view.
            For example: ``http_cache=3600`` instructs the requesting browser
            to 'cache this response for an hour, please'.

          - A ``datetime.timedelta`` instance.  If it's a
            ``datetime.timedelta`` instance, it will be converted into a
            number of seconds, and that number of seconds will be used to
            compute the ``Expires`` header and the ``Cache-Control:
            max-age`` parameter of responses to requests which call this view.
            For example: ``http_cache=datetime.timedelta(days=1)`` instructs
            the requesting browser to 'cache this response for a day, please'.

          - Zero (``0``).  If the value is zero, the ``Cache-Control`` and
            ``Expires`` headers present in all responses from this view will
            be composed such that client browser cache (and any intermediate
            caches) are instructed to never cache the response.

          - A two-tuple.  If it's a two tuple (e.g. ``http_cache=(1,
            {'public':True})``), the first value in the tuple may be a
            nonzero integer or a ``datetime.timedelta`` instance; in either
            case this value will be used as the number of seconds to cache
            the response.  The second value in the tuple must be a
            dictionary.  The values present in the dictionary will be used as
            input to the ``Cache-Control`` response header.  For example:
            ``http_cache=(3600, {'public':True})`` means 'cache for an hour,
            and add ``public`` to the Cache-Control header of the response'.
            All keys and values supported by the
            ``webob.cachecontrol.CacheControl`` interface may be added to the
            dictionary.  Supplying ``{'public':True}`` is equivalent to
            calling ``response.cache_control.public = True``.

          Providing a non-tuple value as ``http_cache`` is equivalent to
          calling ``response.cache_expires(value)`` within your view's body.

          Providing a two-tuple value as ``http_cache`` is equivalent to
          calling ``response.cache_expires(value[0], **value[1])`` within your
          view's body.

          If you wish to avoid influencing, the ``Expires`` header, and
          instead wish to only influence ``Cache-Control`` headers, pass a
          tuple as ``http_cache`` with the first element of ``None``, e.g.:
          ``(None, {'public':True})``.

          If you wish to prevent a view that uses ``http_cache`` in its
          configuration from having its caching response headers changed by
          this machinery, set ``response.cache_control.prevent_auto = True``
          before returning the response from the view.  This effectively
          disables any HTTP caching done by ``http_cache`` for that response.

        wrapper

          The :term:`view name` of a different :term:`view
          configuration` which will receive the response body of this
          view as the ``request.wrapped_body`` attribute of its own
          :term:`request`, and the :term:`response` returned by this
          view as the ``request.wrapped_response`` attribute of its
          own request.  Using a wrapper makes it possible to "chain"
          views together to form a composite response.  The response
          of the outermost wrapper view will be returned to the user.
          The wrapper view will be found as any view is found: see
          :ref:`view_lookup`.  The "best" wrapper view will be found
          based on the lookup ordering: "under the hood" this wrapper
          view is looked up via
          ``pyramid.view.render_view_to_response(context, request,
          'wrapper_viewname')``. The context and request of a wrapper
          view is the same context and request of the inner view.  If
          this attribute is unspecified, no view wrapping is done.

        decorator

          A :term:`dotted Python name` to function (or the function itself,
          or an iterable of the aforementioned) which will be used to
          decorate the registered :term:`view callable`.  The decorator
          function(s) will be called with the view callable as a single
          argument.  The view callable it is passed will accept
          ``(context, request)``.  The decorator(s) must return a
          replacement view callable which also accepts ``(context,
          request)``.

          If decorator is an iterable, the callables will be combined and
          used in the order provided as a decorator.
          For example::

            @view_config(...,
                decorator=(decorator2,
                           decorator1))
            def myview(request):
                ....

          Is similar to doing::

            @view_config(...)
            @decorator2
            @decorator1
            def myview(request):
                ...

          Except with the existing benefits of ``decorator=`` (having a common
          decorator syntax for all view calling conventions and not having to
          think about preserving function attributes such as ``__name__`` and
          ``__module__`` within decorator logic).

          .. versionchanged:: 1.4a4
             Passing an iterable.

        mapper

          A Python object or :term:`dotted Python name` which refers to a
          :term:`view mapper`, or ``None``.  By default it is ``None``, which
          indicates that the view should use the default view mapper.  This
          plug-point is useful for Pyramid extension developers, but it's not
          very useful for 'civilians' who are just developing stock Pyramid
          applications. Pay no attention to the man behind the curtain.

        Predicate Arguments

        name

          The :term:`view name`.  Read :ref:`traversal_chapter` to
          understand the concept of a view name.

        context

          An object or a :term:`dotted Python name` referring to an
          interface or class object that the :term:`context` must be
          an instance of, *or* the :term:`interface` that the
          :term:`context` must provide in order for this view to be
          found and called.  This predicate is true when the
          :term:`context` is an instance of the represented class or
          if the :term:`context` provides the represented interface;
          it is otherwise false.  This argument may also be provided
          to ``add_view`` as ``for_`` (an older, still-supported
          spelling).

        route_name

          This value must match the ``name`` of a :term:`route
          configuration` declaration (see :ref:`urldispatch_chapter`)
          that must match before this view will be called.

        request_type

          This value should be an :term:`interface` that the
          :term:`request` must provide in order for this view to be
          found and called.  This value exists only for backwards
          compatibility purposes.

        request_method

          This value can be either a strings (such as ``GET``, ``POST``,
          ``PUT``, ``DELETE``, or ``HEAD``) representing an HTTP
          ``REQUEST_METHOD``, or a tuple containing one or more of these
          strings.  A view declaration with this argument ensures that the
          view will only be called when the ``method`` attribute of the
          request (aka the ``REQUEST_METHOD`` of the WSGI environment) matches
          a supplied value.  Note that use of ``GET`` also implies that the
          view will respond to ``HEAD`` as of Pyramid 1.4.

          .. versionchanged:: 1.2
             The ability to pass a tuple of items as ``request_method``.
             Previous versions allowed only a string.

        request_param

          This value can be any string or any sequence of strings.  A view 
          declaration with this argument ensures that the view will only be 
          called when the :term:`request` has a key in the ``request.params``
          dictionary (an HTTP ``GET`` or ``POST`` variable) that has a
          name which matches the supplied value (if the value is a string)
          or values (if the value is a tuple).  If any value
          supplied has a ``=`` sign in it,
          e.g. ``request_param="foo=123"``, then the key (``foo``)
          must both exist in the ``request.params`` dictionary, *and*
          the value must match the right hand side of the expression
          (``123``) for the view to "match" the current request.

        match_param

          .. versionadded:: 1.2

          This value can be a string of the format "key=value" or a tuple
          containing one or more of these strings.

          A view declaration with this argument ensures that the view will
          only be called when the :term:`request` has key/value pairs in its
          :term:`matchdict` that equal those supplied in the predicate.
          e.g. ``match_param="action=edit"`` would require the ``action``
          parameter in the :term:`matchdict` match the right hand side of
          the expression (``edit``) for the view to "match" the current
          request.

          If the ``match_param`` is a tuple, every key/value pair must match
          for the predicate to pass.

        containment

          This value should be a Python class or :term:`interface` (or a
          :term:`dotted Python name`) that an object in the
          :term:`lineage` of the context must provide in order for this view
          to be found and called.  The nodes in your object graph must be
          "location-aware" to use this feature.  See
          :ref:`location_aware` for more information about
          location-awareness.

        xhr

          This value should be either ``True`` or ``False``.  If this
          value is specified and is ``True``, the :term:`request`
          must possess an ``HTTP_X_REQUESTED_WITH`` (aka
          ``X-Requested-With``) header that has the value
          ``XMLHttpRequest`` for this view to be found and called.
          This is useful for detecting AJAX requests issued from
          jQuery, Prototype and other Javascript libraries.

        accept

          The value of this argument represents a match query for one
          or more mimetypes in the ``Accept`` HTTP request header.  If
          this value is specified, it must be in one of the following
          forms: a mimetype match token in the form ``text/plain``, a
          wildcard mimetype match token in the form ``text/*`` or a
          match-all wildcard mimetype match token in the form ``*/*``.
          If any of the forms matches the ``Accept`` header of the
          request, this predicate will be true.

        header

          This value represents an HTTP header name or a header
          name/value pair.  If the value contains a ``:`` (colon), it
          will be considered a name/value pair
          (e.g. ``User-Agent:Mozilla/.*`` or ``Host:localhost``).  The
          value portion should be a regular expression.  If the value
          does not contain a colon, the entire value will be
          considered to be the header name
          (e.g. ``If-Modified-Since``).  If the value evaluates to a
          header name only without a value, the header specified by
          the name must be present in the request for this predicate
          to be true.  If the value evaluates to a header name/value
          pair, the header specified by the name must be present in
          the request *and* the regular expression specified as the
          value must match the header value.  Whether or not the value
          represents a header name or a header name/value pair, the
          case of the header name is not significant.

        path_info

          This value represents a regular expression pattern that will
          be tested against the ``PATH_INFO`` WSGI environment
          variable.  If the regex matches, this predicate will be
          ``True``.

        check_csrf

          If specified, this value should be one of ``None``, ``True``,
          ``False``, or a string representing the 'check name'.  If the value
          is ``True`` or a string, CSRF checking will be performed.  If the
          value is ``False`` or ``None``, CSRF checking will not be performed.

          If the value provided is a string, that string will be used as the
          'check name'.  If the value provided is ``True``, ``csrf_token`` will
          be used as the check name.

          If CSRF checking is performed, the checked value will be the value
          of ``request.params[check_name]``.  This value will be compared
          against the value of ``request.session.get_csrf_token()``, and the
          check will pass if these two values are the same.  If the check
          passes, the associated view will be permitted to execute.  If the
          check fails, the associated view will not be permitted to execute.

          Note that using this feature requires a :term:`session factory` to
          have been configured.
         
          .. versionadded:: 1.4a2

        physical_path

          If specified, this value should be a string or a tuple representing
          the :term:`physical path` of the context found via traversal for this
          predicate to match as true.  For example: ``physical_path='/'`` or
          ``physical_path='/a/b/c'`` or ``physical_path=('', 'a', 'b', 'c')``.
          This is not a path prefix match or a regex, it's a whole-path match.
          It's useful when you want to always potentially show a view when some
          object is traversed to, but you can't be sure about what kind of
          object it will be, so you can't use the ``context`` predicate.  The
          individual path elements inbetween slash characters or in tuple
          elements should be the Unicode representation of the name of the
          resource and should not be encoded in any way.

          .. versionadded:: 1.4a3

        effective_principals

          If specified, this value should be a :term:`principal` identifier or
          a sequence of principal identifiers.  If the
          :attr:`pyramid.request.Request.effective_principals` property
          indicates that every principal named in the argument list is present
          in the current request, this predicate will return True; otherwise it
          will return False.  For example:
          ``effective_principals=pyramid.security.Authenticated`` or
          ``effective_principals=('fred', 'group:admins')``.

          .. versionadded:: 1.4a4

        custom_predicates

            .. deprecated:: 1.5
                This value should be a sequence of references to custom
                predicate callables.  Use custom predicates when no set of
                predefined predicates do what you need.  Custom predicates
                can be combined with predefined predicates as necessary. 
                Each custom predicate callable should accept two arguments:
                ``context`` and ``request`` and should return either
                ``True`` or ``False`` after doing arbitrary evaluation of
                the context and/or the request.  The ``predicates`` argument
                to this method and the ability to register third-party view
                predicates via
                :meth:`pyramid.config.Configurator.add_view_predicate`
                obsoletes this argument, but it is kept around for backwards
                compatibility.

        predicates

          Pass a key/value pair here to use a third-party predicate
          registered via
          :meth:`pyramid.config.Configurator.add_view_predicate`.  More than
          one key/value pair can be used at the same time.  See
          :ref:`view_and_route_predicates` for more information about
          third-party predicates.

          .. versionadded: 1.4a1

        """
        if custom_predicates:
            warnings.warn(
                ('The "custom_predicates" argument to Configurator.add_view '
                 'is deprecated as of Pyramid 1.5.  Use '
                 '"config.add_view_predicate" and use the registered '
                 'view predicate as a predicate argument to add_view instead. '
                 'See "Adding A Third Party View, Route, or Subscriber '
                 'Predicate" in the "Hooks" chapter of the documentation '
                 'for more information.'),
                DeprecationWarning,
                stacklevel=4
                )
        
        view = self.maybe_dotted(view)
        context = self.maybe_dotted(context)
        for_ = self.maybe_dotted(for_)
        containment = self.maybe_dotted(containment)
        mapper = self.maybe_dotted(mapper)

        def combine(*decorators):
            def decorated(view_callable):
                # reversed() is allows a more natural ordering in the api
                for decorator in reversed(decorators):
                    view_callable = decorator(view_callable)
                return view_callable
            return decorated

        if is_nonstr_iter(decorator):
            decorator = combine(*map(self.maybe_dotted, decorator))
        else:
            decorator = self.maybe_dotted(decorator)

        if not view:
            if renderer:
                def view(context, request):
                    return {}
            else:
                raise ConfigurationError('"view" was not specified and '
                                         'no "renderer" specified')

        if request_type is not None:
            request_type = self.maybe_dotted(request_type)
            if not IInterface.providedBy(request_type):
                raise ConfigurationError(
                    'request_type must be an interface, not %s' % request_type)

        if context is None:
            context = for_

        r_context = context
        if r_context is None:
            r_context = Interface
        if not IInterface.providedBy(r_context):
            r_context = implementedBy(r_context)

        if isinstance(renderer, string_types):
            renderer = renderers.RendererHelper(
                name=renderer, package=self.package,
                registry = self.registry)

        if accept is not None:
            accept = accept.lower()

        introspectables = []
        pvals = predicates.copy()
        pvals.update(
            dict(
                xhr=xhr,
                request_method=request_method,
                path_info=path_info,
                request_param=request_param,
                header=header,
                accept=accept,
                containment=containment,
                request_type=request_type,
                match_param=match_param,
                check_csrf=check_csrf,
                custom=predvalseq(custom_predicates),
                )
            )

        def discrim_func():
            # We need to defer the discriminator until we know what the phash
            # is.  It can't be computed any sooner because thirdparty
            # predicates may not yet exist when add_view is called.
            order, preds, phash = predlist.make(self, **pvals)
            view_intr.update({'phash':phash, 'order':order, 'predicates':preds})
            return ('view', context, name, route_name, phash)

        discriminator = Deferred(discrim_func)

        if inspect.isclass(view) and attr:
            view_desc = 'method %r of %s' % (
                attr, self.object_description(view))
        else:
            view_desc = self.object_description(view)

        tmpl_intr = None
            
        view_intr = self.introspectable('views',
                                        discriminator,
                                        view_desc,
                                        'view')
        view_intr.update(
            dict(name=name,
                 context=context,
                 containment=containment,
                 request_param=request_param,
                 request_methods=request_method,
                 route_name=route_name,
                 attr=attr,
                 xhr=xhr,
                 accept=accept,
                 header=header,
                 path_info=path_info,
                 match_param=match_param,
                 check_csrf=check_csrf,
                 callable=view,
                 mapper=mapper,
                 decorator=decorator,
                 )
            )
        view_intr.update(**predicates)
        introspectables.append(view_intr)
        predlist = self.get_predlist('view')

        def register(permission=permission, renderer=renderer):
            request_iface = IRequest
            if route_name is not None:
                request_iface = self.registry.queryUtility(IRouteRequest,
                                                           name=route_name)
                if request_iface is None:
                    # route configuration should have already happened in
                    # phase 2
                    raise ConfigurationError(
                        'No route named %s found for view registration' %
                        route_name)

            if renderer is None:
                # use default renderer if one exists (reg'd in phase 1)
                if self.registry.queryUtility(IRendererFactory) is not None:
                    renderer = renderers.RendererHelper(
                        name=None,
                        package=self.package,
                        registry=self.registry
                        )

            if permission is None:
                # intent: will be None if no default permission is registered
                # (reg'd in phase 1)
                permission = self.registry.queryUtility(IDefaultPermission)

            # added by discrim_func above during conflict resolving
            preds = view_intr['predicates']
            order = view_intr['order']
            phash = view_intr['phash']

            # __no_permission_required__ handled by _secure_view
            deriver = ViewDeriver(
                registry=self.registry,
                permission=permission,
                predicates=preds,
                attr=attr,
                renderer=renderer,
                wrapper_viewname=wrapper,
                viewname=name,
                accept=accept,
                order=order,
                phash=phash,
                package=self.package,
                mapper=mapper,
                decorator=decorator,
                http_cache=http_cache,
                )
            derived_view = deriver(view)
            derived_view.__discriminator__ = lambda *arg: discriminator
            # __discriminator__ is used by superdynamic systems
            # that require it for introspection after manual view lookup;
            # see also MultiView.__discriminator__
            view_intr['derived_callable'] = derived_view

            registered = self.registry.adapters.registered

            # A multiviews is a set of views which are registered for
            # exactly the same context type/request type/name triad.  Each
            # consituent view in a multiview differs only by the
            # predicates which it possesses.

            # To find a previously registered view for a context
            # type/request type/name triad, we need to use the
            # ``registered`` method of the adapter registry rather than
            # ``lookup``.  ``registered`` ignores interface inheritance
            # for the required and provided arguments, returning only a
            # view registered previously with the *exact* triad we pass
            # in.

            # We need to do this three times, because we use three
            # different interfaces as the ``provided`` interface while
            # doing registrations, and ``registered`` performs exact
            # matches on all the arguments it receives.

            old_view = None

            for view_type in (IView, ISecuredView, IMultiView):
                old_view = registered((IViewClassifier, request_iface,
                                       r_context), view_type, name)
                if old_view is not None:
                    break

            isexc = isexception(context)

            def regclosure():
                if hasattr(derived_view, '__call_permissive__'):
                    view_iface = ISecuredView
                else:
                    view_iface = IView
                self.registry.registerAdapter(
                    derived_view,
                    (IViewClassifier, request_iface, context), view_iface, name
                    )
                if isexc:
                    self.registry.registerAdapter(
                        derived_view,
                        (IExceptionViewClassifier, request_iface, context),
                        view_iface, name)

            is_multiview = IMultiView.providedBy(old_view)
            old_phash = getattr(old_view, '__phash__', DEFAULT_PHASH)

            if old_view is None:
                # - No component was yet registered for any of our I*View
                #   interfaces exactly; this is the first view for this
                #   triad.
                regclosure()

            elif (not is_multiview) and (old_phash == phash):
                # - A single view component was previously registered with
                #   the same predicate hash as this view; this registration
                #   is therefore an override.
                regclosure()

            else:
                # - A view or multiview was already registered for this
                #   triad, and the new view is not an override.

                # XXX we could try to be more efficient here and register
                # a non-secured view for a multiview if none of the
                # multiview's consituent views have a permission
                # associated with them, but this code is getting pretty
                # rough already
                if is_multiview:
                    multiview = old_view
                else:
                    multiview = MultiView(name)
                    old_accept = getattr(old_view, '__accept__', None)
                    old_order = getattr(old_view, '__order__', MAX_ORDER)
                    multiview.add(old_view, old_order, old_accept, old_phash)
                multiview.add(derived_view, order, accept, phash)
                for view_type in (IView, ISecuredView):
                    # unregister any existing views
                    self.registry.adapters.unregister(
                        (IViewClassifier, request_iface, r_context),
                        view_type, name=name)
                    if isexc:
                        self.registry.adapters.unregister(
                            (IExceptionViewClassifier, request_iface,
                             r_context), view_type, name=name)
                self.registry.registerAdapter(
                    multiview,
                    (IViewClassifier, request_iface, context),
                    IMultiView, name=name)
                if isexc:
                    self.registry.registerAdapter(
                        multiview,
                        (IExceptionViewClassifier, request_iface, context),
                        IMultiView, name=name)
            renderer_type = getattr(renderer, 'type', None) # gard against None
            intrspc = self.introspector
            if (
                renderer_type is not None and
                tmpl_intr is not None and
                intrspc is not None and
                intrspc.get('renderer factories', renderer_type) is not None
                ):
                # allow failure of registered template factories to be deferred
                # until view execution, like other bad renderer factories; if
                # we tried to relate this to an existing renderer factory
                # without checking if it the factory actually existed, we'd end
                # up with a KeyError at startup time, which is inconsistent
                # with how other bad renderer registrations behave (they throw
                # a ValueError at view execution time)
                tmpl_intr.relate('renderer factories', renderer.type)

        if mapper:
            mapper_intr = self.introspectable(
                'view mappers',
                discriminator,
                'view mapper for %s' % view_desc,
                'view mapper'
                )
            mapper_intr['mapper'] = mapper
            mapper_intr.relate('views', discriminator)
            introspectables.append(mapper_intr)
        if route_name:
            view_intr.relate('routes', route_name) # see add_route
        if renderer is not None and renderer.name and '.' in renderer.name:
            # the renderer is a template
            tmpl_intr = self.introspectable(
                'templates',
                discriminator,
                renderer.name,
                'template'
                )
            tmpl_intr.relate('views', discriminator)
            tmpl_intr['name'] = renderer.name
            tmpl_intr['type'] = renderer.type
            tmpl_intr['renderer'] = renderer
            introspectables.append(tmpl_intr)
        if permission is not None:
            # if a permission exists, register a permission introspectable
            perm_intr = self.introspectable(
                'permissions',
                permission,
                permission,
                'permission'
                )
            perm_intr['value'] = permission
            perm_intr.relate('views', discriminator)
            introspectables.append(perm_intr)
        self.action(discriminator, register, introspectables=introspectables)

    @action_method
    def add_view_predicate(self, name, factory, weighs_more_than=None,
                           weighs_less_than=None):
        """
        .. versionadded:: 1.4

        Adds a view predicate factory.  The associated view predicate can
        later be named as a keyword argument to
        :meth:`pyramid.config.Configurator.add_view` in the
        ``predicates`` anonyous keyword argument dictionary.

        ``name`` should be the name of the predicate.  It must be a valid
        Python identifier (it will be used as a keyword argument to
        ``add_view`` by others).

        ``factory`` should be a :term:`predicate factory` or :term:`dotted
        Python name` which refers to a predicate factory.

        See :ref:`view_and_route_predicates` for more information.
        """
        self._add_predicate(
            'view',
            name,
            factory,
            weighs_more_than=weighs_more_than,
            weighs_less_than=weighs_less_than
            )

    def add_default_view_predicates(self):
        p = pyramid.config.predicates
        for (name, factory) in (
            ('xhr', p.XHRPredicate),
            ('request_method', p.RequestMethodPredicate),
            ('path_info', p.PathInfoPredicate),
            ('request_param', p.RequestParamPredicate),
            ('header', p.HeaderPredicate),
            ('accept', p.AcceptPredicate),
            ('containment', p.ContainmentPredicate),
            ('request_type', p.RequestTypePredicate),
            ('match_param', p.MatchParamPredicate),
            ('check_csrf', p.CheckCSRFTokenPredicate),
            ('physical_path', p.PhysicalPathPredicate),
            ('effective_principals', p.EffectivePrincipalsPredicate),
            ('custom', p.CustomPredicate),
            ):
            self.add_view_predicate(name, factory)

    def derive_view(self, view, attr=None, renderer=None):
        """
        Create a :term:`view callable` using the function, instance,
        or class (or :term:`dotted Python name` referring to the same)
        provided as ``view`` object.

        .. warning::

           This method is typically only used by :app:`Pyramid` framework
           extension authors, not by :app:`Pyramid` application developers.

        This is API is useful to framework extenders who create
        pluggable systems which need to register 'proxy' view
        callables for functions, instances, or classes which meet the
        requirements of being a :app:`Pyramid` view callable.  For
        example, a ``some_other_framework`` function in another
        framework may want to allow a user to supply a view callable,
        but he may want to wrap the view callable in his own before
        registering the wrapper as a :app:`Pyramid` view callable.
        Because a :app:`Pyramid` view callable can be any of a
        number of valid objects, the framework extender will not know
        how to call the user-supplied object.  Running it through
        ``derive_view`` normalizes it to a callable which accepts two
        arguments: ``context`` and ``request``.

        For example:

        .. code-block:: python

           def some_other_framework(user_supplied_view):
               config = Configurator(reg)
               proxy_view = config.derive_view(user_supplied_view)
               def my_wrapper(context, request):
                   do_something_that_mutates(request)
                   return proxy_view(context, request)
               config.add_view(my_wrapper)

        The ``view`` object provided should be one of the following:

        - A function or another non-class callable object that accepts
          a :term:`request` as a single positional argument and which
          returns a :term:`response` object.

        - A function or other non-class callable object that accepts
          two positional arguments, ``context, request`` and which
          returns a :term:`response` object.

        - A class which accepts a single positional argument in its
          constructor named ``request``, and which has a ``__call__``
          method that accepts no arguments that returns a
          :term:`response` object.

        - A class which accepts two positional arguments named
          ``context, request``, and which has a ``__call__`` method
          that accepts no arguments that returns a :term:`response`
          object.

        - A :term:`dotted Python name` which refers to any of the
          kinds of objects above.

        This API returns a callable which accepts the arguments
        ``context, request`` and which returns the result of calling
        the provided ``view`` object.

        The ``attr`` keyword argument is most useful when the view
        object is a class.  It names the method that should be used as
        the callable.  If ``attr`` is not provided, the attribute
        effectively defaults to ``__call__``.  See
        :ref:`class_as_view` for more information.

        The ``renderer`` keyword argument should be a renderer
        name. If supplied, it will cause the returned callable to use
        a :term:`renderer` to convert the user-supplied view result to
        a :term:`response` object.  If a ``renderer`` argument is not
        supplied, the user-supplied view must itself return a
        :term:`response` object.  """
        return self._derive_view(view, attr=attr, renderer=renderer)

    # b/w compat
    def _derive_view(self, view, permission=None, predicates=(),
                     attr=None, renderer=None, wrapper_viewname=None,
                     viewname=None, accept=None, order=MAX_ORDER,
                     phash=DEFAULT_PHASH, decorator=None,
                     mapper=None, http_cache=None):
        view = self.maybe_dotted(view)
        mapper = self.maybe_dotted(mapper)
        if isinstance(renderer, string_types):
            renderer = renderers.RendererHelper(
                name=renderer, package=self.package,
                registry = self.registry)
        if renderer is None:
            # use default renderer if one exists
            if self.registry.queryUtility(IRendererFactory) is not None:
                renderer = renderers.RendererHelper(
                    name=None,
                    package=self.package,
                    registry=self.registry)

        deriver = ViewDeriver(registry=self.registry,
                              permission=permission,
                              predicates=predicates,
                              attr=attr,
                              renderer=renderer,
                              wrapper_viewname=wrapper_viewname,
                              viewname=viewname,
                              accept=accept,
                              order=order,
                              phash=phash,
                              package=self.package,
                              mapper=mapper,
                              decorator=decorator,
                              http_cache=http_cache)

        return deriver(view)

    @viewdefaults
    @action_method
    def add_forbidden_view(
        self,
        view=None,
        attr=None,
        renderer=None,
        wrapper=None,
        route_name=None,
        request_type=None,
        request_method=None, 
        request_param=None,
        containment=None,
        xhr=None,
        accept=None,
        header=None,
        path_info=None,
        custom_predicates=(),
        decorator=None,
        mapper=None,
        match_param=None,
        **predicates
        ):
        """ Add a forbidden view to the current configuration state.  The
        view will be called when Pyramid or application code raises a
        :exc:`pyramid.httpexceptions.HTTPForbidden` exception and the set of
        circumstances implied by the predicates provided are matched.  The
        simplest example is:

          .. code-block:: python

            def forbidden(request):
                return Response('Forbidden', status='403 Forbidden')

            config.add_forbidden_view(forbidden)

        All arguments have the same meaning as
        :meth:`pyramid.config.Configurator.add_view` and each predicate
        argument restricts the set of circumstances under which this notfound
        view will be invoked.  Unlike
        :meth:`pyramid.config.Configurator.add_view`, this method will raise
        an exception if passed ``name``, ``permission``, ``context``,
        ``for_``, or ``http_cache`` keyword arguments.  These argument values
        make no sense in the context of a forbidden view.

        .. versionadded:: 1.3
        """
        for arg in ('name', 'permission', 'context', 'for_', 'http_cache'):
            if arg in predicates:
                raise ConfigurationError(
                    '%s may not be used as an argument to add_forbidden_view'
                    % arg
                    )
        
        settings = dict(
            view=view,
            context=HTTPForbidden,
            wrapper=wrapper,
            request_type=request_type,
            request_method=request_method,
            request_param=request_param,
            containment=containment,
            xhr=xhr,
            accept=accept,
            header=header, 
            path_info=path_info,
            custom_predicates=custom_predicates,
            decorator=decorator,
            mapper=mapper,
            match_param=match_param,
            route_name=route_name,
            permission=NO_PERMISSION_REQUIRED,
            attr=attr,
            renderer=renderer,
            )
        settings.update(predicates)
        return self.add_view(**settings)

    set_forbidden_view = add_forbidden_view # deprecated sorta-bw-compat alias
    
    @viewdefaults
    @action_method
    def add_notfound_view(
        self,
        view=None,
        attr=None,
        renderer=None,
        wrapper=None,
        route_name=None,
        request_type=None,
        request_method=None, 
        request_param=None,
        containment=None,
        xhr=None,
        accept=None,
        header=None,
        path_info=None,
        custom_predicates=(),
        decorator=None,
        mapper=None,
        match_param=None,
        append_slash=False,
        **predicates
        ):
        """ Add a default Not Found View to the current configuration state.
        The view will be called when Pyramid or application code raises an
        :exc:`pyramid.httpexceptions.HTTPNotFound` exception (e.g. when a
        view cannot be found for the request).  The simplest example is:

          .. code-block:: python

            def notfound(request):
                return Response('Not Found', status='404 Not Found')

            config.add_notfound_view(notfound)

        All arguments except ``append_slash`` have the same meaning as
        :meth:`pyramid.config.Configurator.add_view` and each predicate
        argument restricts the set of circumstances under which this notfound
        view will be invoked.  Unlike
        :meth:`pyramid.config.Configurator.add_view`, this method will raise
        an exception if passed ``name``, ``permission``, ``context``,
        ``for_``, or ``http_cache`` keyword arguments.  These argument values
        make no sense in the context of a Not Found View.

        If ``append_slash`` is ``True``, when this Not Found View is invoked,
        and the current path info does not end in a slash, the notfound logic
        will attempt to find a :term:`route` that matches the request's path
        info suffixed with a slash.  If such a route exists, Pyramid will
        issue a redirect to the URL implied by the route; if it does not,
        Pyramid will return the result of the view callable provided as
        ``view``, as normal.

        .. versionadded:: 1.3
        """
        for arg in ('name', 'permission', 'context', 'for_', 'http_cache'):
            if arg in predicates:
                raise ConfigurationError(
                    '%s may not be used as an argument to add_notfound_view'
                    % arg
                    )
                    
        settings = dict(
            view=view,
            context=HTTPNotFound,
            wrapper=wrapper,
            request_type=request_type,
            request_method=request_method,
            request_param=request_param,
            containment=containment,
            xhr=xhr,
            accept=accept,
            header=header, 
            path_info=path_info,
            custom_predicates=custom_predicates,
            decorator=decorator,
            mapper=mapper,
            match_param=match_param,
            route_name=route_name,
            permission=NO_PERMISSION_REQUIRED,
            )
        settings.update(predicates)
        if append_slash:
            view = self._derive_view(view, attr=attr, renderer=renderer)
            view = AppendSlashNotFoundViewFactory(view)
            settings['view'] = view
        else:
            settings['attr'] = attr
            settings['renderer'] = renderer
        return self.add_view(**settings)

    set_notfound_view = add_notfound_view # deprecated sorta-bw-compat alias

    @action_method
    def set_view_mapper(self, mapper):
        """
        Setting a :term:`view mapper` makes it possible to make use of
        :term:`view callable` objects which implement different call
        signatures than the ones supported by :app:`Pyramid` as described in
        its narrative documentation.

        The ``mapper`` should argument be an object implementing
        :class:`pyramid.interfaces.IViewMapperFactory` or a :term:`dotted
        Python name` to such an object.  The provided ``mapper`` will become
        the default view mapper to be used by all subsequent :term:`view
        configuration` registrations.

        .. seealso::

            See also :ref:`using_a_view_mapper`.

        .. note::

           Using the ``default_view_mapper`` argument to the
           :class:`pyramid.config.Configurator` constructor
           can be used to achieve the same purpose.
        """
        mapper = self.maybe_dotted(mapper)
        def register():
            self.registry.registerUtility(mapper, IViewMapperFactory)
        # IViewMapperFactory is looked up as the result of view config
        # in phase 3
        intr = self.introspectable('view mappers',
                                   IViewMapperFactory,
                                   self.object_description(mapper),
                                   'default view mapper')
        intr['mapper'] = mapper
        self.action(IViewMapperFactory, register, order=PHASE1_CONFIG,
                    introspectables=(intr,))

    @action_method
    def add_static_view(self, name, path, **kw):
        """ Add a view used to render static assets such as images
        and CSS files.

        The ``name`` argument is a string representing an
        application-relative local URL prefix.  It may alternately be a full
        URL.

        The ``path`` argument is the path on disk where the static files
        reside.  This can be an absolute path, a package-relative path, or a
        :term:`asset specification`.

        The ``cache_max_age`` keyword argument is input to set the
        ``Expires`` and ``Cache-Control`` headers for static assets served.
        Note that this argument has no effect when the ``name`` is a *url
        prefix*.  By default, this argument is ``None``, meaning that no
        particular Expires or Cache-Control headers are set in the response.

        The ``permission`` keyword argument is used to specify the
        :term:`permission` required by a user to execute the static view.  By
        default, it is the string
        :data:`pyramid.security.NO_PERMISSION_REQUIRED`, a special sentinel
        which indicates that, even if a :term:`default permission` exists for
        the current application, the static view should be renderered to
        completely anonymous users.  This default value is permissive
        because, in most web apps, static assets seldom need protection from
        viewing.  If ``permission`` is specified, the security checking will
        be performed against the default root factory ACL.

        Any other keyword arguments sent to ``add_static_view`` are passed on
        to :meth:`pyramid.config.Configurator.add_route` (e.g. ``factory``,
        perhaps to define a custom factory with a custom ACL for this static
        view).

        *Usage*

        The ``add_static_view`` function is typically used in conjunction
        with the :meth:`pyramid.request.Request.static_url` method.
        ``add_static_view`` adds a view which renders a static asset when
        some URL is visited; :meth:`pyramid.request.Request.static_url`
        generates a URL to that asset.

        The ``name`` argument to ``add_static_view`` is usually a simple URL
        prefix (e.g. ``'images'``).  When this is the case, the
        :meth:`pyramid.request.Request.static_url` API will generate a URL
        which points to a Pyramid view, which will serve up a set of assets
        that live in the package itself. For example:

        .. code-block:: python

           add_static_view('images', 'mypackage:images/')

        Code that registers such a view can generate URLs to the view via
        :meth:`pyramid.request.Request.static_url`:

        .. code-block:: python

           request.static_url('mypackage:images/logo.png')

        When ``add_static_view`` is called with a ``name`` argument that
        represents a URL prefix, as it is above, subsequent calls to
        :meth:`pyramid.request.Request.static_url` with paths that start with
        the ``path`` argument passed to ``add_static_view`` will generate a
        URL something like ``http://<Pyramid app URL>/images/logo.png``,
        which will cause the ``logo.png`` file in the ``images`` subdirectory
        of the ``mypackage`` package to be served.

        ``add_static_view`` can alternately be used with a ``name`` argument
        which is a *URL*, causing static assets to be served from an external
        webserver.  This happens when the ``name`` argument is a fully
        qualified URL (e.g. starts with ``http://`` or similar).  In this
        mode, the ``name`` is used as the prefix of the full URL when
        generating a URL using :meth:`pyramid.request.Request.static_url`.
        Furthermore, if a protocol-relative URL (e.g. ``//example.com/images``)
        is used as the ``name`` argument, the generated URL will use the
        protocol of the request (http or https, respectively).

        For example, if ``add_static_view`` is called like so:

        .. code-block:: python

           add_static_view('http://example.com/images', 'mypackage:images/')

        Subsequently, the URLs generated by
        :meth:`pyramid.request.Request.static_url` for that static view will
        be prefixed with ``http://example.com/images`` (the external webserver
        listening on ``example.com`` must be itself configured to respond
        properly to such a request.):

        .. code-block:: python

           static_url('mypackage:images/logo.png', request)

        See :ref:`static_assets_section` for more information.
        """
        spec = self._make_spec(path)
        info = self.registry.queryUtility(IStaticURLInfo)
        if info is None:
            info = StaticURLInfo()
            self.registry.registerUtility(info, IStaticURLInfo)
        info.add(self, name, spec, **kw)

def isexception(o):
    if IInterface.providedBy(o):
        if IException.isEqualOrExtendedBy(o):
            return True
    return (
        isinstance(o, Exception) or
        (inspect.isclass(o) and (issubclass(o, Exception)))
        )


@implementer(IStaticURLInfo)
class StaticURLInfo(object):

    def _get_registrations(self, registry):
        try:
            reg = registry._static_url_registrations
        except AttributeError:
            reg = registry._static_url_registrations = []
        return reg

    def generate(self, path, request, **kw):
        try:
            registry = request.registry
        except AttributeError: # bw compat (for tests)
            registry = get_current_registry()
        for (url, spec, route_name) in self._get_registrations(registry):
            if path.startswith(spec):
                subpath = path[len(spec):]
                if WIN: # pragma: no cover
                    subpath = subpath.replace('\\', '/') # windows
                if url is None:
                    kw['subpath'] = subpath
                    return request.route_url(route_name, **kw)
                else:
                    app_url, scheme, host, port, qs, anchor = \
                        parse_url_overrides(kw)
                    parsed = url_parse(url)
                    if not parsed.scheme:
                        url = urlparse.urlunparse(parsed._replace(
                            scheme=request.environ['wsgi.url_scheme']))
                    subpath = url_quote(subpath)
                    result = urljoin(url, subpath)
                    return result + qs + anchor

        raise ValueError('No static URL definition matching %s' % path)

    def add(self, config, name, spec, **extra):
        # This feature only allows for the serving of a directory and
        # the files contained within, not of a single asset;
        # appending a slash here if the spec doesn't have one is
        # required for proper prefix matching done in ``generate``
        # (``subpath = path[len(spec):]``).
        if os.path.isabs(spec): # FBO windows
            sep = os.sep
        else:
            sep = '/'
        if not spec.endswith(sep):
            spec = spec + sep

        # we also make sure the name ends with a slash, purely as a
        # convenience: a name that is a url is required to end in a
        # slash, so that ``urljoin(name, subpath))`` will work above
        # when the name is a URL, and it doesn't hurt things for it to
        # have a name that ends in a slash if it's used as a route
        # name instead of a URL.
        if not name.endswith('/'):
            # make sure it ends with a slash
            name = name + '/'

        if url_parse(name).netloc:
            # it's a URL
            # url, spec, route_name
            url = name
            route_name = None
        else:
            # it's a view name
            url = None
            cache_max_age = extra.pop('cache_max_age', None)
            # create a view
            view = static_view(spec, cache_max_age=cache_max_age,
                               use_subpath=True)

            # Mutate extra to allow factory, etc to be passed through here.
            # Treat permission specially because we'd like to default to
            # permissiveness (see docs of config.add_static_view).
            permission = extra.pop('permission', None)
            if permission is None:
                permission = NO_PERMISSION_REQUIRED

            context = extra.pop('context', None)
            if context is None:
                context = extra.pop('for_', None)

            renderer = extra.pop('renderer', None)

            # register a route using the computed view, permission, and
            # pattern, plus any extras passed to us via add_static_view
            pattern = "%s*subpath" % name # name already ends with slash
            if config.route_prefix:
                route_name = '__%s/%s' % (config.route_prefix, name)
            else:
                route_name = '__%s' % name
            config.add_route(route_name, pattern, **extra)
            config.add_view(
                route_name=route_name,
                view=view,
                permission=permission,
                context=context,
                renderer=renderer,
                )

        def register():
            registrations = self._get_registrations(config.registry)

            names = [ t[0] for t in  registrations ]

            if name in names:
                idx = names.index(name)
                registrations.pop(idx)

            # url, spec, route_name
            registrations.append((url, spec, route_name))

        intr = config.introspectable('static views',
                                     name,
                                     'static view for %r' % name,
                                     'static view')
        intr['name'] = name
        intr['spec'] = spec

        config.action(None, callable=register, introspectables=(intr,))


