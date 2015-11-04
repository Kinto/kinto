import ConfigParser
import os,binascii

cfgfile = open("/{{cookiecutter.repo_name}}/{{cookiecutter.repo_name}}/{{cookiecutter.repo_name}}.ini",'w') #enter path of file
parser = ConfigParser.SafeConfigParser()
parser.set('authentication_configuration','kinto.userid_hmac_secret', binascii.b2a_hex(os.urandom(8)))
