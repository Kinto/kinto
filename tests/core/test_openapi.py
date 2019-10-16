import unittest
from unittest import mock

from cornice.service import get_services

from kinto.core.openapi import OpenAPI

from .support import BaseWebTest


class OpenAPITest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(OpenAPITest, self).setUp()
        self.request = mock.MagicMock()
        self.request.registry.settings = self.get_app_settings()
        self.generator = OpenAPI(get_services(), self.request)
        self.api_doc = self.generator.generate()

    def test_assign_base_path(self):
        self.assertEqual(self.api_doc["basePath"], "/{}".format(self.api_prefix))

    def test_default_security_generator(self):
        self.assertEqual(self.api_doc["paths"]["/"]["get"]["security"], [])
        self.assertEqual(
            self.api_doc["paths"]["/mushrooms"]["get"]["security"], [{"basicauth": []}]
        )

    def test_security_extensions(self):
        method = {
            "type": "oauth2",
            "authorizationUrl": "https://oauth-stable.dev.lcip.org/v1",
            "flow": "implicit",
            "scopes": {"kinto": "Kinto user scope."},
        }

        self.generator.expose_authentication_method("fxa", method)
        api_doc = self.generator.generate()

        self.assertEqual(api_doc["securityDefinitions"]["fxa"], method)
        self.assertCountEqual(
            api_doc["paths"]["/mushrooms"]["get"]["security"],
            [{"basicauth": []}, {"fxa": ["kinto"]}],
        )

    def test_default_tags(self):
        self.assertEqual(self.api_doc["paths"]["/mushrooms"]["get"]["tags"], ["Mushrooms"])
        self.assertEqual(self.api_doc["paths"]["/mushrooms/{id}"]["get"]["tags"], ["Mushrooms"])

    def test_default_operation_ids(self):
        self.assertEqual(
            self.api_doc["paths"]["/mushrooms"]["get"]["operationId"], "get_mushrooms"
        )
        self.assertEqual(
            self.api_doc["paths"]["/mushrooms/{id}"]["get"]["operationId"], "get_mushroom"
        )
