import threading

import colander

from readinglist.utils import native_value, strip_whitespace

from .support import unittest


class NativeValueTest(unittest.TestCase):
    def test_simple_string(self):
        self.assertEqual(native_value('value'), 'value')

    def test_integer(self):
        self.assertEqual(native_value('7'), 7)

    def test_float(self):
        self.assertEqual(native_value('3.14'), 3.14)

    def test_true_values(self):
        true_strings = ['True', 'on', 'true', 'yes', '1']
        true_values = [native_value(s) for s in true_strings]
        self.assertTrue(all(true_values))

    def test_false_values(self):
        false_strings = ['False', 'off', 'false', 'no', '0']
        false_values = [native_value(s) for s in false_strings]
        self.assertFalse(any(false_values))


class StripWhitespaceTest(unittest.TestCase):
    def test_removes_all_kinds_of_spaces(self):
        value = " \t teaser \n \r"
        self.assertEqual(strip_whitespace(value), 'teaser')

    def test_does_remove_middle_spaces(self):
        self.assertEqual(strip_whitespace('a b c'), 'a b c')

    def test_idempotent_for_null_values(self):
        self.assertEqual(strip_whitespace(colander.null), colander.null)


class TimeStamperTest(unittest.TestCase):
    def test_timestamps_are_based_on_real_time(self):
        msec_before = msec_time()
        now = timestamper.now()
        msec_after = msec_time()
        self.assertTrue(msec_before - 1 < now < msec_after + 1)

    def test_timestamp_are_always_different(self):
        before = timestamper.now()
        now = timestamper.now()
        after = timestamper.now()
        self.assertTrue(before < now < after)

    def test_timestamp_have_under_one_millisecond_precision(self):
        msec_before = msec_time()
        now1 = timestamper.now()
        now2 = timestamper.now()
        msec_after = msec_time()
        self.assertNotEqual(now1, now2)
        # Assert than less than 1 msec elapsed (Can fail on very slow machine)
        self.assertTrue(msec_before - msec_after <= 1)

    def test_timestamp_are_thread_safe(self):
        obtained = []

        def hit_timestamp():
            for i in range(1000):
                obtained.append(timestamper.now())

        thread1 = threading.Thread(target=hit_timestamp)
        thread2 = threading.Thread(target=hit_timestamp)
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # With CPython (GIL), list appending is thread-safe
        self.assertEqual(len(obtained), 2000)
        # No duplicated timestamps
        self.assertEqual(len(set(obtained)), len(obtained))
