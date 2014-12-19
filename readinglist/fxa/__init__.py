import json

import requests
from requests import exceptions as requests_exceptions


class OAuth2Error(Exception):
    def __init__(self, error=None, code=None, message=None, errorno=None):
        super(Exception, self).__init__(error or 'OAuth error')
        self.error = error
        self.code = code
        self.message = message
        self.errorno = errorno

    @classmethod
    def from_response(cls, response):
        kwargs = dict(code=response.status_code)
        try:
            attrs = {k: v for k, v in response.json().iteritems()
                     if k in ('errorno', 'error', 'message')}
            kwargs.update(**attrs)
        except ValueError:
            pass
        return cls(**kwargs)


def trade_code(oauth_uri, client_id, client_secret, code):
    url = '%s/token' % oauth_uri
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret
    }
    headers = {'Content-Type': 'application/json'}

    try:
        resp = requests.post(url, data=json.dumps(data), headers=headers)
    except requests_exceptions.RequestException as e:
        error_msg = 'OAuth connection error ({})'.format(e)
        raise OAuth2Error(error_msg)

    if not 200 <= resp.status_code < 300:
        raise OAuth2Error.from_response(resp)

    oauth_server_response = resp.json()

    if 'access_token' not in oauth_server_response:
        error_msg = 'access_token missing in OAuth response'
        raise OAuth2Error(error_msg)

    return oauth_server_response['access_token']


def verify_token(oauth_uri, token):
    url = '%s/verify' % oauth_uri
    data = {
        'token': token
    }
    headers = {'Content-Type': 'application/json'}

    try:
        resp = requests.post(url, data=json.dumps(data), headers=headers)
    except requests_exceptions.RequestException as e:
        error_msg = 'OAuth connection error ({})'.format(e)
        raise OAuth2Error(error_msg)

    if not 200 <= resp.status_code < 300:
        raise OAuth2Error.from_response(resp)

    verify_response = resp.json()

    missing_attrs = ", ".join([k for k in ('user', 'scopes', 'client_id')
                               if k not in verify_response])
    if missing_attrs:
        error_msg = '{} missing in OAuth response'.format(missing_attrs)
        raise OAuth2Error(error_msg)

    return verify_response
