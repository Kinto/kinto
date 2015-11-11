import contextlib
import warnings

from cliquet import logger
from cliquet.storage import exceptions
from cliquet.utils import sqlalchemy


class PostgreSQLClient(object):
    def __init__(self, engine):
        self._engine = engine

        # # Register ujson, globally for all futur cursors
        # with self.connect() as cursor:
        #     psycopg2.extras.register_json(cursor,
        #                                   globally=True,
        #                                   loads=json.loads)

    @contextlib.contextmanager
    def connect(self, readonly=False):
        """Pulls a connection from the pool when context is entered and
        returns it when context is exited.

        A COMMIT is performed on the current transaction if everything went
        well. Otherwise transaction is ROLLBACK, and everything cleaned up.

        XXX: Committing should not happen here but using a global transaction
        manager like `pyramid-tm`.
        """
        connection = None
        trans = None
        try:
            # Pull from pool.
            connection = self._engine.connect()
            if not readonly:
                trans = connection.begin()
            # Start context
            yield connection
            # Success
            if not readonly:
                trans.commit()
            # Give back to pool.
            connection.close()

        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(e)
            if trans:
                trans.rollback()
            if connection:
                connection.close()
            raise exceptions.BackendError(original=e)


_ENGINES = {}


def create_from_config(config, prefix=''):
    """Create a PostgreSQLClient client using settings in the provided config.
    """
    if sqlalchemy is None:
        message = ("PostgreSQL SQLAlchemy dependency missing. "
                   "Refer to installation section in documentation.")
        raise ImportWarning(message)

    settings = config.get_settings()
    url = settings[prefix + 'url']

    if url in _ENGINES:
        msg = ("Reuse existing PostgreSQL connection. "
               "Parameters %s* will be ignored." % prefix)
        warnings.warn(msg)
        return PostgreSQLClient(_ENGINES[url])

    # Initialize SQLAlchemy engine.
    poolclass_key = prefix + 'poolclass'
    settings.setdefault(poolclass_key, 'sqlalchemy.pool.QueuePool')
    settings[poolclass_key] = config.maybe_dotted(settings[poolclass_key])
    settings.pop(prefix + 'max_fetch_size', None)
    settings.pop(prefix + 'backend', None)

    engine = sqlalchemy.engine_from_config(settings, prefix=prefix, url=url)

    # Store one engine per URI.
    _ENGINES[url] = engine

    return PostgreSQLClient(engine)
