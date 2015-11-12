import os
import binascii

def render_template(template, destination, **kwargs):

<<<<<<< HEAD
    here = os.path.abspath(os.path.dirname(__file__))
    template = os.path.join(here, 'kinto.tpl') 
    destination = os.path.join(here, 'kinto.ini')   
    
=======
   here = os.path.abspath(os.path.dirname(__file__))
   template = os.path.join(here, 'kinto.tpl') 
   destination = os.path.join(here, 'kinto.ini')

>>>>>>> master
    with open(template, 'r') as f:
        raw_template = f.read()
       
        rendered = raw_template.format(**kwargs)

        with open(destination, 'w+') as output:
            output.write(rendered)


def init():
	values= {}
	values['secret'] = binascii.b2a_hex(os.urandom(32))

	backend = raw_input("Which backend to use ? (1 - in-memory, 2 - postgresql, 3 - redis) :")

	if backend == '':
	    backend = '2';     #default

	if backend == '2':
	    values['storage_backend'] = "cliquet.storage.postgresql"
	    values['storage_url'] = "postgres://postgres:postgres@localhost/postgres"
	    values['cache_backend'] = "cliquet.cache.postgresql"
	    values['cache_url'] ="postgres://postgres:postgres@localhost/postgres"
	    values['permission_backend'] = "cliquet.permission.postgresql"
	    values['permission_url'] = "postgres://postgres:postgres@localhost/postgres"


	    
	    
	    render_template("kinto.tpl", "kinto.ini",
		            secret = values['secret'],
		            storage_backend = values['storage_backend'],
		            storage_url = values['storage_url'],
		            cache_backend = values['cache_backend'],
		            cache_url = values['cache_url'],
		            permission_backend = values['permission_backend'],
		            permission_url = values['permission_url']
		            )


