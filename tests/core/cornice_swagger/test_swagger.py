import unittest

from flex.core import validate

from kinto.core.cornice.service import Service
from kinto.core.cornice.validators import colander_validator
from kinto.core.cornice_swagger.swagger import CorniceSwagger, CorniceSwaggerException

from .support import GetRequestSchema, PutRequestSchema, response_schemas


class CorniceSwaggerGeneratorTest(unittest.TestCase):
    def setUp(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(
                validators=(colander_validator,),
                schema=GetRequestSchema(),
                response_schemas=response_schemas,
            )
            def view_get(self, request):
                """Serve ice cream"""
                return self.request.validated

            @service.put(validators=(colander_validator,), schema=PutRequestSchema())
            def view_put(self, request):
                """Add flavour"""
                return self.request.validated

        self.service = service
        CorniceSwagger.services = [self.service]
        CorniceSwagger.api_title = "IceCreamAPI"
        CorniceSwagger.api_version = "4.2"
        self.swagger = CorniceSwagger()
        self.spec = self.swagger.generate()
        validate(self.spec)

    def test_path(self):
        self.assertIn("/icecream/{flavour}", self.spec["paths"])

    def test_path_methods(self):
        path = self.spec["paths"]["/icecream/{flavour}"]
        self.assertIn("get", path)
        self.assertIn("put", path)

    def test_path_parameters(self):
        parameters = self.spec["paths"]["/icecream/{flavour}"]["parameters"]
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0]["name"], "flavour")

    def test_summary_docstrings(self):
        self.swagger.summary_docstrings = True
        self.spec = self.swagger.generate()
        validate(self.spec)
        summary = self.spec["paths"]["/icecream/{flavour}"]["get"]["summary"]
        self.assertEqual(summary, "Serve ice cream")

    def test_summary_docstrings_with_klass(self):
        class TemperatureCooler(object):
            def put_view(self):
                """Put it."""
                pass

        service = Service("TemperatureCooler", "/freshair", klass=TemperatureCooler)
        service.add_view("put", "put_view")
        CorniceSwagger.services = [service]
        self.swagger = CorniceSwagger()
        self.spec = self.swagger.generate()
        validate(self.spec)

    def test_with_schema_ref(self):
        swagger = CorniceSwagger([self.service], def_ref_depth=1)
        spec = swagger.generate()
        validate(spec)
        self.assertIn("definitions", spec)

    def test_with_param_ref(self):
        swagger = CorniceSwagger([self.service], param_ref=True)
        spec = swagger.generate()
        validate(spec)
        self.assertIn("parameters", spec)

    def test_with_resp_ref(self):
        swagger = CorniceSwagger([self.service], resp_ref=True)
        spec = swagger.generate()
        validate(spec)
        self.assertIn("responses", spec)

    def test_swagger_field_updates_extracted_paths(self):
        self.swagger.swagger = {"definitions": {"OtherDef": {"additionalProperties": {}}}}
        spec = self.swagger.generate()
        validate(spec)
        self.assertEqual(spec["definitions"], self.swagger.swagger["definitions"])


class ExtractContentTypesTest(unittest.TestCase):
    def test_default_renderer(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(
            spec["paths"]["/icecream/{flavour}"]["get"]["produces"], ["application/json"]
        )

    def test_json_renderer(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(renderer="json")
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(
            spec["paths"]["/icecream/{flavour}"]["get"]["produces"], ["application/json"]
        )

    def test_xml_renderer(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(renderer="xml")
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(spec["paths"]["/icecream/{flavour}"]["get"]["produces"], ["text/xml"])

    def test_unkown_renderer(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(renderer="")
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertNotIn("produces", spec["paths"]["/icecream/{flavour}"]["get"])

    def test_single_ctype(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.put(content_type="application/json")
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(
            spec["paths"]["/icecream/{flavour}"]["put"]["consumes"], ["application/json"]
        )

    def test_no_ctype_no_list_with_none(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.put()
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertNotIn("consumes", spec["paths"]["/icecream/{flavour}"]["put"])

    def test_multiple_ctypes(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.put(content_type=("application/json", "text/xml"))
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(
            spec["paths"]["/icecream/{flavour}"]["put"]["consumes"],
            ["application/json", "text/xml"],
        )

    def test_single_ctype_callable(self):
        service = Service("IceCream", "/icecream/{flavour}")

        def my_ctype_callable(request):
            return "application/octet-stream"

        class IceCream(object):
            @service.put(content_type=my_ctype_callable)
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(spec["paths"]["/icecream/{flavour}"]["put"]["consumes"], [])

    def test_mixed_ctype_string_and_callable(self):
        service = Service("IceCream", "/icecream/{flavour}")

        def my_ctype_callable(request):
            return "application/octet-stream"

        def my_ctype_callable_2(request):
            return "image/png"

        class IceCream(object):
            @service.put(
                content_type=(
                    my_ctype_callable,
                    "application/json",
                    my_ctype_callable_2,
                    "image/jpeg",
                )
            )
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        self.assertEqual(
            spec["paths"]["/icecream/{flavour}"]["put"]["consumes"],
            ["application/json", "image/jpeg"],
        )

    def test_ignore_multiple_views_by_ctype(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            def view_put(self, request):
                return "red"

        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator,),
            schema=PutRequestSchema(),
            content_type="application/json",
        )
        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator,),
            schema=PutRequestSchema(),
            content_type="text/xml",
        )

        swagger = CorniceSwagger([service])
        swagger.ignore_ctypes = ["text/xml"]
        spec = swagger.generate()
        self.assertEqual(
            spec["paths"]["/icecream/{flavour}"]["put"]["consumes"], ["application/json"]
        )

    def test_multiple_views_with_different_ctypes_raises_exception(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            def view_put(self, request):
                return "red"

        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator,),
            schema=PutRequestSchema(),
            content_type="application/json",
        )
        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator,),
            schema=PutRequestSchema(),
            content_type="text/xml",
        )

        swagger = CorniceSwagger([service])
        self.assertRaises(CorniceSwaggerException, swagger.generate)


class ExtractPathTest(unittest.TestCase):
    def test_handles_subpaths_as_parameters(self):
        service = Service("IceCream", "/icecream/*subpath")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return self.request

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        expected = {"name": "subpath", "required": True, "type": "string", "in": "path"}
        self.assertDictEqual(spec["paths"]["/icecream/{subpath}"]["parameters"][0], expected)


class ExtractTagsTest(unittest.TestCase):
    def test_service_defined_tags(self):
        service = Service("IceCream", "/icecream/{flavour}", tags=["yum"])

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        validate(spec)
        tags = spec["paths"]["/icecream/{flavour}"]["get"]["tags"]
        self.assertEqual(tags, ["yum"])

    def test_view_defined_tags(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(tags=["cold", "foo"])
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        validate(spec)
        tags = spec["paths"]["/icecream/{flavour}"]["get"]["tags"]
        self.assertEqual(tags, ["cold", "foo"])

    def test_both_defined_tags(self):
        service = Service("IceCream", "/icecream/{flavour}", tags=["yum"])

        class IceCream(object):
            @service.get(tags=["cold", "foo"])
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        validate(spec)
        tags = spec["paths"]["/icecream/{flavour}"]["get"]["tags"]
        self.assertEqual(tags, ["yum", "cold", "foo"])

    def test_listed_default_tags(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        swagger.default_tags = ["cold"]
        spec = swagger.generate()
        validate(spec)
        tags = spec["paths"]["/icecream/{flavour}"]["get"]["tags"]
        self.assertEqual(tags, ["cold"])

    def test_callable_default_tags(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return service

        def default_tag_callable(service, method):
            return ["cold"]

        swagger = CorniceSwagger([service])
        swagger.default_tags = default_tag_callable
        spec = swagger.generate()
        validate(spec)
        tags = spec["paths"]["/icecream/{flavour}"]["get"]["tags"]
        self.assertEqual(tags, ["cold"])

    def test_provided_tags_override_sorting(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(tags=["cold", "foo"])
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        tags = [{"name": "foo", "description": "bar"}]
        swagger.swagger = {"tags": tags}
        spec = swagger.generate()
        validate(spec)
        self.assertListEqual(
            [{"name": "foo", "description": "bar"}, {"name": "cold"}], spec["tags"]
        )

    def test_invalid_view_tag_raises_exception(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(tags="cold")
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        self.assertRaises(CorniceSwaggerException, swagger.generate)

    def test_invalid_service_tag_raises_exception(self):
        service = Service("IceCream", "/icecream/{flavour}", tags="cold")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        self.assertRaises(CorniceSwaggerException, swagger.generate)


class ExtractOperationIdTest(unittest.TestCase):
    def test_view_defined_operation_id(self):
        service = Service("IceCream", "/icecream/{flavour}")

        @service.get(operation_id="serve_icecream")
        def view_get(self, request):
            return service

        swagger = CorniceSwagger([service])
        spec = swagger.generate()
        validate(spec)
        op_id = spec["paths"]["/icecream/{flavour}"]["get"]["operationId"]
        self.assertEqual(op_id, "serve_icecream")

    def test_default_operation_ids(self):
        service = Service("IceCream", "/icecream/{flavour}")

        @service.get()
        def view_get(self, request):
            return service

        @service.put()
        def view_put(self, request):
            return service

        def op_id_generator(service, method):
            return "%s_%s" % (method.lower(), service.path.split("/")[-2])

        swagger = CorniceSwagger([service])
        swagger.default_op_ids = op_id_generator
        spec = swagger.generate()
        validate(spec)
        op_id = spec["paths"]["/icecream/{flavour}"]["get"]["operationId"]
        self.assertEqual(op_id, "get_icecream")
        op_id = spec["paths"]["/icecream/{flavour}"]["put"]["operationId"]
        self.assertEqual(op_id, "put_icecream")

    def test_invalid_default_opid_raises_exception(self):
        service = Service("IceCream", "/icecream/{flavour}")

        @service.get()
        def view_get(self, request):
            return service

        swagger = CorniceSwagger([service])
        swagger.default_op_ids = "foo"
        self.assertRaises(CorniceSwaggerException, swagger.generate)


class ExtractSecurityTest(unittest.TestCase):
    def test_view_defined_security(self):
        service = Service("IceCream", "/icecream/{flavour}")

        @service.get(api_security=[{"basicAuth": []}])
        def view_get(self, request):
            return service

        swagger = CorniceSwagger([service])
        swagger.swagger = {"securityDefinitions": {"basicAuth": {"type": "basic"}}}
        spec = swagger.generate()
        validate(spec)
        security = spec["paths"]["/icecream/{flavour}"]["get"]["security"]
        self.assertEqual(security, [{"basicAuth": []}])

    def test_listed_default_security(self):
        service = Service("IceCream", "/icecream/{flavour}")

        @service.get()
        def view_get(self, request):
            return service

        swagger = CorniceSwagger([service])
        swagger.swagger = {"securityDefinitions": {"basicAuth": {"type": "basic"}}}
        swagger.default_security = [{"basicAuth": []}]
        spec = swagger.generate()
        validate(spec)
        security = spec["paths"]["/icecream/{flavour}"]["get"]["security"]
        self.assertEqual(security, [{"basicAuth": []}])

    def test_callable_default_security(self):
        def get_security(service, method):
            definitions = service.definitions
            for definition in definitions:
                met, view, args = definition
                if met == method:
                    break

            if "security" in args:
                return [{"basicAuth": []}]
            else:
                return []

        service = Service("IceCream", "/icecream/{flavour}")

        @service.get()
        def view_get(self, request):
            return service

        @service.post(security="foo")
        def view_post(self, request):
            return service

        swagger = CorniceSwagger([service])
        swagger.swagger = {"securityDefinitions": {"basicAuth": {"type": "basic"}}}
        swagger.default_security = get_security
        spec = swagger.generate()
        validate(spec)
        security = spec["paths"]["/icecream/{flavour}"]["post"]["security"]
        self.assertEqual(security, [{"basicAuth": []}])
        security = spec["paths"]["/icecream/{flavour}"]["get"]["security"]
        self.assertEqual(security, [])

    def test_invalid_security_raises_exception(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(api_security="basicAuth")
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        self.assertRaises(CorniceSwaggerException, swagger.generate)
