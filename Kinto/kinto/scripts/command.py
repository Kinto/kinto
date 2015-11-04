import ConfigParser
import sys
import os,binascii

cfgfile = open("kinto/config/kinto.ini",'w') #enter path of file
parser = ConfigParser.SafeConfigParser()

parser.add_section('app:main')
parser.set('app:main', 'use', 'egg:kinto')

parser.set('','pyramid.debug_notfound', 'true')
parser.set('','kinto.http_scheme', 'http')
parser.set('','kinto.http_host','localhost:8888')



parser.add_section('backends')
backend = raw_input("cache backend? ")
parser.set('backends','kinto.cache_backend',backend) # = cliquet.cache.postgresql
cache_url = raw_input("cache url? ")
parser.set('backends','kinto.cache_url',cache_url)# postgres://postgres:postgres@localhost/postgres
storage = raw_input("storage at backend? ")
parser.set('backends','kinto.storage_backend',storage)# = cliquet.storage.postgresql
storage_url = raw_input("storage url? ")
parser.set('backends','kinto.storage_url',storage_url)# = postgres://postgres:postgres@localhost/postgres
permission = raw_input("set permission at backend: ")
parser.set('backends','kinto.permission_backend',permission)# = cliquet.permission.postgresql
permission_url = raw_input("enter permission url ")
parser.set('backends','kinto.permission_url',permission_url)# = postgres://postgres:postgres@localhost/postgres

parser.set('backends','kinto.backoff','10')
parser.set('backends','kinto.batch_max_requests','25')
parser.set('backends','kinto.retry_after_seconds','30')
parser.set('backends','kinto.eos',' ')

parser.add_section('authentication_configuration')
parser.set('authentication_configuration','kinto.userid_hmac_secret', binascii.b2a_hex(os.urandom(8)))
multiauth_policies = raw_input("enter multiauth policies [basicauth/fxa_basicauth]")

parser.set('authentication_configuration','multiauth.policies',multiauth_policies)
if multiauth_policies in ['fxa_basicauth']:
    parser.set('authentication_configuration','pyramid.includes','cliquet_fxa')
    client_id = raw_input("enter client id: ")
    parser.set('authentication_configuration','fxa-oauth.client_id',client_id)# = 61c3f791f740c19a
    client_secret = raw_input("enter client secret:")
    parser.set('authentication_configuration','fxa-oauth.client_secret',client_secret)# = b13739d8a905315314b09fb7b947aaeb62b47c6a4a5efb00c378fdecacd1e95e
    parser.set('authentication_configuration','fxa-oauth.oauth_uri','https://oauth-stable.dev.lcip.org/v1')
    parser.set('authentication_configuration','fxa-oauth.requested_scope','profile kinto')
    parser.set('authentication_configuration','fxa-oauth.required_scope','kinto')
    parser.set('authentication_configuration','fxa-oauth.relier.enabled','true')
    parser.set('authentication_configuration','fxa-oauth.webapp.authorized_domains','*')

parser.add_section('Client_cache_headers')
#
# Every bucket objects objects and list
parser.set('Client_cache_headers','kinto.bucket_cache_expires_seconds','3600')
#
# Every collection objects and list of every buckets
parser.set('Client_cache_headers','kinto.collection_cache_expires_seconds','3600')
#
# Every group objects and list of every buckets
parser.set('Client_cache_headers','kinto.group_cache_expires_seconds','3600')
#
# Every records objects and list of every collections
parser.set('Client_cache_headers','kinto.record_cache_expires_seconds','3600')
#
# Records in a specific bucket
parser.set('Client_cache_headers','kinto.blog_record_cache_expires_seconds','3600')
#
# Records in a specific collection in a specific bucket
parser.set('Client_cache_headers','kinto.blog_article_record_cache_expires_seconds','3600')


setup = raw_input("Would you like to setup the uwsgi configuration? [y/N]")

if setup in ['y','Y','yes']:
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
    virtualenv = raw_input("In which virtualenv should uwsgi start?")
    parser.set('uwsgi','virtualenv',virtualenv) #.venv/
    parser.set('uwsgi','lazy','true')
    parser.set('uwsgi','lazy-apps','true')
    parser.set('uwsgi','single-interpreter','true')
    parser.set('uwsgi','buffer-size','65535')
    parser.set('uwsgi','post-buffering','65535')
    socket_file = raw_input("Where would you like to create the socket file? ")
    sckfile = open(socket_file,'w')



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
parser.add_section('formatter_generic')
parser.set('formatter_generic','format','format = %%(asctime)s %%(levelname)-5.5s [%%(name)s][%%(threadName)s] %%(message)s')


parser.write(cfgfile)
