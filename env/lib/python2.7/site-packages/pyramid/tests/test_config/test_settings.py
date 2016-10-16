import unittest

class TestSettingsConfiguratorMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test__set_settings_as_None(self):
        config = self._makeOne()
        settings = config._set_settings(None)
        self.assertTrue(settings)

    def test__set_settings_as_dictwithvalues(self):
        config = self._makeOne()
        settings = config._set_settings({'a':'1'})
        self.assertEqual(settings['a'], '1')

    def test_get_settings_nosettings(self):
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        self.assertEqual(config.get_settings(), None)

    def test_get_settings_withsettings(self):
        settings = {'a':1}
        config = self._makeOne()
        config.registry.settings = settings
        self.assertEqual(config.get_settings(), settings)

    def test_add_settings_settings_already_registered(self):
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        config._set_settings({'a':1})
        config.add_settings({'b':2})
        settings = reg.settings
        self.assertEqual(settings['a'], 1)
        self.assertEqual(settings['b'], 2)

    def test_add_settings_settings_not_yet_registered(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ISettings
        reg = Registry()
        config = self._makeOne(reg)
        config.add_settings({'a':1})
        settings = reg.getUtility(ISettings)
        self.assertEqual(settings['a'], 1)

    def test_add_settings_settings_None(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ISettings
        reg = Registry()
        config = self._makeOne(reg)
        config.add_settings(None, a=1)
        settings = reg.getUtility(ISettings)
        self.assertEqual(settings['a'], 1)

class TestSettings(unittest.TestCase):

    def _getTargetClass(self):
        from pyramid.config.settings import Settings
        return Settings

    def _makeOne(self, d=None, environ=None):
        if environ is None:
            environ = {}
        klass = self._getTargetClass()
        return klass(d, _environ_=environ)

    def test_getattr_success(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always')
            settings = self._makeOne({'reload_templates':False})
            self.assertEqual(settings.reload_templates, False)
            self.assertEqual(len(w), 1)

    def test_getattr_fail(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always')
            settings = self._makeOne({})
            self.assertRaises(AttributeError, settings.__getattr__, 'wontexist')
            self.assertEqual(len(w), 0)

    def test_getattr_raises_attribute_error(self):
        settings = self._makeOne()
        self.assertRaises(AttributeError, settings.__getattr__, 'mykey')

    def test_noargs(self):
        settings = self._makeOne()
        self.assertEqual(settings['debug_authorization'], False)
        self.assertEqual(settings['debug_notfound'], False)
        self.assertEqual(settings['debug_routematch'], False)
        self.assertEqual(settings['reload_templates'], False)
        self.assertEqual(settings['reload_resources'], False)

        self.assertEqual(settings['pyramid.debug_authorization'], False)
        self.assertEqual(settings['pyramid.debug_notfound'], False)
        self.assertEqual(settings['pyramid.debug_routematch'], False)
        self.assertEqual(settings['pyramid.reload_templates'], False)
        self.assertEqual(settings['pyramid.reload_resources'], False)

    def test_prevent_http_cache(self):
        settings = self._makeOne({})
        self.assertEqual(settings['prevent_http_cache'], False)
        self.assertEqual(settings['pyramid.prevent_http_cache'], False)
        result = self._makeOne({'prevent_http_cache':'false'})
        self.assertEqual(result['prevent_http_cache'], False)
        self.assertEqual(result['pyramid.prevent_http_cache'], False)
        result = self._makeOne({'prevent_http_cache':'t'})
        self.assertEqual(result['prevent_http_cache'], True)
        self.assertEqual(result['pyramid.prevent_http_cache'], True)
        result = self._makeOne({'prevent_http_cache':'1'})
        self.assertEqual(result['prevent_http_cache'], True)
        self.assertEqual(result['pyramid.prevent_http_cache'], True)
        result = self._makeOne({'pyramid.prevent_http_cache':'t'})
        self.assertEqual(result['prevent_http_cache'], True)
        self.assertEqual(result['pyramid.prevent_http_cache'], True)
        result = self._makeOne({}, {'PYRAMID_PREVENT_HTTP_CACHE':'1'})
        self.assertEqual(result['prevent_http_cache'], True)
        self.assertEqual(result['pyramid.prevent_http_cache'], True)
        result = self._makeOne({'prevent_http_cache':'false',
                                'pyramid.prevent_http_cache':'1'})
        self.assertEqual(result['prevent_http_cache'], True)
        self.assertEqual(result['pyramid.prevent_http_cache'], True)
        result = self._makeOne({'prevent_http_cache':'false',
                                'pyramid.prevent_http_cache':'f'},
                               {'PYRAMID_PREVENT_HTTP_CACHE':'1'})
        self.assertEqual(result['prevent_http_cache'], True)
        self.assertEqual(result['pyramid.prevent_http_cache'], True)

    def test_prevent_cachebust(self):
        settings = self._makeOne({})
        self.assertEqual(settings['prevent_cachebust'], False)
        self.assertEqual(settings['pyramid.prevent_cachebust'], False)
        result = self._makeOne({'prevent_cachebust':'false'})
        self.assertEqual(result['prevent_cachebust'], False)
        self.assertEqual(result['pyramid.prevent_cachebust'], False)
        result = self._makeOne({'prevent_cachebust':'t'})
        self.assertEqual(result['prevent_cachebust'], True)
        self.assertEqual(result['pyramid.prevent_cachebust'], True)
        result = self._makeOne({'prevent_cachebust':'1'})
        self.assertEqual(result['prevent_cachebust'], True)
        self.assertEqual(result['pyramid.prevent_cachebust'], True)
        result = self._makeOne({'pyramid.prevent_cachebust':'t'})
        self.assertEqual(result['prevent_cachebust'], True)
        self.assertEqual(result['pyramid.prevent_cachebust'], True)
        result = self._makeOne({}, {'PYRAMID_PREVENT_CACHEBUST':'1'})
        self.assertEqual(result['prevent_cachebust'], True)
        self.assertEqual(result['pyramid.prevent_cachebust'], True)
        result = self._makeOne({'prevent_cachebust':'false',
                                'pyramid.prevent_cachebust':'1'})
        self.assertEqual(result['prevent_cachebust'], True)
        self.assertEqual(result['pyramid.prevent_cachebust'], True)
        result = self._makeOne({'prevent_cachebust':'false',
                                'pyramid.prevent_cachebust':'f'},
                               {'PYRAMID_PREVENT_CACHEBUST':'1'})
        self.assertEqual(result['prevent_cachebust'], True)
        self.assertEqual(result['pyramid.prevent_cachebust'], True)

    def test_reload_templates(self):
        settings = self._makeOne({})
        self.assertEqual(settings['reload_templates'], False)
        self.assertEqual(settings['pyramid.reload_templates'], False)
        result = self._makeOne({'reload_templates':'false'})
        self.assertEqual(result['reload_templates'], False)
        self.assertEqual(result['pyramid.reload_templates'], False)
        result = self._makeOne({'reload_templates':'t'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        result = self._makeOne({'reload_templates':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        result = self._makeOne({'pyramid.reload_templates':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        result = self._makeOne({}, {'PYRAMID_RELOAD_TEMPLATES':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        result = self._makeOne({'reload_templates':'false',
                                'pyramid.reload_templates':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        result = self._makeOne({'reload_templates':'false'},
                               {'PYRAMID_RELOAD_TEMPLATES':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)

    def test_reload_resources(self):
        # alias for reload_assets
        result = self._makeOne({})
        self.assertEqual(result['reload_resources'], False)
        self.assertEqual(result['reload_assets'], False)
        self.assertEqual(result['pyramid.reload_resources'], False)
        self.assertEqual(result['pyramid.reload_assets'], False)
        result = self._makeOne({'reload_resources':'false'})
        self.assertEqual(result['reload_resources'], False)
        self.assertEqual(result['reload_assets'], False)
        self.assertEqual(result['pyramid.reload_resources'], False)
        self.assertEqual(result['pyramid.reload_assets'], False)
        result = self._makeOne({'reload_resources':'t'})
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'reload_resources':'1'})
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'pyramid.reload_resources':'1'})
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({}, {'PYRAMID_RELOAD_RESOURCES':'1'})
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'reload_resources':'false',
                                'pyramid.reload_resources':'1'})
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'reload_resources':'false',
                                'pyramid.reload_resources':'false'},
                               {'PYRAMID_RELOAD_RESOURCES':'1'})
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)

    def test_reload_assets(self):
        # alias for reload_resources
        result = self._makeOne({})
        self.assertEqual(result['reload_assets'], False)
        self.assertEqual(result['reload_resources'], False)
        self.assertEqual(result['pyramid.reload_assets'], False)
        self.assertEqual(result['pyramid.reload_resources'], False)
        result = self._makeOne({'reload_assets':'false'})
        self.assertEqual(result['reload_resources'], False)
        self.assertEqual(result['reload_assets'], False)
        self.assertEqual(result['pyramid.reload_assets'], False)
        self.assertEqual(result['pyramid.reload_resources'], False)
        result = self._makeOne({'reload_assets':'t'})
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        result = self._makeOne({'reload_assets':'1'})
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        result = self._makeOne({'pyramid.reload_assets':'1'})
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        result = self._makeOne({}, {'PYRAMID_RELOAD_ASSETS':'1'})
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        result = self._makeOne({'reload_assets':'false',
                                'pyramid.reload_assets':'1'})
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        result = self._makeOne({'reload_assets':'false',
                                'pyramid.reload_assets':'false'},
                               {'PYRAMID_RELOAD_ASSETS':'1'})
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)

    def test_reload_all(self):
        result = self._makeOne({})
        self.assertEqual(result['reload_templates'], False)
        self.assertEqual(result['reload_resources'], False)
        self.assertEqual(result['reload_assets'], False)
        self.assertEqual(result['pyramid.reload_templates'], False)
        self.assertEqual(result['pyramid.reload_resources'], False)
        self.assertEqual(result['pyramid.reload_assets'], False)
        result = self._makeOne({'reload_all':'false'})
        self.assertEqual(result['reload_templates'], False)
        self.assertEqual(result['reload_resources'], False)
        self.assertEqual(result['reload_assets'], False)
        self.assertEqual(result['pyramid.reload_templates'], False)
        self.assertEqual(result['pyramid.reload_resources'], False)
        self.assertEqual(result['pyramid.reload_assets'], False)
        result = self._makeOne({'reload_all':'t'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'reload_all':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'pyramid.reload_all':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({}, {'PYRAMID_RELOAD_ALL':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'reload_all':'false',
                                'pyramid.reload_all':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)
        result = self._makeOne({'reload_all':'false',
                                'pyramid.reload_all':'false'},
                               {'PYRAMID_RELOAD_ALL':'1'})
        self.assertEqual(result['reload_templates'], True)
        self.assertEqual(result['reload_resources'], True)
        self.assertEqual(result['reload_assets'], True)
        self.assertEqual(result['pyramid.reload_templates'], True)
        self.assertEqual(result['pyramid.reload_resources'], True)
        self.assertEqual(result['pyramid.reload_assets'], True)

    def test_debug_authorization(self):
        result = self._makeOne({})
        self.assertEqual(result['debug_authorization'], False)
        self.assertEqual(result['pyramid.debug_authorization'], False)
        result = self._makeOne({'debug_authorization':'false'})
        self.assertEqual(result['debug_authorization'], False)
        self.assertEqual(result['pyramid.debug_authorization'], False)
        result = self._makeOne({'debug_authorization':'t'})
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        result = self._makeOne({'debug_authorization':'1'})
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        result = self._makeOne({'pyramid.debug_authorization':'1'})
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        result = self._makeOne({}, {'PYRAMID_DEBUG_AUTHORIZATION':'1'})
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        result = self._makeOne({'debug_authorization':'false',
                                'pyramid.debug_authorization':'1'})
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        result = self._makeOne({'debug_authorization':'false',
                                'pyramid.debug_authorization':'false'},
                               {'PYRAMID_DEBUG_AUTHORIZATION':'1'})
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)

    def test_debug_notfound(self):
        result = self._makeOne({})
        self.assertEqual(result['debug_notfound'], False)
        self.assertEqual(result['pyramid.debug_notfound'], False)
        result = self._makeOne({'debug_notfound':'false'})
        self.assertEqual(result['debug_notfound'], False)
        self.assertEqual(result['pyramid.debug_notfound'], False)
        result = self._makeOne({'debug_notfound':'t'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        result = self._makeOne({'debug_notfound':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        result = self._makeOne({'pyramid.debug_notfound':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        result = self._makeOne({}, {'PYRAMID_DEBUG_NOTFOUND':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        result = self._makeOne({'debug_notfound':'false',
                                'pyramid.debug_notfound':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        result = self._makeOne({'debug_notfound':'false',
                                'pyramid.debug_notfound':'false'},
                               {'PYRAMID_DEBUG_NOTFOUND':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)

    def test_debug_routematch(self):
        result = self._makeOne({})
        self.assertEqual(result['debug_routematch'], False)
        self.assertEqual(result['pyramid.debug_routematch'], False)
        result = self._makeOne({'debug_routematch':'false'})
        self.assertEqual(result['debug_routematch'], False)
        self.assertEqual(result['pyramid.debug_routematch'], False)
        result = self._makeOne({'debug_routematch':'t'})
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        result = self._makeOne({'debug_routematch':'1'})
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        result = self._makeOne({'pyramid.debug_routematch':'1'})
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        result = self._makeOne({}, {'PYRAMID_DEBUG_ROUTEMATCH':'1'})
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        result = self._makeOne({'debug_routematch':'false',
                                'pyramid.debug_routematch':'1'})
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        result = self._makeOne({'debug_routematch':'false',
                                'pyramid.debug_routematch':'false'},
                               {'PYRAMID_DEBUG_ROUTEMATCH':'1'})
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)

    def test_debug_templates(self):
        result = self._makeOne({})
        self.assertEqual(result['debug_templates'], False)
        self.assertEqual(result['pyramid.debug_templates'], False)
        result = self._makeOne({'debug_templates':'false'})
        self.assertEqual(result['debug_templates'], False)
        self.assertEqual(result['pyramid.debug_templates'], False)
        result = self._makeOne({'debug_templates':'t'})
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'debug_templates':'1'})
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'pyramid.debug_templates':'1'})
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({}, {'PYRAMID_DEBUG_TEMPLATES':'1'})
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'debug_templates':'false',
                                'pyramid.debug_templates':'1'})
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'debug_templates':'false',
                                'pyramid.debug_templates':'false'},
                               {'PYRAMID_DEBUG_TEMPLATES':'1'})
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)

    def test_debug_all(self):
        result = self._makeOne({})
        self.assertEqual(result['debug_notfound'], False)
        self.assertEqual(result['debug_routematch'], False)
        self.assertEqual(result['debug_authorization'], False)
        self.assertEqual(result['debug_templates'], False)
        self.assertEqual(result['pyramid.debug_notfound'], False)
        self.assertEqual(result['pyramid.debug_routematch'], False)
        self.assertEqual(result['pyramid.debug_authorization'], False)
        self.assertEqual(result['pyramid.debug_templates'], False)
        result = self._makeOne({'debug_all':'false'})
        self.assertEqual(result['debug_notfound'], False)
        self.assertEqual(result['debug_routematch'], False)
        self.assertEqual(result['debug_authorization'], False)
        self.assertEqual(result['debug_templates'], False)
        self.assertEqual(result['pyramid.debug_notfound'], False)
        self.assertEqual(result['pyramid.debug_routematch'], False)
        self.assertEqual(result['pyramid.debug_authorization'], False)
        self.assertEqual(result['pyramid.debug_templates'], False)
        result = self._makeOne({'debug_all':'t'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'debug_all':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'pyramid.debug_all':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({}, {'PYRAMID_DEBUG_ALL':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'debug_all':'false',
                                'pyramid.debug_all':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)
        result = self._makeOne({'debug_all':'false',
                                'pyramid.debug_all':'false'},
                               {'PYRAMID_DEBUG_ALL':'1'})
        self.assertEqual(result['debug_notfound'], True)
        self.assertEqual(result['debug_routematch'], True)
        self.assertEqual(result['debug_authorization'], True)
        self.assertEqual(result['debug_templates'], True)
        self.assertEqual(result['pyramid.debug_notfound'], True)
        self.assertEqual(result['pyramid.debug_routematch'], True)
        self.assertEqual(result['pyramid.debug_authorization'], True)
        self.assertEqual(result['pyramid.debug_templates'], True)

    def test_default_locale_name(self):
        result = self._makeOne({})
        self.assertEqual(result['default_locale_name'], 'en')
        self.assertEqual(result['pyramid.default_locale_name'], 'en')
        result = self._makeOne({'default_locale_name':'abc'})
        self.assertEqual(result['default_locale_name'], 'abc')
        self.assertEqual(result['pyramid.default_locale_name'], 'abc')
        result = self._makeOne({'pyramid.default_locale_name':'abc'})
        self.assertEqual(result['default_locale_name'], 'abc')
        self.assertEqual(result['pyramid.default_locale_name'], 'abc')
        result = self._makeOne({}, {'PYRAMID_DEFAULT_LOCALE_NAME':'abc'})
        self.assertEqual(result['default_locale_name'], 'abc')
        self.assertEqual(result['pyramid.default_locale_name'], 'abc')
        result = self._makeOne({'default_locale_name':'def',
                                'pyramid.default_locale_name':'abc'})
        self.assertEqual(result['default_locale_name'], 'abc')
        self.assertEqual(result['pyramid.default_locale_name'], 'abc')
        result = self._makeOne({'default_locale_name':'def',
                                'pyramid.default_locale_name':'ghi'},
                               {'PYRAMID_DEFAULT_LOCALE_NAME':'abc'})
        self.assertEqual(result['default_locale_name'], 'abc')
        self.assertEqual(result['pyramid.default_locale_name'], 'abc')

    def test_originals_kept(self):
        result = self._makeOne({'a':'i am so a'})
        self.assertEqual(result['a'], 'i am so a')


