import os
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
            stream = overrides.get_stream(resource_name)
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

    def insert(self, path, source):
        if not path or path.endswith('/'):
            override = DirectoryOverride(path, source)
        else:
            override = FileOverride(path, source)
        self.overrides.insert(0, override)
        return override

    def filtered_sources(self, resource_name):
        for override in self.overrides:
            o = override(resource_name)
            if o is not None:
                yield o

    def get_filename(self, resource_name):
        for source, path in self.filtered_sources(resource_name):
            result = source.get_filename(path)
            if result is not None:
                return result

    def get_stream(self, resource_name):
        for source, path in self.filtered_sources(resource_name):
            result = source.get_stream(path)
            if result is not None:
                return result

    def get_string(self, resource_name):
        for source, path in self.filtered_sources(resource_name):
            result = source.get_string(path)
            if result is not None:
                return result

    def has_resource(self, resource_name):
        for source, path in self.filtered_sources(resource_name):
            if source.exists(path):
                return True

    def isdir(self, resource_name):
        for source, path in self.filtered_sources(resource_name):
            result = source.isdir(path)
            if result is not None:
                return result

    def listdir(self, resource_name):
        for source, path in self.filtered_sources(resource_name):
            result = source.listdir(path)
            if result is not None:
                return result

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
    def __init__(self, path, source):
        self.path = path
        self.pathlen = len(self.path)
        self.source = source

    def __call__(self, resource_name):
        if resource_name.startswith(self.path):
            new_path = resource_name[self.pathlen:]
            return self.source, new_path

class FileOverride:
    def __init__(self, path, source):
        self.path = path
        self.source = source

    def __call__(self, resource_name):
        if resource_name == self.path:
            return self.source, ''


class PackageAssetSource(object):
    """
    An asset source relative to a package.

    If this asset source is a file, then we expect the ``prefix`` to point
    to the new name of the file, and the incoming ``resource_name`` will be
    the empty string, as returned by the ``FileOverride``.

    """
    def __init__(self, package, prefix):
        self.package = package
        if hasattr(package, '__name__'):
            self.pkg_name = package.__name__
        else:
            self.pkg_name = package
        self.prefix = prefix

    def get_path(self, resource_name):
        return '%s%s' % (self.prefix, resource_name)

    def get_filename(self, resource_name):
        path = self.get_path(resource_name)
        if pkg_resources.resource_exists(self.pkg_name, path):
            return pkg_resources.resource_filename(self.pkg_name, path)

    def get_stream(self, resource_name):
        path = self.get_path(resource_name)
        if pkg_resources.resource_exists(self.pkg_name, path):
            return pkg_resources.resource_stream(self.pkg_name, path)

    def get_string(self, resource_name):
        path = self.get_path(resource_name)
        if pkg_resources.resource_exists(self.pkg_name, path):
            return pkg_resources.resource_string(self.pkg_name, path)

    def exists(self, resource_name):
        path = self.get_path(resource_name)
        if pkg_resources.resource_exists(self.pkg_name, path):
            return True

    def isdir(self, resource_name):
        path = self.get_path(resource_name)
        if pkg_resources.resource_exists(self.pkg_name, path):
            return pkg_resources.resource_isdir(self.pkg_name, path)

    def listdir(self, resource_name):
        path = self.get_path(resource_name)
        if pkg_resources.resource_exists(self.pkg_name, path):
            return pkg_resources.resource_listdir(self.pkg_name, path)


class FSAssetSource(object):
    """
    An asset source relative to a path in the filesystem.

    """
    def __init__(self, prefix):
        self.prefix = prefix

    def get_path(self, resource_name):
        if resource_name:
            path = os.path.join(self.prefix, resource_name)
        else:
            path = self.prefix
        return path

    def get_filename(self, resource_name):
        path = self.get_path(resource_name)
        if os.path.exists(path):
            return path

    def get_stream(self, resource_name):
        path = self.get_filename(resource_name)
        if path is not None:
            return open(path, 'rb')

    def get_string(self, resource_name):
        stream = self.get_stream(resource_name)
        if stream is not None:
            with stream:
                return stream.read()

    def exists(self, resource_name):
        path = self.get_filename(resource_name)
        if path is not None:
            return True

    def isdir(self, resource_name):
        path = self.get_filename(resource_name)
        if path is not None:
            return os.path.isdir(path)

    def listdir(self, resource_name):
        path = self.get_filename(resource_name)
        if path is not None:
            return os.listdir(path)


class AssetsConfiguratorMixin(object):
    def _override(self, package, path, override_source,
                  PackageOverrides=PackageOverrides):
        pkg_name = package.__name__
        override = self.registry.queryUtility(IPackageOverrides, name=pkg_name)
        if override is None:
            override = PackageOverrides(package)
            self.registry.registerUtility(override, IPackageOverrides,
                                          name=pkg_name)
        override.insert(path, override_source)

    @action_method
    def override_asset(self, to_override, override_with, _override=None):
        """ Add a :app:`Pyramid` asset override to the current
        configuration state.

        ``to_override`` is an :term:`asset specification` to the
        asset being overridden.

        ``override_with`` is an :term:`asset specification` to the
        asset that is performing the override. This may also be an absolute
        path.

        See :ref:`assets_chapter` for more
        information about asset overrides."""
        if to_override == override_with:
            raise ConfigurationError(
                'You cannot override an asset with itself')

        package = to_override
        path = ''
        if ':' in to_override:
            package, path = to_override.split(':', 1)

        # *_isdir = override is package or directory
        overridden_isdir = path == '' or path.endswith('/')

        if os.path.isabs(override_with):
            override_source = FSAssetSource(override_with)
            if not os.path.exists(override_with):
                raise ConfigurationError(
                    'Cannot override asset with an absolute path that does '
                    'not exist')
            override_isdir = os.path.isdir(override_with)
            override_package = None
            override_prefix = override_with
        else:
            override_package = override_with
            override_prefix = ''
            if ':' in override_with:
                override_package, override_prefix = override_with.split(':', 1)

            __import__(override_package)
            to_package = sys.modules[override_package]
            override_source = PackageAssetSource(to_package, override_prefix)

            override_isdir = (
                override_prefix == '' or
                override_with.endswith('/')
            )

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
            from_package = sys.modules[package]
            override(from_package, path, override_source)

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
