import contextlib
import warnings

from six.moves.urllib import parse as urlparse

from cliquet import logger
from cliquet.storage import exceptions
from cliquet.utils import json, psycopg2

if psycopg2:
    import psycopg2.extras
    import psycopg2.pool

    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)


class PostgreSQLClient(object):

    pool = None

    def __init__(self, *args, **kwargs):
        if psycopg2 is None:
            message = "You must install psycopg2 to use the postgresql backend"
            raise ImportWarning(message)

        pool_size = kwargs.pop('pool_size')
        self._conn_kwargs = kwargs
        pool_klass = psycopg2.pool.ThreadedConnectionPool
        if PostgreSQLClient.pool is None:
            PostgreSQLClient.pool = pool_klass(minconn=pool_size,
                                               maxconn=pool_size,
                                               **self._conn_kwargs)
        elif pool_size != self.pool.minconn:
            msg = ("Pool size %s ignored for PostgreSQL backend "
                   "(Already set to %s).") % (pool_size, self.pool.minconn)
            warnings.warn(msg)

        # When fsync setting is off, like on TravisCI or in during development,
        # cliquet some storage tests fail because commits are not applied
        # accross every opened connections.
        # XXX: find a proper solution to support fsync off.
        # Meanhwile, disable connection pooling to prevent test suite failures.
        self._always_close = False
        with self.connect(readonly=True) as cursor:
            cursor.execute("SELECT current_setting('fsync');")
            fsync = cursor.fetchone()[0]
            if fsync == 'off':  # pragma: no cover
                warnings.warn('Option fsync = off detected. Disable pooling.')
                self._always_close = True
        # Register ujson, globally for all futur cursors
        with self.connect() as cursor:
            psycopg2.extras.register_json(cursor,
                                          globally=True,
                                          loads=json.loads)

    @contextlib.contextmanager
    def connect(self, readonly=False):
        """Connect to the database and instantiates a cursor.
        At exiting the context manager, a COMMIT is performed on the current
        transaction if everything went well. Otherwise transaction is ROLLBACK,
        and everything cleaned up.

        If the database could not be be reached a 503 error is raised.
        """
        conn = None
        cursor = None
        try:
            conn = self.pool.getconn()
            conn.autocommit = readonly
            options = dict(cursor_factory=psycopg2.extras.DictCursor)
            cursor = conn.cursor(**options)
            # Start context
            yield cursor
            # End context
            if not readonly:
                conn.commit()
        except psycopg2.Error as e:
            if cursor:
                logger.debug(cursor.query)
            logger.error(e)
            if conn and not conn.closed:
                conn.rollback()
            raise exceptions.BackendError(original=e)
        finally:
            if cursor:
                cursor.close()
            if conn and not conn.closed:
                self.pool.putconn(conn, close=self._always_close)


def create_from_config(config, prefix=''):
    """Create a PostgreSQLClient client using settings in the provided config.
    """
    settings = config.get_settings()
    pool_size = int(settings[prefix + 'pool_size'])
    uri = settings[prefix + 'url']
    parsed = urlparse.urlparse(uri)
    conn_kwargs = dict(host=parsed.hostname,
                       port=parsed.port,
                       user=parsed.username,
                       password=parsed.password,
                       database=parsed.path[1:] if parsed.path else '')
    # Filter specified values only, to preserve PostgreSQL defaults
    conn_kwargs = dict([(k, v) for k, v in conn_kwargs.items() if v])
    return PostgreSQLClient(pool_size=pool_size, **conn_kwargs)
