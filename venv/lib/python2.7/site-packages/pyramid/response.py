import mimetypes
from os.path import (
    getmtime,
    getsize,
    )

import venusian

from webob import Response as _Response
from zope.interface import implementer
from pyramid.interfaces import IResponse

def init_mimetypes(mimetypes):
    # this is a function so it can be unittested
    if hasattr(mimetypes, 'init'):
        mimetypes.init()
        return True
    return False

# See http://bugs.python.org/issue5853 which is a recursion bug
# that seems to effect Python 2.6, Python 2.6.1, and 2.6.2 (a fix
# has been applied on the Python 2 trunk).
init_mimetypes(mimetypes)

_BLOCK_SIZE = 4096 * 64 # 256K

@implementer(IResponse)
class Response(_Response):
    pass

class FileResponse(Response):
    """
    A Response object that can be used to serve a static file from disk
    simply.

    ``path`` is a file path on disk.

    ``request`` must be a Pyramid :term:`request` object.  Note
    that a request *must* be passed if the response is meant to attempt to
    use the ``wsgi.file_wrapper`` feature of the web server that you're using
    to serve your Pyramid application.

    ``cache_max_age`` is the number of seconds that should be used
    to HTTP cache this response.

    ``content_type`` is the content_type of the response.

    ``content_encoding`` is the content_encoding of the response.
    It's generally safe to leave this set to ``None`` if you're serving a
    binary file.  This argument will be ignored if you also leave
    ``content-type`` as ``None``.
    """
    def __init__(self, path, request=None, cache_max_age=None,
                 content_type=None, content_encoding=None):
        if content_type is None:
            content_type, content_encoding = mimetypes.guess_type(
                path,
                strict=False
                )
            if content_type is None:
                content_type = 'application/octet-stream'
            # str-ifying content_type is a workaround for a bug in Python 2.7.7
            # on Windows where mimetypes.guess_type returns unicode for the
            # content_type.
            content_type = str(content_type)
        super(FileResponse, self).__init__(
            conditional_response=True,
            content_type=content_type,
            content_encoding=content_encoding
        )
        self.last_modified = getmtime(path)
        content_length = getsize(path)
        f = open(path, 'rb')
        app_iter = None
        if request is not None:
            environ = request.environ
            if 'wsgi.file_wrapper' in environ:
                app_iter = environ['wsgi.file_wrapper'](f, _BLOCK_SIZE)
        if app_iter is None:
            app_iter = FileIter(f, _BLOCK_SIZE)
        self.app_iter = app_iter
        # assignment of content_length must come after assignment of app_iter
        self.content_length = content_length
        if cache_max_age is not None:
            self.cache_expires = cache_max_age

class FileIter(object):
    """ A fixed-block-size iterator for use as a WSGI app_iter.

    ``file`` is a Python file pointer (or at least an object with a ``read``
    method that takes a size hint).

    ``block_size`` is an optional block size for iteration.
    """
    def __init__(self, file, block_size=_BLOCK_SIZE):
        self.file = file
        self.block_size = block_size

    def __iter__(self):
        return self

    def next(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    __next__ = next # py3

    def close(self):
        self.file.close()


class response_adapter(object):
    """ Decorator activated via a :term:`scan` which treats the function
    being decorated as a :term:`response adapter` for the set of types or
    interfaces passed as ``*types_or_ifaces`` to the decorator constructor.

    For example, if you scan the following response adapter:

    .. code-block:: python

        from pyramid.response import Response
        from pyramid.response import response_adapter

        @response_adapter(int)
        def myadapter(i):
            return Response(status=i)

    You can then return an integer from your view callables, and it will be
    converted into a response with the integer as the status code.

    More than one type or interface can be passed as a constructor argument.
    The decorated response adapter will be called for each type or interface.

    .. code-block:: python

        import json

        from pyramid.response import Response
        from pyramid.response import response_adapter

        @response_adapter(dict, list)
        def myadapter(ob):
            return Response(json.dumps(ob))
        
    This method will have no effect until a :term:`scan` is performed
    agains the package or module which contains it, ala:

    .. code-block:: python

        from pyramid.config import Configurator
        config = Configurator()
        config.scan('somepackage_containing_adapters')

    """
    venusian = venusian # for unit testing

    def __init__(self, *types_or_ifaces):
        self.types_or_ifaces = types_or_ifaces

    def register(self, scanner, name, wrapped):
        config = scanner.config
        for type_or_iface in self.types_or_ifaces:
            config.add_response_adapter(wrapped, type_or_iface)

    def __call__(self, wrapped):
        self.venusian.attach(wrapped, self.register, category='pyramid')
        return wrapped
