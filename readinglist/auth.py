import json

import requests
from requests import exceptions as requests_exceptions
from eve.auth import TokenAuth
from flask import request, current_app as app


class OAuth2(TokenAuth):
    def authorized(self, allowed_roles, resource, method):
        auth = request.authorization = request.headers.get('Authorization', '')

        try:
            token_type, token = auth.split()
            assert token_type == 'Bearer'
        except (ValueError, AssertionError):
            auth = None

        return auth and self.check_auth(token, allowed_roles, resource, method)


class FxAAuth(OAuth2):
    def check_auth(self, token, allowed_roles, resource, method):
        try:
            account = fxa_verify(oauth_uri=app.config["FXA_OAUTH_URI"],
                                 token=token)
        except OAuth2Error:
            return False
        self.set_request_auth_value(account['user'])
        return True


class OAuth2Error(Exception):
    pass


def fxa_trade_token(oauth_uri, client_id, client_secret, code):
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
        # XXX : if 400, take message from response
        # https://github.com/mozilla/fxa-oauth-server/blob/master/docs/api.md#errors
        error_msg = 'Bad OAuth response ({})'.format(resp.status_code)
        raise OAuth2Error(error_msg)

    oauth_server_response = resp.json()

    if 'access_token' not in oauth_server_response:
        error_msg = 'access_token missing in OAuth response'
        raise OAuth2Error(error_msg)

    return oauth_server_response['access_token']


def fxa_verify(oauth_uri, token):
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
        # XXX : if 400, take message from response
        # https://github.com/mozilla/fxa-oauth-server/blob/master/docs/api.md#errors
        error_msg = 'Bad OAuth response ({})'.format(resp.status_code)
        raise OAuth2Error(error_msg)

    verify_response = resp.json()

    is_incomplete = any(k not in verify_response
                        for k in ('user', 'scopes', 'client_id'))

    if is_incomplete:
        error_msg = 'Incomplete OAuth response ({})'.format(verify_response)
        raise OAuth2Error(error_msg)

    return verify_response


def fxa_fetch_profile(profile_uri, token):
    url = '%s/profile' % profile_uri
    headers = {
        'Authorization': 'Bearer %s' % token,
        'Accept': 'application/json'
    }

    try:
        resp = requests.get(url, headers=headers)
    except requests_exceptions.RequestException as e:
        error_msg = 'Profile server connection error ({})'.format(e)
        raise OAuth2Error(error_msg)

    if not 200 <= resp.status_code < 300:
        # XXX : if 400, take message from response
        # https://github.com/mozilla/fxa-profile-server/blob/master/docs/API.md#errors
        error_msg = 'Bad profile response ({})'.format(resp.status_code)
        raise OAuth2Error(error_msg)

    profile_response = resp.json()

    is_incomplete = any(k not in profile_response for k in ('uid', 'email'))

    if is_incomplete:
        error_msg = 'Incomplete profile response ({})'.format(profile_response)
        raise OAuth2Error(error_msg)

    return profile_response
