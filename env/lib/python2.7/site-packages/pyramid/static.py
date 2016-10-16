# -*- coding: utf-8 -*-
import json
import os

from os.path import (
    getmtime,
    normcase,
    normpath,
    join,
    isdir,
    exists,
    )

from pkg_resources import (
    resource_exists,
    resource_filename,
    resource_isdir,
    )

from repoze.lru import lru_cache

from pyramid.asset import (
    abspath_from_asset_spec,
    resolve_asset_spec,
)

from pyramid.compat import text_

from pyramid.httpexceptions import (
    HTTPNotFound,
    HTTPMovedPermanently,
    )

from pyramid.path import caller_package
from pyramid.response import FileResponse
from pyramid.traversal import traversal_path_info

slash = text_('/')

class static_view(object):
    """ An instance of this class is a callable which can act as a
    :app:`Pyramid` :term:`view callable`; this view will serve
    static files from a directory on disk based on the ``root_dir``
    you provide to its constructor.

    The directory may contain subdirectories (recursively); the static
    view implementation will descend into these directories as
    necessary based on the components of the URL in order to resolve a
    path into a response.

    You may pass an absolute or relative filesystem path or a
    :term:`asset specification` representing the directory
    containing static files as the ``root_dir`` argument to this
    class' constructor.

    If the ``root_dir`` path is relative, and the ``package_name``
    argument is ``None``, ``root_dir`` will be considered relative to
    the directory in which the Python file which *calls* ``static``
    resides.  If the ``package_name`` name argument is provided, and a
    relative ``root_dir`` is provided, the ``root_dir`` will be
    considered relative to the Python :term:`package` specified by
    ``package_name`` (a dotted path to a Python package).

    ``cache_max_age`` influences the ``Expires`` and ``Max-Age``
    response headers returned by the view (default is 3600 seconds or
    one hour).

    ``use_subpath`` influences whether ``request.subpath`` will be used as
    ``PATH_INFO`` when calling the underlying WSGI application which actually
    serves the static files.  If it is ``True``, the static application will
    consider ``request.subpath`` as ``PATH_INFO`` input.  If it is ``False``,
    the static application will consider request.environ[``PATH_INFO``] as
    ``PATH_INFO`` input. By default, this is ``False``.

    .. note::

       If the ``root_dir`` is relative to a :term:`package`, or is a
       :term:`asset specification` the :app:`Pyramid`
       :class:`pyramid.config.Configurator` method can be used to override
       assets within the named ``root_dir`` package-relative directory.
       However, if the ``root_dir`` is absolute, configuration will not be able
       to override the assets it contains.
    """

    def __init__(self, root_dir, cache_max_age=3600, package_name=None,
                 use_subpath=False, index='index.html', cachebust_match=None):
        # package_name is for bw compat; it is preferred to pass in a
        # package-relative path as root_dir
        # (e.g. ``anotherpackage:foo/static``).
        self.cache_max_age = cache_max_age
        if package_name is None:
            package_name = caller_package().__name__
        package_name, docroot = resolve_asset_spec(root_dir, package_name)
        self.use_subpath = use_subpath
        self.package_name = package_name
        self.docroot = docroot
        self.norm_docroot = normcase(normpath(docroot))
        self.index = index
        self.cachebust_match = cachebust_match

    def __call__(self, context, request):
        if self.use_subpath:
            path_tuple = request.subpath
        else:
            path_tuple = traversal_path_info(request.environ['PATH_INFO'])
        if self.cachebust_match:
            path_tuple = self.cachebust_match(path_tuple)
        path = _secure_path(path_tuple)

        if path is None:
            raise HTTPNotFound('Out of bounds: %s' % request.url)

        if self.package_name: # package resource
            resource_path = '%s/%s' % (self.docroot.rstrip('/'), path)
            if resource_isdir(self.package_name, resource_path):
                if not request.path_url.endswith('/'):
                    self.add_slash_redirect(request)
                resource_path = '%s/%s' % (
                    resource_path.rstrip('/'), self.index
                )

            if not resource_exists(self.package_name, resource_path):
                raise HTTPNotFound(request.url)
            filepath = resource_filename(self.package_name, resource_path)

        else: # filesystem file

            # os.path.normpath converts / to \ on windows
            filepath = normcase(normpath(join(self.norm_docroot, path)))
            if isdir(filepath):
                if not request.path_url.endswith('/'):
                    self.add_slash_redirect(request)
                filepath = join(filepath, self.index)
            if not exists(filepath):
                raise HTTPNotFound(request.url)

        return FileResponse(filepath, request, self.cache_max_age)

    def add_slash_redirect(self, request):
        url = request.path_url + '/'
        qs = request.query_string
        if qs:
            url = url + '?' + qs
        raise HTTPMovedPermanently(url)

_seps = set(['/', os.sep])
def _contains_slash(item):
    for sep in _seps:
        if sep in item:
            return True

_has_insecure_pathelement = set(['..', '.', '']).intersection

@lru_cache(1000)
def _secure_path(path_tuple):
    if _has_insecure_pathelement(path_tuple):
        # belt-and-suspenders security; this should never be true
        # unless someone screws up the traversal_path code
        # (request.subpath is computed via traversal_path too)
        return None
    if any([_contains_slash(item) for item in path_tuple]):
        return None
    encoded = slash.join(path_tuple) # will be unicode
    return encoded

class QueryStringCacheBuster(object):
    """
    An implementation of :class:`~pyramid.interfaces.ICacheBuster` which adds
    a token for cache busting in the query string of an asset URL.

    The optional ``param`` argument determines the name of the parameter added
    to the query string and defaults to ``'x'``.

    To use this class, subclass it and provide a ``tokenize`` method which
    accepts ``request, pathspec, kw`` and returns a token.

    .. versionadded:: 1.6
    """
    def __init__(self, param='x'):
        self.param = param

    def __call__(self, request, subpath, kw):
        token = self.tokenize(request, subpath, kw)
        query = kw.setdefault('_query', {})
        if isinstance(query, dict):
            query[self.param] = token
        else:
            kw['_query'] = tuple(query) + ((self.param, token),)
        return subpath, kw

class QueryStringConstantCacheBuster(QueryStringCacheBuster):
    """
    An implementation of :class:`~pyramid.interfaces.ICacheBuster` which adds
    an arbitrary token for cache busting in the query string of an asset URL.

    The ``token`` parameter is the token string to use for cache busting and
    will be the same for every request.

    The optional ``param`` argument determines the name of the parameter added
    to the query string and defaults to ``'x'``.

    .. versionadded:: 1.6
    """
    def __init__(self, token, param='x'):
        super(QueryStringConstantCacheBuster, self).__init__(param=param)
        self._token = token

    def tokenize(self, request, subpath, kw):
        return self._token

class ManifestCacheBuster(object):
    """
    An implementation of :class:`~pyramid.interfaces.ICacheBuster` which
    uses a supplied manifest file to map an asset path to a cache-busted
    version of the path.

    The ``manifest_spec`` can be an absolute path or a :term:`asset
    specification` pointing to a package-relative file.

    The manifest file is expected to conform to the following simple JSON
    format:

    .. code-block:: json

       {
           "css/main.css": "css/main-678b7c80.css",
           "images/background.png": "images/background-a8169106.png",
       }

    By default, it is a JSON-serialized dictionary where the keys are the
    source asset paths used in calls to
    :meth:`~pyramid.request.Request.static_url`. For example:

    .. code-block:: pycon

       >>> request.static_url('myapp:static/css/main.css')
       "http://www.example.com/static/css/main-678b7c80.css"

    The file format and location can be changed by subclassing and overriding
    :meth:`.parse_manifest`.

    If a path is not found in the manifest it will pass through unchanged.

    If ``reload`` is ``True`` then the manifest file will be reloaded when
    changed. It is not recommended to leave this enabled in production.

    If the manifest file cannot be found on disk it will be treated as
    an empty mapping unless ``reload`` is ``False``.

    .. versionadded:: 1.6
    """
    exists = staticmethod(exists) # testing
    getmtime = staticmethod(getmtime) # testing

    def __init__(self, manifest_spec, reload=False):
        package_name = caller_package().__name__
        self.manifest_path = abspath_from_asset_spec(
            manifest_spec, package_name)
        self.reload = reload

        self._mtime = None
        if not reload:
            self._manifest = self.get_manifest()

    def get_manifest(self):
        with open(self.manifest_path, 'rb') as fp:
            return self.parse_manifest(fp.read())

    def parse_manifest(self, content):
        """
        Parse the ``content`` read from the ``manifest_path`` into a
        dictionary mapping.

        Subclasses may override this method to use something other than
        ``json.loads`` to load any type of file format and return a conforming
        dictionary.

        """
        return json.loads(content.decode('utf-8'))

    @property
    def manifest(self):
        """ The current manifest dictionary."""
        if self.reload:
            if not self.exists(self.manifest_path):
                return {}
            mtime = self.getmtime(self.manifest_path)
            if self._mtime is None or mtime > self._mtime:
                self._manifest = self.get_manifest()
                self._mtime = mtime
        return self._manifest

    def __call__(self, request, subpath, kw):
        subpath = self.manifest.get(subpath, subpath)
        return (subpath, kw)
