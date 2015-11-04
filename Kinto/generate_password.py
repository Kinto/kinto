
import sys
import os,binascii
import ConfigParser


cfgfile = open("/{{cookiecutter.repo_name}}/config/{{cookiecutter.file_name}}.ini",'a') #enter path of file

parser = ConfigParser.SafeConfigParser()

parser.add_section('passkey')
parser.set('passkey','kinto.userid_hmac_secret', binascii.b2a_hex(os.urandom(8)))
