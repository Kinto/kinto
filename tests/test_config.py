import codecs
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from time import strftime
from unittest import mock

from kinto import __version__, config


class ConfigTest(unittest.TestCase):
    def _assertTimestampStringsAlmostEqual(self, s1, s2, delta=timedelta(seconds=1)):
        """Assert that two timestamp strings are almost equal, within a
        specified timedelta.

        :param s1: a string representing a timestamp with the format
            format %a, %d %b %Y %H:%M:%S %z
        :param s2: a string representing a timestamp with the format
            format %a, %d %b %Y %H:%M:%S %z
        :param delta: timedelta, default is 1 second
        :returns: True, if time between s1 and s2 is less than delta.
            False, otherwise.

        """
        s1 = datetime.strptime(s1, "%a, %d %b %Y %H:%M:%S %z")
        s2 = datetime.strptime(s2, "%a, %d %b %Y %H:%M:%S %z")

        return self.assertLessEqual(
            abs(s1 - s2),
            delta,
            f"Delta between {s1} and {s2} is {s1 - s2}. Expected difference "
            f"to be less than or equal to {delta}",
        )

    def test_transpose_parameters_into_template(self):
        self.maxDiff = None
        template = "kinto.tpl"
        dest = tempfile.mktemp()
        config.render_template(
            template,
            dest,
            host="127.0.0.1",
            secret="secret",
            bucket_id_salt="bucket_id_salt",
            storage_backend="storage_backend",
            cache_backend="cache_backend",
            permission_backend="permission_backend",
            storage_url="storage_url",
            cache_url="cache_url",
            permission_url="permission_url",
            kinto_version="kinto_version",
            config_file_timestamp="config_file_timestamp",
        )

        with codecs.open(dest, "r", encoding="utf-8") as d:
            destination_temp = d.read()

        sample_path = os.path.join(os.path.dirname(__file__), "test_configuration/test.ini")
        with codecs.open(sample_path, "r", encoding="utf-8") as c:
            sample = c.read()

        self.assertEqual(destination_temp, sample)

    def test_create_destination_directory(self):
        dest = os.path.join(tempfile.mkdtemp(), "config", "kinto.ini")

        config.render_template(
            "kinto.tpl",
            dest,
            host="127.0.0.1",
            secret="secret",
            bucket_id_salt="bucket_id_salt",
            storage_backend="storage_backend",
            cache_backend="cache_backend",
            permission_backend="permission_backend",
            storage_url="storage_url",
            cache_url="cache_url",
            permission_url="permission_url",
            kinto_version="kinto_version",
            config_file_timestamp="config_file_timestamp",
        )

        self.assertTrue(os.path.exists(dest))

    @mock.patch("kinto.config.render_template")
    def test_hmac_secret_is_text(self, mocked_render_template):
        config.init("kinto.ini", backend="postgresql", cache_backend="postgresql")
        args, kwargs = list(mocked_render_template.call_args)
        self.assertEqual(type(kwargs["secret"]), str)

    @mock.patch("kinto.config.render_template")
    def test_bucket_id_salt_is_text(self, mocked_render_template):
        config.init("kinto.ini", backend="postgresql", cache_backend="postgresql")
        args, kwargs = list(mocked_render_template.call_args)
        self.assertEqual(type(kwargs["bucket_id_salt"]), str)

    @mock.patch("kinto.config.render_template")
    def test_init_postgresql_values(self, mocked_render_template):
        self.maxDiff = None
        config.init("kinto.ini", backend="postgresql", cache_backend="postgresql")

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEqual(args, ("kinto.tpl", "kinto.ini"))

        postgresql_url = "postgresql://postgres:postgres@localhost/postgres"
        self.assertDictEqual(
            kwargs,
            {
                "host": "127.0.0.1",
                "secret": kwargs["secret"],
                "bucket_id_salt": kwargs["bucket_id_salt"],
                "storage_backend": "kinto.core.storage.postgresql",
                "cache_backend": "kinto.core.cache.postgresql",
                "permission_backend": "kinto.core.permission.postgresql",
                "storage_url": postgresql_url,
                "cache_url": postgresql_url,
                "permission_url": postgresql_url,
                "kinto_version": __version__,
                "config_file_timestamp": mock.ANY,
            },
        )

        self._assertTimestampStringsAlmostEqual(
            strftime("%a, %d %b %Y %H:%M:%S %z"),  # expected
            kwargs["config_file_timestamp"],  # actual
        )

    @mock.patch("kinto.config.render_template")
    def test_init_postgresql_memcached_values(self, mocked_render_template):
        config.init("kinto.ini", backend="postgresql", cache_backend="memcached")

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEqual(args, ("kinto.tpl", "kinto.ini"))

        postgresql_url = "postgresql://postgres:postgres@localhost/postgres"
        cache_url = "127.0.0.1:11211 127.0.0.2:11211"
        self.assertDictEqual(
            kwargs,
            {
                "host": "127.0.0.1",
                "secret": kwargs["secret"],
                "bucket_id_salt": kwargs["bucket_id_salt"],
                "storage_backend": "kinto.core.storage.postgresql",
                "cache_backend": "kinto.core.cache.memcached",
                "permission_backend": "kinto.core.permission.postgresql",
                "storage_url": postgresql_url,
                "cache_url": cache_url,
                "permission_url": postgresql_url,
                "kinto_version": __version__,
                "config_file_timestamp": mock.ANY,
            },
        )

        self._assertTimestampStringsAlmostEqual(
            strftime("%a, %d %b %Y %H:%M:%S %z"),  # expected
            kwargs["config_file_timestamp"],  # actual
        )

    @mock.patch("kinto.config.render_template")
    def test_init_memory_values(self, mocked_render_template):
        config.init("kinto.ini", backend="memory", cache_backend="memory")

        args, kwargs = list(mocked_render_template.call_args)
        self.assertEqual(args, ("kinto.tpl", "kinto.ini"))

        self.assertDictEqual(
            kwargs,
            {
                "host": "127.0.0.1",
                "secret": kwargs["secret"],
                "bucket_id_salt": kwargs["bucket_id_salt"],
                "storage_backend": "kinto.core.storage.memory",
                "cache_backend": "kinto.core.cache.memory",
                "permission_backend": "kinto.core.permission.memory",
                "storage_url": "",
                "cache_url": "",
                "permission_url": "",
                "kinto_version": __version__,
                "config_file_timestamp": mock.ANY,
            },
        )

        self._assertTimestampStringsAlmostEqual(
            strftime("%a, %d %b %Y %H:%M:%S %z"),  # expected
            kwargs["config_file_timestamp"],  # actual
        )

    def test_render_template_works_with_file_in_cwd(self):
        temp_path = tempfile.mkdtemp()
        os.chdir(temp_path)
        config.render_template(
            "kinto.tpl",
            "kinto.ini",
            **{
                "host": "127.0.0.1",
                "secret": "abcd-ceci-est-un-secret",
                "bucket_id_salt": "backet-id-salt-random",
                "storage_backend": "kinto.core.storage.memory",
                "cache_backend": "kinto.core.cache.memory",
                "permission_backend": "kinto.core.permission.memory",
                "storage_url": "",
                "cache_url": "",
                "permission_url": "",
                "kinto_version": "",
                "config_file_timestamp": "",
            },
        )
        self.assertTrue(os.path.exists(os.path.join(temp_path, "kinto.ini")))
