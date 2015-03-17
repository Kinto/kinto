from __future__ import absolute_import

import os

from six.moves.urllib import parse as urlparse

from cliquet import logger
from cliquet.storage.postgresql import PostgreSQLClient
from cliquet.session import SessionStorageBase


class PostgreSQL(PostgreSQLClient, SessionStorageBase):
    """Session backend using PostgreSQL.

    Enable in configuration::

        cliquet.session_backend = cliquet.session.postgresql

    Database location URI can be customized::

        cliquet.session_url = postgres://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in ``~/.pgpass`` (*see PostgreSQL documentation*).

    :note:

        During the first run of the application, the tables are created.

        **Alternatively**, the schema can be initialized outside the
        application starting process, using the SQL file located in
        :file:`cliquet/session/postgresql/schema.sql`. This allows to tune
        distinguish schema manipulation privileges from schema usage.

    :note:

        Using a `connection pool <http://pgpool.net>`_ is highly recommended to
        boost performances and bound memory usage (*work_mem per connection*).

    """
    def __init__(self, **kwargs):
        super(PostgreSQL, self).__init__(**kwargs)
        self._init_schema()

    def _init_schema(self):
        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, 'schema.sql')).read()
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
    uri = config.registry.settings['cliquet.session_url']
    uri = urlparse.urlparse(uri)
    conn_kwargs = dict(host=uri.hostname,
                       port=uri.port,
                       user=uri.username,
                       password=uri.password,
                       database=uri.path[1:] if uri.path else '')
    # Filter specified values only, to preserve PostgreSQL defaults
    conn_kwargs = dict([(k, v) for k, v in conn_kwargs.items() if v])

    return PostgreSQL(**conn_kwargs)
