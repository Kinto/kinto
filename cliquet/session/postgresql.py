from __future__ import absolute_import

from six.moves.urllib import parse as urlparse

from cliquet import logger
from cliquet.storage.postgresql import PostgreSQLClient
from cliquet.session import SessionStorageBase


class PostgreSQL(PostgreSQLClient, SessionStorageBase):

    def __init__(self, **kwargs):
        super(PostgreSQL, self).__init__(**kwargs)
        self._init_schema()

    def _init_schema(self):
        schema = """
        CREATE TABLE IF NOT EXISTS session(
            key VARCHAR(256) PRIMARY KEY,
            value TEXT NOT NULL,
            ttl TIMESTAMP DEFAULT NULL
        );
        DROP INDEX IF EXISTS idx_session_ttl;
        CREATE INDEX idx_session_ttl ON session(ttl);

        CREATE OR REPLACE FUNCTION sec2ttl(seconds FLOAT)
        RETURNS TIMESTAMP AS $$
        BEGIN
            IF seconds IS NULL THEN
                RETURN NULL;
            END IF;
            RETURN now() + (seconds || ' SECOND')::INTERVAL;
        END;
        $$ LANGUAGE plpgsql;
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
            return True
        except:
            return False

    def ttl(self, key):
        query = """
        SELECT EXTRACT(SECOND FROM (ttl - now())) AS ttl
          FROM session
         WHERE key = %s
           AND ttl IS NOT NULL;
        """
        with self.connect() as cursor:
            cursor.execute(query, (key,))
            if cursor.rowcount > 0:
                return cursor.fetchone()['ttl']
        return -1

    def expire(self, key, ttl):
        query = """
        UPDATE session SET ttl = sec2ttl(%s) WHERE key = %s;
        """
        with self.connect() as cursor:
            cursor.execute(query, (ttl, key,))

    def set(self, key, value, ttl=None):
        query = """
        WITH upsert AS (
            UPDATE session SET value = %(value)s, ttl = sec2ttl(%(ttl)s)
             WHERE key=%(key)s
            RETURNING *)
        INSERT INTO session (key, value, ttl)
        SELECT %(key)s, %(value)s, sec2ttl(%(ttl)s)
        WHERE NOT EXISTS (SELECT * FROM upsert)
        """
        with self.connect() as cursor:
            cursor.execute(query, dict(key=key, value=value, ttl=ttl))

    def get(self, key):
        purge = "DELETE FROM session WHERE ttl IS NOT NULL AND now() > ttl;"
        query = "SELECT value FROM session WHERE key = %s;"
        with self.connect() as cursor:
            cursor.execute(purge)
            cursor.execute(query, (key,))
            if cursor.rowcount > 0:
                return cursor.fetchone()['value']

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
