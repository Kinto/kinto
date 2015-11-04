import ConfigParser
import sys
import os,binascii

cfgfile = open("/kinto/kinto/scripts/kinto.ini",'w') #enter path of file
parser = ConfigParser.SafeConfigParser()

parser.add_section('app:main')
parser.set('app:main', 'use', 'egg:kinto')

parser.set('','pyramid.debug_notfound', 'true')
parser.set('','kinto.http_scheme', 'http')
parser.set('','kinto.http_host','localhost:8888')


parser.set('','kinto.userid_hmac_secret', binascii.b2a_hex(os.urandom(8)))
parser.set('','multiauth.policies','basicauth')

#to Do: ask question about uwsgi
parser.add_section('uwsgi')
parser.set('uwsgi','wsgi-file','app.wsgi')
parser.set('uwsgi','enable-threads','true')
parser.set('uwsgi','socket','127.0.0.1:8888')
parser.set('uwsgi','chmod-socket','666')
parser.set('uwsgi','cheaper-algo','busyness')
parser.set('uwsgi','cheaper','1')
parser.set('uwsgi','cheaper-initial','1')
parser.set('uwsgi','workers','2')
parser.set('uwsgi','cheaper-step','1')
parser.set('uwsgi','cheaper-overload','30')
parser.set('uwsgi','cheaper-busyness-verbose','true')
parser.set('uwsgi','master','true')
parser.set('uwsgi','module','kinto')
parser.set('uwsgi','harakiri','120')
parser.set('uwsgi','virtualenv','.venv/')
parser.set('uwsgi','lazy','true')
parser.set('uwsgi','lazy-apps','true')
parser.set('uwsgi','single-interpreter','true')
parser.set('uwsgi','buffer-size','65535')
parser.set('uwsgi','post-buffering','65535')




parser.add_section('server:main')
parser.set('server:main','use','egg:waitress')
parser.set('server:main','host','0.0.0.0')
parser.set('server:main','port','8888')

# Begin logging configuration

parser.add_section('loggers')
parser.set('loggers','keys','root, cliquet, kinto')

parser.add_section('handlers')
parser.set('handlers','keys','console')

parser.add_section('formatters')
parser.set('formatters','keys','generic')

parser.add_section('logger_root')
parser.set('logger_root','level','INFO')
parser.set('logger_root','handlers','console')

parser.add_section('logger_cliquet')
parser.set('logger_cliquet','level','DEBUG')
parser.set('logger_cliquet','handlers','')
parser.set('logger_cliquet','qualname','cliquet')

parser.add_section('logger_kinto')
parser.set('logger_kinto','level','DEBUG')
parser.set('logger_kinto','handlers','')
parser.set('logger_kinto','qualname','kinto')

parser.add_section('handler_console')
parser.set('handler_console','class','StreamHandler')
parser.set('handler_console','args','(sys.stderr,)')
parser.set('handler_console','level','NOTSET')
parser.set('handler_console','formatter','generic')

#to do: add formatter_generic



parser.write(cfgfile)
