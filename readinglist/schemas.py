from auth import FxaAuth


schema = {
    'title': {
        'type': 'string'
    },
    'url': {
        'type': 'string'
    },
    'status': {
        'type': 'string',
        'allowed': ['unread', 'read']
    }
}

article = {
    'schema': schema,
    'authentication': FxaAuth(),
    'auth_field': '_author',
    'item_title': 'article',
    'resource_methods': ['GET', 'POST'],
    'item_methods': ['GET', 'PATCH', 'DELETE'],
}
