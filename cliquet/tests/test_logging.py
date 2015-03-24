import logging
import os

import mock
import six
from pyramid import testing

from cliquet import DEFAULT_SETTINGS
from cliquet import logs as cliquet_logs
from cliquet.utils import json

from .support import BaseWebTest, unittest


def logger_context():
    return cliquet_logs.logger._context._dict


class LoggingSetupTest(BaseWebTest, unittest.TestCase):
    def test_classic_logger_is_used_by_default(self):
        config = testing.setUp()
        config.registry.settings = DEFAULT_SETTINGS
        classiclog_class = mock.patch('cliquet.logs.ClassicLogRenderer')
        with classiclog_class as mocked:
            cliquet_logs.setup_logging(config)
            mocked.assert_called()

    def test_mozlog_logger_is_enabled_via_setting(self):
        mozlog_class = mock.patch('cliquet.logs.MozillaHekaRenderer')
        classiclog_class = mock.patch('cliquet.logs.ClassicLogRenderer')

        config = testing.setUp()
        with mock.patch.dict(config.registry.settings,
                             [('cliquet.logging_renderer',
                               'cliquet.logs.MozillaHekaRenderer')]):
            with mozlog_class as moz_mocked:
                with classiclog_class as classic_mocked:
                    cliquet_logs.setup_logging(config)
                    self.assertTrue(moz_mocked.called)
                    self.assertFalse(classic_mocked.called)


class ClassicLogRendererTest(unittest.TestCase):
    def setUp(self):
        self.renderer = cliquet_logs.ClassicLogRenderer({})
        self.logger = logging.getLogger(__name__)

    def test_output_is_serialized_as_string(self):
        value = self.renderer(self.logger, 'debug', {})
        self.assertIsInstance(value, six.string_types)

    def test_output_is_simple_if_no_request_is_bound(self):
        value = self.renderer(self.logger, 'debug', {'event': ':)'})
        self.assertNotIn('? ms', value)

    def test_values_are_defaulted_to_question_mark(self):
        value = self.renderer(self.logger, 'debug', {'path': '/'})
        self.assertIn('? ms', value)

    def test_querystring_is_rendered_as_string(self):
        event_dict = {
            'path': '/',
            'querystring': {'param': 'val'}
        }
        value = self.renderer(self.logger, 'debug', event_dict)
        self.assertIn('/?param=val', value)

    def test_extra_event_infos_is_rendered_as_key_values(self):
        event_dict = {
            'nb_records': 5,
        }
        value = self.renderer(self.logger, 'debug', event_dict)
        self.assertIn('nb_records=5', value)

    def test_every_event_dict_entry_appears_in_log_message(self):
        event_dict = {
            'method': 'GET',
            'path': '/v1/',
            'querystring': {'_sort': 'field'},
            'code': 200,
            't': 32,
            'event': 'app.event',
            'nb_records': 5
        }
        value = self.renderer(self.logger, 'debug', event_dict)
        self.assertEqual(('"GET   /v1/?_sort=field" 200 (32 ms)'
                          ' app.event nb_records=5'), value)

    def test_fields_values_support_unicode(self):
        value = self.renderer(self.logger, 'critical', {'value': u'\u2014'})
        self.assertIn(u'\u2014', value)


class MozillaHekaRendererTest(unittest.TestCase):
    def setUp(self):
        self.settings = {'cliquet.project_name': ''}
        self.renderer = cliquet_logs.MozillaHekaRenderer(self.settings)
        self.logger = logging.getLogger(__name__)

    def test_output_is_serialized_json(self):
        value = self.renderer(self.logger, 'debug', {})
        self.assertIsInstance(value, six.string_types)

    def test_standard_entries_are_filled(self):
        with mock.patch('cliquet.utils.msec_time', return_value=12):
            value = self.renderer(self.logger, 'debug', {})

        log = json.loads(value)
        self.assertDictEqual(log, {
            'EnvVersion': '2.0',
            'Hostname': os.uname()[1],
            'Logger': '',
            'Pid': os.getpid(),
            'Severity': 7,
            'Timestamp': 12000000,
            'Type': '',
            'Fields': {}
        })

    def test_hostname_can_be_specified_via_environment(self):
        os.environ['HOSTNAME'] = 'abc'
        renderer = cliquet_logs.MozillaHekaRenderer(self.settings)
        os.environ.pop('HOSTNAME')
        self.assertEqual(renderer.hostname, 'abc')

    def test_standard_entries_are_not_overwritten(self):
        value = self.renderer(self.logger, 'debug', {'Hostname': 'her'})
        log = json.loads(value)
        self.assertEqual(log['Hostname'], 'her')

    def test_type_comes_from_structlog_event(self):
        value = self.renderer(self.logger, 'debug', {'event': 'booh'})
        log = json.loads(value)
        self.assertEqual(log['Type'], 'booh')

    def test_severity_comes_from_logger_name(self):
        value = self.renderer(self.logger, 'critical', {})
        log = json.loads(value)
        self.assertEqual(log['Severity'], 0)

    def test_unknown_fields_are_moved_to_fields_entry(self):
        value = self.renderer(self.logger, 'critical', {'win': 11})
        log = json.loads(value)
        self.assertEqual(log['Fields'], {'win': 11})

    def test_fields_can_be_provided_directly(self):
        value = self.renderer(self.logger, 'critical', {'Fields': {'win': 11}})
        log = json.loads(value)
        self.assertEqual(log['Fields'], {'win': 11})


class RequestSummaryTest(BaseWebTest, unittest.TestCase):
    def test_request_summary_is_sent_as_info(self):
        with mock.patch('cliquet.logs.logger.info') as mocked:
            self.app.get('/')
            mocked.assert_called_with('request.summary')

    def test_standard_info_is_bound(self):
        self.app.get('/', headers=self.headers)
        event_dict = logger_context()
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
        event_dict = logger_context()
        self.assertIsNone(event_dict['uid'])

    def test_lang_is_not_none_when_provided(self):
        self.app.get('/', headers={'Accept-Language': 'fr-FR'})
        event_dict = logger_context()
        self.assertEqual(event_dict['lang'], 'fr-FR')

    def test_agent_is_not_none_when_provided(self):
        self.app.get('/', headers={'User-Agent': 'webtest/x.y.z'})
        event_dict = logger_context()
        self.assertEqual(event_dict['agent'], 'webtest/x.y.z')

    def test_errno_is_specified_on_error(self):
        self.app.get('/unknown', status=404)
        event_dict = logger_context()
        self.assertEqual(event_dict['errno'], 111)

    def test_fxa_auth_type_is_bound(self):
        self.app.get('/mushrooms', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['auth_type'], 'FxA')

    def test_basic_auth_type_is_bound(self):
        with mock.patch.dict(self.app.app.registry.settings,
                             [('cliquet.basic_auth_enabled', 'true')]):
            self.app.get('/mushrooms',
                         headers={'Authorization': 'Basic bmlrbzpuaWtv'})
        event_dict = logger_context()
        self.assertEqual(event_dict['auth_type'], 'Basic')


class BatchSubrequestTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(BatchSubrequestTest, self).setUp()
        headers = self.headers.copy()
        headers['User-Agent'] = 'readinglist'
        body = {
            'requests': [{
                'path': '/unknown',
                'headers': {'User-Agent': 'foo'}
            }]
        }
        self.app.post_json('/batch', body, headers=headers)

    def test_batch_global_request_is_preserved(self):
        event_dict = logger_context()
        self.assertEqual(event_dict['code'], 200)
        self.assertEqual(event_dict['path'], '/batch')
        self.assertEqual(event_dict['agent'], 'readinglist')

    def test_batch_size_is_bound(self):
        event_dict = logger_context()
        self.assertEqual(event_dict['batch_size'], 1)

    def test_subrequest_summaries_are_logged(self):
        # XXX: how ?
        pass


class ResourceInfoTest(BaseWebTest, unittest.TestCase):
    def test_resource_name_is_bound(self):
        self.app.get('/mushrooms', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['resource_name'], 'mushroom')

    def test_resource_timestamp_is_bound(self):
        r = self.app.get('/mushrooms', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['resource_timestamp'],
                         int(r.headers['Last-Modified']))

    def test_result_size_and_limit_are_bound(self):
        self.app.post_json('/mushrooms', {'name': 'a'}, headers=self.headers)
        self.app.post_json('/mushrooms', {'name': 'b'}, headers=self.headers)
        self.app.post_json('/mushrooms', {'name': 'c'}, headers=self.headers)

        self.app.get('/mushrooms?_limit=5', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['limit'], 5)
        self.assertEqual(event_dict['nb_records'], 3)
