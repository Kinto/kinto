import unittest
from unittest import mock

from kinto import scripts


class RebuildQuotasTest(unittest.TestCase):
    def setUp(self):
        self.registry = mock.MagicMock()
        self.registry.settings = {"includes": "kinto.plugins.quotas"}

    def test_rebuild_quotas_in_read_only_display_an_error(self):
        with mock.patch("kinto.scripts.logger") as mocked:
            self.registry.settings["readonly"] = "true"
            code = scripts.rebuild_quotas({"registry": self.registry})
            assert code == 41
            mocked.error.assert_any_call("Cannot rebuild quotas while " "in readonly mode.")

    def test_rebuild_quotas_when_not_included_display_an_error(self):
        with mock.patch("kinto.scripts.logger") as mocked:
            self.registry.settings["includes"] = ""
            code = scripts.rebuild_quotas({"registry": self.registry})
            assert code == 42
            mocked.error.assert_any_call(
                "Cannot rebuild quotas when " "quotas plugin is not installed."
            )

    def test_rebuild_quotas_calls_quotas_script(self):
        with mock.patch("kinto.scripts.quotas.rebuild_quotas") as mocked:
            code = scripts.rebuild_quotas({"registry": self.registry})
            assert code == 0
            mocked.assert_called_with(self.registry.storage, dry_run=False)
