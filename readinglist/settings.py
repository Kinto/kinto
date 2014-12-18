import os

from eve.io.sql.decorators import registerSchema
from readinglist import schemas, auth


PROJECT_ROOT = os.path.dirname(__file__)

API_VERSION = 'v1'

X_DOMAINS = '*'  # CORS
XML = False  # JSON only
IF_MATCH = False  # Disable concurrency control

SQLALCHEMY_DATABASE_URI = 'sqlite:///'

SECRET_KEY = ''


registerSchema('article')(schemas.Article)
article = schemas.Article.eve_schema('article')

article.update({
    'authentication': auth.FxaAuth(),
    'auth_field': 'author',
    'item_title': 'article',
    'resource_methods': ['GET', 'POST'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
})


registerSchema('device')(schemas.ArticleDevice)
device = schemas.ArticleDevice.eve_schema('device')

device.update({
    'authentication': auth.FxaAuth(),
    'url': 'articles/<regex("\d+"):article>/devices',
    'resource_methods': ['GET'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
    'additional_lookup': {
        'url': 'regex(".+")',
        'field': 'device'
    },
})


DOMAIN = {
    'articles': article,
    'devices': device
}
