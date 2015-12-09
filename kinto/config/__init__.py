import os
import binascii
import codecs

HERE = os.path.abspath(os.path.dirname(__file__))


def render_template(template, destination, **kwargs):
    template = os.path.join(HERE, template)

    folder = os.path.dirname(destination)
    os.makedirs(folder)

    with codecs.open(template, 'r', encoding='utf-8') as f:
        raw_template = f.read()
        rendered = raw_template.format(**kwargs)
        with codecs.open(destination, 'w+', encoding='utf-8') as output:
            output.write(rendered)


def init(config_file, backend):
    values = {}
    values['secret'] = binascii.b2a_hex(os.urandom(32))

    values['storage_backend'] = "cliquet.storage.%s" % backend
    values['cache_backend'] = "cliquet.cache.%s" % backend
    values['permission_backend'] = "cliquet.permission.%s" % backend

    if backend == 'postgresql':
        postgresql_url = "postgres://postgres:postgres@localhost/postgres"
        values['storage_url'] = postgresql_url
        values['cache_url'] = postgresql_url
        values['permission_url'] = postgresql_url

    elif backend == 'redis':
        redis_url = "redis://localhost:6379"
        values['storage_url'] = redis_url + "/1"
        values['cache_url'] = redis_url + "/2"
        values['permission_url'] = redis_url + "/3"

    else:
        values['storage_url'] = ''
        values['cache_url'] = ''
        values['permission_url'] = ''

    render_template("kinto.tpl", config_file, **values)
