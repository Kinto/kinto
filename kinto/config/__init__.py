import os
import binascii
import codecs
from six.moves import input

HERE = os.path.abspath(os.path.dirname(__file__))

def render_template(template, destination, values):
   
   from pdb import set_trace; set_trace();

   here = os.path.abspath(os.path.dirname(__file__))
   template = os.path.join(here, 'kinto.tpl') 
   destination = os.path.join(here, 'kinto.ini')

   with codecs.open(template, 'r', encoding='utf-8') as f:
        raw_template = f.read()
       
        rendered = raw_template.format(**values)

        with codecs.open(destination, 'w', encoding='utf-8') as output:
            output.write(rendered)

def init(config_file, backend):
    values = {}
    values.update({'secret' : binascii.b2a_hex(os.urandom(32)),
                 'storage_backend' : "cliquet.storage.%s" % backend,
                 'cache_backend' : "cliquet.cache.%s" % backend,
                 'permission_backend' : "cliquet.permission.%s" % backend})

    if backend == 'postgresql':
        postgresql_url = "postgres://postgres:postgres@localhost/postgres"
        values.update({'storage_url' : postgresql_url,
                     'cache_url' : postgresql_url,
                     'permission_url' : postgresql_url})

    elif backend == 'redis':
        redis_url = "redis://localhost:6379"
        values.update({'storage_url' : redis_url + "/1",
                     'cache_url' : redis_url + "/2",
                     'permission_url' : redis_url + "/3"})

    else:
        values.update({'storage_url' : '',
                     'cache_url' : '',
                     'permission_url' : ''})

    render_template("kinto.tpl", config_file, values)
