import codecs
import mock
import os
import tempfile
import unittest

from kinto.config import render_template, init


class ConfigTest(unittest.TestCase):
    def test_transpose_parameters_into_template(self):
        self.maxDiff = None
        template = "kinto.tpl"
        dest = tempfile.mktemp()
        render_template(template, dest,
                        secret='secret',
                        storage_backend='storage_backend',
                        cache_backend='cache_backend',
                        permission_backend='permission_backend',
                        storage_url='storage_url',
                        cache_url='cache_url',
                        permission_url='permission_url')

        with codecs.open(dest, 'r', encoding='utf-8') as d:
            destination_temp = d.read()

        sample_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                   "test_configuration/test.ini")
        with codecs.open(sample_path, 'r', encoding='utf-8') as c:
            sample = c.read()

        self.assertEqual(destination_temp, sample)

    def test_create_destination_directory(self):
        dest = os.path.join(tempfile.mkdtemp(), 'config', 'kinto.ini')

        render_template("kinto.tpl", dest,
                        secret='secret',
                        storage_backend='storage_backend',
                        cache_backend='cache_backend',
                        permission_backend='permission_backend',
                        storage_url='storage_url',
                        cache_url='cache_url',
                        permission_url='permission_url')

        self.assertTrue(os.path.exists(dest))

    @mock.patch('kinto.config.render_template')
    def test_init_postgresql_values(self, mocked_render_template):
        init('kinto.ini', 'postgresql')

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
            'permission_url': postgresql_url
        })

    @mock.patch('kinto.config.render_template')
    def test_init_redis_values(self, mocked_render_template):
        init('kinto.ini', 'redis')

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
            'permission_url': redis_url + '/3'
        })

    @mock.patch('kinto.config.render_template')
    def test_init_memory_values(self, mocked_render_template):
        init('kinto.ini', 'memory')

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEquals(args, ('kinto.tpl', 'kinto.ini'))

        self.assertDictEqual(kwargs, {
            'secret': kwargs['secret'],
            'storage_backend': 'cliquet.storage.memory',
            'cache_backend': 'cliquet.cache.memory',
            'permission_backend': 'cliquet.permission.memory',
            'storage_url': '',
            'cache_url':  '',
            'permission_url': ''
        })
