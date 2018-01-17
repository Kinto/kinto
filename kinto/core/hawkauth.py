import logging
from pyramid.exceptions import ConfigurationError
from mohawk import Receiver

from kinto.core import errors

logger = logging.getLogger(__name__)

algorithms = set(['sha256'])

class HawkAuth():
    """Class reponsible for performing hawk authentication.

    Relies on Mohawk library to check signature and nonce.
    """
    def __init__(self, client_id, secret, algo, config):
        """initialize instance variables with hawk credentials.

        :param client_id: Client ID used by kinto server to check signature
        :param secret: Client Secret assoicated with the Client ID
        :param algo: Algorithm used to create MAC
        :param config: pyramid Configurator object.
        """
        self._client_id = client_id
        self._secret = secret
        self._algo = algo.lower()
        # Get the cache for nonce checking
        self._cache_backend = config.registry.cache

        self._validate_config()

    def _validate_config(self):
        """Validate the hawk credentials configuration.

        The Client ID and secret should not be empty, and the algorithm
        should be acceptable.
        """ 
        if not self._client_id or not self._secret:
            raise ConfigurationError('Hawk authorization credentials are invalid in \
                                     settings configuration:  kinto.hawk.id and \
                                     kinto.hawk.secret must not be empty.')    
        elif self._algo not in algorithms:
            raise ConfigurationError('Hawk authorization algorithm is invalid in \
                                     configuration settings: "{}" is not a valid \
                                     algorithm.'.format(self._algo))

    def authenticate(self, request):
        """Perform hawk authorization on the request.  

        The sender(client) credentials are checked against our receiver(server)
        credentials.  The timestamp of the request must match the server time
        (within 60 seconds by default) and the nonce sent by the client must be new.

        :param request: Pyramid request object
        :returns: ``True`` if authentication is successful, ``False`` otherwise
        """

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
            if self._cache_backend.get(key):
                return True
            else:
                # Messages expire after 60 seconds, so we can be confident that
                # we only need to store the nonce for slightly longer than the
                # timeout (because a replayed nonce won't work if the entire message
                # is expired).
                self._cache_backend.set(key, True, 90)
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





