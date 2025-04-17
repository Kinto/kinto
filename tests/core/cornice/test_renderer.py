from unittest import TestCase, mock

from pyramid.renderers import JSON

from kinto.core.cornice import CorniceRenderer
from kinto.core.cornice.renderer import JSONError


class TestRenderer(TestCase):
    def test_renderer_is_pyramid_renderer_subclass(self):
        self.assertIsInstance(CorniceRenderer(), JSON)

    def test_renderer_calls_render_method(self):
        renderer = CorniceRenderer()
        self.assertEqual(renderer(info=None), renderer.render)

    def test_renderer_render_errors(self):
        renderer = CorniceRenderer()
        request = mock.MagicMock()

        class FakeErrors(object):
            status = 418

            def __json__(self, request):
                return ["error_1", "error_2"]

        request.errors = FakeErrors()

        result = renderer.render_errors(request)
        self.assertIsInstance(result, JSONError)
        self.assertEqual(result.status_int, 418)
        self.assertEqual(result.json_body, {"status": "error", "errors": ["error_1", "error_2"]})
