from eve.auth import TokenAuth
from flask import request, current_app as app

from readinglist import fxa


class FxAAuth(TokenAuth):
    def authorized(self, allowed_roles, resource, method):
        auth = request.authorization = request.headers.get('Authorization', '')

        try:
            token_type, token = auth.split()
            assert token_type == 'Bearer'
        except (ValueError, AssertionError):
            auth = None

        return auth and self.check_auth(token, allowed_roles, resource, method)

    def check_auth(self, token, allowed_roles, resource, method):
        try:
            account = fxa.verify_token(oauth_uri=app.config["FXA_OAUTH_URI"],
                                       token=token)
        except fxa.OAuth2Error:
            return False
        self.set_request_auth_value(account['user'])
        return True
