import unittest

import os

from pyramid.compat import im_func
from pyramid.testing import skip_on

from pyramid.tests.test_config import dummy_tween_factory
from pyramid.tests.test_config import dummy_include
from pyramid.tests.test_config import dummy_extend
from pyramid.tests.test_config import dummy_extend2
from pyramid.tests.test_config import IDummy
from pyramid.tests.test_config import DummyContext

from pyramid.exceptions import ConfigurationExecutionError
from pyramid.exceptions import ConfigurationConflictError

from pyramid.interfaces import IRequest

class ConfiguratorTests(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def _getViewCallable(self, config, ctx_iface=None, request_iface=None,
                         name='', exception_view=False):
        from zope.interface import Interface
        from pyramid.interfaces import IRequest
        from pyramid.interfaces import IView
        from pyramid.interfaces import IViewClassifier
        from pyramid.interfaces import IExceptionViewClassifier
        if exception_view: # pragma: no cover
            classifier = IExceptionViewClassifier
        else:
            classifier = IViewClassifier
        if ctx_iface is None:
            ctx_iface = Interface
        if request_iface is None:
            request_iface = IRequest
        return config.registry.adapters.lookup(
            (classifier, request_iface, ctx_iface), IView, name=name,
            default=None)

    def _registerEventListener(self, config, event_iface=None):
        if event_iface is None: # pragma: no cover
            from zope.interface import Interface
            event_iface = Interface
        L = []
        def subscriber(*event):
            L.extend(event)
        config.registry.registerHandler(subscriber, (event_iface,))
        return L

    def _makeRequest(self, config):
        request = DummyRequest()
        request.registry = config.registry
        return request

    def test_ctor_no_registry(self):
        import sys
        from pyramid.interfaces import ISettings
        from pyramid.config import Configurator
        from pyramid.interfaces import IRendererFactory
        config = Configurator()
        this_pkg = sys.modules['pyramid.tests.test_config']
        self.assertTrue(config.registry.getUtility(ISettings))
        self.assertEqual(config.package, this_pkg)
        config.commit()
        self.assertTrue(config.registry.getUtility(IRendererFactory, 'json'))
        self.assertTrue(config.registry.getUtility(IRendererFactory, 'string'))

    def test_begin(self):
        from pyramid.config import Configurator
        config = Configurator()
        manager = DummyThreadLocalManager()
        config.manager = manager
        config.begin()
        self.assertEqual(manager.pushed,
                         {'registry':config.registry, 'request':None})
        self.assertEqual(manager.popped, False)

    def test_begin_with_request(self):
        from pyramid.config import Configurator
        config = Configurator()
        request = object()
        manager = DummyThreadLocalManager()
        config.manager = manager
        config.begin(request=request)
        self.assertEqual(manager.pushed,
                         {'registry':config.registry, 'request':request})
        self.assertEqual(manager.popped, False)

    def test_end(self):
        from pyramid.config import Configurator
        config = Configurator()
        manager = DummyThreadLocalManager()
        config.manager = manager
        config.end()
        self.assertEqual(manager.pushed, None)
        self.assertEqual(manager.popped, True)

    def test_ctor_with_package_registry(self):
        import sys
        from pyramid.config import Configurator
        pkg = sys.modules['pyramid']
        config = Configurator(package=pkg)
        self.assertEqual(config.package, pkg)

    def test_ctor_noreg_custom_settings(self):
        from pyramid.interfaces import ISettings
        settings = {'reload_templates':True,
                    'mysetting':True}
        config = self._makeOne(settings=settings)
        settings = config.registry.getUtility(ISettings)
        self.assertEqual(settings['reload_templates'], True)
        self.assertEqual(settings['debug_authorization'], False)
        self.assertEqual(settings['mysetting'], True)

    def test_ctor_noreg_debug_logger_None_default(self):
        from pyramid.interfaces import IDebugLogger
        config = self._makeOne()
        logger = config.registry.getUtility(IDebugLogger)
        self.assertEqual(logger.name, 'pyramid.tests.test_config')

    def test_ctor_noreg_debug_logger_non_None(self):
        from pyramid.interfaces import IDebugLogger
        logger = object()
        config = self._makeOne(debug_logger=logger)
        result = config.registry.getUtility(IDebugLogger)
        self.assertEqual(logger, result)

    def test_ctor_authentication_policy(self):
        from pyramid.interfaces import IAuthenticationPolicy
        policy = object()
        config = self._makeOne(authentication_policy=policy)
        config.commit()
        result = config.registry.getUtility(IAuthenticationPolicy)
        self.assertEqual(policy, result)

    def test_ctor_authorization_policy_only(self):
        policy = object()
        config = self._makeOne(authorization_policy=policy)
        self.assertRaises(ConfigurationExecutionError, config.commit)

    def test_ctor_no_root_factory(self):
        from pyramid.interfaces import IRootFactory
        config = self._makeOne()
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)

    def test_ctor_with_root_factory(self):
        from pyramid.interfaces import IRootFactory
        factory = object()
        config = self._makeOne(root_factory=factory)
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.queryUtility(IRootFactory), factory)

    def test_ctor_alternate_renderers(self):
        from pyramid.interfaces import IRendererFactory
        renderer = object()
        config = self._makeOne(renderers=[('yeah', renderer)])
        config.commit()
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'yeah'),
                         renderer)

    def test_ctor_default_renderers(self):
        from pyramid.interfaces import IRendererFactory
        from pyramid.renderers import json_renderer_factory
        config = self._makeOne()
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'json'),
                         json_renderer_factory)

    def test_ctor_default_permission(self):
        from pyramid.interfaces import IDefaultPermission
        config = self._makeOne(default_permission='view')
        config.commit()
        self.assertEqual(config.registry.getUtility(IDefaultPermission), 'view')

    def test_ctor_session_factory(self):
        from pyramid.interfaces import ISessionFactory
        factory = object()
        config = self._makeOne(session_factory=factory)
        self.assertEqual(config.registry.queryUtility(ISessionFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(ISessionFactory), factory)

    def test_ctor_default_view_mapper(self):
        from pyramid.interfaces import IViewMapperFactory
        mapper = object()
        config = self._makeOne(default_view_mapper=mapper)
        config.commit()
        self.assertEqual(config.registry.getUtility(IViewMapperFactory),
                         mapper)

    def test_ctor_httpexception_view_default(self):
        from pyramid.interfaces import IExceptionResponse
        from pyramid.httpexceptions import default_exceptionresponse_view
        from pyramid.interfaces import IRequest
        config = self._makeOne()
        view = self._getViewCallable(config,
                                     ctx_iface=IExceptionResponse,
                                     request_iface=IRequest)
        self.assertTrue(view.__wraps__ is default_exceptionresponse_view)

    def test_ctor_exceptionresponse_view_None(self):
        from pyramid.interfaces import IExceptionResponse
        from pyramid.interfaces import IRequest
        config = self._makeOne(exceptionresponse_view=None)
        view = self._getViewCallable(config,
                                     ctx_iface=IExceptionResponse,
                                     request_iface=IRequest)
        self.assertTrue(view is None)

    def test_ctor_exceptionresponse_view_custom(self):
        from pyramid.interfaces import IExceptionResponse
        from pyramid.interfaces import IRequest
        def exceptionresponse_view(context, request): pass
        config = self._makeOne(exceptionresponse_view=exceptionresponse_view)
        view = self._getViewCallable(config,
                                     ctx_iface=IExceptionResponse,
                                     request_iface=IRequest)
        self.assertTrue(view.__wraps__ is exceptionresponse_view)

    def test_ctor_with_introspection(self):
        config = self._makeOne(introspection=False)
        self.assertEqual(config.introspection, False)

    def test_ctor_default_webob_response_adapter_registered(self):
        from webob import Response as WebobResponse
        response = WebobResponse()
        from pyramid.interfaces import IResponse
        config = self._makeOne(autocommit=True)
        result = config.registry.queryAdapter(response, IResponse)
        self.assertEqual(result, response)
        
    def test_with_package_module(self):
        from pyramid.tests.test_config import test_init
        import pyramid.tests
        config = self._makeOne()
        newconfig = config.with_package(test_init)
        self.assertEqual(newconfig.package, pyramid.tests.test_config)

    def test_with_package_package(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        newconfig = config.with_package(pyramid.tests.test_config)
        self.assertEqual(newconfig.package, pyramid.tests.test_config)

    def test_with_package(self):
        import pyramid.tests
        config = self._makeOne()
        config.basepath = 'basepath'
        config.info = 'info'
        config.includepath = ('spec',)
        config.autocommit = True
        config.route_prefix = 'prefix'
        newconfig = config.with_package(pyramid.tests)
        self.assertEqual(newconfig.package, pyramid.tests)
        self.assertEqual(newconfig.registry, config.registry)
        self.assertEqual(newconfig.autocommit, True)
        self.assertEqual(newconfig.route_prefix, 'prefix')
        self.assertEqual(newconfig.info, 'info')
        self.assertEqual(newconfig.basepath, 'basepath')
        self.assertEqual(newconfig.includepath, ('spec',))

    def test_maybe_dotted_string_success(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        result = config.maybe_dotted('pyramid.tests.test_config')
        self.assertEqual(result, pyramid.tests.test_config)

    def test_maybe_dotted_string_fail(self):
        config = self._makeOne()
        self.assertRaises(ImportError, config.maybe_dotted, 'cant.be.found')

    def test_maybe_dotted_notstring_success(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        result = config.maybe_dotted(pyramid.tests.test_config)
        self.assertEqual(result, pyramid.tests.test_config)

    def test_absolute_asset_spec_already_absolute(self):
        import pyramid.tests.test_config
        config = self._makeOne(package=pyramid.tests.test_config)
        result = config.absolute_asset_spec('already:absolute')
        self.assertEqual(result, 'already:absolute')

    def test_absolute_asset_spec_notastring(self):
        import pyramid.tests.test_config
        config = self._makeOne(package=pyramid.tests.test_config)
        result = config.absolute_asset_spec(None)
        self.assertEqual(result, None)

    def test_absolute_asset_spec_relative(self):
        import pyramid.tests.test_config
        config = self._makeOne(package=pyramid.tests.test_config)
        result = config.absolute_asset_spec('files')
        self.assertEqual(result, 'pyramid.tests.test_config:files')

    def test__fix_registry_has_listeners(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertEqual(reg.has_listeners, True)

    def test__fix_registry_notify(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertEqual(reg.notify(1), None)
        self.assertEqual(reg.events, (1,))

    def test__fix_registry_queryAdapterOrSelf(self):
        from zope.interface import Interface
        from zope.interface import implementer
        class IFoo(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        class Bar(object):
            pass
        adaptation = ()
        foo = Foo()
        bar = Bar()
        reg = DummyRegistry(adaptation)
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertTrue(reg.queryAdapterOrSelf(foo, IFoo) is foo)
        self.assertTrue(reg.queryAdapterOrSelf(bar, IFoo) is adaptation)

    def test__fix_registry_registerSelfAdapter(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        reg.registerSelfAdapter('required', 'provided', name='abc')
        self.assertEqual(len(reg.adapters), 1)
        args, kw = reg.adapters[0]
        self.assertEqual(args[0]('abc'), 'abc')
        self.assertEqual(kw,
                         {'info': '', 'provided': 'provided',
                          'required': 'required', 'name': 'abc', 'event': True})

    def test__fix_registry_adds__lock(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertTrue(hasattr(reg, '_lock'))

    def test__fix_registry_adds_clear_view_lookup_cache(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        self.assertFalse(hasattr(reg, '_clear_view_lookup_cache'))
        config._fix_registry()
        self.assertFalse(hasattr(reg, '_view_lookup_cache'))
        reg._clear_view_lookup_cache()
        self.assertEqual(reg._view_lookup_cache, {})

    def test_setup_registry_calls_fix_registry(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config.add_view = lambda *arg, **kw: False
        config._add_tween = lambda *arg, **kw: False
        config.setup_registry()
        self.assertEqual(reg.has_listeners, True)

    def test_setup_registry_registers_default_exceptionresponse_views(self):
        from webob.exc import WSGIHTTPException
        from pyramid.interfaces import IExceptionResponse
        from pyramid.view import default_exceptionresponse_view
        reg = DummyRegistry()
        config = self._makeOne(reg)
        views = []
        config.add_view = lambda *arg, **kw: views.append((arg, kw))
        config.add_default_view_predicates = lambda *arg: None
        config._add_tween = lambda *arg, **kw: False
        config.setup_registry()
        self.assertEqual(views[0], ((default_exceptionresponse_view,),
                                    {'context':IExceptionResponse}))
        self.assertEqual(views[1], ((default_exceptionresponse_view,),
                                    {'context':WSGIHTTPException}))

    def test_setup_registry_registers_default_view_predicates(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        vp_called = []
        config.add_view = lambda *arg, **kw: None
        config.add_default_view_predicates = lambda *arg: vp_called.append(True)
        config._add_tween = lambda *arg, **kw: False
        config.setup_registry()
        self.assertTrue(vp_called)

    def test_setup_registry_registers_default_webob_iresponse_adapter(self):
        from webob import Response
        from pyramid.interfaces import IResponse
        config = self._makeOne()
        config.setup_registry()
        response = Response()
        self.assertTrue(
            config.registry.queryAdapter(response, IResponse) is response)

    def test_setup_registry_explicit_notfound_trumps_iexceptionresponse(self):
        from pyramid.renderers import null_renderer
        from zope.interface import implementedBy
        from pyramid.interfaces import IRequest
        from pyramid.httpexceptions import HTTPNotFound
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg, autocommit=True)
        config.setup_registry() # registers IExceptionResponse default view
        def myview(context, request):
            return 'OK'
        config.add_view(myview, context=HTTPNotFound, renderer=null_renderer)
        request = self._makeRequest(config)
        view = self._getViewCallable(config,
                                     ctx_iface=implementedBy(HTTPNotFound),
                                     request_iface=IRequest)
        result = view(None, request)
        self.assertEqual(result, 'OK')

    def test_setup_registry_custom_settings(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ISettings
        settings = {'reload_templates':True,
                    'mysetting':True}
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(settings=settings)
        settings = reg.getUtility(ISettings)
        self.assertEqual(settings['reload_templates'], True)
        self.assertEqual(settings['debug_authorization'], False)
        self.assertEqual(settings['mysetting'], True)

    def test_setup_registry_debug_logger_None_default(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDebugLogger
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry()
        logger = reg.getUtility(IDebugLogger)
        self.assertEqual(logger.name, 'pyramid.tests.test_config')

    def test_setup_registry_debug_logger_non_None(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDebugLogger
        logger = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(debug_logger=logger)
        result = reg.getUtility(IDebugLogger)
        self.assertEqual(logger, result)

    def test_setup_registry_debug_logger_name(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDebugLogger
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(debug_logger='foo')
        result = reg.getUtility(IDebugLogger)
        self.assertEqual(result.name, 'foo')

    def test_setup_registry_authentication_policy(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IAuthenticationPolicy
        policy = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(authentication_policy=policy)
        config.commit()
        result = reg.getUtility(IAuthenticationPolicy)
        self.assertEqual(policy, result)

    def test_setup_registry_authentication_policy_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IAuthenticationPolicy
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(authentication_policy='pyramid.tests.test_config')
        config.commit()
        result = reg.getUtility(IAuthenticationPolicy)
        import pyramid.tests.test_config
        self.assertEqual(result, pyramid.tests.test_config)

    def test_setup_registry_authorization_policy_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IAuthorizationPolicy
        reg = Registry()
        config = self._makeOne(reg)
        dummy = object()
        config.setup_registry(authentication_policy=dummy,
                              authorization_policy='pyramid.tests.test_config')
        config.commit()
        result = reg.getUtility(IAuthorizationPolicy)
        import pyramid.tests.test_config
        self.assertEqual(result, pyramid.tests.test_config)

    def test_setup_registry_authorization_policy_only(self):
        from pyramid.registry import Registry
        policy = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(authorization_policy=policy)
        config = self.assertRaises(ConfigurationExecutionError, config.commit)

    def test_setup_registry_no_default_root_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRootFactory
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry()
        config.commit()
        self.assertEqual(reg.queryUtility(IRootFactory), None)

    def test_setup_registry_dottedname_root_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRootFactory
        reg = Registry()
        config = self._makeOne(reg)
        import pyramid.tests.test_config
        config.setup_registry(root_factory='pyramid.tests.test_config')
        self.assertEqual(reg.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(reg.getUtility(IRootFactory),
                         pyramid.tests.test_config)

    def test_setup_registry_locale_negotiator_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ILocaleNegotiator
        reg = Registry()
        config = self._makeOne(reg)
        import pyramid.tests.test_config
        config.setup_registry(locale_negotiator='pyramid.tests.test_config')
        self.assertEqual(reg.queryUtility(ILocaleNegotiator), None)
        config.commit()
        utility = reg.getUtility(ILocaleNegotiator)
        self.assertEqual(utility, pyramid.tests.test_config)

    def test_setup_registry_locale_negotiator(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ILocaleNegotiator
        reg = Registry()
        config = self._makeOne(reg)
        negotiator = object()
        config.setup_registry(locale_negotiator=negotiator)
        self.assertEqual(reg.queryUtility(ILocaleNegotiator), None)
        config.commit()
        utility = reg.getUtility(ILocaleNegotiator)
        self.assertEqual(utility, negotiator)

    def test_setup_registry_request_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRequestFactory
        reg = Registry()
        config = self._makeOne(reg)
        factory = object()
        config.setup_registry(request_factory=factory)
        self.assertEqual(reg.queryUtility(IRequestFactory), None)
        config.commit()
        utility = reg.getUtility(IRequestFactory)
        self.assertEqual(utility, factory)

    def test_setup_registry_response_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IResponseFactory
        reg = Registry()
        config = self._makeOne(reg)
        factory = lambda r: object()
        config.setup_registry(response_factory=factory)
        self.assertEqual(reg.queryUtility(IResponseFactory), None)
        config.commit()
        utility = reg.getUtility(IResponseFactory)
        self.assertEqual(utility, factory)

    def test_setup_registry_request_factory_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRequestFactory
        reg = Registry()
        config = self._makeOne(reg)
        import pyramid.tests.test_config
        config.setup_registry(request_factory='pyramid.tests.test_config')
        self.assertEqual(reg.queryUtility(IRequestFactory), None)
        config.commit()
        utility = reg.getUtility(IRequestFactory)
        self.assertEqual(utility, pyramid.tests.test_config)

    def test_setup_registry_alternate_renderers(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRendererFactory
        renderer = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(renderers=[('yeah', renderer)])
        config.commit()
        self.assertEqual(reg.getUtility(IRendererFactory, 'yeah'),
                         renderer)

    def test_setup_registry_default_permission(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDefaultPermission
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(default_permission='view')
        config.commit()
        self.assertEqual(reg.getUtility(IDefaultPermission), 'view')

    def test_setup_registry_includes(self):
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        settings = {
            'pyramid.includes':
"""pyramid.tests.test_config.dummy_include
pyramid.tests.test_config.dummy_include2""",
        }
        config.setup_registry(settings=settings)
        self.assertTrue(reg.included)
        self.assertTrue(reg.also_included)

    def test_setup_registry_includes_spaces(self):
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        settings = {
            'pyramid.includes':
"""pyramid.tests.test_config.dummy_include pyramid.tests.test_config.dummy_include2""",
        }
        config.setup_registry(settings=settings)
        self.assertTrue(reg.included)
        self.assertTrue(reg.also_included)

    def test_setup_registry_tweens(self):
        from pyramid.interfaces import ITweens
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        settings = {
            'pyramid.tweens':
                    'pyramid.tests.test_config.dummy_tween_factory'
        }
        config.setup_registry(settings=settings)
        config.commit()
        tweens = config.registry.getUtility(ITweens)
        self.assertEqual(
            tweens.explicit,
            [('pyramid.tests.test_config.dummy_tween_factory',
              dummy_tween_factory)])

    def test_introspector_decorator(self):
        inst = self._makeOne()
        default = inst.introspector
        self.assertTrue(hasattr(default, 'add'))
        self.assertEqual(inst.introspector, inst.registry.introspector)
        introspector = object()
        inst.introspector = introspector
        new = inst.introspector
        self.assertTrue(new is introspector)
        self.assertEqual(inst.introspector, inst.registry.introspector)
        del inst.introspector
        default = inst.introspector
        self.assertFalse(default is new)
        self.assertTrue(hasattr(default, 'add'))

    def test_make_wsgi_app(self):
        import pyramid.config
        from pyramid.router import Router
        from pyramid.interfaces import IApplicationCreated
        manager = DummyThreadLocalManager()
        config = self._makeOne()
        subscriber = self._registerEventListener(config, IApplicationCreated)
        config.manager = manager
        app = config.make_wsgi_app()
        self.assertEqual(app.__class__, Router)
        self.assertEqual(manager.pushed['registry'], config.registry)
        self.assertEqual(manager.pushed['request'], None)
        self.assertTrue(manager.popped)
        self.assertEqual(pyramid.config.global_registries.last, app.registry)
        self.assertEqual(len(subscriber), 1)
        self.assertTrue(IApplicationCreated.providedBy(subscriber[0]))
        pyramid.config.global_registries.empty()

    def test_include_with_dotted_name(self):
        from pyramid.tests import test_config
        config = self._makeOne()
        config.include('pyramid.tests.test_config.dummy_include')
        after = config.action_state
        actions = after.actions
        self.assertEqual(len(actions), 1)
        action = after.actions[0]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_include_with_python_callable(self):
        from pyramid.tests import test_config
        config = self._makeOne()
        config.include(dummy_include)
        after = config.action_state
        actions = after.actions
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_include_with_module_defaults_to_includeme(self):
        from pyramid.tests import test_config
        config = self._makeOne()
        config.include('pyramid.tests.test_config')
        after = config.action_state
        actions = after.actions
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_include_with_module_defaults_to_includeme_missing(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError, config.include, 'pyramid.tests')

    def test_include_with_route_prefix(self):
        root_config = self._makeOne(autocommit=True)
        def dummy_subapp(config):
            self.assertEqual(config.route_prefix, 'root')
        root_config.include(dummy_subapp, route_prefix='root')

    def test_include_with_nested_route_prefix(self):
        root_config = self._makeOne(autocommit=True, route_prefix='root')
        def dummy_subapp2(config):
            self.assertEqual(config.route_prefix, 'root/nested')
        def dummy_subapp3(config):
            self.assertEqual(config.route_prefix, 'root/nested/nested2')
            config.include(dummy_subapp4)
        def dummy_subapp4(config):
            self.assertEqual(config.route_prefix, 'root/nested/nested2')
        def dummy_subapp(config):
            self.assertEqual(config.route_prefix, 'root/nested')
            config.include(dummy_subapp2)
            config.include(dummy_subapp3, route_prefix='nested2')

        root_config.include(dummy_subapp, route_prefix='nested')

    def test_include_with_missing_source_file(self):
        from pyramid.exceptions import ConfigurationError
        import inspect
        config = self._makeOne()
        class DummyInspect(object):
            def getmodule(self, c):
                return inspect.getmodule(c)
            def getsourcefile(self, c):
                return None
        config.inspect = DummyInspect()
        try:
            config.include('pyramid.tests.test_config.dummy_include')
        except ConfigurationError as e:
            self.assertEqual(
                e.args[0], 
                "No source file for module 'pyramid.tests.test_config' (.py "
                "file must exist, refusing to use orphan .pyc or .pyo file).")
        else: # pragma: no cover
            raise AssertionError

    def test_include_constant_root_package(self):
        from pyramid import tests
        from pyramid.tests import test_config
        config = self._makeOne(root_package=tests)
        results = {}
        def include(config):
            results['package'] = config.package
            results['root_package'] = config.root_package
        config.include(include)
        self.assertEqual(results['root_package'], tests)
        self.assertEqual(results['package'], test_config)

    def test_action_branching_kw_is_None(self):
        config = self._makeOne(autocommit=True)
        self.assertEqual(config.action('discrim'), None)

    def test_action_branching_kw_is_not_None(self):
        config = self._makeOne(autocommit=True)
        self.assertEqual(config.action('discrim', kw={'a':1}), None)

    def test_action_autocommit_with_introspectables(self):
        from pyramid.util import ActionInfo
        config = self._makeOne(autocommit=True)
        intr = DummyIntrospectable()
        config.action('discrim', introspectables=(intr,))
        self.assertEqual(len(intr.registered), 1)
        self.assertEqual(intr.registered[0][0], config.introspector)
        self.assertEqual(intr.registered[0][1].__class__, ActionInfo)

    def test_action_autocommit_with_introspectables_introspection_off(self):
        config = self._makeOne(autocommit=True)
        config.introspection = False
        intr = DummyIntrospectable()
        config.action('discrim', introspectables=(intr,))
        self.assertEqual(len(intr.registered), 0)
        
    def test_action_branching_nonautocommit_with_config_info(self):
        config = self._makeOne(autocommit=False)
        config.info = 'abc'
        state = DummyActionState()
        state.autocommit = False
        config.action_state = state
        config.action('discrim', kw={'a':1})
        self.assertEqual(
            state.actions,
            [((),
             {'args': (),
             'callable': None,
             'discriminator': 'discrim',
             'includepath': (),
             'info': 'abc',
             'introspectables': (),
             'kw': {'a': 1},
             'order': 0})])

    def test_action_branching_nonautocommit_without_config_info(self):
        config = self._makeOne(autocommit=False)
        config.info = ''
        config._ainfo = ['z']
        state = DummyActionState()
        config.action_state = state
        state.autocommit = False
        config.action('discrim', kw={'a':1})
        self.assertEqual(
            state.actions,
            [((),
             {'args': (),
             'callable': None,
             'discriminator': 'discrim',
             'includepath': (),
             'info': 'z',
             'introspectables': (),
             'kw': {'a': 1},
             'order': 0})])

    def test_action_branching_nonautocommit_with_introspectables(self):
        config = self._makeOne(autocommit=False)
        config.info = ''
        config._ainfo = []
        state = DummyActionState()
        config.action_state = state
        state.autocommit = False
        intr = DummyIntrospectable()
        config.action('discrim', introspectables=(intr,))
        self.assertEqual(
            state.actions[0][1]['introspectables'], (intr,))

    def test_action_nonautocommit_with_introspectables_introspection_off(self):
        config = self._makeOne(autocommit=False)
        config.info = ''
        config._ainfo = []
        config.introspection = False
        state = DummyActionState()
        config.action_state = state
        state.autocommit = False
        intr = DummyIntrospectable()
        config.action('discrim', introspectables=(intr,))
        self.assertEqual(
            state.actions[0][1]['introspectables'], ())
        
    def test_scan_integration(self):
        from zope.interface import alsoProvides
        from pyramid.interfaces import IRequest
        from pyramid.view import render_view_to_response
        import pyramid.tests.test_config.pkgs.scannable as package
        config = self._makeOne(autocommit=True)
        config.scan(package)

        ctx = DummyContext()
        req = DummyRequest()
        alsoProvides(req, IRequest)
        req.registry = config.registry

        req.method = 'GET'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked')

        req.method = 'POST'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked_post')

        result= render_view_to_response(ctx, req, 'grokked_class')
        self.assertEqual(result, 'grokked_class')

        result= render_view_to_response(ctx, req, 'grokked_instance')
        self.assertEqual(result, 'grokked_instance')

        result= render_view_to_response(ctx, req, 'oldstyle_grokked_class')
        self.assertEqual(result, 'oldstyle_grokked_class')

        req.method = 'GET'
        result = render_view_to_response(ctx, req, 'another')
        self.assertEqual(result, 'another_grokked')

        req.method = 'POST'
        result = render_view_to_response(ctx, req, 'another')
        self.assertEqual(result, 'another_grokked_post')

        result= render_view_to_response(ctx, req, 'another_grokked_class')
        self.assertEqual(result, 'another_grokked_class')

        result= render_view_to_response(ctx, req, 'another_grokked_instance')
        self.assertEqual(result, 'another_grokked_instance')

        result= render_view_to_response(ctx, req,
                                        'another_oldstyle_grokked_class')
        self.assertEqual(result, 'another_oldstyle_grokked_class')

        result = render_view_to_response(ctx, req, 'stacked1')
        self.assertEqual(result, 'stacked')

        result = render_view_to_response(ctx, req, 'stacked2')
        self.assertEqual(result, 'stacked')

        result = render_view_to_response(ctx, req, 'another_stacked1')
        self.assertEqual(result, 'another_stacked')

        result = render_view_to_response(ctx, req, 'another_stacked2')
        self.assertEqual(result, 'another_stacked')

        result = render_view_to_response(ctx, req, 'stacked_class1')
        self.assertEqual(result, 'stacked_class')

        result = render_view_to_response(ctx, req, 'stacked_class2')
        self.assertEqual(result, 'stacked_class')

        result = render_view_to_response(ctx, req, 'another_stacked_class1')
        self.assertEqual(result, 'another_stacked_class')

        result = render_view_to_response(ctx, req, 'another_stacked_class2')
        self.assertEqual(result, 'another_stacked_class')

        # NB: on Jython, a class without an __init__ apparently accepts
        # any number of arguments without raising a TypeError, so the next
        # assertion may fail there.  We don't support Jython at the moment,
        # this is just a note to a future self.

        self.assertRaises(TypeError,
                          render_view_to_response, ctx, req, 'basemethod')

        result = render_view_to_response(ctx, req, 'method1')
        self.assertEqual(result, 'method1')

        result = render_view_to_response(ctx, req, 'method2')
        self.assertEqual(result, 'method2')

        result = render_view_to_response(ctx, req, 'stacked_method1')
        self.assertEqual(result, 'stacked_method')

        result = render_view_to_response(ctx, req, 'stacked_method2')
        self.assertEqual(result, 'stacked_method')

        result = render_view_to_response(ctx, req, 'subpackage_init')
        self.assertEqual(result, 'subpackage_init')

        result = render_view_to_response(ctx, req, 'subpackage_notinit')
        self.assertEqual(result, 'subpackage_notinit')

        result = render_view_to_response(ctx, req, 'subsubpackage_init')
        self.assertEqual(result, 'subsubpackage_init')

        result = render_view_to_response(ctx, req, 'pod_notinit')
        self.assertEqual(result, None)

    def test_scan_integration_with_ignore(self):
        from zope.interface import alsoProvides
        from pyramid.interfaces import IRequest
        from pyramid.view import render_view_to_response
        import pyramid.tests.test_config.pkgs.scannable as package
        config = self._makeOne(autocommit=True)
        config.scan(package, 
                    ignore='pyramid.tests.test_config.pkgs.scannable.another')

        ctx = DummyContext()
        req = DummyRequest()
        alsoProvides(req, IRequest)
        req.registry = config.registry

        req.method = 'GET'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked')

        # ignored
        v = render_view_to_response(ctx, req, 'another_stacked_class2')
        self.assertEqual(v, None)
        
    def test_scan_integration_dottedname_package(self):
        from zope.interface import alsoProvides
        from pyramid.interfaces import IRequest
        from pyramid.view import render_view_to_response
        config = self._makeOne(autocommit=True)
        config.scan('pyramid.tests.test_config.pkgs.scannable')

        ctx = DummyContext()
        req = DummyRequest()
        alsoProvides(req, IRequest)
        req.registry = config.registry

        req.method = 'GET'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked')

    def test_scan_integration_with_extra_kw(self):
        config = self._makeOne(autocommit=True)
        config.scan('pyramid.tests.test_config.pkgs.scanextrakw', a=1)
        self.assertEqual(config.a, 1)

    def test_scan_integration_with_onerror(self):
        # fancy sys.path manipulation here to appease "setup.py test" which
        # fails miserably when it can't import something in the package
        import sys
        try:
            here = os.path.dirname(__file__)
            path = os.path.join(here, 'path')
            sys.path.append(path)
            config = self._makeOne(autocommit=True)
            class FooException(Exception):
                pass
            def onerror(name):
                raise FooException
            self.assertRaises(FooException, config.scan, 'scanerror',
                              onerror=onerror)
        finally:
            sys.path.remove(path)

    def test_scan_integration_conflict(self):
        from pyramid.tests.test_config.pkgs import selfscan
        from pyramid.config import Configurator
        c = Configurator()
        c.scan(selfscan)
        c.scan(selfscan)
        try:
            c.commit()
        except ConfigurationConflictError as why:
            def scanconflicts(e):
                conflicts = e._conflicts.values()
                for conflict in conflicts:
                    for confinst in conflict:
                        yield confinst.src
            which = list(scanconflicts(why))
            self.assertEqual(len(which), 4)
            self.assertTrue("@view_config(renderer='string')" in which)
            self.assertTrue("@view_config(name='two', renderer='string')" in
                            which)

    @skip_on('py3')
    def test_hook_zca(self):
        from zope.component import getSiteManager
        def foo():
            '123'
        try:
            config = self._makeOne()
            config.hook_zca()
            config.begin()
            sm = getSiteManager()
            self.assertEqual(sm, config.registry)
        finally:
            getSiteManager.reset()

    @skip_on('py3')
    def test_unhook_zca(self):
        from zope.component import getSiteManager
        def foo():
            '123'
        try:
            getSiteManager.sethook(foo)
            config = self._makeOne()
            config.unhook_zca()
            sm = getSiteManager()
            self.assertNotEqual(sm, '123')
        finally:
            getSiteManager.reset()

    def test_commit_conflict_simple(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.add_view(view1)
        config.add_view(view2)
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_commit_conflict_resolved_with_include(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        def includeme(config):
            config.add_view(view2)
        config.add_view(view1)
        config.include(includeme)
        config.commit()
        registeredview = self._getViewCallable(config)
        self.assertEqual(registeredview.__name__, 'view1')

    def test_commit_conflict_with_two_includes(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        def includeme1(config):
            config.add_view(view1)
        def includeme2(config):
            config.add_view(view2)
        config.include(includeme1)
        config.include(includeme2)
        try:
            config.commit()
        except ConfigurationConflictError as why:
            c1, c2 = _conflictFunctions(why)
            self.assertEqual(c1, 'includeme1')
            self.assertEqual(c2, 'includeme2')
        else: #pragma: no cover
            raise AssertionError

    def test_commit_conflict_resolved_with_two_includes_and_local(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        def view3(request): pass
        def includeme1(config):
            config.add_view(view1)
        def includeme2(config):
            config.add_view(view2)
        config.include(includeme1)
        config.include(includeme2)
        config.add_view(view3)
        config.commit()
        registeredview = self._getViewCallable(config)
        self.assertEqual(registeredview.__name__, 'view3')

    def test_autocommit_no_conflicts(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        def view1(request): pass
        def view2(request): pass
        def view3(request): pass
        config.add_view(view1, renderer=null_renderer)
        config.add_view(view2, renderer=null_renderer)
        config.add_view(view3, renderer=null_renderer)
        config.commit()
        registeredview = self._getViewCallable(config)
        self.assertEqual(registeredview.__name__, 'view3')

    def test_conflict_set_notfound_view(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.set_notfound_view(view1)
        config.set_notfound_view(view2)
        try:
            config.commit()
        except ConfigurationConflictError as why:
            c1, c2 = _conflictFunctions(why)
            self.assertEqual(c1, 'test_conflict_set_notfound_view')
            self.assertEqual(c2, 'test_conflict_set_notfound_view')
        else: # pragma: no cover
            raise AssertionError

    def test_conflict_set_forbidden_view(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.set_forbidden_view(view1)
        config.set_forbidden_view(view2)
        try:
            config.commit()
        except ConfigurationConflictError as why:
            c1, c2 = _conflictFunctions(why)
            self.assertEqual(c1, 'test_conflict_set_forbidden_view')
            self.assertEqual(c2, 'test_conflict_set_forbidden_view')
        else: # pragma: no cover
            raise AssertionError

    def test___getattr__missing_when_directives_exist(self):
        config = self._makeOne()
        directives = {}
        config.registry._directives = directives
        self.assertRaises(AttributeError, config.__getattr__, 'wontexist')

    def test___getattr__missing_when_directives_dont_exist(self):
        config = self._makeOne()
        self.assertRaises(AttributeError, config.__getattr__, 'wontexist')

    def test___getattr__matches(self):
        config = self._makeOne()
        def foo(config): pass
        directives = {'foo':(foo, True)}
        config.registry._directives = directives
        foo_meth = config.foo
        self.assertTrue(getattr(foo_meth, im_func).__docobj__ is foo)

    def test___getattr__matches_no_action_wrap(self):
        config = self._makeOne()
        def foo(config): pass
        directives = {'foo':(foo, False)}
        config.registry._directives = directives
        foo_meth = config.foo
        self.assertTrue(getattr(foo_meth, im_func) is foo)

class TestConfigurator_add_directive(unittest.TestCase):

    def setUp(self):
        from pyramid.config import Configurator
        self.config = Configurator()

    def test_extend_with_dotted_name(self):
        from pyramid.tests import test_config
        config = self.config
        config.add_directive(
            'dummy_extend', 'pyramid.tests.test_config.dummy_extend')
        self.assertTrue(hasattr(config, 'dummy_extend'))
        config.dummy_extend('discrim')
        after = config.action_state
        action = after.actions[-1]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_add_directive_with_partial(self):
        from pyramid.tests import test_config
        config = self.config
        config.add_directive(
                'dummy_partial', 'pyramid.tests.test_config.dummy_partial')
        self.assertTrue(hasattr(config, 'dummy_partial'))
        config.dummy_partial()
        after = config.action_state
        action = after.actions[-1]
        self.assertEqual(action['discriminator'], 'partial')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_add_directive_with_custom_callable(self):
        from pyramid.tests import test_config
        config = self.config
        config.add_directive(
                'dummy_callable', 'pyramid.tests.test_config.dummy_callable')
        self.assertTrue(hasattr(config, 'dummy_callable'))
        config.dummy_callable('discrim')
        after = config.action_state
        action = after.actions[-1]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_extend_with_python_callable(self):
        from pyramid.tests import test_config
        config = self.config
        config.add_directive(
            'dummy_extend', dummy_extend)
        self.assertTrue(hasattr(config, 'dummy_extend'))
        config.dummy_extend('discrim')
        after = config.action_state
        action = after.actions[-1]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], test_config)

    def test_extend_same_name_doesnt_conflict(self):
        config = self.config
        config.add_directive(
            'dummy_extend', dummy_extend)
        config.add_directive(
            'dummy_extend', dummy_extend2)
        self.assertTrue(hasattr(config, 'dummy_extend'))
        config.dummy_extend('discrim')
        after = config.action_state
        action = after.actions[-1]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], config.registry)

    def test_extend_action_method_successful(self):
        config = self.config
        config.add_directive(
            'dummy_extend', dummy_extend)
        config.dummy_extend('discrim')
        config.dummy_extend('discrim')
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_directive_persists_across_configurator_creations(self):
        config = self.config
        config.add_directive('dummy_extend', dummy_extend)
        config2 = config.with_package('pyramid.tests')
        config2.dummy_extend('discrim')
        after = config2.action_state
        actions = after.actions
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action['discriminator'], 'discrim')
        self.assertEqual(action['callable'], None)
        self.assertEqual(action['args'], config2.package)

class TestConfigurator__add_predicate(unittest.TestCase):
    def _makeOne(self):
        from pyramid.config import Configurator
        return Configurator()

    def test_factory_as_object(self):
        config = self._makeOne()

        def _fakeAction(discriminator, callable=None, args=(), kw=None,
                        order=0, introspectables=(), **extra):
            self.assertEqual(len(introspectables), 1)
            self.assertEqual(introspectables[0]['name'], 'testing')
            self.assertEqual(introspectables[0]['factory'], DummyPredicate)

        config.action = _fakeAction
        config._add_predicate('route', 'testing', DummyPredicate)

    def test_factory_as_dotted_name(self):
        config = self._makeOne()

        def _fakeAction(discriminator, callable=None, args=(),
                        kw=None, order=0, introspectables=(), **extra):
            self.assertEqual(len(introspectables), 1)
            self.assertEqual(introspectables[0]['name'], 'testing')
            self.assertEqual(introspectables[0]['factory'], DummyPredicate)

        config.action = _fakeAction
        config._add_predicate(
            'route',
            'testing',
            'pyramid.tests.test_config.test_init.DummyPredicate'
            )
        
class TestActionState(unittest.TestCase):
    def _makeOne(self):
        from pyramid.config import ActionState
        return ActionState()
    
    def test_it(self):
        c = self._makeOne()
        self.assertEqual(c.actions, [])

    def test_action_simple(self):
        from pyramid.tests.test_config import dummyfactory as f
        c = self._makeOne()
        c.actions = []
        c.action(1, f, (1,), {'x':1})
        self.assertEqual(
            c.actions,
            [{'args': (1,),
             'callable': f,
             'discriminator': 1,
             'includepath': (),
             'info': None,
             'introspectables': (),
             'kw': {'x': 1},
             'order': 0}])
        c.action(None)
        self.assertEqual(
            c.actions,
            [{'args': (1,),
             'callable': f,
             'discriminator': 1,
             'includepath': (),
             'info': None,
             'introspectables': (),
             'kw': {'x': 1},
             'order': 0},

             {'args': (),
             'callable': None,
             'discriminator': None,
             'includepath': (),
             'info': None,
             'introspectables': (),
             'kw': {},
             'order': 0},])

    def test_action_with_includepath(self):
        c = self._makeOne()
        c.actions = []
        c.action(None, includepath=('abc',))
        self.assertEqual(
            c.actions,
            [{'args': (),
             'callable': None,
             'discriminator': None,
             'includepath': ('abc',),
             'info': None,
             'introspectables': (),
             'kw': {},
             'order': 0}])

    def test_action_with_info(self):
        c = self._makeOne()
        c.action(None, info='abc')
        self.assertEqual(
            c.actions,
            [{'args': (),
             'callable': None,
             'discriminator': None,
             'includepath': (),
             'info': 'abc',
             'introspectables': (),
             'kw': {},
             'order': 0}])

    def test_action_with_includepath_and_info(self):
        c = self._makeOne()
        c.action(None, includepath=('spec',), info='bleh')
        self.assertEqual(
            c.actions,
            [{'args': (),
             'callable': None,
             'discriminator': None,
             'includepath': ('spec',),
             'info': 'bleh',
             'introspectables': (),
             'kw': {},
             'order': 0}])

    def test_action_with_order(self):
        c = self._makeOne()
        c.actions = []
        c.action(None, order=99999)
        self.assertEqual(
            c.actions,
            [{'args': (),
             'callable': None,
             'discriminator': None,
             'includepath': (),
             'info': None,
             'introspectables': (),
             'kw': {},
             'order': 99999}])

    def test_action_with_introspectables(self):
        c = self._makeOne()
        c.actions = []
        intr = DummyIntrospectable()
        c.action(None, introspectables=(intr,))
        self.assertEqual(
            c.actions,
            [{'args': (),
             'callable': None,
             'discriminator': None,
             'includepath': (),
             'info': None,
             'introspectables': (intr,),
             'kw': {},
             'order': 0}])

    def test_processSpec(self):
        c = self._makeOne()
        self.assertTrue(c.processSpec('spec'))
        self.assertFalse(c.processSpec('spec'))

    def test_execute_actions_tuples(self):
        output = []
        def f(*a, **k):
            output.append((a, k))
        c = self._makeOne()
        c.actions = [
            (1, f, (1,)),
            (1, f, (11,), {}, ('x', )),
            (2, f, (2,)),
            (None, None),
            ]
        c.execute_actions()
        self.assertEqual(output,  [((1,), {}), ((2,), {})])

    def test_execute_actions_dicts(self):
        output = []
        def f(*a, **k):
            output.append((a, k))
        c = self._makeOne()
        c.actions = [
            {'discriminator':1, 'callable':f, 'args':(1,), 'kw':{},
             'order':0, 'includepath':(), 'info':None,
             'introspectables':()},
            {'discriminator':1, 'callable':f, 'args':(11,), 'kw':{},
             'includepath':('x',), 'order': 0, 'info':None,
             'introspectables':()},
            {'discriminator':2, 'callable':f, 'args':(2,), 'kw':{},
             'order':0, 'includepath':(), 'info':None,
             'introspectables':()},
            {'discriminator':None, 'callable':None, 'args':(), 'kw':{},
             'order':0, 'includepath':(), 'info':None,
             'introspectables':()},
            ]
        c.execute_actions()
        self.assertEqual(output,  [((1,), {}), ((2,), {})])

    def test_execute_actions_with_introspectables(self):
        output = []
        def f(*a, **k):
            output.append((a, k))
        c = self._makeOne()
        intr = DummyIntrospectable()
        c.actions = [
            {'discriminator':1, 'callable':f, 'args':(1,), 'kw':{},
             'order':0, 'includepath':(), 'info':None,
             'introspectables':(intr,)},
            ]
        introspector = object()
        c.execute_actions(introspector=introspector)
        self.assertEqual(output,  [((1,), {})])
        self.assertEqual(intr.registered, [(introspector, None)])

    def test_execute_actions_with_introspectable_no_callable(self):
        c = self._makeOne()
        intr = DummyIntrospectable()
        c.actions = [
            {'discriminator':1, 'callable':None, 'args':(1,), 'kw':{},
             'order':0, 'includepath':(), 'info':None,
             'introspectables':(intr,)},
            ]
        introspector = object()
        c.execute_actions(introspector=introspector)
        self.assertEqual(intr.registered, [(introspector, None)])

    def test_execute_actions_error(self):
        output = []
        def f(*a, **k):
            output.append(('f', a, k))
        def bad():
            raise NotImplementedError
        c = self._makeOne()
        c.actions = [
            (1, f, (1,)),
            (1, f, (11,), {}, ('x', )),
            (2, f, (2,)),
            (3, bad, (), {}, (), 'oops')
            ]
        self.assertRaises(ConfigurationExecutionError, c.execute_actions)
        self.assertEqual(output, [('f', (1,), {}), ('f', (2,), {})])

    def test_reentrant_action(self):
        output = []
        c = self._makeOne()
        def f(*a, **k):
            output.append(('f', a, k))
            c.actions.append((3, g, (8,), {}))
        def g(*a, **k):
            output.append(('g', a, k))
        c.actions = [
            (1, f, (1,)),
        ]
        c.execute_actions()
        self.assertEqual(output, [('f', (1,), {}), ('g', (8,), {})])

    def test_reentrant_action_error(self):
        from pyramid.exceptions import ConfigurationError
        c = self._makeOne()
        def f(*a, **k):
            c.actions.append((3, g, (8,), {}, (), None, -1))
        def g(*a, **k): pass
        c.actions = [
            (1, f, (1,)),
        ]
        self.assertRaises(ConfigurationError, c.execute_actions)

    def test_reentrant_action_without_clear(self):
        c = self._makeOne()
        def f(*a, **k):
            c.actions.append((3, g, (8,)))
        def g(*a, **k): pass
        c.actions = [
            (1, f, (1,)),
        ]
        c.execute_actions(clear=False)
        self.assertEqual(c.actions, [
            (1, f, (1,)),
            (3, g, (8,)),
        ])

class Test_reentrant_action_functional(unittest.TestCase):
    def _makeConfigurator(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_functional(self):
        def add_auto_route(config, name, view):
               def register():
                   config.add_view(route_name=name, view=view)
                   config.add_route(name, '/' + name)
               config.action(
                   ('auto route', name), register, order=-30
                   )
        config = self._makeConfigurator()
        config.add_directive('add_auto_route', add_auto_route)
        def my_view(request): return request.response
        config.add_auto_route('foo', my_view)
        config.commit()
        from pyramid.interfaces import IRoutesMapper
        mapper = config.registry.getUtility(IRoutesMapper)
        routes = mapper.get_routes()
        route = routes[0]
        self.assertEqual(len(routes), 1)
        self.assertEqual(route.name, 'foo')
        self.assertEqual(route.path, '/foo')


class Test_resolveConflicts(unittest.TestCase):
    def _callFUT(self, actions):
        from pyramid.config import resolveConflicts
        return resolveConflicts(actions)

    def test_it_success_tuples(self):
        from pyramid.tests.test_config import dummyfactory as f
        result = self._callFUT([
            (None, f),
            (1, f, (1,), {}, (), 'first'),
            (1, f, (2,), {}, ('x',), 'second'),
            (1, f, (3,), {}, ('y',), 'third'),
            (4, f, (4,), {}, ('y',), 'should be last', 99999),
            (3, f, (3,), {}, ('y',)),
            (None, f, (5,), {}, ('y',)),
            ])
        result = list(result)
        self.assertEqual(
            result,
            [{'info': None,
              'args': (),
              'callable': f,
              'introspectables': (),
              'kw': {},
              'discriminator': None,
              'includepath': (),
              'order': 0},

              {'info': 'first',
               'args': (1,),
               'callable': f,
               'introspectables': (),
               'kw': {},
               'discriminator': 1,
               'includepath': (),
               'order': 0},

               {'info': None,
                'args': (3,),
                'callable': f,
                'introspectables': (),
                'kw': {},
                'discriminator': 3,
                'includepath': ('y',),
                'order': 0},

                {'info': None,
                 'args': (5,),
                 'callable': f,
                 'introspectables': (),
                 'kw': {},
                 'discriminator': None,
                 'includepath': ('y',),
                 'order': 0},

                 {'info': 'should be last',
                  'args': (4,),
                  'callable': f,
                  'introspectables': (),
                  'kw': {},
                  'discriminator': 4,
                  'includepath': ('y',),
                  'order': 99999}
                  ]
                  )

    def test_it_success_dicts(self):
        from pyramid.tests.test_config import dummyfactory as f
        from pyramid.config import expand_action
        result = self._callFUT([
            expand_action(None, f),
            expand_action(1, f, (1,), {}, (), 'first'),
            expand_action(1, f, (2,), {}, ('x',), 'second'),
            expand_action(1, f, (3,), {}, ('y',), 'third'),
            expand_action(4, f, (4,), {}, ('y',), 'should be last', 99999),
            expand_action(3, f, (3,), {}, ('y',)),
            expand_action(None, f, (5,), {}, ('y',)),
            ])
        result = list(result)
        self.assertEqual(
            result,
            [{'info': None,
              'args': (),
              'callable': f,
              'introspectables': (),
              'kw': {},
              'discriminator': None,
              'includepath': (),
              'order': 0},

              {'info': 'first',
               'args': (1,),
               'callable': f,
               'introspectables': (),
               'kw': {},
               'discriminator': 1,
               'includepath': (),
               'order': 0},

               {'info': None,
                'args': (3,),
                'callable': f,
                'introspectables': (),
                'kw': {},
                'discriminator': 3,
                'includepath': ('y',),
                'order': 0},

                {'info': None,
                 'args': (5,),
                 'callable': f,
                 'introspectables': (),
                 'kw': {},
                 'discriminator': None,
                 'includepath': ('y',),
                 'order': 0},

                 {'info': 'should be last',
                  'args': (4,),
                  'callable': f,
                  'introspectables': (),
                  'kw': {},
                  'discriminator': 4,
                  'includepath': ('y',),
                  'order': 99999}
                  ]
                  )

    def test_it_conflict(self):
        from pyramid.tests.test_config import dummyfactory as f
        result = self._callFUT([
            (None, f),
            (1, f, (2,), {}, ('x',), 'eek'),     # will conflict
            (1, f, (3,), {}, ('y',), 'ack'),     # will conflict
            (4, f, (4,), {}, ('y',)),
            (3, f, (3,), {}, ('y',)),
            (None, f, (5,), {}, ('y',)),
            ])
        self.assertRaises(ConfigurationConflictError, list, result)

    def test_it_with_actions_grouped_by_order(self):
        from pyramid.tests.test_config import dummyfactory as f
        from pyramid.config import expand_action
        result = self._callFUT([
            expand_action(None, f),                                 # X
            expand_action(1, f, (1,), {}, (), 'third', 10),         # X
            expand_action(1, f, (2,), {}, ('x',), 'fourth', 10),
            expand_action(1, f, (3,), {}, ('y',), 'fifth', 10),
            expand_action(2, f, (1,), {}, (), 'sixth', 10),         # X
            expand_action(3, f, (1,), {}, (), 'seventh', 10),       # X
            expand_action(5, f, (4,), {}, ('y',), 'eighth', 99999), # X
            expand_action(4, f, (3,), {}, (), 'first', 5),          # X
            expand_action(4, f, (5,), {}, ('y',), 'second', 5),
            ])
        result = list(result)
        self.assertEqual(len(result), 6)
        # resolved actions should be grouped by (order, i)
        self.assertEqual(
            result,
            [{'info': None,
              'args': (),
              'callable': f,
              'introspectables': (),
              'kw': {},
              'discriminator': None,
              'includepath': (),
              'order': 0},

              {'info': 'first',
               'args': (3,),
               'callable': f,
               'introspectables': (),
               'kw': {},
               'discriminator': 4,
               'includepath': (),
               'order': 5},

               {'info': 'third',
                'args': (1,),
                'callable': f,
                'introspectables': (),
                'kw': {},
                'discriminator': 1,
                'includepath': (),
                'order': 10},

               {'info': 'sixth',
                'args': (1,),
                'callable': f,
                'introspectables': (),
                'kw': {},
                'discriminator': 2,
                'includepath': (),
                'order': 10},

               {'info': 'seventh',
                'args': (1,),
                'callable': f,
                'introspectables': (),
                'kw': {},
                'discriminator': 3,
                'includepath': (),
                'order': 10},

                 {'info': 'eighth',
                  'args': (4,),
                  'callable': f,
                  'introspectables': (),
                  'kw': {},
                  'discriminator': 5,
                  'includepath': ('y',),
                  'order': 99999}
                  ]
                  )
        

class TestGlobalRegistriesIntegration(unittest.TestCase):
    def setUp(self):
        from pyramid.config import global_registries
        global_registries.empty()

    tearDown = setUp

    def _makeConfigurator(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_global_registries_empty(self):
        from pyramid.config import global_registries
        self.assertEqual(global_registries.last, None)

    def test_global_registries(self):
        from pyramid.config import global_registries
        config1 = self._makeConfigurator()
        config1.make_wsgi_app()
        self.assertEqual(global_registries.last, config1.registry)
        config2 = self._makeConfigurator()
        config2.make_wsgi_app()
        self.assertEqual(global_registries.last, config2.registry)
        self.assertEqual(list(global_registries),
                         [config1.registry, config2.registry])
        global_registries.remove(config2.registry)
        self.assertEqual(global_registries.last, config1.registry)

class DummyRequest:
    subpath = ()
    matchdict = None
    request_iface = IRequest
    def __init__(self, environ=None):
        if environ is None:
            environ = {}
        self.environ = environ
        self.params = {}
        self.cookies = {}

class DummyThreadLocalManager(object):
    pushed = None
    popped = False
    def push(self, d):
        self.pushed = d
    def pop(self):
        self.popped = True

from zope.interface import implementer
@implementer(IDummy)
class DummyEvent:
    pass

class DummyRegistry(object):
    def __init__(self, adaptation=None, util=None):
        self.utilities = []
        self.adapters = []
        self.adaptation = adaptation
        self.util = util
    def subscribers(self, events, name):
        self.events = events
        return events
    def registerUtility(self, *arg, **kw):
        self.utilities.append((arg, kw))
    def registerAdapter(self, *arg, **kw):
        self.adapters.append((arg, kw))
    def queryAdapter(self, *arg, **kw):
        return self.adaptation
    def queryUtility(self, *arg, **kw):
        return self.util

from zope.interface import Interface
class IOther(Interface):
    pass

def _conflictFunctions(e):
    conflicts = e._conflicts.values()
    for conflict in conflicts:
        for confinst in conflict:
            yield confinst.function

class DummyActionState(object):
    autocommit = False
    info = ''
    def __init__(self):
        self.actions = []
    def action(self, *arg, **kw):
        self.actions.append((arg, kw))

class DummyIntrospectable(object):
    def __init__(self):
        self.registered = []
    def register(self, introspector, action_info):
        self.registered.append((introspector, action_info))
        
class DummyPredicate(object):
    pass
