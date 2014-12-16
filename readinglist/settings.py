import os

from eve.io.sql.decorators import registerSchema
from readinglist import schemas, auth


PROJECT_ROOT = os.path.dirname(__file__)

URL_PREFIX = 'v1'

X_DOMAINS = '*'  # CORS
XML = False  # JSON only

SQLALCHEMY_DATABASE_URI = 'sqlite:///'


registerSchema('article')(schemas.Article)
registerSchema('device')(schemas.ArticleDevice)
article = schemas.Article._eve_schema['article']
device = schemas.ArticleDevice._eve_schema['device']

article.update({
    'authentication': auth.FxaAuth(),
    'auth_field': 'author',
    'item_title': 'article',
    'resource_methods': ['GET', 'POST'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
})

article['schema']['url']['minlength'] = 6
article['schema']['title']['minlength'] = 1

device.update({
    'authentication': auth.FxaAuth(),
    'url': 'articles/<regex("\d"):article>/devices',
    'resource_methods': ['GET'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
})

DOMAIN = {
    'articles': article,
    'devices': device
}
