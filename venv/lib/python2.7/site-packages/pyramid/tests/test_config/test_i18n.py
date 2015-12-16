import os
import unittest

from pyramid.tests.test_config import dummyfactory

here = os.path.dirname(__file__)
locale = os.path.abspath(
    os.path.join(here, '..', 'pkgs', 'localeapp', 'locale'))
locale2 = os.path.abspath(
    os.path.join(here, '..', 'pkgs', 'localeapp', 'locale2'))
locale3 = os.path.abspath(
    os.path.join(here, '..', 'pkgs', 'localeapp', 'locale3'))

class TestI18NConfiguratorMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_set_locale_negotiator(self):
        from pyramid.interfaces import ILocaleNegotiator
        config = self._makeOne(autocommit=True)
        def negotiator(request): pass
        config.set_locale_negotiator(negotiator)
        self.assertEqual(config.registry.getUtility(ILocaleNegotiator),
                         negotiator)

    def test_set_locale_negotiator_dottedname(self):
        from pyramid.interfaces import ILocaleNegotiator
        config = self._makeOne(autocommit=True)
        config.set_locale_negotiator(
            'pyramid.tests.test_config.dummyfactory')
        self.assertEqual(config.registry.getUtility(ILocaleNegotiator),
                         dummyfactory)

    def test_add_translation_dirs_missing_dir(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError,
                          config.add_translation_dirs,
                          '/wont/exist/on/my/system')

    def test_add_translation_dirs_no_specs(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne()
        config.add_translation_dirs()
        self.assertEqual(config.registry.queryUtility(ITranslationDirectories),
                         None)

    def test_add_translation_dirs_asset_spec(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs('pyramid.tests.pkgs.localeapp:locale')
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale])

    def test_add_translation_dirs_asset_spec_existing_translation_dirs(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        directories = ['abc']
        config.registry.registerUtility(directories, ITranslationDirectories)
        config.add_translation_dirs('pyramid.tests.pkgs.localeapp:locale')
        result = config.registry.getUtility(ITranslationDirectories)
        self.assertEqual(result, [locale, 'abc'])

    def test_add_translation_dirs_multiple_specs(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs('pyramid.tests.pkgs.localeapp:locale',
                                    'pyramid.tests.pkgs.localeapp:locale2')
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale, locale2])

    def test_add_translation_dirs_multiple_specs_multiple_calls(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs('pyramid.tests.pkgs.localeapp:locale',
                                    'pyramid.tests.pkgs.localeapp:locale2')
        config.add_translation_dirs('pyramid.tests.pkgs.localeapp:locale3')
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale3, locale, locale2])

    def test_add_translation_dirs_abspath(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs(locale)
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale])

