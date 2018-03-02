from time import time

from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.plugins.hawk.hawkauth import HawkAuthenticator
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.errors import (http_error, raise_invalid, 
                               send_alert, ERRORS, request_GET)

import requests
from requests_hawk import HawkAuth

from pyramid.exceptions import ConfigurationError
from pyramid.response import Response
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound, HTTPServiceUnavailable)

def clear_all_hawk_sessions(request, account):
    """Remove all hawk sessions on the account."""
    try:
        account['hawk-sessions'].clear();
    except KeyError:
        pass

    ACCOUNT_CACHE_KEY = 'accounts:{}:verified'

    request.registry.storage.update(collection_id='account', 
                                   parent_id=account['id'],
                                   object_id=account['id'], 
                                   record=account)

def add_hawk_session(request, account, token):
    """Add a hawk session to the account using `token` as the session token.
    
    Sessions are stored at the cache layer, with the client ID as the key.
    This allows for fast lookups by HAWK client ID, which is found in the auth 
    header of the request.
    """
    hawk_auth = HawkAuth(hawk_session=token)
    time_valid = request.registry.settings.get('kinto.hawk_session.ttl_seconds')
    expire_time = (time() + (time_valid or 86400))

    hawk_auth.credentials.update({
        'session': token,
        'id': hawk_auth.credentials['id'].decode(), 
        'key': hawk_auth.credentials['key'].decode(),
        'expires': expire_time,
        'account_user_id': account['id']
    })

    account.setdefault('hawk-sessions', [])
    client_id = hawk_auth.credentials['id']
    # The client ID is the dict key into the session credentials.
    account['hawk-sessions'].append(client_id)
    request.registry.storage.update(collection_id='account', 
                                   parent_id=account['id'],
                                   object_id=account['id'], 
                                   record=account)

    request.registry.cache.set(client_id, hawk_auth.credentials, expire_time)

def hawk_sessions(request):
    """Route handler for the /accounts/hawk-sessions endpoint

    Supports POST and DELETE calls.
    """
    userid = request.matchdict['userid']
    try:
        account = request.registry.storage.get(parent_id=userid,
                                               collection_id='account',
                                               object_id=userid)
    except storage_exceptions.RecordNotFoundError:
        details = {
            'id': userid,
            'resource_name': 'accounts'
        }
        response = http_error(HTTPNotFound(), errno=ERRORS.INVALID_RESOURCE_ID,
                              details=details)
        raise response

    method = request.method.lower()
    if method == 'post':
        token = HawkAuthenticator.generate_session_token()
        add_hawk_session(request, account, token)
        headers = {'Hawk-Session-Token': token}
        return Response(headers=headers, status_code=201)
    elif method == 'delete':
        clear_all_hawk_sessions(request, account)
        return Response(status_code=204)


def hawk_sessions_current(request):
    pass

def includeme(config):
    # Add routes for hawk session management
    config.add_view(hawk_sessions,
                   route_name='hawk_sessions')
    config.add_view(hawk_sessions_current,
                   route_name='hawk_sessions_current')
    config.add_route('hawk_sessions', '/accounts/{userid:.*}/hawk-sessions')
    config.add_route('hawk_sessions_current', 
                     '/accounts/{userid:.*}/hawk-sessions/current')

    config.add_api_capability(
        'accounts',
        description='Manage user accounts.',
        url='https://kinto.readthedocs.io/en/latest/api/1.x/accounts.html')

    config.scan('kinto.plugins.accounts.views')

    PERMISSIONS_INHERITANCE_TREE[''].update({
        'account:create': {}
    })
    PERMISSIONS_INHERITANCE_TREE['account'] = {
        'write': {'account': ['write']},
        'read': {'account': ['write', 'read']}
    }

    # Add some safety to avoid weird behaviour with basicauth default policy.
    settings = config.get_settings()
    auth_policies = settings['multiauth.policies']
    if 'basicauth' in auth_policies and 'account' in auth_policies:
        if auth_policies.index('basicauth') < auth_policies.index('account'):
            error_msg = ("'basicauth' should not be mentioned before 'account' "
                         "in 'multiauth.policies' setting.")
            raise ConfigurationError(error_msg)

    # We assume anyone in account_create_principals is to create
    # accounts for other people.
    # No one can create accounts for other people unless they are an
    # "admin", defined as someone matching account_write_principals.
    # Therefore any account that is in account_create_principals
    # should be in account_write_principals too.
    creators = set(settings.get('account_create_principals', '').split())
    admins = set(settings.get('account_write_principals', '').split())
    cant_create_anything = creators.difference(admins)
    # system.Everyone isn't an account.
    cant_create_anything.discard('system.Everyone')
    if cant_create_anything:
        message = ('Configuration has some principals in account_create_principals '
                   'but not in account_write_principals. These principals will only be '
                   'able to create their own accounts. This may not be what you want.\n'
                   'If you want these users to be able to create accounts for other users, '
                   'add them to account_write_principals.\n'
                   'Affected users: {}'.format(list(cant_create_anything)))

        raise ConfigurationError(message)
