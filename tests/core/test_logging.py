import json
import logging
import unittest
from unittest import mock

from pyramid import testing

from kinto.core import DEFAULT_SETTINGS, JsonLogFormatter, initialization

from .support import BaseWebTest


class RequestSummaryTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super().setUp()
        config = testing.setUp()
        config.registry.settings = DEFAULT_SETTINGS
        initialization.setup_logging(config)

        patch = mock.patch("kinto.core.initialization.summary_logger")
        self.mocked = patch.start()
        self.addCleanup(patch.stop)

    def logger_context(self):
        args, kwargs = self.mocked.info.call_args_list[-1]
        return kwargs["extra"]

    def test_standard_info_is_bound(self):
        headers = {"User-Agent": "Smith", **self.headers}
        self.app.get("/", headers=headers)
        event_dict = self.logger_context()
        self.assertEqual(event_dict["path"], "/v0/")
        self.assertEqual(event_dict["method"], "GET")
        self.assertEqual(event_dict["code"], 200)
        self.assertEqual(event_dict["agent"], "Smith")
        self.assertIsNotNone(event_dict["uid"])
        self.assertIsNotNone(event_dict["time"])
        self.assertIsNotNone(event_dict["t"])
        self.assertEqual(event_dict["errno"], 0)
        self.assertNotIn("lang", event_dict)
        self.assertNotIn("headers", event_dict)
        self.assertNotIn("body", event_dict)

    def test_userid_is_none_when_anonymous(self):
        self.app.get("/")
        event_dict = self.logger_context()
        self.assertNotIn("uid", event_dict)

    def test_lang_is_not_none_when_provided(self):
        self.app.get("/", headers={"Accept-Language": "fr-FR"})
        event_dict = self.logger_context()
        self.assertEqual(event_dict["lang"], "fr-FR")

    def test_agent_is_not_none_when_provided(self):
        self.app.get("/", headers={"User-Agent": "webtest/x.y.z"})
        event_dict = self.logger_context()
        self.assertEqual(event_dict["agent"], "webtest/x.y.z")

    def test_errno_is_specified_on_error(self):
        self.app.get("/unknown", status=404)
        event_dict = self.logger_context()
        self.assertEqual(event_dict["errno"], 111)

    def test_basic_authn_type_is_bound(self):
        app = self.make_app({"multiauth.policies": "basicauth"})
        app.get("/mushrooms", headers={"Authorization": "Basic bWF0OjE="})
        event_dict = self.logger_context()
        self.assertEqual(event_dict["authn_type"], "basicauth")

    def test_headers_and_body_when_level_is_debug(self):
        self.mocked.level = logging.DEBUG
        body = b'{"boom": 1}'
        self.app.post("/batch", body, headers=self.headers, status=400)
        event_dict = self.logger_context()
        self.assertEqual(
            event_dict["headers"],
            {
                "Authorization": "Basic bWF0OnNlY3JldA==",
                "Content-Length": "11",
                "Content-Type": "application/json",
                "Host": "localhost:80",
            },
        )
        self.assertEqual(event_dict["body"], body)

        self.maxDiff = None

        responseBody = event_dict["response"]["body"]
        self.assertEqual(json.loads(responseBody.decode("utf-8"))["error"], "Invalid parameters")
        responseHeaders = event_dict["response"]["headers"]
        self.assertEqual(
            sorted(responseHeaders.keys()),
            [
                "Access-Control-Expose-Headers",
                "Content-Length",
                "Content-Security-Policy",
                "Content-Type",
                "X-Content-Type-Options",
            ],
        )


class BatchSubrequestTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super().setUp()

        patch = mock.patch("kinto.core.views.batch.subrequest_logger")
        self.subrequest_mocked = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch("kinto.core.initialization.summary_logger")
        self.summary_mocked = patch.start()
        self.addCleanup(patch.stop)

        headers = {**self.headers, "User-Agent": "readinglist"}
        body = {
            "requests": [
                {"path": "/unknown", "headers": {"User-Agent": "foo"}},
                {"path": "/unknown2"},
            ]
        }
        self.app.post_json("/batch", body, headers=headers)

    def test_batch_global_request_is_preserved(self):
        args, kwargs = self.summary_mocked.info.call_args_list[-1]
        extra = kwargs["extra"]
        self.assertEqual(extra["code"], 200)
        self.assertEqual(extra["path"], "/v0/batch")
        self.assertEqual(extra["agent"], "readinglist")

    def test_batch_size_is_bound(self):
        args, kwargs = self.summary_mocked.info.call_args_list[-1]
        extra = kwargs["extra"]
        self.assertEqual(extra["batch_size"], 2)

    def test_subrequests_are_not_logged_as_request_summary(self):
        self.assertEqual(self.summary_mocked.info.call_count, 1)

    def test_subrequests_are_logged_as_subrequest_summary(self):
        self.assertEqual(self.subrequest_mocked.info.call_count, 2)
        args, kwargs = self.subrequest_mocked.info.call_args_list[-1]
        extra = kwargs["extra"]
        self.assertEqual(extra["path"], "/v0/unknown2")
        args, kwargs = self.subrequest_mocked.info.call_args_list[-2]
        extra = kwargs["extra"]
        self.assertEqual(extra["path"], "/v0/unknown")


class JsonFormatterTest(unittest.TestCase):
    def test_logger_name(self):
        JsonLogFormatter.init_from_settings({"project_name": "kintowe"})
        f = JsonLogFormatter()
        record = logging.LogRecord("app.log", logging.DEBUG, "", 0, "coucou", (), None)
        result = f.format(record)
        logged = json.loads(result)
        self.assertEqual(logged["Logger"], "kintowe")
        self.assertEqual(logged["Type"], "app.log")
        # See https://github.com/mozilla/mozilla-cloud-services-logger/issues/2
        self.assertEqual(logged["Fields"]["msg"], "coucou")
