from readinglist import schemas

DEBUG = True

URL_PREFIX = 'v1'

X_DOMAINS = '*'  # CORS
XML = False  # JSON only

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
# MONGO_USERNAME = 'user'
# MONGO_PASSWORD = 'user'
MONGO_DBNAME = 'apitest'


DOMAIN = {'article': schemas.article}
