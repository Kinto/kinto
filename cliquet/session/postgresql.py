from __future__ import absolute_import
import psycopg2
from six.moves.urllib import parse as urlparse

from cliquet import logger
from cliquet.storage import postgresql as postgresql_storage
from cliquet.session import SessionStorageBase


class PostgreSQL(SessionStorageBase):

    connect = postgresql_storage.PostgreSQL.connect

    def __init__(self, **kwargs):
        self._conn_kwargs = kwargs
        self._init_schema()

    def _init_schema(self):
        schema = """
        CREATE TABLE IF NOT EXISTS session(
            key VARCHAR(256) PRIMARY KEY,
            value TEXT NOT NULL,
            ttl INT4 DEFAULT NULL
        );
        """
        with self.connect() as cursor:
            cursor.execute(schema)
        logger.info('Created PostgreSQL session tables')

    def flush(self):
        query = """
        DELETE FROM session;
        """
        with self.connect() as cursor:
            cursor.execute(query)
        logger.debug('Flushed PostgreSQL session tables')

    def ping(self):
        try:
            self.set('heartbeat', True)
        except psycopg2.Error:
            return False

    def ttl(self, key):
        query = """
        SELECT EXTRACT(SECOND FROM (now() - ttl)) AS ttl
          FROM session
         WHERE key = %s
           AND ttl IS NOT NULL;
        """
        with self.connect() as cursor:
            result = cursor.execute(query, (key,))
            if result.rowcount > 0:
                return result.fetchone()['ttl']

    def expire(self, key, value):
        query = """
        UPDATE session SET ttl = now() + INTERVAL '%s second'
        WHERE key = %s;
        """
        with self.connect() as cursor:
            cursor.execute(query, (key, value))

    def set(self, key, value, ttl=None):
        query = """
        WITH upsert AS (
            UPDATE session SET value=%(value)s, ttl=%(ttl)s
             WHERE key=%(key)s
            RETURNING *)
        INSERT INTO session (key, value, ttl)
        SELECT %(key)s, %(value)s, %(ttl)s
        WHERE NOT EXISTS (SELECT * FROM upsert)
        """
        with self.connect() as cursor:
            cursor.execute(query, dict(key=key, value=value, ttl=ttl))

    def get(self, key):
        purge = "DELETE FROM session WHERE ttl IS NOT NULL AND now() > ttl;"
        query = "SELECT value FROM session WHERE key = %s;"
        with self.connect() as cursor:
            result = cursor.execute(purge)
            result = cursor.execute(query, (key,))
            if result.rowcount > 0:
                return result.fetchone()['value']

    def delete(self, key):
        query = "DELETE FROM session WHERE key = %s"
        with self.connect() as cursor:
            cursor.execute(query, (key,))


def load_from_config(config):
    settings = config.registry.settings
    uri = settings.get('cliquet.session_url', '')
    uri = urlparse.urlparse(uri)
    conn_kwargs = dict(host=uri.hostname,
                       port=uri.port,
                       user=uri.username,
                       password=uri.password,
                       database=uri.path[1:] if uri.path else '')
    # Filter specified values only, to preserve PostgreSQL defaults
    conn_kwargs = dict([(k, v) for k, v in conn_kwargs.items() if v])

    return PostgreSQL(**conn_kwargs)
