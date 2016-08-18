# -*- coding: utf-8 -*-
import logging
import os
import re

import mock
import six
from pyramid import testing

from kinto.core import DEFAULT_SETTINGS
from kinto.core import initialization
from kinto.core import logs as core_logs
from kinto.core.utils import json

from .support import BaseWebTest, unittest


def logger_context():
    return core_logs.logger._context._dict


def strip_ansi(text):
    """
    Strip ANSI sequences (colors) from text.
    Source: http://stackoverflow.com/a/15780675
    """
    SEQUENCES = r'\x1b\[([0-9,A-Z]{1,2}(;[0-9]{1,2})?(;[0-9]{3})?)?[m|K]?'
    return re.sub(SEQUENCES, '', text)


class LoggingSetupTest(unittest.TestCase):
    def tearDown(self):
        super(LoggingSetupTest, self).tearDown()
        core_logs.structlog.reset_defaults()

    def test_classic_logger_is_used_by_default(self):
        config = testing.setUp()
        config.registry.settings = DEFAULT_SETTINGS
        classiclog_class = mock.patch('kinto.core.logs.ClassicLogRenderer')
        with classiclog_class as mocked:
            initialization.setup_logging(config)
            mocked.assert_called_with(DEFAULT_SETTINGS)

    def test_mozlog_logger_is_enabled_via_setting(self):
        mozlog_class = mock.patch('kinto.core.logs.MozillaHekaRenderer')
        classiclog_class = mock.patch('kinto.core.logs.ClassicLogRenderer')

        config = testing.setUp()
        with mock.patch.dict(config.registry.settings,
                             [('logging_renderer',
                               'kinto.core.logs.MozillaHekaRenderer')]):
            with mozlog_class as moz_mocked:
                with classiclog_class as classic_mocked:
                    initialization.setup_logging(config)
                    self.assertTrue(moz_mocked.called)
                    self.assertFalse(classic_mocked.called)


class ClassicLogRendererTest(unittest.TestCase):
    def setUp(self):
        self.renderer = core_logs.ClassicLogRenderer({})
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
        self.assertIn('nb_records=5', strip_ansi(value))

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
                          ' app.event nb_records=5'), strip_ansi(value))

    def test_fields_values_support_unicode(self):
        value = self.renderer(self.logger, 'critical', {'value': u'\u2014'})
        self.assertIn(u'\u2014', value)

    @unittest.skipIf(six.PY3, "Error with Python2 only")
    def test_fields_values_support_bytes(self):
        value = self.renderer(self.logger, 'critical',
                              {'event': AssertionError('\xc3\xa8')})
        self.assertIn(u'è', value)


class MozillaHekaRendererTest(unittest.TestCase):
    def setUp(self):
        self.settings = {'project_name': ''}
        self.renderer = core_logs.MozillaHekaRenderer(self.settings)
        self.logger = logging.getLogger(__name__)

    def test_output_is_serialized_json(self):
        value = self.renderer(self.logger, 'debug', {})
        self.assertIsInstance(value, six.string_types)

    def test_standard_entries_are_filled(self):
        with mock.patch('kinto.core.utils.msec_time', return_value=12):
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
        renderer = core_logs.MozillaHekaRenderer(self.settings)
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

    def test_objects_values_are_serialized_as_string(self):
        querystring = {'_sort': 'name'}
        logged = self.renderer(self.logger, 'info', {'params': querystring})
        log = json.loads(logged)
        self.assertEqual(log['Fields']['params'], json.dumps(querystring))

    def test_list_of_homogeneous_values_are_serialized_as_string(self):
        list_values = ['life', 'of', 'pi', 3.14]
        logged = self.renderer(self.logger, 'info', {'params': list_values})
        log = json.loads(logged)
        self.assertEqual(log['Fields']['params'], json.dumps(list_values))

    def test_list_of_string_values_are_not_serialized(self):
        list_values = ['life', 'of', 'pi']
        logged = self.renderer(self.logger, 'info', {'params': list_values})
        log = json.loads(logged)
        self.assertEqual(log['Fields']['params'], list_values)


class RequestSummaryTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(RequestSummaryTest, self).setUp()
        config = testing.setUp()
        config.registry.settings = DEFAULT_SETTINGS
        initialization.setup_logging(config)

    def tearDown(self):
        super(RequestSummaryTest, self).tearDown()
        core_logs.structlog.reset_defaults()

    def test_request_summary_is_sent_as_info(self):
        with mock.patch('kinto.core.logs.logger.info') as mocked:
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

    def test_basic_authn_type_is_bound(self):
        app = self.make_app({'multiauth.policies': 'basicauth'})
        app.get('/mushrooms', headers={'Authorization': 'Basic bWF0OjE='})
        event_dict = logger_context()
        self.assertEqual(event_dict['authn_type'], 'basicauth')


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

    def test_subrequests_are_not_logged_as_request_summary(self):
        with mock.patch('kinto.core.logs.logger.info') as log_patched:
            body = {
                'requests': [{'path': '/unknown1'}, {'path': '/unknown2'}]
            }
            self.app.post_json('/batch', body)
            self.assertEqual(log_patched.call_count, 1)
            log_patched.assert_called_with('request.summary')

    def test_subrequests_are_logged_as_subrequest_summary(self):
        with mock.patch('kinto.core.logger.new') as log_patched:
            body = {
                'requests': [{'path': '/unknown1'}, {'path': '/unknown2'}]
            }
            self.app.post_json('/batch', body)
            self.assertEqual(log_patched().info.call_count, 2)
            log_patched().info.assert_called_with('subrequest.summary')


class ResourceInfoTest(BaseWebTest, unittest.TestCase):
    def setUp(self):
        super(ResourceInfoTest, self).setUp()
        config = testing.setUp()
        config.registry.settings = DEFAULT_SETTINGS
        initialization.setup_logging(config)

    def tearDown(self):
        super(ResourceInfoTest, self).tearDown()
        core_logs.structlog.reset_defaults()

    def test_collection_id_is_bound(self):
        self.app.get('/mushrooms', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['collection_id'], 'mushroom')

    def test_collection_timestamp_is_bound(self):
        r = self.app.get('/mushrooms', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['collection_timestamp'],
                         int(r.headers['ETag'][1:-1]))

    def test_result_size_and_limit_are_bound(self):
        for name in ['a', 'b', 'c']:
            body = {'data': {'name': name}}
            self.app.post_json('/mushrooms', body, headers=self.headers)

        self.app.get('/mushrooms?_limit=5', headers=self.headers)
        event_dict = logger_context()
        self.assertEqual(event_dict['limit'], 5)
        self.assertEqual(event_dict['nb_records'], 3)
