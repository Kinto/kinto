from functools import wraps
from pyramid.request import call_app_with_subpath_as_path_info

def wsgiapp(wrapped):
    """ Decorator to turn a WSGI application into a :app:`Pyramid`
    :term:`view callable`.  This decorator differs from the
    :func:`pyramid.wsgi.wsgiapp2` decorator inasmuch as fixups of
    ``PATH_INFO`` and ``SCRIPT_NAME`` within the WSGI environment *are
    not* performed before the application is invoked.

    E.g., the following in a ``views.py`` module::

      @wsgiapp
      def hello_world(environ, start_response):
          body = 'Hello world'
          start_response('200 OK', [ ('Content-Type', 'text/plain'),
                                     ('Content-Length', len(body)) ] )
          return [body]

    Allows the following call to
    :meth:`pyramid.config.Configurator.add_view`::

        from views import hello_world
        config.add_view(hello_world, name='hello_world.txt')

    The ``wsgiapp`` decorator will convert the result of the WSGI
    application to a :term:`Response` and return it to
    :app:`Pyramid` as if the WSGI app were a :app:`Pyramid`
    view.

    """

    if wrapped is None:
        raise ValueError('wrapped can not be None')

    def decorator(context, request):
        return request.get_response(wrapped)

    # Support case where wrapped is a callable object instance
    if getattr(wrapped, '__name__', None):
        return wraps(wrapped)(decorator)
    return wraps(wrapped, ('__module__', '__doc__'))(decorator)

def wsgiapp2(wrapped):
    """ Decorator to turn a WSGI application into a :app:`Pyramid`
    view callable.  This decorator differs from the
    :func:`pyramid.wsgi.wsgiapp` decorator inasmuch as fixups of
    ``PATH_INFO`` and ``SCRIPT_NAME`` within the WSGI environment
    *are* performed before the application is invoked.

    E.g. the following in a ``views.py`` module::

      @wsgiapp2
      def hello_world(environ, start_response):
          body = 'Hello world'
          start_response('200 OK', [ ('Content-Type', 'text/plain'),
                                     ('Content-Length', len(body)) ] )
          return [body]

    Allows the following call to
    :meth:`pyramid.config.Configurator.add_view`::

        from views import hello_world
        config.add_view(hello_world, name='hello_world.txt')

    The ``wsgiapp2`` decorator will convert the result of the WSGI
    application to a Response and return it to :app:`Pyramid` as if the WSGI
    app were a :app:`Pyramid` view.  The ``SCRIPT_NAME`` and ``PATH_INFO``
    values present in the WSGI environment are fixed up before the
    application is invoked.  In particular, a new WSGI environment is
    generated, and the :term:`subpath` of the request passed to ``wsgiapp2``
    is used as the new request's ``PATH_INFO`` and everything preceding the
    subpath is used as the ``SCRIPT_NAME``.  The new environment is passed to
    the downstream WSGI application."""

    if wrapped is None:
        raise ValueError('wrapped can not be None')

    def decorator(context, request):
        return call_app_with_subpath_as_path_info(request, wrapped)

    # Support case where wrapped is a callable object instance
    if getattr(wrapped, '__name__', None):
        return wraps(wrapped)(decorator)
    return wraps(wrapped, ('__module__', '__doc__'))(decorator)
