from pyramid import httpexceptions

from kinto.core.errors import ERRORS
from . import BaseTest


class FilteringTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.validated = self.resource.request.validated
        self.patch_known_field.start()
        objects = [
            {"title": "MoFo", "status": 0, "favorite": True, "colors": ["blue", "red"]},
            {"title": "MoFo", "status": 1, "favorite": False, "colors": ["blue", "gray"]},
            {"title": "MoFo", "status": 2, "favorite": False, "sometimes": "available"},
            {"title": "MoFo", "status": 0, "favorite": False, "sometimes": None},
            {"title": "MoFo", "status": 1, "favorite": True, "fib": [1, 2, 3]},
            {"title": "MoFo", "status": 2, "favorite": False, "fib": [3, 5, 8]},
            {"title": "Foo", "status": 3, "favorite": False, "aliases": [{"ll": "ls -l"}]},
            {
                "title": "Bar",
                "status": 3,
                "favorite": False,
                "sometimes": "present",
                "aliases": [{"ll": "ls -l"}, {"rm": "rm -i"}],
            },
        ]
        for r in objects:
            self.model.create_object(r)

    def test_list_can_be_filtered_on_deleted_with_since(self):
        since = self.model.timestamp()
        r = self.model.create_object({})
        self.model.delete_object(r)
        self.validated["querystring"] = {"_since": since, "deleted": True}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 1)
        self.assertTrue(result["data"][0]["deleted"])

    def test_filter_on_id_is_supported(self):
        self.patch_known_field.stop()
        r = self.model.create_object({})
        r.pop(self.model.permissions_field)
        self.validated["querystring"] = {"id": "{}".format(r["id"])}
        result = self.resource.plural_get()
        self.assertEqual(result["data"][0], r)

    def test_list_cannot_be_filtered_on_deleted_without_since(self):
        r = self.model.create_object({})
        self.model.delete_object(r)
        self.validated["querystring"] = {"deleted": True}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_filter_works_with_empty_list(self):
        self.resource.model.parent_id = "alice"
        self.validated["querystring"] = {"status": 1}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_number_of_objects_matches_filter(self):
        self.validated["querystring"] = {"status": 1}
        self.resource.plural_head()
        headers = self.last_response.headers
        self.assertEqual(int(headers["Total-Objects"]), 2)

    def test_single_basic_filter_by_attribute(self):
        self.validated["querystring"] = {"status": 1}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 2)

    def test_filter_on_unknown_attribute_raises_error(self):
        self.patch_known_field.stop()
        self.validated["querystring"] = {"foo": 1}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)

    def test_filter_raises_error_if_last_modified_value_is_empty(self):
        self.validated["querystring"] = {"last_modified": ""}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)
        self.validated["querystring"] = {"_since": ""}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)
        self.validated["querystring"] = {"lt_last_modified": ""}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)

    def test_filter_errors_are_json_formatted(self):
        self.patch_known_field.stop()
        self.validated["querystring"] = {"foo": 1}
        try:
            self.resource.plural_get()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(
            error.json,
            {
                "errno": ERRORS.INVALID_PARAMETERS.value,
                "message": "Unknown filter field 'foo'",
                "code": 400,
                "error": "Invalid parameters",
                "details": [
                    {
                        "description": "Unknown filter field 'foo'",
                        "location": "querystring",
                        "name": "foo",
                    }
                ],
            },
        )

    def test_regexp_is_strict_for_min_and_max(self):
        self.patch_known_field.stop()
        self.validated["querystring"] = {"madmax_status": 1}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)

    def test_double_basic_filter_by_attribute(self):
        self.validated["querystring"] = {"status": 1, "favorite": True}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 1)

    def test_string_filters_naively_by_value(self):
        self.validated["querystring"] = {"title": "MoF"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)
        self.validated["querystring"] = {"title": "MoFo"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 6)

    def test_not_string_filter(self):
        self.validated["querystring"] = {"like_title": 10}
        try:
            self.resource.plural_get()
        except httpexceptions.HTTPBadRequest as e:
            error = e
        self.assertEqual(
            error.json,
            {
                "code": 400,
                "details": [
                    {
                        "description": "Invalid value for like_title",
                        "location": "querystring",
                        "name": "like_title",
                    }
                ],
                "errno": 107,
                "error": "Invalid parameters",
                "message": "Invalid value for like_title",
            },
        )

    def test_string_filters_searching_by_value_not_matching(self):
        self.validated["querystring"] = {"like_title": "MoFoo"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_string_filters_searching_by_value_matching_many(self):
        self.validated["querystring"] = {"like_title": "Fo"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 7)

    def test_string_filters_searching_by_value_matching_one(self):
        self.validated["querystring"] = {"like_title": "Bar"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 1)

    def test_string_filters_searching_by_value_matching_vary_case(self):
        self.validated["querystring"] = {"like_title": "FoO"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 1)

    def test_filter_considers_string_if_syntaxically_invalid(self):
        self.validated["querystring"] = {"status": "1.2.3"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_filter_does_not_fail_with_complex_type_syntax(self):
        self.validated["querystring"] = {"status": "(1,2,3)"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_different_value(self):
        self.validated["querystring"] = {"not_status": 2}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertTrue(all([value != 2 for value in values]))

    def test_minimal_value(self):
        self.validated["querystring"] = {"min_status": 2}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertTrue(all([value >= 2 for value in values]))

    def test_gt_value(self):
        self.validated["querystring"] = {"gt_status": 2}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertTrue(all([value > 2 for value in values]))

    def test_maximal_value(self):
        self.validated["querystring"] = {"max_status": 2}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertTrue(all([value <= 2 for value in values]))

    def test_lt_value(self):
        self.validated["querystring"] = {"lt_status": 2}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertTrue(all([value < 2 for value in values]))

    def test_in_values(self):
        self.validated["querystring"] = {"in_status": [0, 1]}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertEqual(sorted(values), [0, 0, 1, 1])

    def test_exclude_values(self):
        self.validated["querystring"] = {"exclude_status": [0]}
        result = self.resource.plural_get()
        values = [item["status"] for item in result["data"]]
        self.assertEqual(sorted(values), [1, 1, 2, 2, 3, 3])

    def test_has_values(self):
        self.validated["querystring"] = {"has_sometimes": True}
        result = self.resource.plural_get()
        values = [item["sometimes"] for item in result["data"]]
        assert None in values
        self.assertEqual(sorted([v for v in values if v]), ["available", "present"])

    def test_has_values_false(self):
        self.validated["querystring"] = {"has_sometimes": False}
        result = self.resource.plural_get()
        values = ["sometimes" in item for item in result["data"]]
        self.assertEqual(sorted(values), [False, False, False, False, False])

    def test_include_returns_400_if_value_has_wrong_type(self):
        self.validated["querystring"] = {"in_id": [0, 1]}
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.plural_get()
        self.assertIn("in_id", cm.exception.json["message"])

        self.validated["querystring"] = {"in_last_modified": ["a", "b"]}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)

    def test_exclude_returns_400_if_value_has_wrong_type(self):
        self.validated["querystring"] = {"exclude_id": [0, 1]}
        with self.assertRaises(httpexceptions.HTTPBadRequest) as cm:
            self.resource.plural_get()
        self.assertIn("exclude_id", cm.exception.json["message"])

        self.validated["querystring"] = {"exclude_last_modified": ["a", "b"]}
        self.assertRaises(httpexceptions.HTTPBadRequest, self.resource.plural_get)

    def test_contains_can_filter_with_one_string(self):
        self.validated["querystring"] = {"contains_colors": ["red"]}
        result = self.resource.plural_get()
        values = [item["colors"] for item in result["data"]]
        assert len(values) == 1
        for value in values:
            assert "red" in value

    def test_contains_can_filter_with_one_object(self):
        self.validated["querystring"] = {"contains_aliases": [{"ll": "ls -l"}]}
        result = self.resource.plural_get()
        values = [item["aliases"] for item in result["data"]]
        assert len(values) == 2
        for value in values:
            assert {"ll": "ls -l"} in value

    def test_contains_can_filter_with_list_of_strings(self):
        self.validated["querystring"] = {"contains_colors": ["red", "blue"]}
        result = self.resource.plural_get()
        values = [item["colors"] for item in result["data"]]
        assert len(values) == 1
        for value in values:
            assert "red" in value and "blue" in value

    def test_contains_can_filter_with_an_integer(self):
        self.validated["querystring"] = {"contains_fib": [3]}
        result = self.resource.plural_get()
        values = [item["fib"] for item in result["data"]]
        assert len(values) == 2
        for value in values:
            assert 3 in value

    def test_contains_any_can_filter_with_a_list_of_strings(self):
        self.validated["querystring"] = {"contains_any_colors": ["red", "blue"]}
        result = self.resource.plural_get()
        values = [item["colors"] for item in result["data"]]
        assert len(values) == 2
        for value in values:
            assert "red" in value or "blue" in value

    def test_contains_any_can_filter_with_a_list_of_integers(self):
        self.validated["querystring"] = {"contains_any_fib": [3, 5]}
        result = self.resource.plural_get()
        values = [item["fib"] for item in result["data"]]
        assert len(values) == 2
        for value in values:
            assert 3 in value or 5 in value

    def test_contains_fails_on_a_non_sequence_object_value(self):
        self.validated["querystring"] = {"contains_favorite": [True]}
        result = self.resource.plural_get()
        values = result["data"]
        assert len(values) == 0

    def test_contains_any_fails_on_a_non_sequence_object_value(self):
        self.validated["querystring"] = {"contains_any_favorite": [True]}
        result = self.resource.plural_get()
        values = result["data"]
        assert len(values) == 0


class SubobjectFilteringTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.validated = self.resource.request.validated
        self.patch_known_field.start()
        for i in range(6):
            obj = {"party": {"candidate": "Marie", "voters": i}, "location": "Creuse"}
            self.model.create_object(obj)

    def test_objects_can_be_filtered_by_subobjects(self):
        self.validated["querystring"] = {"party.voters": 1}
        result = self.resource.plural_get()
        values = [item["party"]["voters"] for item in result["data"]]
        self.assertEqual(sorted(values), [1])

    def test_subobjects_filters_are_ignored_if_not_object(self):
        self.validated["querystring"] = {"location.city": "barcelona"}
        result = self.resource.plural_get()
        self.assertEqual(len(result["data"]), 0)

    def test_subobjects_filters_works_with_directives(self):
        self.validated["querystring"] = {"in_party.voters": [1, 2, 3]}
        result = self.resource.plural_get()
        values = [item["party"]["voters"] for item in result["data"]]
        self.assertEqual(sorted(values), [1, 2, 3])


class JSONFilteringTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.validated = self.resource.request.validated
        self.patch_known_field.start()
        objects = [
            {
                "id": "strawberry",
                "flavor": "strawberry",
                "orders": [],
                "attributes": {"ibu": 25, "seen_on": "2017-06-01"},
                "author": None,
            },
            {"id": "blueberry-1", "flavor": "blueberry", "orders": [1]},
            {"id": "blueberry-2", "flavor": "blueberry", "orders": ""},
            {"id": "raspberry-1", "flavor": "raspberry", "attributes": {}},
            {"id": "raspberry-2", "flavor": "raspberry", "attributes": []},
            {
                "id": "raspberry-3",
                "flavor": "raspberry",
                "attributes": {"ibu": 25, "seen_on": "2017-06-01", "price": 9.99},
            },
            {"id": "watermelon-1", "flavor": "watermelon", "author": "null"},
            {"id": "watermelon-2", "flavor": "watermelon", "author": 0},
        ]
        for r in objects:
            self.model.create_object(r)

    def test_filter_by_empty_array(self):
        self.validated["querystring"] = {"orders": []}
        result = self.resource.plural_get()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "strawberry"

    def test_filter_by_nonempty_array(self):
        self.validated["querystring"] = {"orders": [1]}
        result = self.resource.plural_get()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "blueberry-1"

    def test_filter_by_empty_object(self):
        self.validated["querystring"] = {"attributes": {}}
        result = self.resource.plural_get()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "raspberry-1"

    def test_filter_by_nonempty_object(self):
        self.validated["querystring"] = {"attributes": {"ibu": 25, "seen_on": "2017-06-01"}}
        result = self.resource.plural_get()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "strawberry"

    def test_filter_by_null(self):
        self.validated["querystring"] = {"author": None}
        result = self.resource.plural_get()
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "strawberry"
