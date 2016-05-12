# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

import colander
import mock
import six
from kinto.core import includeme
from kinto.core import DEFAULT_SETTINGS
from pyramid import httpexceptions
from pyramid import request as pyramid_request
from pyramid import testing

from kinto.core.utils import (
    native_value, strip_whitespace, random_bytes_hex, read_env, hmac_digest,
    current_service, encode_header, decode_header, follow_subrequest,
    build_request, dict_subset
)

from .support import unittest, DummyRequest


def build_real_request(wsgi_environ):
    """Build a Pyramid request, as if it was instantiated by Pyramid.
    """
    config = testing.setUp(settings=DEFAULT_SETTINGS)
    includeme(config)
    request = pyramid_request.Request(wsgi_environ)
    request.registry = config.registry
    return request


class NativeValueTest(unittest.TestCase):
    def test_simple_string(self):
        self.assertEqual(native_value('value'), 'value')

    def test_integer(self):
        self.assertEqual(native_value('7'), 7)

    def test_zero_and_one_coerce_to_integers(self):
        self.assertEqual(native_value('1'), 1)
        self.assertEqual(native_value('0'), 0)

    def test_float(self):
        self.assertEqual(native_value('3.14'), 3.14)

    def test_true_values(self):
        true_strings = ['True', 'on', 'true', 'yes']
        true_values = [native_value(s) for s in true_strings]
        self.assertTrue(all(true_values))

    def test_false_values(self):
        false_strings = ['False', 'off', 'false', 'no']
        false_values = [native_value(s) for s in false_strings]
        self.assertFalse(any(false_values))

    def test_non_string_values(self):
        self.assertEqual(native_value(7), 7)
        self.assertEqual(native_value(True), True)


class StripWhitespaceTest(unittest.TestCase):
    def test_removes_all_kinds_of_spaces(self):
        value = " \t teaser \n \r"
        self.assertEqual(strip_whitespace(value), 'teaser')

    def test_does_remove_middle_spaces(self):
        self.assertEqual(strip_whitespace('a b c'), 'a b c')

    def test_idempotent_for_null_values(self):
        self.assertEqual(strip_whitespace(colander.null), colander.null)


class CryptographicRandomBytesTest(unittest.TestCase):
    def test_return_hex_string(self):
        value = random_bytes_hex(16)
        try:
            int(value, 16)
        except ValueError:
            self.fail("%s is not an hexadecimal value." % value)

    def test_return_right_length_string(self):
        for x in range(2, 4):
            value = random_bytes_hex(x)
            self.assertEqual(len(value), x * 2)

    def test_return_text_string(self):
        value = random_bytes_hex(16)
        self.assertIsInstance(value, six.text_type)


class HmacDigestTest(unittest.TestCase):
    def test_supports_secret_as_text(self):
        value = hmac_digest("blah", "input data")
        self.assertTrue(value.startswith("d4f5c51db246c7faeb42240545b47274b6"))

    def test_supports_secret_as_bytes(self):
        value = hmac_digest(b"blah", "input data")
        self.assertTrue(value.startswith("d4f5c51db246c7faeb42240545b47274b6"))


class ReadEnvironmentTest(unittest.TestCase):
    def test_return_passed_value_if_not_defined_in_env(self):
        self.assertEqual(read_env('missing', 12), 12)

    def test_return_env_value_if_defined_in_env(self):
        os.environ.setdefault('KINTO_CONF', 'abc')
        self.assertEqual(read_env('KINTO_CONF', 12), 'abc')

    def test_return_env_name_as_uppercase(self):
        os.environ.setdefault('KINTO_NAME', 'abc')
        self.assertEqual(read_env('kinto.name', 12), 'abc')

    def test_return_env_value_is_coerced_to_python(self):
        os.environ.setdefault('KINTO_CONF_NAME', '3.14')
        self.assertEqual(read_env('kinto-conf.name', 12), 3.14)


class CurrentServiceTest(unittest.TestCase):

    def test_current_service_returns_the_service_for_existing_patterns(self):
        request = DummyRequest()
        request.matched_route.pattern = '/buckets'
        request.registry.cornice_services = {'/buckets': mock.sentinel.service}

        self.assertEqual(current_service(request), mock.sentinel.service)

    def test_current_service_returns_none_for_unexisting_patterns(self):
        request = DummyRequest()
        request.matched_route.pattern = '/unexisting'
        request.registry.cornice_services = {}

        self.assertEqual(current_service(request), None)


class BuildRequestTest(unittest.TestCase):

    def test_built_request_has_kinto_core_custom_methods(self):
        original = build_real_request({'PATH_INFO': '/foo'})
        request = build_request(original, {"path": "bar"})
        self.assertTrue(hasattr(request, 'current_service'))


class EncodeHeaderTest(unittest.TestCase):

    def test_returns_a_string_if_passed_a_string(self):
        entry = str('Toto')
        value = encode_header(entry)
        self.assertEqual(entry, value)
        self.assertEqual(type(value), str)

    def test_returns_a_string_if_passed_bytes(self):
        entry = 'Toto'.encode('utf-8')
        value = encode_header(entry)
        self.assertEqual(type(value), str)

    def test_returns_a_string_if_passed_bytes_and_encoding(self):
        entry = 'Rémy'.encode('latin-1')
        value = encode_header(entry, 'latin-1')
        self.assertEqual(type(value), str)

    def test_returns_a_string_if_passed_unicode(self):
        entry = six.text_type('Rémy')
        value = encode_header(entry)
        self.assertEqual(type(value), str)

    def test_returns_a_string_if_passed_unicode_with_encoding(self):
        entry = six.text_type('Rémy')
        value = encode_header(entry, 'latin-1')
        self.assertEqual(type(value), str)


class DecodeHeaderTest(unittest.TestCase):

    def test_returns_an_unicode_string_if_passed_a_string(self):
        entry = 'Toto'
        value = decode_header(entry)
        self.assertEqual(entry, value)

    def test_returns_an_unicode__string_if_passed_bytes(self):
        entry = 'Toto'.encode('utf-8')
        value = decode_header(entry)
        self.assertEqual(type(value), six.text_type)

    def test_returns_an_unicode__string_if_passed_bytes_and_encoding(self):
        entry = 'Rémy'.encode('latin-1')
        value = decode_header(entry, 'latin-1')
        self.assertEqual(type(value), six.text_type)


class FollowSubrequestTest(unittest.TestCase):

    def test_parent_and_bound_data_are_preserved(self):
        request = DummyRequest()
        request.invoke_subrequest.side_effect = (
            httpexceptions.HTTPTemporaryRedirect, None)
        subrequest = DummyRequest()
        subrequest.parent = mock.sentinel.parent
        subrequest.bound_data = mock.sentinel.bound_data
        _, redirected = follow_subrequest(request, subrequest)
        self.assertEqual(subrequest.parent, redirected.parent)
        self.assertEqual(subrequest.bound_data, redirected.bound_data)


class DictSubsetTest(unittest.TestCase):

    def test_extract_by_keys(self):
        obtained = dict_subset(dict(a=1, b=2), ["b"])
        expected = dict(b=2)
        self.assertEqual(obtained, expected)

    def test_is_noop_if_no_keys(self):
        obtained = dict_subset(dict(a=1, b=2), [])
        expected = dict()
        self.assertEqual(obtained, expected)

    def test_ignores_unknown_keys(self):
        obtained = dict_subset(dict(a=1, b=2), ["a", "c"])
        expected = dict(a=1)
        self.assertEqual(obtained, expected)

    def test_ignores_duplicated_keys(self):
        obtained = dict_subset(dict(a=1, b=2), ["a", "a"])
        expected = dict(a=1)
        self.assertEqual(obtained, expected)

    def test_can_filter_subobjects(self):
        obtained = dict_subset(dict(a=1, b=dict(c=2, d=3)), ["a", "b.c"])
        expected = dict(a=1, b=dict(c=2))
        self.assertEqual(obtained, expected)

    def test_can_filter_subobjects_keys(self):
        input = dict(a=1, b=dict(c=2, d=3, e=4))
        obtained = dict_subset(input, ["a", "b.d", "b.e"])
        expected = dict(a=1, b=dict(d=3, e=4))
        self.assertEqual(obtained, expected)

    def test_can_filter_subobjects_recursively(self):
        input = dict(a=1, b=dict(c=2, d=dict(e=4, f=5)))
        obtained = dict_subset(input, ["a", "b.d.e"])
        expected = dict(a=1, b=dict(d=dict(e=4)))
        self.assertEqual(obtained, expected)

    def test_ignores_if_subobject_is_not_dict(self):
        input = dict(a=1, b=dict(c=2, d=3))
        obtained = dict_subset(input, ["a", "b.c.d", "b.d"])
        expected = dict(a=1, b=dict(c=2, d=3))
        self.assertEqual(obtained, expected)
