import os
import binascii

def render_template(template, destination, **kwargs):
    with open(template, 'r') as f:
        raw_template = f.read()
        rendered = raw_template.format(**kwargs)

        with open(destination, 'w+') as output:
            output.write(rendered)

backend = raw_input("Which backend to use ? (1 - in-memory, 2 - postgresql, 3 - redis) :")
if backend == '':
    backend = 2;     #default

if backend == 2:
    render_template("kinto.tpl", "kinto.ini",
                    secret=binascii.b2a_hex(os.urandom(32)),
                    storage_backend = "cliquet.storage.postgresql",
                    storage_url = "postgres://postgres:postgres@localhost/postgres",
                    cache_backend = "cliquet.cache.postgresql",
                    cache_url ="postgres://postgres:postgres@localhost/postgres",
                    permission_backend = "cliquet.permission.postgresql",
                    permission_url = "postgres://postgres:postgres@localhost/postgres"
                    )
