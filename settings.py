import os

from eve.io.sql.decorators import registerSchema
from readinglist import schemas, auth

PROJECT_ROOT = os.path.dirname(__file__)

DEBUG = True

URL_PREFIX = 'v1'

X_DOMAINS = '*'  # CORS
XML = False  # JSON only

SQLITE_DB = os.path.join(PROJECT_ROOT, 'readinglist.db')
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s' % SQLITE_DB


registerSchema('article')(schemas.Article)
article = schemas.Article._eve_schema['article']

article.update({
    'authentication': auth.FxaAuth(),
    'auth_field': 'author',
    'item_title': 'article',
    'resource_methods': ['GET', 'POST'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
})

DOMAIN = {'articles': article}
