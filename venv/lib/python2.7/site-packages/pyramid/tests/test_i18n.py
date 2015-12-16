# -*- coding: utf-8 -*-
#
import os

here = os.path.dirname(__file__)
localedir = os.path.join(here, 'pkgs', 'localeapp', 'locale')

import unittest
from pyramid import testing

class TestTranslationString(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.i18n import TranslationString
        return TranslationString(*arg, **kw)

    def test_it(self):
        # this is part of the API, we don't actually need to test much more
        # than that it's importable
        ts = self._makeOne('a')
        self.assertEqual(ts, 'a')

class TestTranslationStringFactory(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.i18n import TranslationStringFactory
        return TranslationStringFactory(*arg, **kw)

    def test_it(self):
        # this is part of the API, we don't actually need to test much more
        # than that it's importable
        factory = self._makeOne('a')
        self.assertEqual(factory('').domain, 'a')

class TestLocalizer(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.i18n import Localizer
        return Localizer(*arg, **kw)

    def test_ctor(self):
        localizer = self._makeOne('en_US', None)
        self.assertEqual(localizer.locale_name, 'en_US')
        self.assertEqual(localizer.translations, None)

    def test_translate(self):
        translations = DummyTranslations()
        localizer = self._makeOne(None, translations)
        self.assertEqual(localizer.translate('123', domain='1',
                                             mapping={}), '123')
        self.assertTrue(localizer.translator)

    def test_pluralize(self):
        translations = DummyTranslations()
        localizer = self._makeOne(None, translations)
        result = localizer.pluralize('singular', 'plural', 1,
                                     domain='1', mapping={})
        self.assertEqual(result, 'singular')
        self.assertTrue(localizer.pluralizer)

    def test_pluralize_pluralizer_already_added(self):
        translations = DummyTranslations()
        localizer = self._makeOne(None, translations)
        def pluralizer(*arg, **kw):
            return arg, kw
        localizer.pluralizer = pluralizer
        result = localizer.pluralize('singular', 'plural', 1, domain='1',
                                     mapping={})
        self.assertEqual(
            result,
            (('singular', 'plural', 1), {'domain': '1', 'mapping': {}})
            )
        self.assertTrue(localizer.pluralizer is pluralizer)

    def test_pluralize_default_translations(self):
        # test that even without message ids loaded that
        # "localizer.pluralize" "works" instead of raising an inscrutable
        # "translations object has no attr 'plural' error; see
        # see https://github.com/Pylons/pyramid/issues/235
        from pyramid.i18n import Translations
        translations = Translations()
        translations._catalog = {}
        localizer = self._makeOne(None, translations)
        result = localizer.pluralize('singular', 'plural', 2, domain='1',
                                     mapping={})
        self.assertEqual(result, 'plural')

class Test_negotiate_locale_name(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, request):
        from pyramid.i18n import negotiate_locale_name
        return negotiate_locale_name(request)

    def _registerImpl(self, impl):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        from pyramid.interfaces import ILocaleNegotiator
        registry.registerUtility(impl, ILocaleNegotiator)

    def test_no_registry_on_request(self):
        self._registerImpl(dummy_negotiator)
        request = DummyRequest()
        result = self._callFUT(request)
        self.assertEqual(result, 'bogus')

    def test_with_registry_on_request(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        self._registerImpl(dummy_negotiator)
        request = DummyRequest()
        request.registry = registry
        result = self._callFUT(request)
        self.assertEqual(result, 'bogus')

    def test_default_from_settings(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        settings = {'default_locale_name':'settings'}
        registry.settings = settings
        request = DummyRequest()
        request.registry = registry
        result = self._callFUT(request)
        self.assertEqual(result, 'settings')

    def test_use_default_locale_negotiator(self):
        from pyramid.threadlocal import get_current_registry
        registry = get_current_registry()
        request = DummyRequest()
        request.registry = registry
        request._LOCALE_ = 'locale'
        result = self._callFUT(request)
        self.assertEqual(result, 'locale')

    def test_default_default(self):
        request = DummyRequest()
        result = self._callFUT(request)
        self.assertEqual(result, 'en')

class Test_get_locale_name(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, request):
        from pyramid.i18n import get_locale_name
        return get_locale_name(request)

    def test_name_on_request(self):
        request = DummyRequest()
        request.locale_name = 'ie'
        result = self._callFUT(request)
        self.assertEqual(result, 'ie')

class Test_make_localizer(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, locale, tdirs):
        from pyramid.i18n import make_localizer
        return make_localizer(locale, tdirs)

    def test_locale_from_mo(self):
        from pyramid.i18n import Localizer
        localedirs = [localedir]
        locale_name = 'de'
        result = self._callFUT(locale_name, localedirs)
        self.assertEqual(result.__class__, Localizer)
        self.assertEqual(result.translate('Approve', 'deformsite'),
                         'Genehmigen')
        self.assertEqual(result.translate('Approve'), 'Approve')
        self.assertTrue(hasattr(result, 'pluralize'))

    def test_locale_from_mo_bad_mo(self):
        from pyramid.i18n import Localizer
        localedirs = [localedir]
        locale_name = 'be'
        result = self._callFUT(locale_name, localedirs)
        self.assertEqual(result.__class__, Localizer)
        self.assertEqual(result.translate('Approve', 'deformsite'),
                         'Approve')

    def test_locale_from_mo_mo_isdir(self):
        from pyramid.i18n import Localizer
        localedirs = [localedir]
        locale_name = 'gb'
        result = self._callFUT(locale_name, localedirs)
        self.assertEqual(result.__class__, Localizer)
        self.assertEqual(result.translate('Approve', 'deformsite'),
                         'Approve')

    def test_territory_fallback(self):
        from pyramid.i18n import Localizer
        localedirs = [localedir]
        locale_name = 'de_DE'
        result = self._callFUT(locale_name, localedirs)
        self.assertEqual(result.__class__, Localizer)
        self.assertEqual(result.translate('Submit', 'deformsite'),
                         'different') # prefer translations from de_DE locale
        self.assertEqual(result.translate('Approve', 'deformsite'),
                         'Genehmigen') # missing from de_DE locale, but in de

class Test_get_localizer(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, request):
        from pyramid.i18n import get_localizer
        return get_localizer(request)

    def test_it(self):
        request = DummyRequest()
        request.localizer = 'localizer'
        self.assertEqual(self._callFUT(request), 'localizer')

class Test_default_locale_negotiator(unittest.TestCase):
    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _callFUT(self, request):
        from pyramid.i18n import default_locale_negotiator
        return default_locale_negotiator(request)

    def test_from_none(self):
        request = DummyRequest()
        result = self._callFUT(request)
        self.assertEqual(result, None)

    def test_from_request_attr(self):
        request = DummyRequest()
        request._LOCALE_ = 'foo'
        result = self._callFUT(request)
        self.assertEqual(result, 'foo')

    def test_from_params(self):
        request = DummyRequest()
        request.params['_LOCALE_'] = 'foo'
        result = self._callFUT(request)
        self.assertEqual(result, 'foo')

    def test_from_cookies(self):
        request = DummyRequest()
        request.cookies['_LOCALE_'] = 'foo'
        result = self._callFUT(request)
        self.assertEqual(result, 'foo')

class TestTranslations(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid.i18n import Translations
        return Translations
        
    def _makeOne(self):
        messages1 = [
            ('foo', 'Voh'),
            (('foo1', 1), 'Voh1'),
        ]
        messages2 = [
            ('foo', 'VohD'),
            (('foo1', 1), 'VohD1'),
        ]

        klass = self._getTargetClass()
        
        translations1 = klass(None, domain='messages')
        translations1._catalog = dict(messages1)
        translations1.plural = lambda *arg: 1
        translations2 = klass(None, domain='messages1')
        translations2._catalog = dict(messages2)
        translations2.plural = lambda *arg: 1
        translations = translations1.add(translations2, merge=False)
        return translations

    def test_load_locales_None(self):
        import gettext
        klass = self._getTargetClass()
        result = klass.load(localedir, None, domain=None)
        self.assertEqual(result.__class__, gettext.NullTranslations)

    def test_load_domain_None(self):
        import gettext
        locales = ['de', 'en']
        klass = self._getTargetClass()
        result = klass.load(localedir, locales, domain=None)
        self.assertEqual(result.__class__, gettext.NullTranslations)

    def test_load_found_locale_and_domain(self):
        locales = ['de', 'en']
        klass = self._getTargetClass()
        result = klass.load(localedir, locales, domain='deformsite')
        self.assertEqual(result.__class__, klass)

    def test_load_found_locale_and_domain_locale_is_string(self):
        locales = 'de'
        klass = self._getTargetClass()
        result = klass.load(localedir, locales, domain='deformsite')
        self.assertEqual(result.__class__, klass)

    def test___repr__(self):
        inst = self._makeOne()
        result = repr(inst)
        self.assertEqual(result, '<Translations: "None">')

    def test_merge_not_gnutranslations(self):
        inst = self._makeOne()
        self.assertEqual(inst.merge(None), inst)

    def test_merge_gnutranslations(self):
        inst = self._makeOne()
        inst2 = self._makeOne()
        inst2._catalog['a'] = 'b'
        inst.merge(inst2)
        self.assertEqual(inst._catalog['a'], 'b')

    def test_merge_gnutranslations_not_translations(self):
        import gettext
        t = gettext.GNUTranslations()
        t._catalog = {'a':'b'}
        inst = self._makeOne()
        inst.merge(t)
        self.assertEqual(inst._catalog['a'], 'b')

    def test_add_different_domain_merge_true_notexisting(self):
        inst = self._makeOne()
        inst2 = self._makeOne()
        inst2.domain = 'domain2'
        inst.add(inst2)
        self.assertEqual(inst._domains['domain2'], inst2)

    def test_add_different_domain_merge_true_existing(self):
        inst = self._makeOne()
        inst2 = self._makeOne()
        inst3 = self._makeOne()
        inst2.domain = 'domain2'
        inst2._catalog['a'] = 'b'
        inst3.domain = 'domain2'
        inst._domains['domain2'] = inst3
        inst.add(inst2)
        self.assertEqual(inst._domains['domain2'], inst3)
        self.assertEqual(inst3._catalog['a'], 'b')

    def test_add_same_domain_merge_true(self):
        inst = self._makeOne()
        inst2 = self._makeOne()
        inst2._catalog['a'] = 'b'
        inst.add(inst2)
        self.assertEqual(inst._catalog['a'], 'b')

    def test_dgettext(self):
        t = self._makeOne()
        self.assertEqual(t.dgettext('messages', 'foo'), 'Voh')
        self.assertEqual(t.dgettext('messages1', 'foo'), 'VohD')

    def test_ldgettext(self):
        t = self._makeOne()
        self.assertEqual(t.ldgettext('messages', 'foo'), b'Voh')
        self.assertEqual(t.ldgettext('messages1', 'foo'), b'VohD')

    def test_dugettext(self):
        t = self._makeOne()
        self.assertEqual(t.dugettext('messages', 'foo'), 'Voh')
        self.assertEqual(t.dugettext('messages1', 'foo'), 'VohD')

    def test_dngettext(self):
        t = self._makeOne()
        self.assertEqual(t.dngettext('messages', 'foo1', 'foos1', 1), 'Voh1')
        self.assertEqual(t.dngettext('messages1', 'foo1', 'foos1', 1), 'VohD1')
        
    def test_ldngettext(self):
        t = self._makeOne()
        self.assertEqual(t.ldngettext('messages', 'foo1', 'foos1', 1), b'Voh1')
        self.assertEqual(t.ldngettext('messages1', 'foo1', 'foos1', 1),b'VohD1')

    def test_dungettext(self):
        t = self._makeOne()
        self.assertEqual(t.dungettext('messages', 'foo1', 'foos1', 1), 'Voh1')
        self.assertEqual(t.dungettext('messages1', 'foo1', 'foos1', 1), 'VohD1')

    def test_default_germanic_pluralization(self):
        t = self._getTargetClass()()
        t._catalog = {}
        result = t.dungettext('messages', 'foo1', 'foos1', 2)
        self.assertEqual(result, 'foos1')

class TestLocalizerRequestMixin(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def _makeOne(self):
        from pyramid.i18n import LocalizerRequestMixin
        request = LocalizerRequestMixin()
        request.registry = self.config.registry
        request.cookies = {}
        request.params = {}
        return request

    def test_default_localizer(self):
        # `localizer` returns a default localizer for `en`
        from pyramid.i18n import Localizer
        request = self._makeOne()
        self.assertEqual(request.localizer.__class__, Localizer)
        self.assertEqual(request.locale_name, 'en')

    def test_custom_localizer_for_default_locale(self):
        from pyramid.interfaces import ILocalizer
        dummy = object()
        self.config.registry.registerUtility(dummy, ILocalizer, name='en')
        request = self._makeOne()
        self.assertEqual(request.localizer, dummy)

    def test_custom_localizer_for_custom_locale(self):
        from pyramid.interfaces import ILocalizer
        dummy = object()
        self.config.registry.registerUtility(dummy, ILocalizer, name='ie')
        request = self._makeOne()
        request._LOCALE_ = 'ie'
        self.assertEqual(request.localizer, dummy)

    def test_localizer_from_mo(self):
        from pyramid.interfaces import ITranslationDirectories
        from pyramid.i18n import Localizer
        localedirs = [localedir]
        self.config.registry.registerUtility(
            localedirs, ITranslationDirectories)
        request = self._makeOne()
        request._LOCALE_ = 'de'
        result = request.localizer
        self.assertEqual(result.__class__, Localizer)
        self.assertEqual(result.translate('Approve', 'deformsite'),
                         'Genehmigen')
        self.assertEqual(result.translate('Approve'), 'Approve')
        self.assertTrue(hasattr(result, 'pluralize'))

    def test_localizer_from_mo_bad_mo(self):
        from pyramid.interfaces import ITranslationDirectories
        from pyramid.i18n import Localizer
        localedirs = [localedir]
        self.config.registry.registerUtility(
            localedirs, ITranslationDirectories)
        request = self._makeOne()
        request._LOCALE_ = 'be'
        result = request.localizer
        self.assertEqual(result.__class__, Localizer)
        self.assertEqual(result.translate('Approve', 'deformsite'),
                         'Approve')

class DummyRequest(object):
    def __init__(self):
        self.params = {}
        self.cookies = {}

def dummy_negotiator(request):
    return 'bogus'

class DummyTranslations(object):
    def ugettext(self, text):
        return text

    gettext = ugettext

    def ungettext(self, singular, plural, n):
        return singular

    ngettext = ungettext
