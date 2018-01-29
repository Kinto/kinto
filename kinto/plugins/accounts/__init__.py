from kinto.authorization import PERMISSIONS_INHERITANCE_TREE
from kinto.plugins.hawk.hawkauth import HawkAuth
from kinto.core.storage import exceptions as storage_exceptions
from kinto.core.errors import (http_error, raise_invalid, 
                               send_alert, ERRORS, request_GET)

from pyramid.exceptions import ConfigurationError
from pyramid.response import Response
from pyramid.httpexceptions import (HTTPNotModified, HTTPPreconditionFailed,
                                    HTTPNotFound, HTTPServiceUnavailable)

def hawk_sessions(request):
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

    ACCOUNT_CACHE_KEY = 'accounts:{}:verified'

    token = HawkAuth.generate_session_token()
    headers = {'Hawk-Session-Token': token}
    return Response(headers=headers, status_code=201)

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
