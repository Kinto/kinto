"""
HTTP Exceptions
---------------

This module contains Pyramid HTTP exception classes.  Each class relates to a
single HTTP status code.  Each class is a subclass of the
:class:`~HTTPException`.  Each exception class is also a :term:`response`
object.

Each exception class has a status code according to :rfc:`2068`:
codes with 100-300 are not really errors; 400s are client errors,
and 500s are server errors.

Exception
  HTTPException
    HTTPSuccessful
      * 200 - HTTPOk
      * 201 - HTTPCreated
      * 202 - HTTPAccepted
      * 203 - HTTPNonAuthoritativeInformation
      * 204 - HTTPNoContent
      * 205 - HTTPResetContent
      * 206 - HTTPPartialContent
    HTTPRedirection
      * 300 - HTTPMultipleChoices
      * 301 - HTTPMovedPermanently
      * 302 - HTTPFound
      * 303 - HTTPSeeOther
      * 304 - HTTPNotModified
      * 305 - HTTPUseProxy
      * 307 - HTTPTemporaryRedirect
    HTTPError
      HTTPClientError
        * 400 - HTTPBadRequest
        * 401 - HTTPUnauthorized
        * 402 - HTTPPaymentRequired
        * 403 - HTTPForbidden
        * 404 - HTTPNotFound
        * 405 - HTTPMethodNotAllowed
        * 406 - HTTPNotAcceptable
        * 407 - HTTPProxyAuthenticationRequired
        * 408 - HTTPRequestTimeout
        * 409 - HTTPConflict
        * 410 - HTTPGone
        * 411 - HTTPLengthRequired
        * 412 - HTTPPreconditionFailed
        * 413 - HTTPRequestEntityTooLarge
        * 414 - HTTPRequestURITooLong
        * 415 - HTTPUnsupportedMediaType
        * 416 - HTTPRequestRangeNotSatisfiable
        * 417 - HTTPExpectationFailed
        * 422 - HTTPUnprocessableEntity
        * 423 - HTTPLocked
        * 424 - HTTPFailedDependency
      HTTPServerError
        * 500 - HTTPInternalServerError
        * 501 - HTTPNotImplemented
        * 502 - HTTPBadGateway
        * 503 - HTTPServiceUnavailable
        * 504 - HTTPGatewayTimeout
        * 505 - HTTPVersionNotSupported
        * 507 - HTTPInsufficientStorage

HTTP exceptions are also :term:`response` objects, thus they accept most of
the same parameters that can be passed to a regular
:class:`~pyramid.response.Response`. Each HTTP exception also has the
following attributes:

   ``code``
       the HTTP status code for the exception

   ``title``
       remainder of the status line (stuff after the code)

   ``explanation``
       a plain-text explanation of the error message that is
       not subject to environment or header substitutions;
       it is accessible in the template via ${explanation}

   ``detail``
       a plain-text message customization that is not subject
       to environment or header substitutions; accessible in
       the template via ${detail}

   ``body_template``
       a ``String.template``-format content fragment used for environment
       and header substitution; the default template includes both
       the explanation and further detail provided in the
       message.

Each HTTP exception accepts the following parameters, any others will
be forwarded to its :class:`~pyramid.response.Response` superclass:

   ``detail``
     a plain-text override of the default ``detail``

   ``headers``
     a list of (k,v) header pairs

   ``comment``
     a plain-text additional information which is
     usually stripped/hidden for end-users

   ``body_template``
     a ``string.Template`` object containing a content fragment in HTML
     that frames the explanation and further detail

   ``body``
     a string that will override the ``body_template`` and be used as the
     body of the response.

Substitution of response headers into template values is always performed.
Substitution of WSGI environment values is performed if a ``request`` is
passed to the exception's constructor.

The subclasses of :class:`~_HTTPMove` 
(:class:`~HTTPMultipleChoices`, :class:`~HTTPMovedPermanently`,
:class:`~HTTPFound`, :class:`~HTTPSeeOther`, :class:`~HTTPUseProxy` and
:class:`~HTTPTemporaryRedirect`) are redirections that require a ``Location`` 
field. Reflecting this, these subclasses have one additional keyword argument:
``location``, which indicates the location to which to redirect.
"""

from string import Template

from zope.interface import implementer

from webob import html_escape as _html_escape

from pyramid.compat import (
    class_types,
    text_type,
    binary_type,
    text_,
    )

from pyramid.interfaces import IExceptionResponse
from pyramid.response import Response

def _no_escape(value):
    if value is None:
        return ''
    if not isinstance(value, text_type):
        if hasattr(value, '__unicode__'):
            value = value.__unicode__()
        if isinstance(value, binary_type):
            value = text_(value, 'utf-8')
        else:
            value = text_type(value)
    return value

@implementer(IExceptionResponse)
class HTTPException(Response, Exception):

    ## You should set in subclasses:
    # code = 200
    # title = 'OK'
    # explanation = 'why this happens'
    # body_template_obj = Template('response template')

    # differences from webob.exc.WSGIHTTPException:
    #
    # - doesn't use "strip_tags" (${br} placeholder for <br/>, no other html
    #   in default body template)
    #
    # - __call__ never generates a new Response, it always mutates self
    #
    # - explicitly sets self.message = detail to prevent whining by Python
    #   2.6.5+ access of Exception.message
    #
    # - its base class of HTTPException is no longer a Python 2.4 compatibility
    #   shim; it's purely a base class that inherits from Exception.  This
    #   implies that this class' ``exception`` property always returns
    #   ``self`` (it exists only for bw compat at this point).
    #
    # - documentation improvements (Pyramid-specific docstrings where necessary)
    #
    code = None
    title = None
    explanation = ''
    body_template_obj = Template('''\
${explanation}${br}${br}
${detail}
${html_comment}
''')

    plain_template_obj = Template('''\
${status}

${body}''')

    html_template_obj = Template('''\
<html>
 <head>
  <title>${status}</title>
 </head>
 <body>
  <h1>${status}</h1>
  ${body}
 </body>
</html>''')

    ## Set this to True for responses that should have no request body
    empty_body = False

    def __init__(self, detail=None, headers=None, comment=None,
                 body_template=None, **kw):
        status = '%s %s' % (self.code, self.title)
        Response.__init__(self, status=status, **kw)
        Exception.__init__(self, detail)
        self.detail = self.message = detail
        if headers:
            self.headers.extend(headers)
        self.comment = comment
        if body_template is not None:
            self.body_template = body_template
            self.body_template_obj = Template(body_template)

        if self.empty_body:
            del self.content_type
            del self.content_length

    def __str__(self):
        return self.detail or self.explanation

    def prepare(self, environ):
        if not self.body and not self.empty_body:
            html_comment = ''
            comment = self.comment or ''
            accept = environ.get('HTTP_ACCEPT', '')
            if accept and 'html' in accept or '*/*' in accept:
                self.content_type = 'text/html'
                escape = _html_escape
                page_template = self.html_template_obj
                br = '<br/>'
                if comment:
                    html_comment = '<!-- %s -->' % escape(comment)
            else:
                self.content_type = 'text/plain'
                escape = _no_escape
                page_template = self.plain_template_obj
                br = '\n'
                if comment:
                    html_comment = escape(comment)
            args = {
                'br':br,
                'explanation': escape(self.explanation),
                'detail': escape(self.detail or ''),
                'comment': escape(comment),
                'html_comment':html_comment,
                }
            body_tmpl = self.body_template_obj
            if HTTPException.body_template_obj is not body_tmpl:
                # Custom template; add headers to args
                for k, v in environ.items():
                    if (not k.startswith('wsgi.')) and ('.' in k):
                        # omit custom environ variables, stringifying them may
                        # trigger code that should not be executed here; see
                        # https://github.com/Pylons/pyramid/issues/239
                        continue
                    args[k] = escape(v)
                for k, v in self.headers.items():
                    args[k.lower()] = escape(v)
            body = body_tmpl.substitute(args)
            page = page_template.substitute(status=self.status, body=body)
            if isinstance(page, text_type):
                page = page.encode(self.charset)
            self.app_iter = [page]
            self.body = page

    @property
    def wsgi_response(self):
        # bw compat only
        return self

    exception = wsgi_response # bw compat only

    def __call__(self, environ, start_response):
        # differences from webob.exc.WSGIHTTPException
        #
        # - does not try to deal with HEAD requests
        #
        # - does not manufacture a new response object when generating
        #   the default response
        #
        self.prepare(environ)
        return Response.__call__(self, environ, start_response)

WSGIHTTPException = HTTPException # b/c post 1.5

class HTTPError(HTTPException):
    """
    base class for exceptions with status codes in the 400s and 500s

    This is an exception which indicates that an error has occurred,
    and that any work in progress should not be committed.  
    """

class HTTPRedirection(HTTPException):
    """
    base class for exceptions with status codes in the 300s (redirections)

    This is an abstract base class for 3xx redirection.  It indicates
    that further action needs to be taken by the user agent in order
    to fulfill the request.  It does not necessarly signal an error
    condition.
    """

class HTTPSuccessful(HTTPException):
    """
    Base class for exceptions with status codes in the 200s (successful
    responses)
    """

############################################################
## 2xx success
############################################################

class HTTPOk(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    Indicates that the request has succeeded.
    
    code: 200, title: OK
    """
    code = 200
    title = 'OK'

class HTTPCreated(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    This indicates that request has been fulfilled and resulted in a new
    resource being created.
    
    code: 201, title: Created
    """
    code = 201
    title = 'Created'

class HTTPAccepted(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    This indicates that the request has been accepted for processing, but the
    processing has not been completed.

    code: 202, title: Accepted
    """
    code = 202
    title = 'Accepted'
    explanation = 'The request is accepted for processing.'

class HTTPNonAuthoritativeInformation(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    This indicates that the returned metainformation in the entity-header is
    not the definitive set as available from the origin server, but is
    gathered from a local or a third-party copy.

    code: 203, title: Non-Authoritative Information
    """
    code = 203
    title = 'Non-Authoritative Information'

class HTTPNoContent(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    This indicates that the server has fulfilled the request but does
    not need to return an entity-body, and might want to return updated
    metainformation.
    
    code: 204, title: No Content
    """
    code = 204
    title = 'No Content'
    empty_body = True

class HTTPResetContent(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    This indicates that the server has fulfilled the request and
    the user agent SHOULD reset the document view which caused the
    request to be sent.
    
    code: 205, title: Reset Content
    """
    code = 205
    title = 'Reset Content'
    empty_body = True

class HTTPPartialContent(HTTPSuccessful):
    """
    subclass of :class:`~HTTPSuccessful`

    This indicates that the server has fulfilled the partial GET
    request for the resource.
    
    code: 206, title: Partial Content
    """
    code = 206
    title = 'Partial Content'

## FIXME: add 207 Multi-Status (but it's complicated)

############################################################
## 3xx redirection
############################################################

class _HTTPMove(HTTPRedirection):
    """
    redirections which require a Location field

    Since a 'Location' header is a required attribute of 301, 302, 303,
    305 and 307 (but not 304), this base class provides the mechanics to
    make this easy.

    You must provide a ``location`` keyword argument.
    """
    # differences from webob.exc._HTTPMove:
    #
    # - ${location} isn't wrapped in an <a> tag in body
    #
    # - location keyword arg defaults to ''
    #
    # - location isn't prepended with req.path_url when adding it as
    #   a header
    #
    # - ``location`` is first keyword (and positional) argument
    #
    # - ``add_slash`` argument is no longer accepted:  code that passes
    #   add_slash argument to the constructor will receive an exception.
    explanation = 'The resource has been moved to'
    body_template_obj = Template('''\
${explanation} ${location}; you should be redirected automatically.
${detail}
${html_comment}''')

    def __init__(self, location='', detail=None, headers=None, comment=None,
                 body_template=None, **kw):
        if location is None:
            raise ValueError("HTTP redirects need a location to redirect to.")
        super(_HTTPMove, self).__init__(
            detail=detail, headers=headers, comment=comment,
            body_template=body_template, location=location, **kw)

class HTTPMultipleChoices(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource corresponds to any one
    of a set of representations, each with its own specific location,
    and agent-driven negotiation information is being provided so that
    the user can select a preferred representation and redirect its
    request to that location.
    
    code: 300, title: Multiple Choices
    """
    code = 300
    title = 'Multiple Choices'

class HTTPMovedPermanently(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource has been assigned a new
    permanent URI and any future references to this resource SHOULD use
    one of the returned URIs.

    code: 301, title: Moved Permanently
    """
    code = 301
    title = 'Moved Permanently'

class HTTPFound(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource resides temporarily under
    a different URI.
    
    code: 302, title: Found
    """
    code = 302
    title = 'Found'
    explanation = 'The resource was found at'

# This one is safe after a POST (the redirected location will be
# retrieved with GET):
class HTTPSeeOther(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the response to the request can be found under
    a different URI and SHOULD be retrieved using a GET method on that
    resource.
    
    code: 303, title: See Other
    """
    code = 303
    title = 'See Other'

class HTTPNotModified(HTTPRedirection):
    """
    subclass of :class:`~HTTPRedirection`

    This indicates that if the client has performed a conditional GET
    request and access is allowed, but the document has not been
    modified, the server SHOULD respond with this status code.

    code: 304, title: Not Modified
    """
    # FIXME: this should include a date or etag header
    code = 304
    title = 'Not Modified'
    empty_body = True

class HTTPUseProxy(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource MUST be accessed through
    the proxy given by the Location field.
    
    code: 305, title: Use Proxy
    """
    # Not a move, but looks a little like one
    code = 305
    title = 'Use Proxy'
    explanation = (
        'The resource must be accessed through a proxy located at')

class HTTPTemporaryRedirect(_HTTPMove):
    """
    subclass of :class:`~_HTTPMove`

    This indicates that the requested resource resides temporarily
    under a different URI.
    
    code: 307, title: Temporary Redirect
    """
    code = 307
    title = 'Temporary Redirect'

############################################################
## 4xx client error
############################################################

class HTTPClientError(HTTPError):
    """
    base class for the 400s, where the client is in error

    This is an error condition in which the client is presumed to be
    in-error.  This is an expected problem, and thus is not considered
    a bug.  A server-side traceback is not warranted.  Unless specialized,
    this is a '400 Bad Request'
    """
    code = 400
    title = 'Bad Request'
    explanation = ('The server could not comply with the request since '
                   'it is either malformed or otherwise incorrect.')

class HTTPBadRequest(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the body or headers failed validity checks,
    preventing the server from being able to continue processing.

    code: 400, title: Bad Request
    """
    pass

class HTTPUnauthorized(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the request requires user authentication.
    
    code: 401, title: Unauthorized
    """
    code = 401
    title = 'Unauthorized'
    explanation = (
        'This server could not verify that you are authorized to '
        'access the document you requested.  Either you supplied the '
        'wrong credentials (e.g., bad password), or your browser '
        'does not understand how to supply the credentials required.')

class HTTPPaymentRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`
    
    code: 402, title: Payment Required
    """
    code = 402
    title = 'Payment Required'
    explanation = ('Access was denied for financial reasons.')

class HTTPForbidden(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server understood the request, but is
    refusing to fulfill it.

    code: 403, title: Forbidden

    Raise this exception within :term:`view` code to immediately return the
    :term:`forbidden view` to the invoking user.  Usually this is a basic
    ``403`` page, but the forbidden view can be customized as necessary.  See
    :ref:`changing_the_forbidden_view`.  A ``Forbidden`` exception will be
    the ``context`` of a :term:`Forbidden View`.

    This exception's constructor treats two arguments specially.  The first
    argument, ``detail``, should be a string.  The value of this string will
    be used as the ``message`` attribute of the exception object.  The second
    special keyword argument, ``result`` is usually an instance of
    :class:`pyramid.security.Denied` or :class:`pyramid.security.ACLDenied`
    each of which indicates a reason for the forbidden error.  However,
    ``result`` is also permitted to be just a plain boolean ``False`` object
    or ``None``.  The ``result`` value will be used as the ``result``
    attribute of the exception object.  It defaults to ``None``.

    The :term:`Forbidden View` can use the attributes of a Forbidden
    exception as necessary to provide extended information in an error
    report shown to a user.
    """
    # differences from webob.exc.HTTPForbidden:
    #
    # - accepts a ``result`` keyword argument
    # 
    # - overrides constructor to set ``self.result``
    #
    # differences from older ``pyramid.exceptions.Forbidden``:
    #
    # - ``result`` must be passed as a keyword argument.
    #
    code = 403
    title = 'Forbidden'
    explanation = ('Access was denied to this resource.')
    def __init__(self, detail=None, headers=None, comment=None,
                 body_template=None, result=None, **kw):
        HTTPClientError.__init__(self, detail=detail, headers=headers,
                                 comment=comment, body_template=body_template,
                                 **kw)
        self.result = result

class HTTPNotFound(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server did not find anything matching the
    Request-URI.
    
    code: 404, title: Not Found

    Raise this exception within :term:`view` code to immediately
    return the :term:`Not Found View` to the invoking user.  Usually
    this is a basic ``404`` page, but the Not Found View can be
    customized as necessary.  See :ref:`changing_the_notfound_view`.

    This exception's constructor accepts a ``detail`` argument
    (the first argument), which should be a string.  The value of this
    string will be available as the ``message`` attribute of this exception,
    for availability to the :term:`Not Found View`.
    """
    code = 404
    title = 'Not Found'
    explanation = ('The resource could not be found.')

class HTTPMethodNotAllowed(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the method specified in the Request-Line is
    not allowed for the resource identified by the Request-URI.

    code: 405, title: Method Not Allowed
    """
    # differences from webob.exc.HTTPMethodNotAllowed:
    #
    # - body_template_obj uses ${br} instead of <br />
    code = 405
    title = 'Method Not Allowed'
    body_template_obj = Template('''\
The method ${REQUEST_METHOD} is not allowed for this resource. ${br}${br}
${detail}''')

class HTTPNotAcceptable(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates the resource identified by the request is only
    capable of generating response entities which have content
    characteristics not acceptable according to the accept headers
    sent in the request.
    
    code: 406, title: Not Acceptable
    """
    # differences from webob.exc.HTTPNotAcceptable:
    #
    # - "template" attribute left off (useless, bug in webob?)
    code = 406
    title = 'Not Acceptable'

class HTTPProxyAuthenticationRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This is similar to 401, but indicates that the client must first
    authenticate itself with the proxy.
    
    code: 407, title: Proxy Authentication Required
    """
    code = 407
    title = 'Proxy Authentication Required'
    explanation = ('Authentication with a local proxy is needed.')

class HTTPRequestTimeout(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the client did not produce a request within
    the time that the server was prepared to wait.
    
    code: 408, title: Request Timeout
    """
    code = 408
    title = 'Request Timeout'
    explanation = ('The server has waited too long for the request to '
                   'be sent by the client.')

class HTTPConflict(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the request could not be completed due to a
    conflict with the current state of the resource.
    
    code: 409, title: Conflict
    """
    code = 409
    title = 'Conflict'
    explanation = ('There was a conflict when trying to complete '
                   'your request.')

class HTTPGone(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the requested resource is no longer available
    at the server and no forwarding address is known.
    
    code: 410, title: Gone
    """
    code = 410
    title = 'Gone'
    explanation = ('This resource is no longer available.  No forwarding '
                   'address is given.')

class HTTPLengthRequired(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server refuses to accept the request
    without a defined Content-Length.
    
    code: 411, title: Length Required
    """
    code = 411
    title = 'Length Required'
    explanation = ('Content-Length header required.')

class HTTPPreconditionFailed(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the precondition given in one or more of the
    request-header fields evaluated to false when it was tested on the
    server.
    
    code: 412, title: Precondition Failed
    """
    code = 412
    title = 'Precondition Failed'
    explanation = ('Request precondition failed.')

class HTTPRequestEntityTooLarge(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is refusing to process a request
    because the request entity is larger than the server is willing or
    able to process.

    code: 413, title: Request Entity Too Large
    """
    code = 413
    title = 'Request Entity Too Large'
    explanation = ('The body of your request was too large for this server.')

class HTTPRequestURITooLong(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is refusing to service the request
    because the Request-URI is longer than the server is willing to
    interpret.
    
    code: 414, title: Request-URI Too Long
    """
    code = 414
    title = 'Request-URI Too Long'
    explanation = ('The request URI was too long for this server.')

class HTTPUnsupportedMediaType(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is refusing to service the request
    because the entity of the request is in a format not supported by
    the requested resource for the requested method.
    
    code: 415, title: Unsupported Media Type
    """
    # differences from webob.exc.HTTPUnsupportedMediaType:
    #
    # - "template_obj" attribute left off (useless, bug in webob?)
    code = 415
    title = 'Unsupported Media Type'

class HTTPRequestRangeNotSatisfiable(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    The server SHOULD return a response with this status code if a
    request included a Range request-header field, and none of the
    range-specifier values in this field overlap the current extent
    of the selected resource, and the request did not include an
    If-Range request-header field.
    
    code: 416, title: Request Range Not Satisfiable
    """
    code = 416
    title = 'Request Range Not Satisfiable'
    explanation = ('The Range requested is not available.')

class HTTPExpectationFailed(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indidcates that the expectation given in an Expect
    request-header field could not be met by this server.
    
    code: 417, title: Expectation Failed
    """
    code = 417
    title = 'Expectation Failed'
    explanation = ('Expectation failed.')

class HTTPUnprocessableEntity(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the server is unable to process the contained
    instructions. Only for WebDAV.
    
    code: 422, title: Unprocessable Entity
    """
    ## Note: from WebDAV
    code = 422
    title = 'Unprocessable Entity'
    explanation = 'Unable to process the contained instructions'

class HTTPLocked(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the resource is locked. Only for WebDAV
    
    code: 423, title: Locked
    """
    ## Note: from WebDAV
    code = 423
    title = 'Locked'
    explanation = ('The resource is locked')

class HTTPFailedDependency(HTTPClientError):
    """
    subclass of :class:`~HTTPClientError`

    This indicates that the method could not be performed because the
    requested action depended on another action and that action failed.
    Only for WebDAV.
    
    code: 424, title: Failed Dependency
    """
    ## Note: from WebDAV
    code = 424
    title = 'Failed Dependency'
    explanation = (
        'The method could not be performed because the requested '
        'action dependended on another action and that action failed')

############################################################
## 5xx Server Error
############################################################
#  Response status codes beginning with the digit "5" indicate cases in
#  which the server is aware that it has erred or is incapable of
#  performing the request. Except when responding to a HEAD request, the
#  server SHOULD include an entity containing an explanation of the error
#  situation, and whether it is a temporary or permanent condition. User
#  agents SHOULD display any included entity to the user. These response
#  codes are applicable to any request method.

class HTTPServerError(HTTPError):
    """
    base class for the 500s, where the server is in-error

    This is an error condition in which the server is presumed to be
    in-error.  Unless specialized, this is a '500 Internal Server Error'.
    """
    code = 500
    title = 'Internal Server Error'
    explanation = (
      'The server has either erred or is incapable of performing '
      'the requested operation.')

class HTTPInternalServerError(HTTPServerError):
    pass

class HTTPNotImplemented(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server does not support the functionality
    required to fulfill the request.
    
    code: 501, title: Not Implemented
    """
    # differences from webob.exc.HTTPNotAcceptable:
    #
    # - "template" attr left off (useless, bug in webob?)
    code = 501
    title = 'Not Implemented'

class HTTPBadGateway(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server, while acting as a gateway or proxy,
    received an invalid response from the upstream server it accessed
    in attempting to fulfill the request.
    
    code: 502, title: Bad Gateway
    """
    code = 502
    title = 'Bad Gateway'
    explanation = ('Bad gateway.')

class HTTPServiceUnavailable(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server is currently unable to handle the
    request due to a temporary overloading or maintenance of the server.
    
    code: 503, title: Service Unavailable
    """
    code = 503
    title = 'Service Unavailable'
    explanation = ('The server is currently unavailable. '
                   'Please try again at a later time.')

class HTTPGatewayTimeout(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server, while acting as a gateway or proxy,
    did not receive a timely response from the upstream server specified
    by the URI (e.g. HTTP, FTP, LDAP) or some other auxiliary server
    (e.g. DNS) it needed to access in attempting to complete the request.

    code: 504, title: Gateway Timeout
    """
    code = 504
    title = 'Gateway Timeout'
    explanation = ('The gateway has timed out.')

class HTTPVersionNotSupported(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server does not support, or refuses to
    support, the HTTP protocol version that was used in the request
    message.

    code: 505, title: HTTP Version Not Supported
    """
    code = 505
    title = 'HTTP Version Not Supported'
    explanation = ('The HTTP version is not supported.')

class HTTPInsufficientStorage(HTTPServerError):
    """
    subclass of :class:`~HTTPServerError`

    This indicates that the server does not have enough space to save
    the resource.
    
    code: 507, title: Insufficient Storage
    """
    code = 507
    title = 'Insufficient Storage'
    explanation = ('There was not enough space to save the resource')

def exception_response(status_code, **kw):
    """Creates an HTTP exception based on a status code. Example::

        raise exception_response(404) # raises an HTTPNotFound exception.

    The values passed as ``kw`` are provided to the exception's constructor.
    """
    exc = status_map[status_code](**kw)
    return exc

def default_exceptionresponse_view(context, request):
    if not isinstance(context, Exception):
        # backwards compat for an exception response view registered via
        # config.set_notfound_view or config.set_forbidden_view
        # instead of as a proper exception view
        context = request.exception or context
    return context # assumed to be an IResponse

status_map={}
code = None
for name, value in list(globals().items()):
    if (isinstance(value, class_types) and
        issubclass(value, HTTPException)
        and not name.startswith('_')):
        code = getattr(value, 'code', None)
        if code:
            status_map[code] = value
del name, value, code
