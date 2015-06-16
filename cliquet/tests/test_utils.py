import os

import colander
import mock
import six

from cliquet.utils import (native_value, strip_whitespace, random_bytes_hex,
                           read_env, current_service)

from .support import unittest, DummyRequest


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


class ReadEnvironmentTest(unittest.TestCase):
    def test_return_passed_value_if_not_defined_in_env(self):
        self.assertEqual(read_env('missing', 12), 12)

    def test_return_env_value_if_defined_in_env(self):
        os.environ.setdefault('CLIQUET_CONF', 'abc')
        self.assertEqual(read_env('CLIQUET_CONF', 12), 'abc')

    def test_return_env_name_as_uppercase(self):
        os.environ.setdefault('CLIQUET_NAME', 'abc')
        self.assertEqual(read_env('cliquet.name', 12), 'abc')

    def test_return_env_value_is_coerced_to_python(self):
        os.environ.setdefault('CLIQUET_CONF_NAME', '3.14')
        self.assertEqual(read_env('cliquet-conf.name', 12), 3.14)


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
