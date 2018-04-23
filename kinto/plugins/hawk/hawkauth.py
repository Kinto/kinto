import logging
import os

from pyramid.exceptions import ConfigurationError
from mohawk import Receiver

from kinto.core import errors

logger = logging.getLogger(__name__)

SHA256_ALGO_NAME = 'sha256'
# Currently only support sha256
algorithms = set([SHA256_ALGO_NAME])

class HawkAuth():
    """Class reponsible for performing hawk authentication.

    Relies on Mohawk library to check signature and nonce.
    """
    def __init__(self, client_id, secret, settings):
        """initialize instance variables with hawk credentials.

        :param client_id: Client ID used by kinto server to check signature
        :param secret: Client Secret assoicated with the Client ID
        :param settings: pyramid.registry.settings object.
        """
        self._client_id = client_id
        self._secret = secret
        self._algo = settings.get('kinto.hawk_algo') or SHA256_ALGO_NAME
        self._nonce_lifespan = settings.get('kinto.hawk_nonce_lifespan') or 60

        self._validate_config()

    def _validate_config(self):
        """Validate the hawk settings"""
        if self._algo not in algorithms:
            raise ConfigurationError(
                'Hawk authorization algorithm is invalid in configuration \
                settings: "{}" is not a valid algorithm.'.format(self._algo))
        elif type(self._nonce_lifespan) != int:
            raise ConfigurationError(
                '`kinto.hawk_nonce_lifespan` must be an integer.')

    @staticmethod
    def generate_session_token():
        """Utility method for generating random HAWK session token

        :returns: hex string, 32 bytes
        """
        return os.urandom(32).hex()

    @staticmethod
    def get_credentials_from_session(token):
        """Utility function to derive HAWK credentials from session token"""
        pass

    def authenticate(self, request):
        """Perform hawk authorization on the request.

        The sender(client) credentials are checked against our receiver(server)
        credentials.  The timestamp of the request must match the server time
        (within 60 seconds by default) and the nonce sent by the client must be new.

        :param request: Pyramid request object
        :returns: ``True`` if authentication is successful, ``False`` otherwise
        """
        cache = request.registry.cache
        # HAWK credentials lookup function
        def get_credentials(client_id):
            if client_id == self._client_id:
                return {'id': self._client_id, 'key': self._secret,
                        'algorithm': self._algo}
            raise LookupError('Client ID not found.')

        # define a function for nonce checking
        def seen_nonce(sender_id, nonce, timestamp):
            key = '{id}:{nonce}:{ts}'.format(id=sender_id, nonce=nonce,
                                             ts=timestamp)
            if cache.get(key):
                return True
            else:
                # Messages expire after 60 seconds, and we only need to
                # store the nonce for as long as messages are valid.
                # Users can set their own nonce lifetime in settings.
                cache.set(
                    key, True,
                    self._nonce_lifespan)
                return False

        # Receiver constructor will raise exception if auth fails.
        try:
            receiver = Receiver(get_credentials,
                                request.headers['Authorization'],
                                request.url,
                                request.method,
                                content = request.body,
                                content_type = request.headers['Content-Type'],
                                seen_nonce = seen_nonce)
        except:
            return False

        return True





