import os
import binascii

def render_template(template, destination, **kwargs):
    with open(template, 'r') as f:
        raw_template = f.read()
        rendered = raw_template.format(**kwargs)

        with open(destination, 'w+') as output:
            output.write(rendered)


render_template("kinto.tpl", "kinto.ini", secret=binascii.b2a_hex(os.urandom(8)))

