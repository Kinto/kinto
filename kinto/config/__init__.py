import os
import codecs
from time import strftime

from kinto.core import utils as core_utils

from kinto import logger
from kinto import __version__

HERE = os.path.abspath(os.path.dirname(__file__))


def render_template(template, destination, **kwargs):
    template = os.path.join(HERE, template)
    folder = os.path.dirname(destination)

    if folder and not os.path.exists(folder):
        os.makedirs(folder)

    logger.info("Created config {}".format(os.path.abspath(destination)))

    with codecs.open(template, 'r', encoding='utf-8') as f:
        raw_template = f.read()
        rendered = raw_template.format_map(kwargs)
        with codecs.open(destination, 'w+', encoding='utf-8') as output:
            output.write(rendered)


def init(config_file, backend, host='127.0.0.1'):
    values = {}

    values['host'] = host
    values['secret'] = core_utils.random_bytes_hex(32)

    values['kinto_version'] = __version__
    values['config_file_timestamp'] = str(strftime('%a, %d %b %Y %H:%M:%S %z'))

    values['storage_backend'] = "kinto.core.storage.{}".format(backend)
    values['cache_backend'] = "kinto.core.cache.{}".format(backend)
    values['permission_backend'] = "kinto.core.permission.{}".format(backend)

    if backend == 'postgresql':
        postgresql_url = "postgres://postgres:postgres@localhost/postgres"
        values['storage_url'] = postgresql_url
        values['cache_url'] = postgresql_url
        values['permission_url'] = postgresql_url

    elif backend == 'redis':
        redis_url = "redis://localhost:6379"
        values['storage_backend'] = "kinto_redis.storage"
        values['cache_backend'] = "kinto_redis.cache"
        values['permission_backend'] = "kinto_redis.permission"

        values['storage_url'] = redis_url + "/1"
        values['cache_url'] = redis_url + "/2"
        values['permission_url'] = redis_url + "/3"

    else:
        values['storage_url'] = ''
        values['cache_url'] = ''
        values['permission_url'] = ''

    render_template("kinto.tpl", config_file, **values)
