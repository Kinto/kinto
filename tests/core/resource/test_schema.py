from unittest import mock

import colander

from kinto.core.resource import schema
from kinto.core.testing import unittest


class DepracatedSchemasTest(unittest.TestCase):
    def test_resource_timestamp_is_depracated(self):
        with mock.patch("kinto.core.resource.schema.warnings") as mocked:
            schema.TimeStamp()
            message = (
                "`kinto.core.resource.schema.TimeStamp` is deprecated, "
                "use `kinto.core.schema.TimeStamp` instead."
            )
            mocked.warn.assert_called_with(message, DeprecationWarning)

    def test_resource_URL_is_depracated(self):
        with mock.patch("kinto.core.resource.schema.warnings") as mocked:
            schema.URL()
            message = (
                "`kinto.core.resource.schema.URL` is deprecated, "
                "use `kinto.core.schema.URL` instead."
            )
            mocked.warn.assert_called_with(message, DeprecationWarning)


class ResourceSchemaTest(unittest.TestCase):
    def test_preserves_unknown_fields_when_specified(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                preserve_unknown = True

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({"foo": "bar"})
        self.assertIn("foo", deserialized)
        self.assertEqual(deserialized["foo"], "bar")

    def test_ignore_unknwon_fields_when_specified(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                preserve_unknown = False

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({"foo": "bar"})
        self.assertNotIn("foo", deserialized)

    def test_accepts_unknown_fields_by_default(self):
        schema_instance = schema.ResourceSchema()
        deserialized = schema_instance.deserialize({"foo": "bar"})
        self.assertIn("foo", deserialized)

    def test_options_parameters_use_default_value_when_subclassed(self):
        class PreserveSchema(schema.ResourceSchema):
            class Options:
                pass

        schema_instance = PreserveSchema()
        deserialized = schema_instance.deserialize({"foo": "bar"})
        self.assertIn("foo", deserialized)


class PermissionsSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.PermissionsSchema()

    def test_works_with_any_permission_name_by_default(self):
        perms = {"can_cook": ["mat"]}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_works_with_empty_mapping(self):
        perms = {}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_works_with_empty_list_of_principals(self):
        perms = {"can_cook": []}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_works_with_empty_none_permissions(self):
        perms = {"can_cook": None}
        deserialized = self.schema.deserialize(perms)
        self.assertEqual(deserialized, perms)

    def test_raises_invalid_if_not_a_mapping(self):
        perms = ["gab"]
        self.assertRaises(colander.Invalid, self.schema.deserialize, perms)

    def test_raises_invalid_if_permission_is_unknown(self):
        self.schema.known_perms = ("can_sleep",)
        perms = {"can_work": ["mat"]}
        self.assertRaises(colander.Invalid, self.schema.deserialize, perms)

    def test_raises_invalid_if_not_list(self):
        perms = {"can_cook": 3.14}
        self.assertRaises(colander.Invalid, self.schema.deserialize, perms)

    def test_raises_invalid_if_not_list_of_strings(self):
        perms = {"can_cook": ["pi", 3.14]}
        self.assertRaises(colander.Invalid, self.schema.deserialize, perms)


class HeaderFieldSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.HeaderField(colander.String())

    def test_decode_unicode(self):
        value = "\xe7 is not a c"
        deserialized = self.schema.deserialize(value.encode("utf-8"))
        self.assertEqual(deserialized, value)

    def test_bad_unicode_raises_invalid(self):
        value = b"utf8 \xe9"
        self.assertRaises(colander.Invalid, self.schema.deserialize, value)


class QueryFieldSchemaTest(unittest.TestCase):
    def test_deserialize_integer_between_quotes(self):
        self.schema = schema.QueryField(colander.Integer())
        deserialized = self.schema.deserialize("123")
        self.assertEqual(deserialized, 123)


class FieldListSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.FieldList()

    def test_deserialize_as_list(self):
        value = "foo,-bar,123"
        deserialized = self.schema.deserialize(value)
        self.assertEqual(deserialized, ["foo", "-bar", "123"])

    def test_handle_drop(self):
        value = colander.null
        deserialized = self.schema.deserialize(value)
        self.assertEqual(deserialized, colander.drop)

    def test_handle_empty(self):
        value = ""
        deserialized = self.schema.deserialize(value)
        self.assertEqual(deserialized, [])

    def test_raises_invalid_if_not_string(self):
        value = 123
        self.assertRaises(colander.Invalid, self.schema.deserialize, value)


class HeaderQuotedIntegerSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.HeaderQuotedInteger()

    def test_deserialize_as_integer(self):
        value = '"123"'
        deserialized = self.schema.deserialize(value)
        self.assertEqual(deserialized, 123)

    def test_deserialize_any(self):
        value = "*"
        deserialized = self.schema.deserialize(value)
        self.assertEqual(deserialized, "*")

    def test_unquoted_raises_invalid(self):
        value = "123"
        self.assertRaises(colander.Invalid, self.schema.deserialize, value)

    def test_integer_raises_invalid(self):
        value = 123
        self.assertRaises(colander.Invalid, self.schema.deserialize, value)

    def test_invalid_quoted_raises_invalid(self):
        value = "foo"
        self.assertRaises(colander.Invalid, self.schema.deserialize, value)

    def test_empty_raises_invalid(self):
        value = '""'
        self.assertRaises(colander.Invalid, self.schema.deserialize, value)


class ObjectSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.ObjectSchema()

    def test_binds_data(self):
        bound = self.schema.bind(data=schema.ResourceSchema())
        value = {"data": {"foo": "bar"}}
        deserialized = bound.deserialize(value)
        self.assertEqual(deserialized, value)

    def test_binds_permissions(self):
        permissions = schema.PermissionsSchema(permissions=("sleep",))
        bound = self.schema.bind(permissions=permissions)
        value = {"permissions": {"sleep": []}}
        deserialized = bound.deserialize(value)
        self.assertEqual(deserialized, value)

    def test_allow_binding_perms_after_data(self):
        bound = self.schema.bind(data=schema.ResourceSchema())
        permissions = schema.PermissionsSchema(permissions=("sleep",))
        bound = bound.bind(permissions=permissions)
        value = {"data": {"foo": "bar"}, "permissions": {"sleep": []}}
        deserialized = bound.deserialize(value)
        self.assertEqual(deserialized, value)

    def test_doesnt_allow_permissions_unless_bound(self):
        bound = self.schema.bind(data=schema.ResourceSchema())
        value = {"permissions": {"sleep": []}}
        self.assertRaises(colander.UnsupportedFields, bound.deserialize, value)


class RequestSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.RequestSchema()

    def test_header_supports_binding(self):
        header = colander.MappingSchema(missing={"foo": "bar"})
        bound = self.schema.bind(header=header)
        deserialized = bound.deserialize({})
        self.assertEqual(deserialized["header"], {"foo": "bar"})

    def test_querystring_supports_binding(self):
        querystring = colander.MappingSchema(missing={"foo": "bar"})
        bound = self.schema.bind(querystring=querystring)
        deserialized = bound.deserialize({})
        self.assertEqual(deserialized["querystring"], {"foo": "bar"})

    def test_default_header_if_not_bound(self):
        bound = self.schema.bind()
        self.assertEqual(type(bound["header"]), schema.HeaderSchema)

    def test_default_querystring_if_not_bound(self):
        bound = self.schema.bind()
        self.assertEqual(type(bound["querystring"]), schema.QuerySchema)

    def test_header_preserve_unknown_fields(self):
        value = {"header": {"foo": "bar"}}
        deserialized = self.schema.bind().deserialize(value)
        self.assertEqual(deserialized, value)

    def test_querystring_preserve_unknown_fields(self):
        value = {"querystring": {"foo": "bar"}}
        deserialized = self.schema.bind().deserialize(value)
        self.assertEqual(deserialized, value)

    def test_drops(self):
        deserialized = self.schema.bind().deserialize({})
        self.assertEqual(deserialized, {})


class PayloadRequestSchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.PayloadRequestSchema()

    def test_body_supports_binding(self):
        body = colander.MappingSchema(missing={"foo": "bar"})
        bound = self.schema.bind(body=body)
        deserialized = bound.deserialize({})
        self.assertEqual(deserialized["body"], {"foo": "bar"})

    def test_body_supports_binding_after_other_binds(self):
        querystring = colander.MappingSchema(missing={"foo": "bar"})
        bound = self.schema.bind(querystring=querystring)
        body = colander.MappingSchema(missing={"foo": "beer"})
        bound = bound.bind(body=body)
        deserialized = bound.deserialize({})
        self.assertEqual(deserialized["querystring"], {"foo": "bar"})
        self.assertEqual(deserialized["body"], {"foo": "beer"})


class PluralQuerySchemaTest(unittest.TestCase):
    def setUp(self):
        self.schema = schema.PluralQuerySchema()
        self.querystring = {
            "_limit": "2",
            "_sort": "toto,tata",
            "_token": "abc",
            "_since": "1234",
            "_to": "7890",
            "_before": "4567",
            "id": "toot",
            "last_modified": "9874",
            "in_age": "15,16,17",
            "exclude_id": "45aea306-cf9c-44d3-fbe0e5bb3ef6,2400fc9b-1db6-473d-818b68431545",
            "contains_comma_int": "3,4",
            "contains_any_comma_strings": "red,blue",
            "contains_any_object": '{"id": 1234}',
            "contains_user.name": '["Ethan","Remy"]',
            "contains_any_user.height": "[165, 200]",
            "contains_aliases": '[{"ls": "ll -a"}, {"rimraf": "rm -rf"}]',
        }

    def test_decode_valid_querystring(self):
        self.maxDiff = None
        deserialized = self.schema.deserialize(self.querystring)
        self.assertEqual(
            deserialized,
            {
                "_limit": 2,
                "_sort": ["toto", "tata"],
                "_token": "abc",
                "_since": 1234,
                "_to": 7890,
                "_before": 4567,
                "id": "toot",
                "last_modified": 9874,
                "contains_comma_int": ["3,4"],
                "contains_any_comma_strings": ["red,blue"],
                "contains_any_object": [{"id": 1234}],
                "contains_any_user.height": [165, 200],
                "contains_user.name": ["Ethan", "Remy"],
                "contains_aliases": [{"ls": "ll -a"}, {"rimraf": "rm -rf"}],
                "in_age": [15, 16, 17],
                "exclude_id": [
                    "45aea306-cf9c-44d3-fbe0e5bb3ef6",
                    "2400fc9b-1db6-473d-818b68431545",
                ],
            },
        )

    def test_raises_invalid_for_to_big_integer_in_limit(self):
        querystring = self.querystring.copy()
        querystring["_limit"] = schema.POSTGRESQL_MAX_INTEGER_VALUE + 1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_to_big_integer_in_since(self):
        querystring = self.querystring.copy()
        querystring["_since"] = schema.POSTGRESQL_MAX_INTEGER_VALUE + 1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_to_big_integer_in_to(self):
        querystring = self.querystring.copy()
        querystring["_to"] = schema.POSTGRESQL_MAX_INTEGER_VALUE + 1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_to_big_integer_in_before(self):
        querystring = self.querystring.copy()
        querystring["_before"] = schema.POSTGRESQL_MAX_INTEGER_VALUE + 1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_to_big_integer_in_last_modified(self):
        querystring = self.querystring.copy()
        querystring["last_modified"] = schema.POSTGRESQL_MAX_INTEGER_VALUE + 1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_negative_integer_in_limit(self):
        querystring = self.querystring.copy()
        querystring["_limit"] = -1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_negative_integer_in_since(self):
        querystring = self.querystring.copy()
        querystring["_since"] = -1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_negative_integer_in_to(self):
        querystring = self.querystring.copy()
        querystring["_to"] = -1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_negative_integer_in_before(self):
        querystring = self.querystring.copy()
        querystring["_before"] = -1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)

    def test_raises_invalid_for_negative_integer_in_last_modified(self):
        querystring = self.querystring.copy()
        querystring["last_modified"] = -1
        self.assertRaises(colander.Invalid, self.schema.deserialize, querystring)


class ResourceReponsesTest(unittest.TestCase):
    def setUp(self):
        self.handler = schema.ResourceReponses()
        self.resource = colander.MappingSchema(title="fake")
        self.obj = schema.ObjectSchema().bind(data=self.resource)

    def test_get_and_bind_assign_resource_schema_to_object_endpoint(self):
        responses = self.handler.get_and_bind("object", "get", object=self.obj)
        ok_response = responses["200"]
        self.assertEqual(self.obj["data"], ok_response["body"]["data"])

    def test_get_and_bind_assign_resource_schema_to_plural_endpoint(self):
        responses = self.handler.get_and_bind("plural", "get", object=self.obj)
        ok_response = responses["200"]
        # XXX: Data is repeated because it's a colander sequence type index
        self.assertEqual(self.obj["data"], ok_response["body"]["data"]["data"])

    def test_responses_doesnt_have_permissions_if_not_bound(self):
        responses = self.handler.get_and_bind("object", "get", object=self.obj)
        ok_response = responses["200"]
        self.assertNotIn("permissions", ok_response["body"])
