import contextlib
import warnings
from collections import defaultdict

from kinto.core import logger
from kinto.core.storage import exceptions
from kinto.core.utils import sqlalchemy
import transaction as zope_transaction


class PostgreSQLClient(object):
    def __init__(self, session_factory, commit_manually=True, invalidate=None):
        self.session_factory = session_factory
        self.commit_manually = commit_manually
        self.invalidate = invalidate or (lambda session: None)

        # # Register ujson, globally for all futur cursors
        # with self.connect() as cursor:
        #     psycopg2.extras.register_json(cursor,
        #                                   globally=True,
        #                                   loads=json.loads)

    @contextlib.contextmanager
    def connect(self, readonly=False, force_commit=False):
        """
        Pulls a connection from the pool when context is entered and
        returns it when context is exited.

        A COMMIT is performed on the current transaction if everything went
        well. Otherwise transaction is ROLLBACK, and everything cleaned up.
        """
        with_transaction = not readonly and self.commit_manually
        session = None
        try:
            # Pull connection from pool.
            session = self.session_factory()
            # Start context
            yield session
            if not readonly and not self.commit_manually:
                # Mark session as dirty.
                self.invalidate(session)
            # Success
            if with_transaction:
                session.commit()
            elif force_commit:
                # Commit like would do a succesful request.
                zope_transaction.commit()

        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(e)
            if session and with_transaction:
                session.rollback()
            raise exceptions.BackendError(original=e)

        finally:
            if session and self.commit_manually:
                # Give back to pool if commit done manually.
                session.close()

# Reuse existing client if same URL.
_CLIENTS = defaultdict(dict)


def create_from_config(config, prefix=''):
    """Create a PostgreSQLClient client using settings in the provided config.
    """
    if sqlalchemy is None:
        message = ("PostgreSQL SQLAlchemy dependency missing. "
                   "Refer to installation section in documentation.")
        raise ImportWarning(message)

    from zope.sqlalchemy import ZopeTransactionExtension, invalidate
    from sqlalchemy.orm import sessionmaker, scoped_session

    settings = config.get_settings().copy()
    # Custom Kinto settings, unsupported by SQLAlchemy.
    settings.pop(prefix + 'backend', None)
    settings.pop(prefix + 'max_fetch_size', None)
    settings.pop(prefix + 'prefix', None)
    transaction_per_request = settings.pop('transaction_per_request', False)

    url = settings[prefix + 'url']
    existing_client = _CLIENTS[transaction_per_request].get(url)
    if existing_client:
        msg = ("Reuse existing PostgreSQL connection. "
               "Parameters %s* will be ignored." % prefix)
        warnings.warn(msg)
        return existing_client

    # Initialize SQLAlchemy engine from settings.
    poolclass_key = prefix + 'poolclass'
    settings.setdefault(poolclass_key, ('kinto.core.storage.postgresql.'
                                        'pool.QueuePoolWithMaxBacklog'))
    settings[poolclass_key] = config.maybe_dotted(settings[poolclass_key])
    engine = sqlalchemy.engine_from_config(settings, prefix=prefix, url=url)

    # Initialize thread-safe session factory.
    options = {}
    if transaction_per_request:
        # Plug with Pyramid transaction manager
        options['extension'] = ZopeTransactionExtension()
    session_factory = scoped_session(sessionmaker(bind=engine, **options))

    # Store one client per URI.
    commit_manually = (not transaction_per_request)
    client = PostgreSQLClient(session_factory, commit_manually, invalidate)
    _CLIENTS[transaction_per_request][url] = client
    return client
