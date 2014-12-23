import unittest

from readinglist.backend import BackendBase


class BackendBaseTest(unittest.TestCase):
    def setUp(self):
        self.backend = BackendBase()

    def test_default_generator(self):
        self.assertEqual(type(self.backend.id_generator()), unicode)

    def test_custom_generator(self):
        l = lambda x: x
        backend = BackendBase(id_generator=l)
        self.assertEqual(backend.id_generator, l)

    def test_mandatory_overrides(self):
        calls = [
            (self.backend.flush,),
            (self.backend.create, '', '', {}),
            (self.backend.get, '', '', ''),
            (self.backend.update, '', '', '', {}),
            (self.backend.delete, '', '', ''),
            (self.backend.get_all, '', ''),
        ]
        for call in calls:
            self.assertRaises(NotImplementedError, *call)
