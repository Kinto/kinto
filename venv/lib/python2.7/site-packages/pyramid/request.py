import json

from zope.interface import implementer
from zope.interface.interface import InterfaceClass

from webob import BaseRequest

from pyramid.interfaces import (
    IRequest,
    IResponse,
    ISessionFactory,
    IResponseFactory,
    )

from pyramid.compat import (
    text_,
    bytes_,
    native_,
    )

from pyramid.decorator import reify
from pyramid.i18n import LocalizerRequestMixin
from pyramid.response import Response
from pyramid.security import (
    AuthenticationAPIMixin,
    AuthorizationAPIMixin,
    )
from pyramid.url import URLMethodsMixin
from pyramid.util import InstancePropertyMixin

class TemplateContext(object):
    pass

class CallbackMethodsMixin(object):
    response_callbacks = ()
    finished_callbacks = ()
    def add_response_callback(self, callback):
        """
        Add a callback to the set of callbacks to be called by the
        :term:`router` at a point after a :term:`response` object is
        successfully created.  :app:`Pyramid` does not have a
        global response object: this functionality allows an
        application to register an action to be performed against the
        response once one is created.

        A 'callback' is a callable which accepts two positional
        parameters: ``request`` and ``response``.  For example:

        .. code-block:: python
           :linenos:

           def cache_callback(request, response):
               'Set the cache_control max_age for the response'
               response.cache_control.max_age = 360
           request.add_response_callback(cache_callback)

        Response callbacks are called in the order they're added
        (first-to-most-recently-added).  No response callback is
        called if an exception happens in application code, or if the
        response object returned by :term:`view` code is invalid.

        All response callbacks are called *after* the tweens and 
        *before* the :class:`pyramid.events.NewResponse` event is sent.

        Errors raised by callbacks are not handled specially.  They
        will be propagated to the caller of the :app:`Pyramid`
        router application.

        .. seealso::

            See also :ref:`using_response_callbacks`.
        """

        callbacks = self.response_callbacks
        if not callbacks:
            callbacks = []
        callbacks.append(callback)
        self.response_callbacks = callbacks

    def _process_response_callbacks(self, response):
        callbacks = self.response_callbacks
        while callbacks:
            callback = callbacks.pop(0)
            callback(self, response)

    def add_finished_callback(self, callback):
        """
        Add a callback to the set of callbacks to be called
        unconditionally by the :term:`router` at the very end of
        request processing.

        ``callback`` is a callable which accepts a single positional
        parameter: ``request``.  For example:

        .. code-block:: python
           :linenos:

           import transaction

           def commit_callback(request):
               '''commit or abort the transaction associated with request'''
               if request.exception is not None:
                   transaction.abort()
               else:
                   transaction.commit()
           request.add_finished_callback(commit_callback)

        Finished callbacks are called in the order they're added (
        first- to most-recently- added).  Finished callbacks (unlike
        response callbacks) are *always* called, even if an exception
        happens in application code that prevents a response from
        being generated.

        The set of finished callbacks associated with a request are
        called *very late* in the processing of that request; they are
        essentially the last thing called by the :term:`router`. They
        are called after response processing has already occurred in a
        top-level ``finally:`` block within the router request
        processing code.  As a result, mutations performed to the
        ``request`` provided to a finished callback will have no
        meaningful effect, because response processing will have
        already occurred, and the request's scope will expire almost
        immediately after all finished callbacks have been processed.

        Errors raised by finished callbacks are not handled specially.
        They will be propagated to the caller of the :app:`Pyramid`
        router application.

        .. seealso::

            See also :ref:`using_finished_callbacks`.
        """

        callbacks = self.finished_callbacks
        if not callbacks:
            callbacks = []
        callbacks.append(callback)
        self.finished_callbacks = callbacks

    def _process_finished_callbacks(self):
        callbacks = self.finished_callbacks
        while callbacks:
            callback = callbacks.pop(0)
            callback(self)

@implementer(IRequest)
class Request(
    BaseRequest,
    URLMethodsMixin,
    CallbackMethodsMixin,
    InstancePropertyMixin,
    LocalizerRequestMixin,
    AuthenticationAPIMixin,
    AuthorizationAPIMixin,
    ):
    """
    A subclass of the :term:`WebOb` Request class.  An instance of
    this class is created by the :term:`router` and is provided to a
    view callable (and to other subsystems) as the ``request``
    argument.

    The documentation below (save for the ``add_response_callback`` and
    ``add_finished_callback`` methods, which are defined in this subclass
    itself, and the attributes ``context``, ``registry``, ``root``,
    ``subpath``, ``traversed``, ``view_name``, ``virtual_root`` , and
    ``virtual_root_path``, each of which is added to the request by the
    :term:`router` at request ingress time) are autogenerated from the WebOb
    source code used when this documentation was generated.

    Due to technical constraints, we can't yet display the WebOb
    version number from which this documentation is autogenerated, but
    it will be the 'prevailing WebOb version' at the time of the
    release of this :app:`Pyramid` version.  See
    http://webob.org/ for further information.
    """
    exception = None
    exc_info = None
    matchdict = None
    matched_route = None

    ResponseClass = Response

    @reify
    def tmpl_context(self):
        # docs-deprecated template context for Pylons-like apps; do not
        # remove.
        return TemplateContext()

    @reify
    def session(self):
        """ Obtain the :term:`session` object associated with this
        request.  If a :term:`session factory` has not been registered
        during application configuration, a
        :class:`pyramid.exceptions.ConfigurationError` will be raised"""
        factory = self.registry.queryUtility(ISessionFactory)
        if factory is None:
            raise AttributeError(
                'No session factory registered '
                '(see the Sessions chapter of the Pyramid documentation)')
        return factory(self)

    @reify
    def response(self):
        """This attribute is actually a "reified" property which returns an
        instance of the :class:`pyramid.response.Response`. class.  The
        response object returned does not exist until this attribute is
        accessed.  Subsequent accesses will return the same Response object.

        The ``request.response`` API is used by renderers.  A render obtains
        the response object it will return from a view that uses that renderer
        by accessing ``request.response``.  Therefore, it's possible to use the
        ``request.response`` API to set up a response object with "the
        right" attributes (e.g. by calling ``request.response.set_cookie()``)
        within a view that uses a renderer.  Mutations to this response object
        will be preserved in the response sent to the client."""
        registry = self.registry
        response_factory = registry.queryUtility(IResponseFactory,
                                                 default=Response)
        return response_factory()

    def is_response(self, ob):
        """ Return ``True`` if the object passed as ``ob`` is a valid
        response object, ``False`` otherwise."""
        if ob.__class__ is Response:
            return True
        registry = self.registry
        adapted = registry.queryAdapterOrSelf(ob, IResponse)
        if adapted is None:
            return False
        return adapted is ob

    @property
    def json_body(self):
        return json.loads(text_(self.body, self.charset))

    
def route_request_iface(name, bases=()):
    # zope.interface treats the __name__ as the __doc__ and changes __name__
    # to None for interfaces that contain spaces if you do not pass a
    # nonempty __doc__ (insane); see
    # zope.interface.interface.Element.__init__ and
    # https://github.com/Pylons/pyramid/issues/232; as a result, always pass
    # __doc__ to the InterfaceClass constructor.
    iface = InterfaceClass('%s_IRequest' % name, bases=bases,
                           __doc__="route_request_iface-generated interface")
    # for exception view lookups
    iface.combined = InterfaceClass(
        '%s_combined_IRequest' % name,
        bases=(iface, IRequest),
        __doc__ = 'route_request_iface-generated combined interface')
    return iface

def add_global_response_headers(request, headerlist):
    def add_headers(request, response):
        for k, v in headerlist:
            response.headerlist.append((k, v))
    request.add_response_callback(add_headers)

def call_app_with_subpath_as_path_info(request, app):
    # Copy the request.  Use the source request's subpath (if it exists) as
    # the new request's PATH_INFO.  Set the request copy's SCRIPT_NAME to the
    # prefix before the subpath.  Call the application with the new request
    # and return a response.
    #
    # Postconditions:
    # - SCRIPT_NAME and PATH_INFO are empty or start with /
    # - At least one of SCRIPT_NAME or PATH_INFO are set.
    # - SCRIPT_NAME is not '/' (it should be '', and PATH_INFO should
    #   be '/').

    environ = request.environ
    script_name = environ.get('SCRIPT_NAME', '')
    path_info = environ.get('PATH_INFO', '/')
    subpath = list(getattr(request, 'subpath', ()))

    new_script_name = ''

    # compute new_path_info
    new_path_info = '/' + '/'.join([native_(x.encode('utf-8'), 'latin-1')
                                    for x in subpath])

    if new_path_info != '/': # don't want a sole double-slash
        if path_info != '/': # if orig path_info is '/', we're already done
            if path_info.endswith('/'):
                # readd trailing slash stripped by subpath (traversal)
                # conversion
                new_path_info += '/'

    # compute new_script_name
    workback = (script_name + path_info).split('/')

    tmp = []
    while workback:
        if tmp == subpath:
            break
        el = workback.pop()
        if el:
            tmp.insert(0, text_(bytes_(el, 'latin-1'), 'utf-8'))

    # strip all trailing slashes from workback to avoid appending undue slashes
    # to end of script_name
    while workback and (workback[-1] == ''):
        workback = workback[:-1]

    new_script_name = '/'.join(workback)

    new_request = request.copy()
    new_request.environ['SCRIPT_NAME'] = new_script_name
    new_request.environ['PATH_INFO'] = new_path_info

    return new_request.get_response(app)
