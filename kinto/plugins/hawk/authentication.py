from pyramid.interfaces import IAuthenticationPolicy
from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.authentication import extract_http_basic_credentials

from zope.interface import implementer

from kinto.core.storage import exceptions as storage_exceptions

from .hawkauth import HawkAuth

@implementer(IAuthenticationPolicy)
class HawkAuthenticationPolicy(CallbackAuthenticationPolicy):
    def unauthenticated_userid(self, request):
        user_id = self._test_credentials(request)
        return user_id

    def forget(self, request):
        return [('WWW-Authenticate', 'Hawk')]
        
    def _test_credentials(self, request):
        """Test credentials in request against account HAWK credentials"""
        account_creds = self._get_account_hawk_creds(request)
        try:
            return account_creds['id']
        except:
            return None

    def _get_account_hawk_creds(self, request):
        """Check storage for the request account HAWK credentials.
        
        The accounts plugin is a depency of this plugin, so we can rely
        on Basic Auth credentials to get the account and its HAWK creds.
        """
        print('check hawk')
        basic_creds = extract_http_basic_credentials(request)
        if basic_creds:
            username, password = basic_creds
            try:
                account = request.registry.storage.get(parent_id=username,
                                                       collection_id='account',
                                                       object_id=username)
            except storage_exceptions.RecordNotFoundError:
                return None

            cache = request.registry.cache
            authenticator = HawkAuth(account['id'],
                                     account['hawk_secret'],
                                     cache)
            if authenticator.authenticate(request):
                return account
