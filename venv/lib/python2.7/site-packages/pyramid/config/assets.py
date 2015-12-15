import pkg_resources
import sys

from zope.interface import implementer

from pyramid.interfaces import IPackageOverrides

from pyramid.exceptions import ConfigurationError
from pyramid.threadlocal import get_current_registry

from pyramid.util import action_method

class OverrideProvider(pkg_resources.DefaultProvider):
    def __init__(self, module):
        pkg_resources.DefaultProvider.__init__(self, module)
        self.module_name = module.__name__

    def _get_overrides(self):
        reg = get_current_registry()
        overrides = reg.queryUtility(IPackageOverrides, self.module_name)
        return overrides
    
    def get_resource_filename(self, manager, resource_name):
        """ Return a true filesystem path for resource_name,
        co-ordinating the extraction with manager, if the resource
        must be unpacked to the filesystem.
        """
        overrides = self._get_overrides()
        if overrides is not None:
            filename = overrides.get_filename(resource_name)
            if filename is not None:
                return filename
        return pkg_resources.DefaultProvider.get_resource_filename(
            self, manager, resource_name)
    
    def get_resource_stream(self, manager, resource_name):
        """ Return a readable file-like object for resource_name."""
        overrides = self._get_overrides()
        if overrides is not None:
            stream =  overrides.get_stream(resource_name)
            if stream is not None:
                return stream
        return pkg_resources.DefaultProvider.get_resource_stream(
            self, manager, resource_name)

    def get_resource_string(self, manager, resource_name):
        """ Return a string containing the contents of resource_name."""
        overrides = self._get_overrides()
        if overrides is not None:
            string = overrides.get_string(resource_name)
            if string is not None:
                return string
        return pkg_resources.DefaultProvider.get_resource_string(
            self, manager, resource_name)

    def has_resource(self, resource_name):
        overrides = self._get_overrides()
        if overrides is not None:
            result = overrides.has_resource(resource_name)
            if result is not None:
                return result
        return pkg_resources.DefaultProvider.has_resource(
            self, resource_name)

    def resource_isdir(self, resource_name):
        overrides = self._get_overrides()
        if overrides is not None:
            result = overrides.isdir(resource_name)
            if result is not None:
                return result
        return pkg_resources.DefaultProvider.resource_isdir(
            self, resource_name)

    def resource_listdir(self, resource_name):
        overrides = self._get_overrides()
        if overrides is not None:
            result = overrides.listdir(resource_name)
            if result is not None:
                return result
        return pkg_resources.DefaultProvider.resource_listdir(
            self, resource_name)
        
@implementer(IPackageOverrides)
class PackageOverrides(object):
    # pkg_resources arg in kw args below for testing
    def __init__(self, package, pkg_resources=pkg_resources):
        loader = self._real_loader = getattr(package, '__loader__', None)
        if isinstance(loader, self.__class__):
            self._real_loader = None
        # We register ourselves as a __loader__ *only* to support the
        # setuptools _find_adapter adapter lookup; this class doesn't
        # actually support the PEP 302 loader "API".  This is
        # excusable due to the following statement in the spec:
        # ... Loader objects are not
        # required to offer any useful functionality (any such functionality,
        # such as the zipimport get_data() method mentioned above, is
        # optional)...
        # A __loader__ attribute is basically metadata, and setuptools
        # uses it as such.
        package.__loader__ = self 
        # we call register_loader_type for every instantiation of this
        # class; that's OK, it's idempotent to do it more than once.
        pkg_resources.register_loader_type(self.__class__, OverrideProvider)
        self.overrides = []
        self.overridden_package_name = package.__name__

    def insert(self, path, package, prefix):
        if not path or path.endswith('/'):
            override = DirectoryOverride(path, package, prefix)
        else:
            override = FileOverride(path, package, prefix)
        self.overrides.insert(0, override)
        return override

    def search_path(self, resource_name):
        for override in self.overrides:
            o = override(resource_name)
            if o is not None:
                package, name = o
                yield package, name

    def get_filename(self, resource_name):
        for package, rname in self.search_path(resource_name):
            if pkg_resources.resource_exists(package, rname):
                return pkg_resources.resource_filename(package, rname)

    def get_stream(self, resource_name):
        for package, rname in self.search_path(resource_name):
            if pkg_resources.resource_exists(package, rname):
                return pkg_resources.resource_stream(package, rname)

    def get_string(self, resource_name):
        for package, rname in self.search_path(resource_name):
            if pkg_resources.resource_exists(package, rname):
                return pkg_resources.resource_string(package, rname)

    def has_resource(self, resource_name):
        for package, rname in self.search_path(resource_name):
            if pkg_resources.resource_exists(package, rname):
                return True

    def isdir(self, resource_name):
        for package, rname in self.search_path(resource_name):
            if pkg_resources.resource_exists(package, rname):
                return pkg_resources.resource_isdir(package, rname)

    def listdir(self, resource_name):
        for package, rname in self.search_path(resource_name):
            if pkg_resources.resource_exists(package, rname):
                return pkg_resources.resource_listdir(package, rname)

    @property
    def real_loader(self):
        if self._real_loader is None:
            raise NotImplementedError()
        return self._real_loader

    def get_data(self, path):
        """ See IPEP302Loader.
        """
        return self.real_loader.get_data(path)

    def is_package(self, fullname):
        """ See IPEP302Loader.
        """
        return self.real_loader.is_package(fullname)

    def get_code(self, fullname):
        """ See IPEP302Loader.
        """
        return self.real_loader.get_code(fullname)

    def get_source(self, fullname):
        """ See IPEP302Loader.
        """
        return self.real_loader.get_source(fullname)
 

class DirectoryOverride:
    def __init__(self, path, package, prefix):
        self.path = path
        self.package = package
        self.prefix = prefix
        self.pathlen = len(self.path)

    def __call__(self, resource_name):
        if resource_name.startswith(self.path):
            name = '%s%s' % (self.prefix, resource_name[self.pathlen:])
            return self.package, name

class FileOverride:
    def __init__(self, path, package, prefix):
        self.path = path
        self.package = package
        self.prefix = prefix

    def __call__(self, resource_name):
        if resource_name == self.path:
            return self.package, self.prefix


class AssetsConfiguratorMixin(object):
    def _override(self, package, path, override_package, override_prefix,
                  PackageOverrides=PackageOverrides):
        pkg_name = package.__name__
        override_pkg_name = override_package.__name__
        override = self.registry.queryUtility(IPackageOverrides, name=pkg_name)
        if override is None:
            override = PackageOverrides(package)
            self.registry.registerUtility(override, IPackageOverrides,
                                          name=pkg_name)
        override.insert(path, override_pkg_name, override_prefix)

    @action_method
    def override_asset(self, to_override, override_with, _override=None):
        """ Add a :app:`Pyramid` asset override to the current
        configuration state.

        ``to_override`` is a :term:`asset specification` to the
        asset being overridden.

        ``override_with`` is a :term:`asset specification` to the
        asset that is performing the override.

        See :ref:`assets_chapter` for more
        information about asset overrides."""
        if to_override == override_with:
            raise ConfigurationError('You cannot override an asset with itself')

        package = to_override
        path = ''
        if ':' in to_override:
            package, path = to_override.split(':', 1)

        override_package = override_with
        override_prefix = ''
        if ':' in override_with:
            override_package, override_prefix = override_with.split(':', 1)

        # *_isdir = override is package or directory
        overridden_isdir = path=='' or path.endswith('/') 
        override_isdir = override_prefix=='' or override_prefix.endswith('/')

        if overridden_isdir and (not override_isdir):
            raise ConfigurationError(
                'A directory cannot be overridden with a file (put a '
                'slash at the end of override_with if necessary)')

        if (not overridden_isdir) and override_isdir:
            raise ConfigurationError(
                'A file cannot be overridden with a directory (put a '
                'slash at the end of to_override if necessary)')

        override = _override or self._override # test jig

        def register():
            __import__(package)
            __import__(override_package)
            from_package = sys.modules[package]
            to_package = sys.modules[override_package]
            override(from_package, path, to_package, override_prefix)

        intr = self.introspectable(
            'asset overrides',
            (package, override_package, path, override_prefix),
            '%s -> %s' % (to_override, override_with),
            'asset override',
            )
        intr['to_override'] = to_override
        intr['override_with'] = override_with
        self.action(None, register, introspectables=(intr,))

    override_resource = override_asset # bw compat


