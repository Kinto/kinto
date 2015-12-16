from zope.deprecation import deprecated

from zope.interface import (
    Attribute,
    Interface,
    )

from pyramid.compat import PY3

# public API interfaces

class IContextFound(Interface):
    """ An event type that is emitted after :app:`Pyramid` finds a
    :term:`context` object but before it calls any view code.  See the
    documentation attached to :class:`pyramid.events.ContextFound`
    for more information.

    .. note::

       For backwards compatibility with versions of
       :app:`Pyramid` before 1.0, this event interface can also be
       imported as :class:`pyramid.interfaces.IAfterTraversal`.
    """
    request = Attribute('The request object')

IAfterTraversal = IContextFound

class INewRequest(Interface):
    """ An event type that is emitted whenever :app:`Pyramid`
    begins to process a new request.  See the documentation attached
    to :class:`pyramid.events.NewRequest` for more information."""
    request = Attribute('The request object')

class INewResponse(Interface):
    """ An event type that is emitted whenever any :app:`Pyramid`
    view returns a response. See the
    documentation attached to :class:`pyramid.events.NewResponse`
    for more information."""
    request = Attribute('The request object')
    response = Attribute('The response object')

class IApplicationCreated(Interface):
    """ Event issued when the
    :meth:`pyramid.config.Configurator.make_wsgi_app` method
    is called.  See the documentation attached to
    :class:`pyramid.events.ApplicationCreated` for more
    information.

    .. note::

       For backwards compatibility with :app:`Pyramid`
       versions before 1.0, this interface can also be imported as
       :class:`pyramid.interfaces.IWSGIApplicationCreatedEvent`.
    """
    app = Attribute("Created application")

IWSGIApplicationCreatedEvent = IApplicationCreated # b /c

class IResponse(Interface):
    """ Represents a WSGI response using the WebOb response interface.
    Some attribute and method documentation of this interface references
    :rfc:`2616`.

    This interface is most famously implemented by
    :class:`pyramid.response.Response` and the HTTP exception classes in
    :mod:`pyramid.httpexceptions`."""

    RequestClass = Attribute(
        """ Alias for :class:`pyramid.request.Request` """)

    def __call__(environ, start_response):
        """ :term:`WSGI` call interface, should call the start_response
        callback and should return an iterable"""

    accept_ranges = Attribute(
        """Gets and sets and deletes the Accept-Ranges header. For more
        information on Accept-Ranges see RFC 2616, section 14.5""")

    age = Attribute(
        """Gets and sets and deletes the Age header. Converts using int.
        For more information on Age see RFC 2616, section 14.6.""")

    allow = Attribute(
        """Gets and sets and deletes the Allow header. Converts using
        list. For more information on Allow see RFC 2616, Section 14.7.""")

    app_iter = Attribute(
        """Returns the app_iter of the response.

        If body was set, this will create an app_iter from that body
        (a single-item list)""")

    def app_iter_range(start, stop):
        """ Return a new app_iter built from the response app_iter that
        serves up only the given start:stop range. """

    body = Attribute(
        """The body of the response, as a str. This will read in the entire
        app_iter if necessary.""")

    body_file = Attribute(
        """A file-like object that can be used to write to the body. If you
        passed in a list app_iter, that app_iter will be modified by writes.""")

    cache_control = Attribute(
        """Get/set/modify the Cache-Control header (RFC 2616 section 14.9)""")

    cache_expires = Attribute(
        """ Get/set the Cache-Control and Expires headers. This sets the
            response to expire in the number of seconds passed when set. """)

    charset = Attribute(
        """Get/set the charset (in the Content-Type)""")

    def conditional_response_app(environ, start_response):
        """ Like the normal __call__ interface, but checks conditional
        headers:

        - If-Modified-Since (304 Not Modified; only on GET, HEAD)

        - If-None-Match (304 Not Modified; only on GET, HEAD)

        - Range (406 Partial Content; only on GET, HEAD)"""

    content_disposition = Attribute(
        """Gets and sets and deletes the Content-Disposition header.
        For more information on Content-Disposition see RFC 2616 section
        19.5.1.""")

    content_encoding = Attribute(
        """Gets and sets and deletes the Content-Encoding header.  For more
        information about Content-Encoding see RFC 2616 section 14.11.""")

    content_language = Attribute(
        """Gets and sets and deletes the Content-Language header. Converts
        using list.  For more information about Content-Language see RFC 2616
        section 14.12.""")

    content_length = Attribute(
        """Gets and sets and deletes the Content-Length header. For more
        information on Content-Length see RFC 2616 section 14.17.
        Converts using int. """)

    content_location = Attribute(
        """Gets and sets and deletes the Content-Location header. For more
        information on Content-Location see RFC 2616 section 14.14.""")

    content_md5 = Attribute(
        """Gets and sets and deletes the Content-MD5 header. For more
        information on Content-MD5 see RFC 2616 section 14.14.""")

    content_range  = Attribute(
        """Gets and sets and deletes the Content-Range header. For more
        information on Content-Range see section 14.16. Converts using
        ContentRange object.""")

    content_type = Attribute(
        """Get/set the Content-Type header (or None), without the charset
        or any parameters. If you include parameters (or ; at all) when
        setting the content_type, any existing parameters will be deleted;
        otherwise they will be preserved.""")

    content_type_params = Attribute(
        """A dictionary of all the parameters in the content type.  This is
        not a view, set to change, modifications of the dict would not
        be applied otherwise.""")

    def copy():
        """ Makes a copy of the response and returns the copy. """

    date = Attribute(
        """Gets and sets and deletes the Date header. For more information on
        Date see RFC 2616 section 14.18. Converts using HTTP date.""")

    def delete_cookie(key, path='/', domain=None):
        """ Delete a cookie from the client. Note that path and domain must
        match how the cookie was originally set.  This sets the cookie to the
        empty string, and max_age=0 so that it should expire immediately. """

    def encode_content(encoding='gzip', lazy=False):
        """ Encode the content with the given encoding (only gzip and
        identity are supported)."""

    environ = Attribute(
        """Get/set the request environ associated with this response,
        if any.""")

    etag = Attribute(
        """ Gets and sets and deletes the ETag header. For more information
        on ETag see RFC 2616 section 14.19. Converts using Entity tag.""")

    expires = Attribute(
        """ Gets and sets and deletes the Expires header. For more
        information on Expires see RFC 2616 section 14.21. Converts using
        HTTP date.""")

    headerlist = Attribute(
        """ The list of response headers. """)

    headers = Attribute(
        """ The headers in a dictionary-like object """)

    last_modified = Attribute(
        """ Gets and sets and deletes the Last-Modified header. For more
        information on Last-Modified see RFC 2616 section 14.29. Converts
        using HTTP date.""")

    location = Attribute(
        """ Gets and sets and deletes the Location header. For more
        information on Location see RFC 2616 section 14.30.""")

    def md5_etag(body=None, set_content_md5=False):
        """ Generate an etag for the response object using an MD5 hash of the
        body (the body parameter, or self.body if not given).  Sets self.etag.
        If set_content_md5 is True sets self.content_md5 as well """

    def merge_cookies(resp):
        """ Merge the cookies that were set on this response with the given
        resp object (which can be any WSGI application).  If the resp is a
        webob.Response object, then the other object will be modified
        in-place. """

    pragma = Attribute(
        """ Gets and sets and deletes the Pragma header. For more information
        on Pragma see RFC 2616 section 14.32. """)

    request = Attribute(
        """ Return the request associated with this response if any. """)

    retry_after = Attribute(
        """ Gets and sets and deletes the Retry-After header. For more
        information on Retry-After see RFC 2616 section 14.37. Converts
        using HTTP date or delta seconds.""")

    server = Attribute(
        """ Gets and sets and deletes the Server header. For more information
        on Server see RFC216 section 14.38. """)

    def set_cookie(key, value='', max_age=None, path='/', domain=None,
                   secure=False, httponly=False, comment=None, expires=None,
                   overwrite=False):
        """ Set (add) a cookie for the response """

    status = Attribute(
        """ The status string. """)

    status_int = Attribute(
        """ The status as an integer """)

    unicode_body = Attribute(
        """ Get/set the unicode value of the body (using the charset of
        the Content-Type)""")

    def unset_cookie(key, strict=True):
        """ Unset a cookie with the given name (remove it from the
        response)."""

    vary = Attribute(
        """Gets and sets and deletes the Vary header. For more information
        on Vary see section 14.44. Converts using list.""")

    www_authenticate = Attribute(
        """ Gets and sets and deletes the WWW-Authenticate header. For more
        information on WWW-Authenticate see RFC 2616 section 14.47. Converts
        using 'parse_auth' and 'serialize_auth'. """)

class IException(Interface): # not an API
    """ An interface representing a generic exception """

class IExceptionResponse(IException, IResponse):
    """ An interface representing a WSGI response which is also an exception
    object.  Register an exception view using this interface as a ``context``
    to apply the registered view for all exception types raised by
    :app:`Pyramid` internally (any exception that inherits from
    :class:`pyramid.response.Response`, including
    :class:`pyramid.httpexceptions.HTTPNotFound` and
    :class:`pyramid.httpexceptions.HTTPForbidden`)."""
    def prepare(environ):
        """ Prepares the response for being called as a WSGI application """

class IDict(Interface):
    # Documentation-only interface

    def __contains__(k):
        """ Return ``True`` if key ``k`` exists in the dictionary."""

    def __setitem__(k, value):
        """ Set a key/value pair into the dictionary"""

    def __delitem__(k):
        """ Delete an item from the dictionary which is passed to the
        renderer as the renderer globals dictionary."""

    def __getitem__(k):
        """ Return the value for key ``k`` from the dictionary or raise a
        KeyError if the key doesn't exist"""

    def __iter__():
        """ Return an iterator over the keys of this dictionary """

    def get(k, default=None):
        """ Return the value for key ``k`` from the renderer dictionary, or
        the default if no such value exists."""

    def items():
        """ Return a list of [(k,v)] pairs from the dictionary """

    def keys():
        """ Return a list of keys from the dictionary """

    def values():
        """ Return a list of values from the dictionary """

    if not PY3:

        def iterkeys():
            """ Return an iterator of keys from the dictionary """

        def iteritems():
            """ Return an iterator of (k,v) pairs from the dictionary """

        def itervalues():
            """ Return an iterator of values from the dictionary """

        has_key = __contains__

    def pop(k, default=None):
        """ Pop the key k from the dictionary and return its value.  If k
        doesn't exist, and default is provided, return the default.  If k
        doesn't exist and default is not provided, raise a KeyError."""

    def popitem():
        """ Pop the item with key k from the dictionary and return it as a
        two-tuple (k, v).  If k doesn't exist, raise a KeyError."""

    def setdefault(k, default=None):
        """ Return the existing value for key ``k`` in the dictionary.  If no
         value with ``k`` exists in the dictionary, set the ``default``
         value into the dictionary under the k name passed.  If a value already
         existed in the dictionary, return it.  If a value did not exist in
         the dictionary, return the default"""

    def update(d):
        """ Update the renderer dictionary with another dictionary ``d``."""

    def clear():
        """ Clear all values from the dictionary """

class IBeforeRender(IDict):
    """
    Subscribers to this event may introspect and modify the set of
    :term:`renderer globals` before they are passed to a :term:`renderer`.
    The event object itself provides a dictionary-like interface for adding
    and removing :term:`renderer globals`.  The keys and values of the
    dictionary are those globals.  For example::

      from repoze.events import subscriber
      from pyramid.interfaces import IBeforeRender

      @subscriber(IBeforeRender)
      def add_global(event):
          event['mykey'] = 'foo'

    .. seealso::

        See also :ref:`beforerender_event`.
    """
    rendering_val = Attribute('The value returned by a view or passed to a '
                              '``render`` method for this rendering. '
                              'This feature is new in Pyramid 1.2.')

class IRendererInfo(Interface):
    """ An object implementing this interface is passed to every
    :term:`renderer factory` constructor as its only argument (conventionally
    named ``info``)"""
    name = Attribute('The value passed by the user as the renderer name')
    package = Attribute('The "current package" when the renderer '
                        'configuration statement was found')
    type = Attribute('The renderer type name')
    registry = Attribute('The "current" application registry when the '
                         'renderer was created')
    settings = Attribute('The deployment settings dictionary related '
                         'to the current application')

class IRendererFactory(Interface):
    def __call__(info):
        """ Return an object that implements
        :class:`pyramid.interfaces.IRenderer`. ``info`` is an
        object that implements :class:`pyramid.interfaces.IRendererInfo`.
        """

class IRenderer(Interface):
    def __call__(value, system):
        """ Call the renderer with the result of the
        view (``value``) passed in and return a result (a string or
        unicode object useful as a response body).  Values computed by
        the system are passed by the system in the ``system``
        parameter, which is a dictionary.  Keys in the dictionary
        include: ``view`` (the view callable that returned the value),
        ``renderer_name`` (the template name or simple name of the
        renderer), ``context`` (the context object passed to the
        view), and ``request`` (the request object passed to the
        view)."""

class ITemplateRenderer(IRenderer):
    def implementation():
        """ Return the object that the underlying templating system
        uses to render the template; it is typically a callable that
        accepts arbitrary keyword arguments and returns a string or
        unicode object """

deprecated(
    'ITemplateRenderer',
    'As of Pyramid 1.5 the, "pyramid.interfaces.ITemplateRenderer" interface '
    'is scheduled to be removed. It was used by the Mako and Chameleon '
    'renderers which have been split into their own packages.'
    )

class IViewMapper(Interface):
    def __call__(self, object):
        """ Provided with an arbitrary object (a function, class, or
        instance), returns a callable with the call signature ``(context,
        request)``.  The callable returned should itself return a Response
        object.  An IViewMapper is returned by
        :class:`pyramid.interfaces.IViewMapperFactory`."""

class IViewMapperFactory(Interface):
    def __call__(self, **kw):
        """
        Return an object which implements
        :class:`pyramid.interfaces.IViewMapper`.  ``kw`` will be a dictionary
        containing view-specific arguments, such as ``permission``,
        ``predicates``, ``attr``, ``renderer``, and other items.  An
        IViewMapperFactory is used by
        :meth:`pyramid.config.Configurator.add_view` to provide a plugpoint
        to extension developers who want to modify potential view callable
        invocation signatures and response values.
        """

class IAuthenticationPolicy(Interface):
    """ An object representing a Pyramid authentication policy. """
    def authenticated_userid(request):
        """ Return the authenticated userid or ``None`` if no authenticated
        userid can be found. This method of the policy should ensure that a
        record exists in whatever persistent store is used related to the
        user (the user should not have been deleted); if a record associated
        with the current id does not exist in a persistent store, it should
        return ``None``."""

    def unauthenticated_userid(request):
        """ Return the *unauthenticated* userid.  This method performs the
        same duty as ``authenticated_userid`` but is permitted to return the
        userid based only on data present in the request; it needn't (and
        shouldn't) check any persistent store to ensure that the user record
        related to the request userid exists."""

    def effective_principals(request):
        """ Return a sequence representing the effective principals
        including the userid and any groups belonged to by the current
        user, including 'system' groups such as Everyone and
        Authenticated. """

    def remember(request, principal, **kw):
        """ Return a set of headers suitable for 'remembering' the
        principal named ``principal`` when set in a response.  An
        individual authentication policy and its consumers can decide
        on the composition and meaning of ``**kw.`` """

    def forget(request):
        """ Return a set of headers suitable for 'forgetting' the
        current user on subsequent requests. """

class IAuthorizationPolicy(Interface):
    """ An object representing a Pyramid authorization policy. """
    def permits(context, principals, permission):
        """ Return ``True`` if any of the ``principals`` is allowed the
        ``permission`` in the current ``context``, else return ``False``
        """

    def principals_allowed_by_permission(context, permission):
        """ Return a set of principal identifiers allowed by the
        ``permission`` in ``context``.  This behavior is optional; if you
        choose to not implement it you should define this method as
        something which raises a ``NotImplementedError``.  This method
        will only be called when the
        ``pyramid.security.principals_allowed_by_permission`` API is
        used."""

class IMultiDict(IDict): # docs-only interface
    """
    An ordered dictionary that can have multiple values for each key. A
    multidict adds the methods ``getall``, ``getone``, ``mixed``, ``extend``,
    ``add``, and ``dict_of_lists`` to the normal dictionary interface.  A
    multidict data structure is used as ``request.POST``, ``request.GET``,
    and ``request.params`` within an :app:`Pyramid` application.
    """

    def add(key, value):
        """ Add the key and value, not overwriting any previous value. """

    def dict_of_lists():
        """
        Returns a dictionary where each key is associated with a list of
        values.
        """

    def extend(other=None, **kwargs):
        """ Add a set of keys and values, not overwriting any previous
        values.  The ``other`` structure may be a list of two-tuples or a
        dictionary.  If ``**kwargs`` is passed, its value *will* overwrite
        existing values."""

    def getall(key):
        """ Return a list of all values matching the key (may be an empty
        list) """

    def getone(key):
        """ Get one value matching the key, raising a KeyError if multiple
        values were found. """

    def mixed():
        """ Returns a dictionary where the values are either single values,
        or a list of values when a key/value appears more than once in this
        dictionary. This is similar to the kind of dictionary often used to
        represent the variables in a web request. """

# internal interfaces

class IRequest(Interface):
    """ Request type interface attached to all request objects """

class ITweens(Interface):
    """ Marker interface for utility registration representing the ordered
    set of a configuration's tween factories"""

class IRequestHandler(Interface):
    """ """
    def __call__(self, request):
        """ Must return a tuple of IReqest, IResponse or raise an exception.
        The ``request`` argument will be an instance of an object that
        provides IRequest."""

IRequest.combined = IRequest # for exception view lookups

class IRequestExtensions(Interface):
    """ Marker interface for storing request extensions (properties and
    methods) which will be added to the request object."""
    descriptors = Attribute(
        """A list of descriptors that will be added to each request.""")
    methods = Attribute(
        """A list of methods to be added to each request.""")

class IRouteRequest(Interface):
    """ *internal only* interface used as in a utility lookup to find
    route-specific interfaces.  Not an API."""

class IStaticURLInfo(Interface):
    """ A policy for generating URLs to static assets """
    def add(config, name, spec, **extra):
        """ Add a new static info registration """

    def generate(path, request, **kw):
        """ Generate a URL for the given path """

class IResponseFactory(Interface):
    """ A utility which generates a response factory """
    def __call__():
        """ Return a response factory (e.g. a callable that returns an object
        implementing IResponse, e.g. :class:`pyramid.response.Response`). It
        should accept all the arguments that the Pyramid Response class
        accepts."""

class IRequestFactory(Interface):
    """ A utility which generates a request """
    def __call__(environ):
        """ Return an object implementing IRequest, e.g. an instance
        of ``pyramid.request.Request``"""

    def blank(path):
        """ Return an empty request object (see
        :meth:`pyramid.request.Request.blank`)"""

class IViewClassifier(Interface):
    """ *Internal only* marker interface for views."""

class IExceptionViewClassifier(Interface):
    """ *Internal only* marker interface for exception views."""

class IView(Interface):
    def __call__(context, request):
        """ Must return an object that implements IResponse. """

class ISecuredView(IView):
    """ *Internal only* interface.  Not an API. """
    def __call_permissive__(context, request):
        """ Guaranteed-permissive version of __call__ """

    def __permitted__(context, request):
        """ Return True if view execution will be permitted using the
        context and request, False otherwise"""

class IMultiView(ISecuredView):
    """ *internal only*.  A multiview is a secured view that is a
    collection of other views.  Each of the views is associated with
    zero or more predicates.  Not an API."""
    def add(view, predicates, order, accept=None, phash=None):
        """ Add a view to the multiview. """

class IRootFactory(Interface):
    def __call__(request):
        """ Return a root object based on the request """

class IDefaultRootFactory(Interface):
    def __call__(request):
        """ Return the *default* root object for an application """

class ITraverser(Interface):
    def __call__(request):
        """ Return a dictionary with (at least) the keys ``root``,
        ``context``, ``view_name``, ``subpath``, ``traversed``,
        ``virtual_root``, and ``virtual_root_path``.  These values are
        typically the result of an object graph traversal.  ``root`` is the
        physical root object, ``context`` will be a model object,
        ``view_name`` will be the view name used (a Unicode name),
        ``subpath`` will be a sequence of Unicode names that followed the
        view name but were not traversed, ``traversed`` will be a sequence of
        Unicode names that were traversed (including the virtual root path,
        if any) ``virtual_root`` will be a model object representing the
        virtual root (or the physical root if traversal was not performed),
        and ``virtual_root_path`` will be a sequence representing the virtual
        root path (a sequence of Unicode names) or ``None`` if traversal was
        not performed.

        Extra keys for special purpose functionality can be returned as
        necessary.

        All values returned in the dictionary will be made available
        as attributes of the ``request`` object by the :term:`router`.
        """

ITraverserFactory = ITraverser # b / c for 1.0 code

class IViewPermission(Interface):
    def __call__(context, request):
        """ Return True if the permission allows, return False if it denies.
        """

class IRouter(Interface):
    """ WSGI application which routes requests to 'view' code based on
    a view registry."""
    registry = Attribute(
        """Component architecture registry local to this application.""")

class ISettings(Interface):
    """ Runtime settings utility for pyramid; represents the
    deployment settings for the application.  Implements a mapping
    interface."""

# this interface, even if it becomes unused within Pyramid, is
# imported by other packages (such as traversalwrapper)
class ILocation(Interface):
    """Objects that have a structural location"""
    __parent__ = Attribute("The parent in the location hierarchy")
    __name__ = Attribute("The name within the parent")

class IDebugLogger(Interface):
    """ Interface representing a PEP 282 logger """

ILogger = IDebugLogger # b/c

class IRoutePregenerator(Interface):
    def __call__(request, elements, kw):

        """ A pregenerator is a function associated by a developer with a
        :term:`route`. The pregenerator for a route is called by
        :meth:`pyramid.request.Request.route_url` in order to adjust the set
        of arguments passed to it by the user for special purposes, such as
        Pylons 'subdomain' support.  It will influence the URL returned by
        ``route_url``.

        A pregenerator should return a two-tuple of ``(elements, kw)``
        after examining the originals passed to this function, which
        are the arguments ``(request, elements, kw)``.  The simplest
        pregenerator is::

            def pregenerator(request, elements, kw):
                return elements, kw

        You can employ a pregenerator by passing a ``pregenerator``
        argument to the
        :meth:`pyramid.config.Configurator.add_route`
        function.

        """

class IRoute(Interface):
    """ Interface representing the type of object returned from
    ``IRoutesMapper.get_route``"""
    name = Attribute('The route name')
    pattern = Attribute('The route pattern')
    factory = Attribute(
        'The :term:`root factory` used by the :app:`Pyramid` router '
        'when this route matches (or ``None``)')
    predicates = Attribute(
        'A sequence of :term:`route predicate` objects used to '
        'determine if a request matches this route or not after '
        'basic pattern matching has been completed.')
    pregenerator = Attribute('This attribute should either be ``None`` or '
                             'a callable object implementing the '
                             '``IRoutePregenerator`` interface')
        
    def match(path):
        """
        If the ``path`` passed to this function can be matched by the
        ``pattern`` of this route, return a dictionary (the
        'matchdict'), which will contain keys representing the dynamic
        segment markers in the pattern mapped to values extracted from
        the provided ``path``.

        If the ``path`` passed to this function cannot be matched by
        the ``pattern`` of this route, return ``None``.
        """
    def generate(kw):
        """
        Generate a URL based on filling in the dynamic segment markers
        in the pattern using the ``kw`` dictionary provided.
        """

class IRoutesMapper(Interface):
    """ Interface representing a Routes ``Mapper`` object """
    def get_routes():
        """ Return a sequence of Route objects registered in the mapper.
        Static routes will not be returned in this sequence."""

    def has_routes():
        """ Returns ``True`` if any route has been registered. """

    def get_route(name):
        """ Returns an ``IRoute`` object if a route with the name ``name``
        was registered, otherwise return ``None``."""

    def connect(name, pattern, factory=None, predicates=(), pregenerator=None,
                static=True):
        """ Add a new route. """

    def generate(name, kw):
        """ Generate a URL using the route named ``name`` with the
        keywords implied by kw"""

    def __call__(request):
        """ Return a dictionary containing matching information for
        the request; the ``route`` key of this dictionary will either
        be a Route object or ``None`` if no route matched; the
        ``match`` key will be the matchdict or ``None`` if no route
        matched.  Static routes will not be considered for matching.  """

class IResourceURL(Interface):
    virtual_path = Attribute(
        'The virtual url path of the resource as a string.'
        )
    physical_path = Attribute(
        'The physical url path of the resource as a string.'
        )
    virtual_path_tuple = Attribute(
        'The virtual url path of the resource as a tuple.  (New in 1.5)'
        )
    physical_path_tuple = Attribute(
        'The physical url path of the resource as a tuple. (New in 1.5)'
        )

class IContextURL(IResourceURL):
    """
    .. deprecated:: 1.3
        An adapter which deals with URLs related to a context.  Use
        :class:`pyramid.interfaces.IResourceURL` instead.
    """
    # this class subclasses IResourceURL because request.resource_url looks
    # for IResourceURL via queryAdapter.  queryAdapter will find a deprecated
    # IContextURL registration if no registration for IResourceURL exists.
    # In reality, however, IContextURL objects were never required to have
    # the virtual_path or physical_path attributes spelled in IResourceURL.
    # The inheritance relationship is purely to benefit adapter lookup,
    # not to imply an inheritance relationship of interface attributes
    # and methods.
    #
    # Mechanics:
    #
    # class Fudge(object):
    #     def __init__(self, one, two):
    #         print(one, two)
    # class Another(object):
    #     def __init__(self, one, two):
    #         print(one, two)
    # ob = object()
    # r.registerAdapter(Fudge, (Interface, Interface), IContextURL)
    # print(r.queryMultiAdapter((ob, ob), IResourceURL))
    # r.registerAdapter(Another, (Interface, Interface), IResourceURL)
    # print(r.queryMultiAdapter((ob, ob), IResourceURL))
    #
    # prints
    #
    # <object object at 0x7fa678f3e2a0> <object object at 0x7fa678f3e2a0>
    # <__main__.Fudge object at 0x1cda890>
    # <object object at 0x7fa678f3e2a0> <object object at 0x7fa678f3e2a0>
    # <__main__.Another object at 0x1cda850>
    
    def virtual_root():
        """ Return the virtual root related to a request and the
        current context"""

    def __call__():
        """ Return a URL that points to the context. """

deprecated(
    'IContextURL',
    'As of Pyramid 1.3 the, "pyramid.interfaces.IContextURL" interface is '
    'scheduled to be removed.   Use the '
    '"pyramid.config.Configurator.add_resource_url_adapter" method to register '
    'a class that implements "pyramid.interfaces.IResourceURL" instead. '
    'See the "What\'s new In Pyramid 1.3" document for more details.'
    )

class IPEP302Loader(Interface):
    """ See http://www.python.org/dev/peps/pep-0302/#id30.
    """
    def get_data(path):
        """ Retrieve data for and arbitrary "files" from storage backend.

        Raise IOError for not found.

        Data is returned as bytes.
        """

    def is_package(fullname):
        """ Return True if the module specified by 'fullname' is a package.
        """

    def get_code(fullname):
        """ Return the code object for the module identified by 'fullname'.
        
        Return 'None' if it's a built-in or extension module.
        
        If the loader doesn't have the code object but it does have the source
        code, return the compiled source code.

        Raise ImportError if the module can't be found by the importer at all.
        """

    def get_source(fullname):
        """ Return the source code for the module identified by 'fullname'.
        
        Return a string, using newline characters for line endings, or None
        if the source is not available.
            
        Raise ImportError if the module can't be found by the importer at all.
        """

    def get_filename(fullname):
        """ Return the value of '__file__' if the named module was loaded.
        
        If the module is not found, raise ImportError.
        """


class IPackageOverrides(IPEP302Loader):
    """ Utility for pkg_resources overrides """

# VH_ROOT_KEY is an interface; its imported from other packages (e.g.
# traversalwrapper)
VH_ROOT_KEY = 'HTTP_X_VHM_ROOT'

class ILocalizer(Interface):
    """ Localizer for a specific language """

class ILocaleNegotiator(Interface):
    def __call__(request):
        """ Return a locale name """

class ITranslationDirectories(Interface):
    """ A list object representing all known translation directories
    for an application"""

class IDefaultPermission(Interface):
    """ A string object representing the default permission to be used
    for all view configurations which do not explicitly declare their
    own."""

class ISessionFactory(Interface):
    """ An interface representing a factory which accepts a request object and
    returns an ISession object """
    def __call__(request):
        """ Return an ISession object """

class ISession(IDict):
    """ An interface representing a session (a web session object,
    usually accessed via ``request.session``.

    Keys and values of a session must be pickleable.
    """

    # attributes

    created = Attribute('Integer representing Epoch time when created.')
    new = Attribute('Boolean attribute.  If ``True``, the session is new.')

    # special methods

    def invalidate():
        """ Invalidate the session.  The action caused by
        ``invalidate`` is implementation-dependent, but it should have
        the effect of completely dissociating any data stored in the
        session with the current request.  It might set response
        values (such as one which clears a cookie), or it might not.

        An invalidated session may be used after the call to ``invalidate``
        with the effect that a new session is created to store the data. This
        enables workflows requiring an entirely new session, such as in the
        case of changing privilege levels or preventing fixation attacks.
        """

    def changed():
        """ Mark the session as changed. A user of a session should
        call this method after he or she mutates a mutable object that
        is *a value of the session* (it should not be required after
        mutating the session itself).  For example, if the user has
        stored a dictionary in the session under the key ``foo``, and
        he or she does ``session['foo'] = {}``, ``changed()`` needn't
        be called.  However, if subsequently he or she does
        ``session['foo']['a'] = 1``, ``changed()`` must be called for
        the sessioning machinery to notice the mutation of the
        internal dictionary."""

    def flash(msg, queue='', allow_duplicate=True):
        """ Push a flash message onto the end of the flash queue represented
        by ``queue``.  An alternate flash message queue can used by passing
        an optional ``queue``, which must be a string.  If
        ``allow_duplicate`` is false, if the ``msg`` already exists in the
        queue, it will not be re-added."""

    def pop_flash(queue=''):
        """ Pop a queue from the flash storage.  The queue is removed from
        flash storage after this message is called.  The queue is returned;
        it is a list of flash messages added by
        :meth:`pyramid.interfaces.ISession.flash`"""

    def peek_flash(queue=''):
        """ Peek at a queue in the flash storage.  The queue remains in
        flash storage after this message is called.  The queue is returned;
        it is a list of flash messages added by
        :meth:`pyramid.interfaces.ISession.flash`
        """

    def new_csrf_token():
        """ Create and set into the session a new, random cross-site request
        forgery protection token.  Return the token.  It will be a string."""

    def get_csrf_token():
        """ Return a random cross-site request forgery protection token.  It
        will be a string.  If a token was previously added to the session via
        ``new_csrf_token``, that token will be returned.  If no CSRF token
        was previously set into the session, ``new_csrf_token`` will be
        called, which will create and set a token, and this token will be
        returned.
        """

class IIntrospector(Interface):
    def get(category_name, discriminator, default=None):
        """ Get the IIntrospectable related to the category_name and the
        discriminator (or discriminator hash) ``discriminator``.  If it does
        not exist in the introspector, return the value of ``default`` """

    def get_category(category_name, default=None, sort_key=None):
        """ Get a sequence of dictionaries in the form
        ``[{'introspectable':IIntrospectable, 'related':[sequence of related
        IIntrospectables]}, ...]`` where each introspectable is part of the
        category associated with ``category_name`` .

        If the category named ``category_name`` does not exist in the
        introspector the value passed as ``default`` will be returned.

        If ``sort_key`` is ``None``, the sequence will be returned in the
        order the introspectables were added to the introspector.  Otherwise,
        sort_key should be a function that accepts an IIntrospectable and
        returns a value from it (ala the ``key`` function of Python's
        ``sorted`` callable)."""

    def categories():
        """ Return a sorted sequence of category names known by
         this introspector """

    def categorized(sort_key=None):
        """ Get a sequence of tuples in the form ``[(category_name,
        [{'introspectable':IIntrospectable, 'related':[sequence of related
        IIntrospectables]}, ...])]`` representing all known
        introspectables.  If ``sort_key`` is ``None``, each introspectables
        sequence will be returned in the order the introspectables were added
        to the introspector.  Otherwise, sort_key should be a function that
        accepts an IIntrospectable and returns a value from it (ala the
        ``key`` function of Python's ``sorted`` callable)."""

    def remove(category_name, discriminator):
        """ Remove the IIntrospectable related to ``category_name`` and
        ``discriminator`` from the introspector, and fix up any relations
        that the introspectable participates in. This method will not raise
        an error if an introspectable related to the category name and
        discriminator does not exist."""

    def related(intr):
        """ Return a sequence of IIntrospectables related to the
        IIntrospectable ``intr``. Return the empty sequence if no relations
        for exist."""

    def add(intr):
        """ Add the IIntrospectable ``intr`` (use instead of
        :meth:`pyramid.interfaces.IIntrospector.add` when you have a custom
        IIntrospectable). Replaces any existing introspectable registered
        using the same category/discriminator.

        This method is not typically called directly, instead it's called
        indirectly by :meth:`pyramid.interfaces.IIntrospector.register`"""

    def relate(*pairs):
        """ Given any number of ``(category_name, discriminator)`` pairs
        passed as positional arguments, relate the associated introspectables
        to each other. The introspectable related to each pair must have
        already been added via ``.add`` or ``.add_intr``; a :exc:`KeyError`
        will result if this is not true.  An error will not be raised if any
        pair has already been associated with another.

        This method is not typically called directly, instead it's called
        indirectly by :meth:`pyramid.interfaces.IIntrospector.register`
        """

    def unrelate(*pairs):
        """ Given any number of ``(category_name, discriminator)`` pairs
        passed as positional arguments, unrelate the associated introspectables
        from each other. The introspectable related to each pair must have
        already been added via ``.add`` or ``.add_intr``; a :exc:`KeyError`
        will result if this is not true.  An error will not be raised if any
        pair is not already related to another.

        This method is not typically called directly, instead it's called
        indirectly by :meth:`pyramid.interfaces.IIntrospector.register`
        """


class IIntrospectable(Interface):
    """ An introspectable object used for configuration introspection.  In
    addition to the methods below, objects which implement this interface
    must also implement all the methods of Python's
    ``collections.MutableMapping`` (the "dictionary interface"), and must be
    hashable."""

    title = Attribute('Text title describing this introspectable')
    type_name = Attribute('Text type name describing this introspectable')
    order = Attribute('integer order in which registered with introspector '
                      '(managed by introspector, usually)')
    category_name = Attribute('introspection category name')
    discriminator = Attribute('introspectable discriminator (within category) '
                              '(must be hashable)')
    discriminator_hash = Attribute('an integer hash of the discriminator')
    action_info = Attribute('An IActionInfo object representing the caller '
                            'that invoked the creation of this introspectable '
                            '(usually a sentinel until updated during '
                            'self.register)')

    def relate(category_name, discriminator):
        """ Indicate an intent to relate this IIntrospectable with another
        IIntrospectable (the one associated with the ``category_name`` and
        ``discriminator``) during action execution.
        """

    def unrelate(category_name, discriminator):
        """ Indicate an intent to break the relationship between this
        IIntrospectable with another IIntrospectable (the one associated with
        the ``category_name`` and ``discriminator``) during action execution.
        """

    def register(introspector, action_info):
        """ Register this IIntrospectable with an introspector.  This method
        is invoked during action execution.  Adds the introspectable and its
        relations to the introspector.  ``introspector`` should be an object
        implementing IIntrospector.  ``action_info`` should be a object
        implementing the interface :class:`pyramid.interfaces.IActionInfo`
        representing the call that registered this introspectable.
        Pseudocode for an implementation of this method:

        .. code-block:: python

            def register(self, introspector, action_info):
                self.action_info = action_info
                introspector.add(self)
                for methodname, category_name, discriminator in self._relations:
                    method = getattr(introspector, methodname)
                    method((i.category_name, i.discriminator),
                           (category_name, discriminator))
        """

    def __hash__():

        """ Introspectables must be hashable.  The typical implementation of
        an introsepectable's __hash__ is::

          return hash((self.category_name,) + (self.discriminator,))
        """

class IActionInfo(Interface):
    """ Class which provides code introspection capability associated with an
    action.  The ParserInfo class used by ZCML implements the same interface."""
    file = Attribute(
        'Filename of action-invoking code as a string')
    line = Attribute(
        'Starting line number in file (as an integer) of action-invoking code.'
        'This will be ``None`` if the value could not be determined.')

    def __str__():
        """ Return a representation of the action information (including
        source code from file, if possible) """

class IAssetDescriptor(Interface):
    """
    Describes an :term:`asset`.
    """

    def absspec():
        """
        Returns the absolute asset specification for this asset
        (e.g. ``mypackage:templates/foo.pt``).
        """

    def abspath():
        """
        Returns an absolute path in the filesystem to the asset.
        """

    def stream():
        """
        Returns an input stream for reading asset contents.  Raises an
        exception if the asset is a directory or does not exist.
        """

    def isdir():
        """
        Returns True if the asset is a directory, otherwise returns False.
        """

    def listdir():
        """
        Returns iterable of filenames of directory contents.  Raises an
        exception if asset is not a directory.
        """

    def exists():
        """
        Returns True if asset exists, otherwise returns False.
        """

class IJSONAdapter(Interface):
    """
    Marker interface for objects that can convert an arbitrary object
    into a JSON-serializable primitive.
    """

class IPredicateList(Interface):
    """ Interface representing a predicate list """

# configuration phases: a lower phase number means the actions associated
# with this phase will be executed earlier than those with later phase
# numbers.  The default phase number is 0, FTR.

PHASE1_CONFIG = -20
PHASE2_CONFIG = -10

