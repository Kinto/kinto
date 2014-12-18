import json

import requests
from eve.auth import TokenAuth
from flask import request, current_app as app


class OAuth2Exception(Exception):
    pass


class FxaAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        try:
            profile = fxa_fetch_profile(oauth_uri=app.config["FXA_OAUTH_URI"],
                                        token=token)
        except OAuth2Exception:
            return False

        uid = profile['uid']
        self.set_request_auth_value(uid)
        return True

    def authorized(self, allowed_roles, resource, method):
        auth = request.headers.get('Authorization')
        try:
            token_type, token = auth.split()
            assert token_type == 'Bearer'
        except (ValueError, AssertionError):
            auth = None

        return auth and self.check_auth(token, allowed_roles, resource, method)


def fxa_trade_token(oauth_uri, client_id, client_secret, code):
    url = '%s/token' % oauth_uri,
    data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret
    }
    headers = {'Content-Type': 'application/json'}

    resp = requests.post(url, data=json.dumps(data), headers=headers)

    if not 200 <= resp.status_code < 300:
        error_msg = 'Bad OAuth response ({})'.format(resp.status_code)
        raise OAuth2Exception(error_msg)

    oauth_server_response = resp.json()

    if 'access_token' not in oauth_server_response:
        error_msg = 'access_token missing in OAuth response'
        raise OAuth2Exception(error_msg)

    return oauth_server_response['access_token']


def fxa_fetch_profile(oauth_uri, token):
    url = '%s/profile' % oauth_uri
    headers = {
        'Authorization': 'Bearer %s' % token,
        'Accept': 'application/json'
    }

    resp = requests.get(url, headers=headers)

    if not 200 <= resp.status_code < 300:
        error_msg = 'Bad OAuth response ({})'.format(resp.status_code)
        raise OAuth2Exception(error_msg)

    profile_server_response = resp.json()
    return profile_server_response
