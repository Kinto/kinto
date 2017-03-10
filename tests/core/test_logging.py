import unittest

import mock
from pyramid import testing

from kinto.core import DEFAULT_SETTINGS
from kinto.core import initialization

from .support import BaseWebTest


class RequestSummaryTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super().setUp()
        config = testing.setUp()
        config.registry.settings = DEFAULT_SETTINGS
        initialization.setup_logging(config)

        patch = mock.patch('kinto.core.initialization.summary_logger')
        self.mocked = patch.start()
        self.addCleanup(patch.stop)

    def logger_context(self):
        args, kwargs = self.mocked.info.call_args_list[-1]
        return kwargs['extra']

    def test_standard_info_is_bound(self):
        self.app.get('/', headers=self.headers)
        event_dict = self.logger_context()
        self.assertEqual(event_dict['path'], '/v0/')
        self.assertEqual(event_dict['method'], 'GET')
        self.assertEqual(event_dict['code'], 200)
        self.assertIsNotNone(event_dict['uid'])
        self.assertIsNotNone(event_dict['time'])
        self.assertIsNotNone(event_dict['t'])
        self.assertIsNone(event_dict['agent'])
        self.assertIsNone(event_dict['lang'])
        self.assertIsNone(event_dict['errno'])

    def test_userid_is_none_when_anonymous(self):
        self.app.get('/')
        event_dict = self.logger_context()
        self.assertIsNone(event_dict['uid'])

    def test_lang_is_not_none_when_provided(self):
        self.app.get('/', headers={'Accept-Language': 'fr-FR'})
        event_dict = self.logger_context()
        self.assertEqual(event_dict['lang'], 'fr-FR')

    def test_agent_is_not_none_when_provided(self):
        self.app.get('/', headers={'User-Agent': 'webtest/x.y.z'})
        event_dict = self.logger_context()
        self.assertEqual(event_dict['agent'], 'webtest/x.y.z')

    def test_errno_is_specified_on_error(self):
        self.app.get('/unknown', status=404)
        event_dict = self.logger_context()
        self.assertEqual(event_dict['errno'], 111)

    def test_basic_authn_type_is_bound(self):
        app = self.make_app({'multiauth.policies': 'basicauth'})
        app.get('/mushrooms', headers={'Authorization': 'Basic bWF0OjE='})
        event_dict = self.logger_context()
        self.assertEqual(event_dict['authn_type'], 'basicauth')


class BatchSubrequestTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super().setUp()

        patch = mock.patch('kinto.core.views.batch.subrequest_logger')
        self.subrequest_mocked = patch.start()
        self.addCleanup(patch.stop)

        patch = mock.patch('kinto.core.initialization.summary_logger')
        self.summary_mocked = patch.start()
        self.addCleanup(patch.stop)

        headers = {**self.headers, 'User-Agent': 'readinglist'}
        body = {
            'requests': [{
                'path': '/unknown',
                'headers': {'User-Agent': 'foo'}
            }, {
                'path': '/unknown2'
            }]
        }
        self.app.post_json('/batch', body, headers=headers)

    def test_batch_global_request_is_preserved(self):
        args, kwargs = self.summary_mocked.info.call_args_list[-1]
        extra = kwargs['extra']
        self.assertEqual(extra['code'], 200)
        self.assertEqual(extra['path'], '/v0/batch')
        self.assertEqual(extra['agent'], 'readinglist')

    def test_batch_size_is_bound(self):
        args, kwargs = self.summary_mocked.info.call_args_list[-1]
        extra = kwargs['extra']
        self.assertEqual(extra['batch_size'], 2)

    def test_subrequests_are_not_logged_as_request_summary(self):
        self.assertEqual(self.summary_mocked.info.call_count, 1)

    def test_subrequests_are_logged_as_subrequest_summary(self):
        self.assertEqual(self.subrequest_mocked.info.call_count, 2)
