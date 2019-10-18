import unittest

from kinto import main

from .support import BaseWebTest


class TestMain(BaseWebTest, unittest.TestCase):
    def test_init_sets_command_on_registry(self):
        app = main({"command": "migrate"}, None, **self.get_app_settings())

        self.assertEqual(app.registry.command, "migrate")

    def test_init_with_no_global_config_doesnt_crash(self):
        app = main(None, None, **self.get_app_settings())

        self.assertEqual(app.registry.command, None)
