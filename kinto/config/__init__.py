import os
import binascii
import codecs
from six.moves import input

HERE = os.path.abspath(os.path.dirname(__file__))

def render_template(template, destination, **kwargs):


   here = os.path.abspath(os.path.dirname(__file__))
   template = os.path.join(here, 'kinto.tpl') 
   destination = os.path.join(here, 'kinto.ini')

   with codecs.open(template, 'r', encoding='utf-8') as f:
        raw_template = f.read()
       
        rendered = raw_template.format(**kwargs)

        with codecs.open(destination, 'w+', encoding='utf-8') as output:
            output.write(rendered)


def init():
	values= {}
	values['secret'] = binascii.b2a_hex(os.urandom(32))

	backend = input("Which backend to use ? (1 - in-memory, 2 - postgresql, 3 - redis) :")

	if backend in ('2', ''):
	    values['storage_backend'] = "cliquet.storage.postgresql"
	    values['storage_url'] = "postgres://postgres:postgres@localhost/postgres"
	    values['cache_backend'] = "cliquet.cache.postgresql"
	    values['cache_url'] ="postgres://postgres:postgres@localhost/postgres"
	    values['permission_backend'] = "cliquet.permission.postgresql"
	    values['permission_url'] = "postgres://postgres:postgres@localhost/postgres"

	if backend == '3':
	    values['storage_backend'] = "cliquet.storage.redis"
            values['storage_url'] = "redis://localhos:6379/1"
	    values['cache_backend'] = "cliquet.cache.redis"
	    values['cache_url'] = "redis://localhos:6379/2"
	    values['permission_backend'] = "cliquet.permission.redis"
	    values['permission_url'] = "redis://localhos:6379/3"


	    
	    
        render_template("kinto.tpl", "kinto.ini",
		            secret = values['secret'],
		            storage_backend = values['storage_backend'],
		            storage_url = values['storage_url'],
		            cache_backend = values['cache_backend'],
		            cache_url = values['cache_url'],
		            permission_backend = values['permission_backend'],
		            permission_url = values['permission_url'])
