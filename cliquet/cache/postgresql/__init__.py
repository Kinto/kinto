from __future__ import absolute_import

import os

from six.moves.urllib import parse as urlparse

from cliquet import logger
from cliquet.cache import CacheBase
from cliquet.storage.postgresql import PostgreSQLClient
from cliquet.utils import json


class PostgreSQL(PostgreSQLClient, CacheBase):
    """Cache backend using PostgreSQL.

    Enable in configuration::

        cliquet.cache_backend = cliquet.cache.postgresql

    Database location URI can be customized::

        cliquet.cache_url = postgres://user:pass@db.server.lan:5432/dbname

    Alternatively, username and password could also rely on system user ident
    or even specified in :file:`~/.pgpass` (*see PostgreSQL documentation*).

    .. note::

        Some tables and indices are created when ``cliquet migrate`` is run.
        This requires some privileges on the database, or some error will
        be raised.

        **Alternatively**, the schema can be initialized outside the
        python application, using the SQL file located in
        :file:`cliquet/cache/postgresql/schema.sql`. This allows to
        distinguish schema manipulation privileges from schema usage.


    A threaded connection pool is enabled by default::

        cliquet.cache_pool_size = 10

    .. note::

        Using a `dedicated connection pool <http://pgpool.net>`_ is still
        recommended to allow load balancing, replication or limit the number
        of connections used in a multi-process deployment.

    :noindex:
    """

    def __init__(self, **kwargs):
        super(PostgreSQL, self).__init__(**kwargs)

    def initialize_schema(self):
        # Create schema
        here = os.path.abspath(os.path.dirname(__file__))
        schema = open(os.path.join(here, 'schema.sql')).read()
        with self.connect() as cursor:
            cursor.execute(schema)
        logger.info('Created PostgreSQL cache tables')

    def flush(self):
        query = """
        DELETE FROM cache;
        """
        with self.connect() as cursor:
            cursor.execute(query)
        logger.debug('Flushed PostgreSQL cache tables')

    def ttl(self, key):
        query = """
        SELECT EXTRACT(SECOND FROM (ttl - now())) AS ttl
          FROM cache
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
        UPDATE cache SET ttl = sec2ttl(%s) WHERE key = %s;
        """
        with self.connect() as cursor:
            cursor.execute(query, (ttl, key,))

    def set(self, key, value, ttl=None):
        query = """
        WITH upsert AS (
            UPDATE cache SET value = %(value)s, ttl = sec2ttl(%(ttl)s)
             WHERE key=%(key)s
            RETURNING *)
        INSERT INTO cache (key, value, ttl)
        SELECT %(key)s, %(value)s, sec2ttl(%(ttl)s)
        WHERE NOT EXISTS (SELECT * FROM upsert)
        """
        value = json.dumps(value)
        with self.connect() as cursor:
            cursor.execute(query, dict(key=key, value=value, ttl=ttl))

    def get(self, key):
        purge = "DELETE FROM cache WHERE ttl IS NOT NULL AND now() > ttl;"
        query = "SELECT value FROM cache WHERE key = %s;"
        with self.connect() as cursor:
            cursor.execute(purge)
            cursor.execute(query, (key,))
            if cursor.rowcount > 0:
                value = cursor.fetchone()['value']
                return json.loads(value)

    def delete(self, key):
        query = "DELETE FROM cache WHERE key = %s"
        with self.connect() as cursor:
            cursor.execute(query, (key,))


def load_from_config(config):
    settings = config.get_settings()
    uri = settings['cliquet.cache_url']
    uri = urlparse.urlparse(uri)
    pool_size = int(settings['cliquet.cache_pool_size'])

    conn_kwargs = dict(pool_size=pool_size,
                       host=uri.hostname,
                       port=uri.port,
                       user=uri.username,
                       password=uri.password,
                       database=uri.path[1:] if uri.path else '')
    # Filter specified values only, to preserve PostgreSQL defaults
    conn_kwargs = dict([(k, v) for k, v in conn_kwargs.items() if v])

    return PostgreSQL(**conn_kwargs)
