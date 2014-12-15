import os

from eve.io.sql.decorators import registerSchema
from readinglist import schemas, auth


PROJECT_ROOT = os.path.dirname(__file__)

URL_PREFIX = 'v1'

X_DOMAINS = '*'  # CORS
XML = False  # JSON only

SQLALCHEMY_DATABASE_URI = 'sqlite:///'


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
