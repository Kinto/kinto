import codecs
import mock
import os
import tempfile
import unittest
from time import strftime

import six

from kinto import config
from kinto import __version__


class ConfigTest(unittest.TestCase):
    def test_transpose_parameters_into_template(self):
        self.maxDiff = None
        template = "kinto.tpl"
        dest = tempfile.mktemp()
        config.render_template(template, dest,
                               secret='secret',
                               storage_backend='storage_backend',
                               cache_backend='cache_backend',
                               permission_backend='permission_backend',
                               storage_url='storage_url',
                               cache_url='cache_url',
                               permission_url='permission_url',
                               kinto_version='kinto_version',
                               config_file_timestamp='config_file_timestamp')

        with codecs.open(dest, 'r', encoding='utf-8') as d:
            destination_temp = d.read()

        sample_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   "test_configuration/test.ini")
        with codecs.open(sample_path, 'r', encoding='utf-8') as c:
            sample = c.read()

        self.assertEqual(destination_temp, sample)

    def test_create_destination_directory(self):
        dest = os.path.join(tempfile.mkdtemp(), 'config', 'kinto.ini')

        config.render_template("kinto.tpl", dest,
                               secret='secret',
                               storage_backend='storage_backend',
                               cache_backend='cache_backend',
                               permission_backend='permission_backend',
                               storage_url='storage_url',
                               cache_url='cache_url',
                               permission_url='permission_url',
                               kinto_version='kinto_version',
                               config_file_timestamp='config_file_timestamp')

        self.assertTrue(os.path.exists(dest))

    @mock.patch('kinto.config.render_template')
    def test_hmac_secret_is_text(self, mocked_render_template):
        config.init('kinto.ini', 'postgresql')
        args, kwargs = list(mocked_render_template.call_args)
        self.assertEquals(type(kwargs['secret']), six.text_type)

    @mock.patch('kinto.config.render_template')
    def test_init_postgresql_values(self, mocked_render_template):
        config.init('kinto.ini', 'postgresql')

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEquals(args, ('kinto.tpl', 'kinto.ini'))

        postgresql_url = "postgres://postgres:postgres@localhost/postgres"
        self.assertDictEqual(kwargs, {
            'secret': kwargs['secret'],
            'storage_backend': 'cliquet.storage.postgresql',
            'cache_backend': 'cliquet.cache.postgresql',
            'permission_backend': 'cliquet.permission.postgresql',
            'storage_url': postgresql_url,
            'cache_url':  postgresql_url,
            'permission_url': postgresql_url,
            'kinto_version': __version__,
            'config_file_timestamp': strftime('%a, %d %b %Y %H:%M:%S %z')
        })

    @mock.patch('kinto.config.render_template')
    def test_init_redis_values(self, mocked_render_template):
        config.init('kinto.ini', 'redis')

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEquals(args, ('kinto.tpl', 'kinto.ini'))

        redis_url = "redis://localhost:6379"
        self.assertDictEqual(kwargs, {
            'secret': kwargs['secret'],
            'storage_backend': 'cliquet.storage.redis',
            'cache_backend': 'cliquet.cache.redis',
            'permission_backend': 'cliquet.permission.redis',
            'storage_url': redis_url + '/1',
            'cache_url':  redis_url + '/2',
            'permission_url': redis_url + '/3',
            'kinto_version': __version__,
            'config_file_timestamp': strftime('%a, %d %b %Y %H:%M:%S %z')
        })

    @mock.patch('kinto.config.render_template')
    def test_init_memory_values(self, mocked_render_template):
        config.init('kinto.ini', 'memory')

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEquals(args, ('kinto.tpl', 'kinto.ini'))

        self.assertDictEqual(kwargs, {
            'secret': kwargs['secret'],
            'storage_backend': 'cliquet.storage.memory',
            'cache_backend': 'cliquet.cache.memory',
            'permission_backend': 'cliquet.permission.memory',
            'storage_url': '',
            'cache_url':  '',
            'permission_url': '',
            'kinto_version': __version__,
            'config_file_timestamp': strftime('%a, %d %b %Y %H:%M:%S %z')
        })

    def test_render_template_creates_directory_if_necessary(self):
        temp_path = tempfile.mkdtemp()
        destination = os.path.join(temp_path, 'config/kinto.ini')
        config.render_template('kinto.tpl', destination, **{
            'secret': "abcd-ceci-est-un-secret",
            'storage_backend': 'cliquet.storage.memory',
            'cache_backend': 'cliquet.cache.memory',
            'permission_backend': 'cliquet.permission.memory',
            'storage_url': '',
            'cache_url':  '',
            'permission_url': '',
            'kinto_version': '',
            'config_file_timestamp': ''
        })
        self.assertTrue(os.path.exists(destination))

    def test_render_template_works_with_file_in_cwd(self):
        temp_path = tempfile.mkdtemp()
        os.chdir(temp_path)
        config.render_template('kinto.tpl', 'kinto.ini', **{
            'secret': "abcd-ceci-est-un-secret",
            'storage_backend': 'cliquet.storage.memory',
            'cache_backend': 'cliquet.cache.memory',
            'permission_backend': 'cliquet.permission.memory',
            'storage_url': '',
            'cache_url':  '',
            'permission_url': '',
            'kinto_version': '',
            'config_file_timestamp': ''
        })
        self.assertTrue(os.path.exists(
            os.path.join(temp_path, 'kinto.ini')
        ))
