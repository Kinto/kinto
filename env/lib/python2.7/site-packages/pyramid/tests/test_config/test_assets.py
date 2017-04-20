import os.path
import unittest
from pyramid.testing import cleanUp

# we use this folder
here = os.path.dirname(os.path.abspath(__file__))

class TestAssetsConfiguratorMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_override_asset_samename(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.override_asset, 'a', 'a')

    def test_override_asset_directory_with_file(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.override_asset,
                          'a:foo/',
                          'pyramid.tests.test_config.pkgs.asset:foo.pt')

    def test_override_asset_file_with_directory(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.override_asset,
                          'a:foo.pt',
                          'pyramid.tests.test_config.pkgs.asset:templates/')

    def test_override_asset_file_with_package(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.override_asset,
                          'a:foo.pt',
                          'pyramid.tests.test_config.pkgs.asset')

    def test_override_asset_file_with_file(self):
        from pyramid.config.assets import PackageAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset:templates/foo.pt',
            'pyramid.tests.test_config.pkgs.asset.subpackage:templates/bar.pt',
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        from pyramid.tests.test_config.pkgs.asset import subpackage
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, 'templates/foo.pt')
        source = override.source
        self.assertTrue(isinstance(source, PackageAssetSource))
        self.assertEqual(source.package, subpackage)
        self.assertEqual(source.prefix, 'templates/bar.pt')

        resource_name = ''
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_package_with_package(self):
        from pyramid.config.assets import PackageAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset',
            'pyramid.tests.test_config.pkgs.asset.subpackage',
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        from pyramid.tests.test_config.pkgs.asset import subpackage
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, '')
        source = override.source
        self.assertTrue(isinstance(source, PackageAssetSource))
        self.assertEqual(source.package, subpackage)
        self.assertEqual(source.prefix, '')

        resource_name = 'templates/bar.pt'
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_directory_with_directory(self):
        from pyramid.config.assets import PackageAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset:templates/',
            'pyramid.tests.test_config.pkgs.asset.subpackage:templates/',
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        from pyramid.tests.test_config.pkgs.asset import subpackage
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, 'templates/')
        source = override.source
        self.assertTrue(isinstance(source, PackageAssetSource))
        self.assertEqual(source.package, subpackage)
        self.assertEqual(source.prefix, 'templates/')

        resource_name = 'bar.pt'
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_directory_with_package(self):
        from pyramid.config.assets import PackageAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset:templates/',
            'pyramid.tests.test_config.pkgs.asset.subpackage',
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        from pyramid.tests.test_config.pkgs.asset import subpackage
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, 'templates/')
        source = override.source
        self.assertTrue(isinstance(source, PackageAssetSource))
        self.assertEqual(source.package, subpackage)
        self.assertEqual(source.prefix, '')

        resource_name = 'templates/bar.pt'
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_package_with_directory(self):
        from pyramid.config.assets import PackageAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset',
            'pyramid.tests.test_config.pkgs.asset.subpackage:templates/',
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        from pyramid.tests.test_config.pkgs.asset import subpackage
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, '')
        source = override.source
        self.assertTrue(isinstance(source, PackageAssetSource))
        self.assertEqual(source.package, subpackage)
        self.assertEqual(source.prefix, 'templates/')

        resource_name = 'bar.pt'
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_directory_with_absfile(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.override_asset,
                          'a:foo/',
                          os.path.join(here, 'pkgs', 'asset', 'foo.pt'))

    def test_override_asset_file_with_absdirectory(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        abspath = os.path.join(here, 'pkgs', 'asset', 'subpackage', 'templates')
        self.assertRaises(ConfigurationError, config.override_asset,
                          'a:foo.pt',
                          abspath)

    def test_override_asset_file_with_missing_abspath(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.override_asset,
                          'a:foo.pt',
                          os.path.join(here, 'wont_exist'))

    def test_override_asset_file_with_absfile(self):
        from pyramid.config.assets import FSAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        abspath = os.path.join(here, 'pkgs', 'asset', 'subpackage',
                               'templates', 'bar.pt')
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset:templates/foo.pt',
            abspath,
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, 'templates/foo.pt')
        source = override.source
        self.assertTrue(isinstance(source, FSAssetSource))
        self.assertEqual(source.prefix, abspath)

        resource_name = ''
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_directory_with_absdirectory(self):
        from pyramid.config.assets import FSAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        abspath = os.path.join(here, 'pkgs', 'asset', 'subpackage', 'templates')
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset:templates/',
            abspath,
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, 'templates/')
        source = override.source
        self.assertTrue(isinstance(source, FSAssetSource))
        self.assertEqual(source.prefix, abspath)

        resource_name = 'bar.pt'
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test_override_asset_package_with_absdirectory(self):
        from pyramid.config.assets import FSAssetSource
        config = self._makeOne(autocommit=True)
        override = DummyUnderOverride()
        abspath = os.path.join(here, 'pkgs', 'asset', 'subpackage', 'templates')
        config.override_asset(
            'pyramid.tests.test_config.pkgs.asset',
            abspath,
            _override=override)
        from pyramid.tests.test_config.pkgs import asset
        self.assertEqual(override.package, asset)
        self.assertEqual(override.path, '')
        source = override.source
        self.assertTrue(isinstance(source, FSAssetSource))
        self.assertEqual(source.prefix, abspath)

        resource_name = 'bar.pt'
        expected = os.path.join(here, 'pkgs', 'asset',
                                'subpackage', 'templates', 'bar.pt')
        self.assertEqual(override.source.get_filename(resource_name),
                         expected)

    def test__override_not_yet_registered(self):
        from pyramid.interfaces import IPackageOverrides
        package = DummyPackage('package')
        source = DummyAssetSource()
        config = self._makeOne()
        config._override(package, 'path', source,
                         PackageOverrides=DummyPackageOverrides)
        overrides = config.registry.queryUtility(IPackageOverrides,
                                                 name='package')
        self.assertEqual(overrides.inserted, [('path', source)])
        self.assertEqual(overrides.package, package)

    def test__override_already_registered(self):
        from pyramid.interfaces import IPackageOverrides
        package = DummyPackage('package')
        source = DummyAssetSource()
        overrides = DummyPackageOverrides(package)
        config = self._makeOne()
        config.registry.registerUtility(overrides, IPackageOverrides,
                                        name='package')
        config._override(package, 'path', source,
                         PackageOverrides=DummyPackageOverrides)
        self.assertEqual(overrides.inserted, [('path', source)])
        self.assertEqual(overrides.package, package)


class TestOverrideProvider(unittest.TestCase):
    def setUp(self):
        cleanUp()

    def tearDown(self):
        cleanUp()

    def _getTargetClass(self):
        from pyramid.config.assets import OverrideProvider
        return OverrideProvider

    def _makeOne(self, module):
        klass = self._getTargetClass()
        return klass(module)

    def _registerOverrides(self, overrides, name='pyramid.tests.test_config'):
        from pyramid.interfaces import IPackageOverrides
        from pyramid.threadlocal import get_current_registry
        reg = get_current_registry()
        reg.registerUtility(overrides, IPackageOverrides, name=name)

    def test_get_resource_filename_no_overrides(self):
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        expected = os.path.join(here, resource_name)
        result = provider.get_resource_filename(None, resource_name)
        self.assertEqual(result, expected)

    def test_get_resource_stream_no_overrides(self):
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        with provider.get_resource_stream(None, resource_name) as result:
            _assertBody(result.read(), os.path.join(here, resource_name))

    def test_get_resource_string_no_overrides(self):
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.get_resource_string(None, resource_name)
        _assertBody(result, os.path.join(here, resource_name))

    def test_has_resource_no_overrides(self):
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.has_resource(resource_name)
        self.assertEqual(result, True)

    def test_resource_isdir_no_overrides(self):
        file_resource_name = 'test_assets.py'
        directory_resource_name = 'files'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.resource_isdir(file_resource_name)
        self.assertEqual(result, False)
        result = provider.resource_isdir(directory_resource_name)
        self.assertEqual(result, True)

    def test_resource_listdir_no_overrides(self):
        resource_name = 'files'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.resource_listdir(resource_name)
        self.assertTrue(result)

    def test_get_resource_filename_override_returns_None(self):
        overrides = DummyOverrides(None)
        self._registerOverrides(overrides)
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        expected = os.path.join(here, resource_name)
        result = provider.get_resource_filename(None, resource_name)
        self.assertEqual(result, expected)
        
    def test_get_resource_stream_override_returns_None(self):
        overrides = DummyOverrides(None)
        self._registerOverrides(overrides)
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        with provider.get_resource_stream(None, resource_name) as result:
            _assertBody(result.read(), os.path.join(here, resource_name))

    def test_get_resource_string_override_returns_None(self):
        overrides = DummyOverrides(None)
        self._registerOverrides(overrides)
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.get_resource_string(None, resource_name)
        _assertBody(result, os.path.join(here, resource_name))

    def test_has_resource_override_returns_None(self):
        overrides = DummyOverrides(None)
        self._registerOverrides(overrides)
        resource_name = 'test_assets.py'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.has_resource(resource_name)
        self.assertEqual(result, True)

    def test_resource_isdir_override_returns_None(self):
        overrides = DummyOverrides(None)
        self._registerOverrides(overrides)
        resource_name = 'files'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.resource_isdir(resource_name)
        self.assertEqual(result, True)

    def test_resource_listdir_override_returns_None(self):
        overrides = DummyOverrides(None)
        self._registerOverrides(overrides)
        resource_name = 'files'
        import pyramid.tests.test_config
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.resource_listdir(resource_name)
        self.assertTrue(result)

    def test_get_resource_filename_override_returns_value(self):
        overrides = DummyOverrides('value')
        import pyramid.tests.test_config
        self._registerOverrides(overrides)
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.get_resource_filename(None, 'test_assets.py')
        self.assertEqual(result, 'value')

    def test_get_resource_stream_override_returns_value(self):
        from io import BytesIO
        overrides = DummyOverrides(BytesIO(b'value'))
        import pyramid.tests.test_config
        self._registerOverrides(overrides)
        provider = self._makeOne(pyramid.tests.test_config)
        with provider.get_resource_stream(None, 'test_assets.py') as stream:
            self.assertEqual(stream.getvalue(), b'value')

    def test_get_resource_string_override_returns_value(self):
        overrides = DummyOverrides('value')
        import pyramid.tests.test_config
        self._registerOverrides(overrides)
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.get_resource_string(None, 'test_assets.py')
        self.assertEqual(result, 'value')

    def test_has_resource_override_returns_True(self):
        overrides = DummyOverrides(True)
        import pyramid.tests.test_config
        self._registerOverrides(overrides)
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.has_resource('test_assets.py')
        self.assertEqual(result, True)

    def test_resource_isdir_override_returns_False(self):
        overrides = DummyOverrides(False)
        import pyramid.tests.test_config
        self._registerOverrides(overrides)
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.resource_isdir('files')
        self.assertEqual(result, False)

    def test_resource_listdir_override_returns_values(self):
        overrides = DummyOverrides(['a'])
        import pyramid.tests.test_config
        self._registerOverrides(overrides)
        provider = self._makeOne(pyramid.tests.test_config)
        result = provider.resource_listdir('files')
        self.assertEqual(result, ['a'])

class TestPackageOverrides(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.config.assets import PackageOverrides
        return PackageOverrides

    def _makeOne(self, package=None, pkg_resources=None):
        if package is None:
            package = DummyPackage('package')
        klass = self._getTargetClass()
        if pkg_resources is None:
            pkg_resources = DummyPkgResources()
        return klass(package, pkg_resources=pkg_resources)

    def test_class_conforms_to_IPackageOverrides(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IPackageOverrides
        verifyClass(IPackageOverrides, self._getTargetClass())

    def test_instance_conforms_to_IPackageOverrides(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IPackageOverrides
        verifyObject(IPackageOverrides, self._makeOne())

    def test_class_conforms_to_IPEP302Loader(self):
        from zope.interface.verify import verifyClass
        from pyramid.interfaces import IPEP302Loader
        verifyClass(IPEP302Loader, self._getTargetClass())

    def test_instance_conforms_to_IPEP302Loader(self):
        from zope.interface.verify import verifyObject
        from pyramid.interfaces import IPEP302Loader
        verifyObject(IPEP302Loader, self._makeOne())

    def test_ctor_package_already_has_loader_of_different_type(self):
        package = DummyPackage('package')
        loader = package.__loader__ = DummyLoader()
        po = self._makeOne(package)
        self.assertTrue(package.__loader__ is po)
        self.assertTrue(po.real_loader is loader)

    def test_ctor_package_already_has_loader_of_same_type(self):
        package = DummyPackage('package')
        package.__loader__ = self._makeOne(package)
        po = self._makeOne(package)
        self.assertEqual(package.__loader__, po)

    def test_ctor_sets_loader(self):
        package = DummyPackage('package')
        po = self._makeOne(package)
        self.assertEqual(package.__loader__, po)

    def test_ctor_registers_loader_type(self):
        from pyramid.config.assets import OverrideProvider
        dummy_pkg_resources = DummyPkgResources()
        package = DummyPackage('package')
        po = self._makeOne(package, dummy_pkg_resources)
        self.assertEqual(dummy_pkg_resources.registered, [(po.__class__,
                         OverrideProvider)])

    def test_ctor_sets_local_state(self):
        package = DummyPackage('package')
        po = self._makeOne(package)
        self.assertEqual(po.overrides, [])
        self.assertEqual(po.overridden_package_name, 'package')

    def test_insert_directory(self):
        from pyramid.config.assets import DirectoryOverride
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = [None]
        po.insert('foo/', DummyAssetSource())
        self.assertEqual(len(po.overrides), 2)
        override = po.overrides[0]
        self.assertEqual(override.__class__, DirectoryOverride)

    def test_insert_file(self):
        from pyramid.config.assets import FileOverride
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = [None]
        po.insert('foo.pt', DummyAssetSource())
        self.assertEqual(len(po.overrides), 2)
        override = po.overrides[0]
        self.assertEqual(override.__class__, FileOverride)

    def test_insert_emptystring(self):
        # XXX is this a valid case for a directory?
        from pyramid.config.assets import DirectoryOverride
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = [None]
        source = DummyAssetSource()
        po.insert('', source)
        self.assertEqual(len(po.overrides), 2)
        override = po.overrides[0]
        self.assertEqual(override.__class__, DirectoryOverride)

    def test_filtered_sources(self):
        overrides = [ DummyOverride(None), DummyOverride('foo')]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(list(po.filtered_sources('whatever')), ['foo'])

    def test_get_filename(self):
        source = DummyAssetSource(filename='foo.pt')
        overrides = [ DummyOverride(None), DummyOverride((source, ''))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        result = po.get_filename('whatever')
        self.assertEqual(result, 'foo.pt')
        self.assertEqual(source.resource_name, '')

    def test_get_filename_file_doesnt_exist(self):
        source = DummyAssetSource(filename=None)
        overrides = [DummyOverride(None), DummyOverride((source, 'wont_exist'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.get_filename('whatever'), None)
        self.assertEqual(source.resource_name, 'wont_exist')

    def test_get_stream(self):
        source = DummyAssetSource(stream='a stream?')
        overrides = [DummyOverride(None), DummyOverride((source, 'foo.pt'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.get_stream('whatever'), 'a stream?')
        self.assertEqual(source.resource_name, 'foo.pt')
        
    def test_get_stream_file_doesnt_exist(self):
        source = DummyAssetSource(stream=None)
        overrides = [DummyOverride(None), DummyOverride((source, 'wont_exist'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.get_stream('whatever'), None)
        self.assertEqual(source.resource_name, 'wont_exist')

    def test_get_string(self):
        source = DummyAssetSource(string='a string')
        overrides = [DummyOverride(None), DummyOverride((source, 'foo.pt'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.get_string('whatever'), 'a string')
        self.assertEqual(source.resource_name, 'foo.pt')
        
    def test_get_string_file_doesnt_exist(self):
        source = DummyAssetSource(string=None)
        overrides = [DummyOverride(None), DummyOverride((source, 'wont_exist'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.get_string('whatever'), None)
        self.assertEqual(source.resource_name, 'wont_exist')

    def test_has_resource(self):
        source = DummyAssetSource(exists=True)
        overrides = [DummyOverride(None), DummyOverride((source, 'foo.pt'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.has_resource('whatever'), True)
        self.assertEqual(source.resource_name, 'foo.pt')

    def test_has_resource_file_doesnt_exist(self):
        source = DummyAssetSource(exists=None)
        overrides = [DummyOverride(None), DummyOverride((source, 'wont_exist'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.has_resource('whatever'), None)
        self.assertEqual(source.resource_name, 'wont_exist')

    def test_isdir_false(self):
        source = DummyAssetSource(isdir=False)
        overrides = [DummyOverride(None), DummyOverride((source, 'foo.pt'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.isdir('whatever'), False)
        self.assertEqual(source.resource_name, 'foo.pt')

    def test_isdir_true(self):
        source = DummyAssetSource(isdir=True)
        overrides = [DummyOverride(None), DummyOverride((source, 'foo.pt'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.isdir('whatever'), True)
        self.assertEqual(source.resource_name, 'foo.pt')

    def test_isdir_doesnt_exist(self):
        source = DummyAssetSource(isdir=None)
        overrides = [DummyOverride(None), DummyOverride((source, 'wont_exist'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.isdir('whatever'), None)
        self.assertEqual(source.resource_name, 'wont_exist')

    def test_listdir(self):
        source = DummyAssetSource(listdir=True)
        overrides = [DummyOverride(None), DummyOverride((source, 'foo.pt'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.listdir('whatever'), True)
        self.assertEqual(source.resource_name, 'foo.pt')

    def test_listdir_doesnt_exist(self):
        source = DummyAssetSource(listdir=None)
        overrides = [DummyOverride(None), DummyOverride((source, 'wont_exist'))]
        package = DummyPackage('package')
        po = self._makeOne(package)
        po.overrides = overrides
        self.assertEqual(po.listdir('whatever'), None)
        self.assertEqual(source.resource_name, 'wont_exist')

    # PEP 302 __loader__ extensions:  use the "real" __loader__, if present.
    def test_get_data_pkg_has_no___loader__(self):
        package = DummyPackage('package')
        po = self._makeOne(package)
        self.assertRaises(NotImplementedError, po.get_data, 'whatever')

    def test_get_data_pkg_has___loader__(self):
        package = DummyPackage('package')
        loader = package.__loader__  = DummyLoader()
        po = self._makeOne(package)
        self.assertEqual(po.get_data('whatever'), b'DEADBEEF')
        self.assertEqual(loader._got_data, 'whatever')

    def test_is_package_pkg_has_no___loader__(self):
        package = DummyPackage('package')
        po = self._makeOne(package)
        self.assertRaises(NotImplementedError, po.is_package, 'whatever')

    def test_is_package_pkg_has___loader__(self):
        package = DummyPackage('package')
        loader = package.__loader__  = DummyLoader()
        po = self._makeOne(package)
        self.assertTrue(po.is_package('whatever'))
        self.assertEqual(loader._is_package, 'whatever')

    def test_get_code_pkg_has_no___loader__(self):
        package = DummyPackage('package')
        po = self._makeOne(package)
        self.assertRaises(NotImplementedError, po.get_code, 'whatever')

    def test_get_code_pkg_has___loader__(self):
        package = DummyPackage('package')
        loader = package.__loader__  = DummyLoader()
        po = self._makeOne(package)
        self.assertEqual(po.get_code('whatever'), b'DEADBEEF')
        self.assertEqual(loader._got_code, 'whatever')

    def test_get_source_pkg_has_no___loader__(self):
        package = DummyPackage('package')
        po = self._makeOne(package)
        self.assertRaises(NotImplementedError, po.get_source, 'whatever')

    def test_get_source_pkg_has___loader__(self):
        package = DummyPackage('package')
        loader = package.__loader__ = DummyLoader()
        po = self._makeOne(package)
        self.assertEqual(po.get_source('whatever'), 'def foo():\n    pass')
        self.assertEqual(loader._got_source, 'whatever')

class AssetSourceIntegrationTests(object):

    def test_get_filename(self):
        source = self._makeOne('')
        self.assertEqual(source.get_filename('test_assets.py'),
                         os.path.join(here, 'test_assets.py'))

    def test_get_filename_with_prefix(self):
        source = self._makeOne('test_assets.py')
        self.assertEqual(source.get_filename(''),
                         os.path.join(here, 'test_assets.py'))

    def test_get_filename_file_doesnt_exist(self):
        source = self._makeOne('')
        self.assertEqual(source.get_filename('wont_exist'), None)

    def test_get_stream(self):
        source = self._makeOne('')
        with source.get_stream('test_assets.py') as stream:
            _assertBody(stream.read(), os.path.join(here, 'test_assets.py'))

    def test_get_stream_with_prefix(self):
        source = self._makeOne('test_assets.py')
        with source.get_stream('') as stream:
            _assertBody(stream.read(), os.path.join(here, 'test_assets.py'))

    def test_get_stream_file_doesnt_exist(self):
        source = self._makeOne('')
        self.assertEqual(source.get_stream('wont_exist'), None)

    def test_get_string(self):
        source = self._makeOne('')
        _assertBody(source.get_string('test_assets.py'),
                    os.path.join(here, 'test_assets.py'))

    def test_get_string_with_prefix(self):
        source = self._makeOne('test_assets.py')
        _assertBody(source.get_string(''),
                    os.path.join(here, 'test_assets.py'))

    def test_get_string_file_doesnt_exist(self):
        source = self._makeOne('')
        self.assertEqual(source.get_string('wont_exist'), None)

    def test_exists(self):
        source = self._makeOne('')
        self.assertEqual(source.exists('test_assets.py'), True)

    def test_exists_with_prefix(self):
        source = self._makeOne('test_assets.py')
        self.assertEqual(source.exists(''), True)

    def test_exists_file_doesnt_exist(self):
        source = self._makeOne('')
        self.assertEqual(source.exists('wont_exist'), None)

    def test_isdir_false(self):
        source = self._makeOne('')
        self.assertEqual(source.isdir('test_assets.py'), False)

    def test_isdir_true(self):
        source = self._makeOne('')
        self.assertEqual(source.isdir('files'), True)

    def test_isdir_doesnt_exist(self):
        source = self._makeOne('')
        self.assertEqual(source.isdir('wont_exist'), None)

    def test_listdir(self):
        source = self._makeOne('')
        self.assertTrue(source.listdir('files'))

    def test_listdir_doesnt_exist(self):
        source = self._makeOne('')
        self.assertEqual(source.listdir('wont_exist'), None)

class TestPackageAssetSource(AssetSourceIntegrationTests, unittest.TestCase):

    def _getTargetClass(self):
        from pyramid.config.assets import PackageAssetSource
        return PackageAssetSource

    def _makeOne(self, prefix, package='pyramid.tests.test_config'):
        klass = self._getTargetClass()
        return klass(package, prefix)

class TestFSAssetSource(AssetSourceIntegrationTests, unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.config.assets import FSAssetSource
        return FSAssetSource

    def _makeOne(self, prefix, base_prefix=here):
        klass = self._getTargetClass()
        return klass(os.path.join(base_prefix, prefix))

class TestDirectoryOverride(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.config.assets import DirectoryOverride
        return DirectoryOverride

    def _makeOne(self, path, source):
        klass = self._getTargetClass()
        return klass(path, source)

    def test_it_match(self):
        source = DummyAssetSource()
        o = self._makeOne('foo/', source)
        result = o('foo/something.pt')
        self.assertEqual(result, (source, 'something.pt'))
        
    def test_it_no_match(self):
        source = DummyAssetSource()
        o = self._makeOne('foo/', source)
        result = o('baz/notfound.pt')
        self.assertEqual(result, None)

class TestFileOverride(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.config.assets import FileOverride
        return FileOverride

    def _makeOne(self, path, source):
        klass = self._getTargetClass()
        return klass(path, source)

    def test_it_match(self):
        source = DummyAssetSource()
        o = self._makeOne('foo.pt', source)
        result = o('foo.pt')
        self.assertEqual(result, (source, ''))
        
    def test_it_no_match(self):
        source = DummyAssetSource()
        o = self._makeOne('foo.pt', source)
        result = o('notfound.pt')
        self.assertEqual(result, None)

class DummyOverride:
    def __init__(self, result):
        self.result = result

    def __call__(self, resource_name):
        return self.result

class DummyOverrides:
    def __init__(self, result):
        self.result = result

    def get_filename(self, resource_name):
        return self.result

    listdir = isdir = has_resource = get_stream = get_string = get_filename

class DummyPackageOverrides:
    def __init__(self, package):
        self.package = package
        self.inserted = []

    def insert(self, path, source):
        self.inserted.append((path, source))
    
class DummyPkgResources:
    def __init__(self):
        self.registered = []

    def register_loader_type(self, typ, inst):
        self.registered.append((typ, inst))

class DummyPackage:
    def __init__(self, name):
        self.__name__ = name

class DummyAssetSource:
    def __init__(self, **kw):
        self.kw = kw

    def get_filename(self, resource_name):
        self.resource_name = resource_name
        return self.kw['filename']

    def get_stream(self, resource_name):
        self.resource_name = resource_name
        return self.kw['stream']

    def get_string(self, resource_name):
        self.resource_name = resource_name
        return self.kw['string']

    def exists(self, resource_name):
        self.resource_name = resource_name
        return self.kw['exists']

    def isdir(self, resource_name):
        self.resource_name = resource_name
        return self.kw['isdir']

    def listdir(self, resource_name):
        self.resource_name = resource_name
        return self.kw['listdir']
 
class DummyLoader:
    _got_data = _is_package = None
    def get_data(self, path):
        self._got_data = path
        return b'DEADBEEF'
    def is_package(self, fullname):
        self._is_package = fullname
        return True
    def get_code(self, fullname):
        self._got_code = fullname
        return b'DEADBEEF'
    def get_source(self, fullname):
        self._got_source = fullname
        return 'def foo():\n    pass'

class DummyUnderOverride:
    def __call__(self, package, path, source, _info=''):
        self.package = package
        self.path = path
        self.source = source

def read_(src):
    with open(src, 'rb') as f:
        contents = f.read()
    return contents

def _assertBody(body, filename):
    # strip both \n and \r for windows
    body = body.replace(b'\r', b'')
    body = body.replace(b'\n', b'')
    data = read_(filename)
    data = data.replace(b'\r', b'')
    data = data.replace(b'\n', b'')
    assert(body == data)
