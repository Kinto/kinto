import unittest

class TestRenderingConfiguratorMixin(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_add_default_renderers(self):
        from pyramid.config.rendering import DEFAULT_RENDERERS
        from pyramid.interfaces import IRendererFactory
        config = self._makeOne(autocommit=True)
        config.add_default_renderers()
        for name, impl in DEFAULT_RENDERERS:
            self.assertTrue(
                config.registry.queryUtility(IRendererFactory, name) is not None
                )

    def test_add_renderer(self):
        from pyramid.interfaces import IRendererFactory
        config = self._makeOne(autocommit=True)
        renderer = object()
        config.add_renderer('name', renderer)
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'name'),
                         renderer)

    def test_add_renderer_dottedname_factory(self):
        from pyramid.interfaces import IRendererFactory
        config = self._makeOne(autocommit=True)
        import pyramid.tests.test_config
        config.add_renderer('name', 'pyramid.tests.test_config')
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'name'),
                         pyramid.tests.test_config)

