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

FXA_CLIENT_ID = ''
FXA_CLIENT_SECRET = ''
FXA_OAUTH_URI = 'https://oauth.accounts.firefox.com/v1'
FXA_PROFILE_URI = 'https://profile.accounts.firefox.com/v1'
FXA_REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:fx:webchannel'
FXA_SCOPE = 'profile'


registerSchema('article')(schemas.Article)
article = schemas.Article.eve_schema('article')

article.update({
    'authentication': auth.FxAAuth(),
    'auth_field': 'author',
    'item_title': 'article',
    'resource_methods': ['GET', 'POST'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
})


registerSchema('device')(schemas.ArticleDevice)
device = schemas.ArticleDevice.eve_schema('device')

device.update({
    'authentication': auth.FxAAuth(),
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
