import contextlib
import warnings

from cliquet import logger
from cliquet.storage import exceptions
from cliquet.utils import sqlalchemy


class PostgreSQLClient(object):
    def __init__(self, session_factory, commit_manually=True):
        self.session_factory = session_factory
        self.commit_manually = commit_manually

        # # Register ujson, globally for all futur cursors
        # with self.connect() as cursor:
        #     psycopg2.extras.register_json(cursor,
        #                                   globally=True,
        #                                   loads=json.loads)

    @contextlib.contextmanager
    def connect(self, readonly=False):
        """
        Pulls a connection from the pool when context is entered and
        returns it when context is exited.

        A COMMIT is performed on the current transaction if everything went
        well. Otherwise transaction is ROLLBACK, and everything cleaned up.
        """
        with_transaction = (not readonly and self.commit_manually)
        session = None
        try:
            # Pull connection from pool.
            session = self.session_factory()
            # Start context
            yield session
            # Success
            if with_transaction:
                session.commit()
                # Give back to pool.
                session.close()

        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(e)
            if session:
                if with_transaction:
                    session.rollback()
                    session.close()
            raise exceptions.BackendError(original=e)


# Reuse existing client if same URL.
_CLIENTS = {}


def create_from_config(config, prefix=''):
    """Create a PostgreSQLClient client using settings in the provided config.
    """
    if sqlalchemy is None:
        message = ("PostgreSQL dependencies missing. "
                   "Refer to installation section in documentation.")
        raise ImportWarning(message)

    settings = config.get_settings().copy()
    # Custom Cliquet settings, unsupported by SQLAlchemy.
    settings.pop(prefix + 'backend', None)
    settings.pop(prefix + 'max_fetch_size', None)

    url = settings[prefix + 'url']
    existing_client = _CLIENTS.get(url)
    if existing_client:
        msg = ("Reuse existing PostgreSQL connection. "
               "Parameters %s* will be ignored." % prefix)
        warnings.warn(msg)
        return existing_client

    # Initialize SQLAlchemy engine from settings.
    poolclass_key = prefix + 'poolclass'
    settings.setdefault(poolclass_key, 'sqlalchemy.pool.QueuePool')
    settings[poolclass_key] = config.maybe_dotted(settings[poolclass_key])
    engine = sqlalchemy.engine_from_config(settings, prefix=prefix, url=url)

    # Initialize thread-safe session factory.
    from sqlalchemy.orm import sessionmaker, scoped_session
    session_factory = scoped_session(sessionmaker(bind=engine))

    # Store one client per URI.
    client = PostgreSQLClient(session_factory)
    _CLIENTS[url] = client
    return client
