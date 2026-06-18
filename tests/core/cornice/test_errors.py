from unittest import TestCase

from pyramid.i18n import TranslationString

from kinto.core.cornice.errors import Errors
from kinto.core.cornice.service import Service


class TestErrorsHelper(TestCase):
    def setUp(self):
        self.errors = Errors()

    def test_add_to_supported_location(self):
        self.errors.add("")
        self.errors.add("body", description="!")
        self.errors.add("querystring", name="field")
        self.errors.add("url")
        self.errors.add("header")
        self.errors.add("path")
        self.errors.add("cookies")
        self.errors.add("method")
        self.assertEqual(len(self.errors), 8)

    def test_raises_an_exception_when_location_is_unsupported(self):
        with self.assertRaises(ValueError):
            self.errors.add("something")


service1 = Service(name="service1", path="/error-service1")


@service1.get()
def get1(request):
    return request.errors.add("body", "field", "Description")


service2 = Service(name="service2", path="/error-service2")


@service2.get()
def get2(request):
    return request.errors.add("body", "field", TranslationString("Description"))
