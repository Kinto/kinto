import ConfigParser
import os,binascii

parser.set('authentication_configuration','kinto.userid_hmac_secret', binascii.b2a_hex(os.urandom(8)))