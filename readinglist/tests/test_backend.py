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
        self.assertRaises(NotImplementedError,
                          self.backend.flush)
        self.assertRaises(NotImplementedError,
                          self.backend.create,
                          '', '', {})
        self.assertRaises(NotImplementedError,
                          self.backend.get,
                          '', '', '')
        self.assertRaises(NotImplementedError,
                          self.backend.update,
                          '', '', '', {})
        self.assertRaises(NotImplementedError,
                          self.backend.delete,
                          '', '', '')
        self.assertRaises(NotImplementedError,
                          self.backend.get_all,
                          '', '')
